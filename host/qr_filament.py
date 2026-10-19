import os
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"
os.environ["FFREPORT"] = "level=quiet"

import cv2
import time
import requests
from pathlib import Path

# Config
PREFIX = "QRF"
VALID_MATERIALS = []

# Internal Config
COOLDOWN_TIME = 5
LOOP_DELAY = 0.25
ERROR_TIME = 10

# Consts
GCODE_PATH = "printer/gcode/script"

# Internal Use
VIDEO_SOURCES = []
VIDEO_FEEDS = []
VIDEO_LAST_READ_TIMES = []
PRINTERS = []
PRINTER_COOLDOWN_TIMES = []

def load_config():
    global PREFIX, VALID_MATERIALS
    global VIDEO_SOURCES, VIDEO_FEEDS, VIDEO_LAST_READ_TIMES, PRINTERS, PRINTER_COOLDOWN_TIMES
    global COOLDOWN_TIME, LOOP_DELAY, ERROR_TIME
    
    stream_sources = []
    moonraker_urls = []
    
    if Path('qr_filament.ini').is_file():
        with open('qr_filament.ini', 'r') as f:
            lines = f.readlines()
        for line in lines:
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
        
def setup_all_feeds():
    for i in range(VIDEO_SOURCES):
        setup_feed(i)
    
def setup_feed(index):
    try:
        if VIDEO_FEEDS[index]:
            try:
                VIDEO_FEEDS[index].release()
            except:
                pass
        cap = cv2.VideoCapture(STREAM_SOURCE)
        VIDEO_FEEDS[index] = cap
    except:
        VIDEO_FEEDS[index] = None
    VIDEO_LAST_READ_TIMES[index] = time.monotonic()

def main():
    load_config()
    setup_all_feeds()
    detector = cv2.QRCodeDetector()
    
    while True:
        try:
            detect_results = [None] * len(VIDEO_SOURCES)
            for i in range(len(VIDEO_SOURCES)):
                if VIDEO_SOURCES[i]:
                    ret, frame = VIDEO_SOURCES[i].read()
                    if ret:
                        VIDEO_LAST_READ_TIMES[i] = time.monotonic()
                        data, bbox, _ = detector.detectAndDecode(frame)
                        if bbox is not None and len(bbox) > 0:
                            if data:
                                detect_results[i] = data
                if ERROR_TIME > 0 and time.monotonic() > VIDEO_LAST_READ_TIMES[i] + ERROR_TIME:
                    setup_feed(i)
                    
            for i in range(len(PRINTERS)):
                data = detect_results[PRINTERS[i][0]]
                if data:
                    if time.monotonic() >= PRINTER_COOLDOWN_TIMES[i]:
                        if handle_data_found(data, i):
                            PRINTER_COOLDOWN_TIMES[i] = time.monotonic() + COOLDOWN_TIME
        except:
            pass
                
        time.sleep(LOOP_DELAY)
        
    for source in VIDEO_SOURCES:
        source.release()

def handle_data_found(data, printer_id):
    data_split = data.split(':')
    if len(data_split) >= 3 or (len(data_split) == 2 and not PREFIX):

        # Validation
        if PREFIX and data_split[0] != PREFIX:
            return False
            
        if PREFIX:
            prefix_offset = 1
        else:
            prefix_offset = 0

        material = data_split[prefix_offset + 0]
        color = data_split[prefix_offset + 1]
        
        if len(VALID_MATERIALS) > 0 and material not in VALID_MATERIALS:
            return False
        if len(color) != 6:
            return False

        send_gcode(f'_QRF_HANDLE_FILAMENT_SCAN MATERIAL={material} COLOR={color}', printer_id)
        return True

    return False

def send_gcode(gcode, printer_id):
    payload = {"script": gcode}
    print(f"Sending command: {gcode}")
    return requests.post(PRINTERS[printer_id][1] + GCODE_PATH, json=payload)

main()