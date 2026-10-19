import os
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"
os.environ["FFREPORT"] = "level=quiet"

import sys
import cv2
import time
import requests
import traceback
from pathlib import Path

# Consts
GCODE_PATH = "printer/gcode/script"
OUTPUT_LEVEL_SILENT = 0
OUTPUT_LEVEL_EXCEPTION = 1
OUTPUT_LEVEL_BASIC = 2
OUTPUT_LEVEL_FULL = 3
OUTPUT_LEVEL_LOOP = 4

# Config
PREFIX = "QRF"
VALID_MATERIALS = []

# Internal Config
COOLDOWN_TIME = 5
LOOP_DELAY = 0.05
ERROR_TIME = 10
OUTPUT_LEVEL = OUTPUT_LEVEL_BASIC

# Internal Use
VIDEO_SOURCES = []
VIDEO_FEEDS = []
VIDEO_LAST_READ_TIMES = []
PRINTERS = []
PRINTER_COOLDOWN_TIMES = []

def log(message, level = OUTPUT_LEVEL_FULL):
    if OUTPUT_LEVEL >= level:
        print(message)
        
def output_exception(e):
    try:
        e_filename, e_line, e_func, e_text = traceback.extract_tb(e.__traceback__)[-1]
    except:
        e_filename = '??'
        e_line = -1
        e_func = '??'
        e_text = '??'
    log(f'!!! Exception [{str(e)}] occurred in {e_filename}, function {e_func}, line {e_line}', OUTPUT_LEVEL_EXCEPTION)
    log(f'!!! Exception text: {e_text}', OUTPUT_LEVEL_EXCEPTION)

def load_config():
    global PREFIX, VALID_MATERIALS
    global VIDEO_SOURCES, VIDEO_FEEDS, VIDEO_LAST_READ_TIMES, PRINTERS, PRINTER_COOLDOWN_TIMES
    global COOLDOWN_TIME, LOOP_DELAY, ERROR_TIME, OUTPUT_LEVEL
    
    for arg in sys.argv[1:]:
        arg = arg.upper()
        if arg.startswith('-OUTPUT='):
            OUTPUT_LEVEL = int(arg[8:])
            
    log('Loading config', OUTPUT_LEVEL_BASIC)
    
    stream_sources = []
    moonraker_urls = []
    
    if Path('qr_filament.ini').is_file():
        log('  qr_filament.ini found. Loading', OUTPUT_LEVEL_FULL)
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
                    
            if keyword == 'COOLDOWN_TIME':
                COOLDOWN_TIME = int(split[1])
                
            if keyword == 'LOOP_DELAY':
                LOOP_DELAY = int(split[1])
                
            if keyword == 'ERROR_TIME':
                ERROR_TIME = int(split[1])
            
            if keyword.startswith('PRINTER_'):
                keyword_split = keyword.split('_')
                if len(keyword_split) >= 2:
                    if len(keyword_split) == 2:
                        printer_id = 0
                        sub_keyword = keyword_split[1]
                    else:
                        printer_id = int(keyword_split[1])
                        sub_keyword = keyword_split[2]
                        
                    while len(stream_sources) <= printer_id:
                        stream_sources += [None]
                    while len(moonraker_urls) <= printer_id:
                        moonraker_urls += [None]
                    
                    if sub_keyword == 'CAMERA':
                        source = split[1].strip()
                        try:
                            source_int = int(source)
                            source = source_int
                        except:
                            pass
                        stream_sources[printer_id] = source
                    
                    if sub_keyword == 'MOONRAKER':
                        moonraker_urls[printer_id] = split[1].strip()
                        
                    if sub_keyword == 'IP':
                        stream_sources[printer_id] = f'http://{split[1].strip()}:8080/?action=stream'
                        moonraker_urls[printer_id] = f'http://{split[1].strip()}:7125/'
    else:
        stream_sources += ['http://127.0.0.1:8080/?action=stream']
        moonraker_urls += ['http://127.0.0.1:7125/']
                    
    for i in range(len(stream_sources)):
        if not stream_sources[i]:
            moonraker_urls[i] = None
        elif not moonraker_urls[i]:
            stream_sources[i] = None
    
    log(f'  Prefix: {PREFIX}', OUTPUT_LEVEL_FULL)
    log(f'  Valid materials: {', '.join(VALID_MATERIALS)}', OUTPUT_LEVEL_FULL)
    log(f'  Cooldown time: {COOLDOWN_TIME}', OUTPUT_LEVEL_FULL)
    log(f'  Loop delay: {LOOP_DELAY}', OUTPUT_LEVEL_FULL)
    log(f'  Error time: {ERROR_TIME}', OUTPUT_LEVEL_FULL)
    for i in range(len(stream_sources)):
        log(f'  Printer {i} camera: {stream_sources[i]}')
        log(f'  Printer {i} Moonraker: {moonraker_urls[i]}')
                    
    unique_sources = list(set(stream_sources))
    for source in unique_sources:
        if source:
            VIDEO_SOURCES += [source]
            VIDEO_FEEDS += [None]
            VIDEO_LAST_READ_TIMES += [None]
            
    for i in range(len(stream_sources)):
        if not (stream_sources[i] and moonraker_urls[i]):
            continue
        PRINTERS += [(VIDEO_SOURCES.index(stream_sources[i]), moonraker_urls[i])]
        PRINTER_COOLDOWN_TIMES += [time.monotonic()]
        
    log(f'  {len(PRINTERS)} printers loaded', OUTPUT_LEVEL_BASIC)
        
def setup_all_feeds():
    log(f'Setting up video feeds', OUTPUT_LEVEL_BASIC)
    for i in range(len(VIDEO_SOURCES)):
        setup_feed(i)
    
def setup_feed(index):
    try:
        if VIDEO_FEEDS[index]:
            log(f'Resetting video feed {index} ({VIDEO_SOURCES[index]})', OUTPUT_LEVEL_BASIC)
            try:
                VIDEO_FEEDS[index].release()
            except:
                pass
        else:
            log(f'Setting up video feed {index} ({VIDEO_SOURCES[index]})', OUTPUT_LEVEL_FULL)
        cap = cv2.VideoCapture(VIDEO_SOURCES[index])
        VIDEO_FEEDS[index] = cap
    except Exception as e:
        VIDEO_FEEDS[index] = None
        output_exception(e)
    VIDEO_LAST_READ_TIMES[index] = time.monotonic()

def main():
    load_config()
    setup_all_feeds()
    detector = cv2.QRCodeDetector()
    
    log('Beginning main loop', OUTPUT_LEVEL_BASIC)
    
    while True:
        try:
            detect_results = [None] * len(VIDEO_SOURCES)
            for i in range(len(VIDEO_SOURCES)):
                if VIDEO_FEEDS[i]:
                    log(f'Updating video source {i}', OUTPUT_LEVEL_LOOP)
                    ret, frame = VIDEO_FEEDS[i].read()
                    if ret:
                        log(f'Frame retrieved successfully', OUTPUT_LEVEL_LOOP)
                        VIDEO_LAST_READ_TIMES[i] = time.monotonic()
                        data, bbox, _ = detector.detectAndDecode(frame)
                        if bbox is not None and len(bbox) > 0:
                            if data:
                                log(f'QR detected on source {i}: "{data}"', OUTPUT_LEVEL_BASIC)
                                detect_results[i] = data
                if ERROR_TIME > 0 and time.monotonic() > VIDEO_LAST_READ_TIMES[i] + ERROR_TIME:
                    setup_feed(i)
                    
            for i in range(len(PRINTERS)):
                log(f'Updating printer {i}', OUTPUT_LEVEL_LOOP)
                data = detect_results[PRINTERS[i][0]]
                if data:
                    if time.monotonic() >= PRINTER_COOLDOWN_TIMES[i]:
                        log(f'QR detected for printer {i}', OUTPUT_LEVEL_FULL)
                        if handle_data_found(data, i):
                            PRINTER_COOLDOWN_TIMES[i] = time.monotonic() + COOLDOWN_TIME
        except Exception as e:
            output_exception(e)
                
        time.sleep(LOOP_DELAY)
        
    log('Loop terminated. Releasing video sources.', OUTPUT_LEVEL_BASIC)
    for source in VIDEO_SOURCES:
        source.release()

def handle_data_found(data, printer_id):
    log('  Processing QR code contents', OUTPUT_LEVEL_FULL)
    data_split = data.split(':')
    if len(data_split) >= 3 or (len(data_split) == 2 and not PREFIX):

        # Validation
        if PREFIX and data_split[0] != PREFIX:
            log('  QR rejected - prefix mismatch', OUTPUT_LEVEL_BASIC)
            return False
            
        if PREFIX:
            prefix_offset = 1
        else:
            prefix_offset = 0

        material = data_split[prefix_offset + 0]
        color = data_split[prefix_offset + 1]
        
        if len(VALID_MATERIALS) > 0 and material not in VALID_MATERIALS:
            log('  QR rejected - {material} not listed as valid', OUTPUT_LEVEL_BASIC)
            return False
        if len(color) != 6:
            log('  QR rejected - color length wrong', OUTPUT_LEVEL_BASIC)
            return False

        log('  QR accepted. Sending to printer.', OUTPUT_LEVEL_FULL)
        send_gcode(f'_QRF_HANDLE_FILAMENT_SCAN MATERIAL={material} COLOR={color}', printer_id)
        return True
    else:
        log('  QR rejected - insufficient elements', OUTPUT_LEVEL_BASIC)
        return False

def send_gcode(gcode, printer_id):
    payload = {"script": gcode}
    log(f"Sending command: {gcode}", OUTPUT_LEVEL_FULL)
    return requests.post(PRINTERS[printer_id][1] + GCODE_PATH, json=payload)

main()