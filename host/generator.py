import qrcode
import sys
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

PREFIX = "QRF"
VALID_MATERIALS = []

def load_config():
    global PREFIX, VALID_MATERIALS
    
    if Path('qr_filament.ini').is_file():
        with open('qr_filament.ini', 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                continue
            split = line.split('=', 1)
            if len(split) < 2:
                continue
                
            keyword = split[0].upper()
            if keyword == 'PREFIX':
                PREFIX = split[1]
                
            if keyword == 'VALID_MATERIALS':
                if len(split[1].strip()) > 0:
                    VALID_MATERIALS = split[1].strip().split(',')

def main():
    load_config()
    
    generate_list = []
    box_size = 5
    border_size = 4
    font_size = -1
    version = None
    error_correction = qrcode.constants.ERROR_CORRECT_M

    stock_mode = False
    wildcard_materials = []
    wildcard_colors = []

    for arg in sys.argv[1:]:
        if arg.startswith('-'):
            if arg.startswith('-boxsize='):
                box_size = int(arg[9:])
            if arg.startswith('-fontsize='):
                font_size = int(arg[10:])
            if arg.startswith('-bordersize='):
                box_size = int(arg[12:])
            if arg.startswith('-version='):
                version = int(arg[9:])
            if arg.startswith('-error_correction='):
                error_correction_id = arg[18]
                if error_correction_id == 'L':
                    error_correction = qrcode.constants.ERROR_CORRECT_L
                elif error_correction_id == 'M':
                    error_correction = qrcode.constants.ERROR_CORRECT_M
                elif error_correction_id == 'Q':
                    error_correction = qrcode.constants.ERROR_CORRECT_Q
                elif error_correction_id == 'H':
                    error_correction = qrcode.constants.ERROR_CORRECT_H
            if arg == '-stock':
                if len(VALID_MATERIALS) == 0:
                    wildcard_materials += ["PLA", "PETG", "SILK", "PLA-CF", "PETG-CF", "ABS", "TPU"]
                else:
                    wildcard_materials += VALID_MATERIALS
                wildcard_colors += [
                    "FFFFFF#White",
                    "FEF043#Bright Yellow",
                    "DCF478#Light Green",
                    "0ACC38#Green",
                    "067749#Dark Green",
                    "0C6283#Cyan",
                    "0DE2A0#Turquoise",
                    "75D9F3#Light Blue",
                    "45A8F9#Blue",
                    "2750E0#Dark Blue",
                    "46328E#Purple",
                    "A03CF7#Bright Purple",
                    "F330F9#Magenta",
                    "D4B0DC#Lilac",
                    "F95D73#Pink",
                    "F72224#Red",
                    "7C4B00#Brown",
                    "F98D33#Orange",
                    "FDEBD5#Beige",
                    "D3C4A3#Light Brown",
                    "AF7836#Terracotta",
                    "898989#Gray",
                    "BCBCBC#Light Gray",
                    "161616#Black"
                    ]
                generate_list = []
                stock_mode = True
                break
            if arg == "-file-materials":
                with open('materials.txt', 'r') as f:
                    wildcard_materials += [line.strip() for line in f.readlines()]
            if arg == "-file-colors":
                with open('colors.txt', 'r') as f:
                    wildcard_colors += [line.strip() for line in f.readlines()]
        elif not stock_mode:
            arg_split = arg.split(':')
            if len(arg_split) < 2:
                continue
            if arg_split[0] == '*':
                if arg_split[1] != '*':
                    wildcard_colors += [arg_split[1]]
            elif arg_split[1] == '*':
                wildcard_materials += [arg_split[0]]
            else:
                generate_list += [arg]
                
    if len(wildcard_materials) == 0:
        wildcard_materials = VALID_MATERIALS

    for material in wildcard_materials:
        for color in wildcard_colors:
            generate_list += [f"{material}:{color}"]

    if font_size <= 0:
        font_size = box_size * 4

    for data in generate_list:
        split = data.split(':')
        qr = qrcode.QRCode(box_size=box_size, border=border_size, error_correction=error_correction, version=version)
        qr.add_data(PREFIX + ':' + split[0] + ':' + split[1][:6])
        qr.make(fit=True)
        img = qr.make_image().convert("RGB")
        mod_img = add_label_to_image(img, split[0], split[1], font_size)
        if len(split[1]) > 6:
            mod_img.save(split[0] + '-' + split[1][7:].replace(' ', '') + '.png')
        else:
            mod_img.save(split[0] + '-' + split[1][:6] + '.png')

def add_label_to_image(img, material, color_raw, font_size):
    color = (int(color_raw[0:2], 16), int(color_raw[2:4], 16), int(color_raw[4:6], 16))
    grayscale = (0.2126 * color[0]) + (0.7152 * color[1]) + (0.0722 * color[2])
    if grayscale >= 128:
        text_color = (0, 0, 0)
    else:
        text_color = (255, 255, 255)
    if grayscale >= 64:
        box_outline_color = (0, 0, 0)
    else:
        box_outline_color = (128, 128, 128)

    orig_width, orig_height = img.size
    text_area_height = font_size * 3
    canvas = Image.new("RGB", (orig_width + 12, orig_height + text_area_height + 12), (255, 255, 255))
    canvas.paste(img, (6, 6))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([6, orig_height + 6, orig_width + 6, orig_height + text_area_height + 6], fill=box_outline_color)
    draw.rectangle([12, orig_height + 12, orig_width, orig_height + text_area_height], fill=color)
    font = ImageFont.truetype("arial.ttf", font_size)

    box_text = material + '\n'
    if len(color_raw) == 6:
        box_text += '#' + color_raw[:6]
    else:
        box_text += color_raw[7:]
    text_bbox = draw.multiline_textbbox((0, 0), box_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (orig_width - text_width) // 2 + 6
    text_y = orig_height + ((text_area_height - text_height) // 3) + 6
    draw.text((text_x, text_y), box_text, fill=text_color, font=font, align="center")

    return canvas

main()