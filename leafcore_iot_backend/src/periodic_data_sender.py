
import requests
import threading
import time
import os
import json
from flask import current_app

BASE_URL = "http://31.11.238.45:8081/terrarium/dataTerrarium/group-A1"

def periodic_data_terrarium_sender(app):
    interval_minutes = 5
    while True:
        for m in range(interval_minutes, 0, -1):
            print(f"[dataTerrarium] Za {m} min wyślę dane do Terrarium...")
            time.sleep(60)
        try:
            with app.app_context():
                sensor_history_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data_history.json")
                with open(sensor_history_file, 'r') as f:
                    data = json.load(f)
            url = f"{BASE_URL}"
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
            print(f"[dataTerrarium] Wysłano dane do Terrarium: status={response.status_code}")
        except Exception as e:
            print(f"[dataTerrarium] Błąd wysyłania danych: {e}")

def start_periodic_sender(app):
    t = threading.Thread(target=periodic_data_terrarium_sender, args=(app,), daemon=True)
    t.start()
