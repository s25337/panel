

import threading
import time
import os
import json
from flask import current_app

def periodic_data_terrarium_sender(app):
    import requests
    interval_minutes = 5
    LOCAL_API_URL = "http://localhost:5000/api/dataTerrarium"
    while True:
        for m in range(interval_minutes, 0, -1):
            print(f"[dataTerrarium] Za {m} min wyślę dane do Terrarium...")
            time.sleep(60)
        try:
            # Wywołaj lokalny endpoint API, który sam wyśle dane do Terrarium
            response = requests.post(LOCAL_API_URL, timeout=10)
            print(f"[dataTerrarium] Wywołano lokalny endpoint /api/dataTerrarium: status={response.status_code}")
        except Exception as e:
            print(f"[dataTerrarium] Błąd wywołania lokalnego API: {e}")

def start_periodic_sender(app):
    t = threading.Thread(target=periodic_data_terrarium_sender, args=(app,), daemon=True)
    t.start()
