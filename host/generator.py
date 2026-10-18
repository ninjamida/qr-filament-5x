import qrcode
import sys
from PIL import Image, ImageDraw, ImageFont

PREFIX = "QRF"

def main():
    generate_list = []
    box_size = 10
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
                wildcard_materials += ["PLA", "PETG", "SILK", "PLA-CF", "PETG-CF", "ABS", "TPU"]
                wildcard_colors += ["FFFFFF", "FEF043", "DCF478", "0ACC38", "067749", "0C6283", "0DE2A0", "75D9F3", "45A8F9", "2750E0", "46328E", "A03CF7", "F330F9", "D4B0DC", "F95D73", "F72224", "7C4B00", "F98D33", "FDEBD5", "D3C4A3", "AF7836", "898989", "BCBCBC", "161616"]
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

    for material in wildcard_materials:
        for color in wildcard_colors:
            generate_list += [f"{material}:{color}"]

    if font_size <= 0:
        font_size = box_size * 4

    for data in generate_list:
        qr = qrcode.QRCode(box_size=box_size, border=border_size, error_correction=error_correction, version=version)
        qr.add_data(PREFIX + ':' + data)
        qr.make(fit=True)
        img = qr.make_image().convert("RGB")
        split = data.split(':')
        mod_img = add_label_to_image(img, split[0], split[1], font_size)
        mod_img.save(data.replace(':', '-') + '.png')

def add_label_to_image(img, material, color_raw, font_size):
    color = (int(color_raw[0:2], 16), int(color_raw[2:4], 16), int(color_raw[4:6], 16))
    if (color[0] >= 128 or color[1] >= 128 or color[2] >= 128 or (color[0] + color[1] + color[2]) >= 256):
        text_color = (0, 0, 0)
    else:
        text_color = (255, 255, 255)
    if (color[0] >= 48 or color[1] >= 48 or color[2] >= 48 or (color[0] + color[1] + color[2]) >= 96):
        box_outline_color = (0, 0, 0)
    else:
        box_outline_color = (64, 64, 64)

    orig_width, orig_height = img.size
    text_area_height = font_size * 3
    canvas = Image.new("RGB", (orig_width + 12, orig_height + text_area_height + 12), (255, 255, 255))
    canvas.paste(img, (6, 6))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([6, orig_height + 6, orig_width + 6, orig_height + text_area_height + 6], fill=box_outline_color)
    draw.rectangle([12, orig_height + 12, orig_width, orig_height + text_area_height], fill=color)
    font = ImageFont.truetype("arial.ttf", font_size)

    box_text = material + '\n' + '#' + color_raw

    text_bbox = draw.multiline_textbbox((0, 0), box_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (orig_width - text_width) // 2 + 6
    text_y = orig_height + ((text_area_height - text_height) // 3) + 6
    draw.text((text_x, text_y), box_text, fill=text_color, font=font, align="center")

    return canvas

main()