import os
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"
os.environ["FFREPORT"] = "level=quiet"

import cv2
import time
import requests

# Config
STREAM_SOURCE = "http://192.168.253.251:8080/?action=stream"
MOONRAKER_URL = "http://192.168.253.251:7125"
PREFIX = "QRF"
VALID_MATERIALS = [] # If blank, all are valid
COOLDOWN_TIME = 5
LOOP_DELAY = 0.05
ERROR_TIME = 10

# Internal
GCODE = f"{MOONRAKER_URL}/printer/gcode/script"

def main():
    while True:
        try:
            cap = cv2.VideoCapture(STREAM_SOURCE)
        except:
            print(f"Connection failed. Trying again in {ERROR_TIME} seconds.")
            time.sleep(ERROR_TIME)
            continue
        detector = cv2.QRCodeDetector()
        cooldown_expire = time.monotonic()
        last_frame_time = time.monotonic()
        error_expire = time.monotonic() + ERROR_TIME

        while time.monotonic() < error_expire:
            try:
                ret, frame = cap.read()

                if ret:
                    error_expire = time.monotonic() + ERROR_TIME
                    if time.monotonic() > cooldown_expire:
                        data, bbox, _ = detector.detectAndDecode(frame)

                        if bbox is not None and len(bbox) > 0:
                            if data:
                                print(f"QR detected: {data}")
                                if handle_data_found(data):
                                    cooldown_expire = time.monotonic() + COOLDOWN_TIME
            except:
                pass

            time.sleep(LOOP_DELAY)
            
        print(f"{ERROR_TIME} seconds elapsed without successful camera update. Restarting connection.")
        cap.release()

def handle_data_found(data):
    data_split = data.split(':')
    if len(data_split) >= 3:

        # Validation
        if data_split[0] != PREFIX:
            return False
        if len(VALID_MATERIALS) > 0 and data_split[1] not in VALID_MATERIALS:
            return False
        if len(data_split[2]) != 6:
            return False

        material = data_split[1]
        color = data_split[2]

        send_gcode(f'_QRF_HANDLE_FILAMENT_SCAN MATERIAL={material} COLOR={color}')
        return True

    return False

def send_gcode(gcode):
    payload = {"script": gcode}
    print(f"Sending command: {gcode}")
    requests.post(GCODE, json=payload)

main()