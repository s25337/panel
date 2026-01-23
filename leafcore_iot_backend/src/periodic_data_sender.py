
import requests
import threading
import time
import os
import json
import logging
from flask import current_app
from src.json_manager import load_json_secure, save_json_secure

SERVER_URL = os.getenv('TARGET_IP', '127.0.0.1')
BASE_URL = f"http://{SERVER_URL}:8081/terrarium/dataTerrarium"

def periodic_data_terrarium_sender(app):
    interval_minutes = 5
    while True:
        for m in range(interval_minutes, 0, -1):
            print(f"[dataTerrarium] Za {m} min wyślę dane do Terrarium...")
            time.sleep(60)
        try:
            with app.app_context():
                sensor_history_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data_history.json")
                devices_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
                data = load_json_secure(sensor_history_file)
                devices = load_json_secure(devices_file)
            group_id = devices["light"]["group_id"]
            url = f"{BASE_URL}/{group_id}"
            logging.info(f"{url}")
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
            print(f"[dataTerrarium] Wysłano dane do Terrarium: status={response.status_code}")
        except Exception as e:
            print(f"[dataTerrarium] Błąd wysyłania danych: {e}")

def start_periodic_sender(app):
    t = threading.Thread(target=periodic_data_terrarium_sender, args=(app,), daemon=True)
    t.start()
