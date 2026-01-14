
from flask import Blueprint, jsonify, request, current_app
import json
import os
import requests

BASE_URL = "http://31.11.238.45:8081/terrarium"
ENDPOINT_ADD_MODULE = f"{BASE_URL}/module"
ENDPOINT_SEND_DATA = f"{BASE_URL}/dataTerrarium"
ENDPOINT_UPDATE_SETTING = f"{BASE_URL}/updateSetting"

api_external = Blueprint('api_external', __name__)

@api_external.route('/module', methods=['POST'])
def add_module():
    # TODO: implement payload logic
    return jsonify({"status": "success", "message": "Module added"}), 200

@api_external.route('/dataTerrarium', methods=['POST'])
def send_data_terrarium():
    sensor_history_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data_history.json")
    try:
        with open(sensor_history_file, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Failed to read sensor history: {e}"}), 500

@api_external.route('/updateSetting', methods=['POST'])
def update_setting():
    # Pobierz aktualne ustawienia z lokalnego endpointa sendData
    group_id = "group-A1"
    try:
        local_url = f"http://localhost:5000/sendData/{group_id}"
        local_resp = requests.post(local_url, headers={"Content-Type": "application/json"}, json={})
        if local_resp.status_code != 200:
            return jsonify({"status": "ERROR", "message": f"Local sendData error: {local_resp.text}"}), 500
        mapped = local_resp.json()
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Failed to get local settings: {e}"}), 500

    url = f"{BASE_URL}/updateSetting/{group_id}"

    print("Wysyłany JSON do Terrarium:")
    print(json.dumps(mapped, indent=2))
    print(f"Pełny URL: {url}")

    # Wyślij mapped settings do zewnętrznego serwera
    try:
        response = requests.post(
            url,
            json=mapped,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Odpowiedź serwera Terrarium: status={response.status_code}, body={response.text}")
        if response.status_code == 200:
            return jsonify({"status": "OK", "message": "Settings sent to Terrarium server"})
        else:
            return jsonify({"status": "ERROR", "message": f"Terrarium server error: {response.text}"}), response.status_code
    except Exception as e:
        print(f"Błąd wysyłania do Terrarium: {e}")
        return jsonify({"status": "ERROR", "message": f"Failed to send to Terrarium server: {e}"}), 503




#pobieranie settingu na starcie serwera 
@api_external.route('/sendData/<group_id>', methods=['POST'])
def send_data(group_id):
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    # Pobierz ustawienia z zewnętrznego API Terrarium
    try:
        ext_url = f"{BASE_URL}/sendData/{group_id}"
        ext_resp = requests.post(ext_url, headers={"Content-Type": "application/json"}, json={})
        if ext_resp.status_code != 200:
            return jsonify({"status": "ERROR", "message": f"Terrarium API error: {ext_resp.text}"}), 500
        ext_settings = ext_resp.json()
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Failed to fetch from Terrarium: {e}"}), 500

    # Zmapuj dane z Terrarium na nasz format i zapisz do settings_config.json
    try:
        # Mapowanie odwrotne: dayOfWeek (nazwy) -> watering_days (numery)
        day_map_rev = {
            "MONDAY": 1,
            "TUESDAY": 2,
            "WEDNESDAY": 3,
            "THURSDAY": 4,
            "FRIDAY": 5,
            "SATURDAY": 6,
            "SUNDAY": 7
        }
        new_settings = {
            "setting_id": ext_settings.get("setting_id", "67"),
            "plant_name": ext_settings.get("plant_name", "Unknown"),
            "target_temp": ext_settings.get("optimal_temperature", 0),
            "target_hum": ext_settings.get("optimal_humidity", 0),
            "light_intensity": ext_settings.get("optimal_brightness", 0),
            "start_hour": int(ext_settings.get("light_schedule_start_time", "00:00").split(":")[0]),
            "end_hour": int(ext_settings.get("light_schedule_end_time", "00:00").split(":")[0]),
            "watering_mode": ext_settings.get("watering_mode", "standard"),
            "water_seconds": ext_settings.get("water_amount", 1),
            "watering_days": [day_map_rev.get(day, 1) for day in ext_settings.get("dayOfWeek", [])],
            "watering_time": ext_settings.get("watering_time", "12:00")
        }
        with open(settings_file, 'w') as f:
            json.dump(new_settings, f, indent=2)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Failed to save settings: {e}"}), 500

    return jsonify(new_settings)