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
    # TODO: implement payload logic
    return jsonify({"status": "success", "message": "Data received"}), 200

@api_external.route('/updateSetting', methods=['POST'])
def update_setting():
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Failed to read settings: {e}"}), 500

    day_map = {
        1: "MONDAY",
        2: "TUESDAY",
        3: "WEDNESDAY",
        4: "THURSDAY",
        5: "FRIDAY",
        6: "SATURDAY",
        7: "SUNDAY"
    }
    mapped = {
        "setting_id": settings.get("setting_id", "67"),
        "plant_name": settings.get("plant_name", "Unknown"),
        "optimal_temperature": float(settings.get("target_temp", 0)),
        "optimal_humidity": float(settings.get("target_hum", 0)),
        "optimal_brightness": float(settings.get("light_intensity", 0)),
        "light_schedule_start_time": f"{settings.get('start_hour', 0):02d}:00",
        "light_schedule_end_time": f"{settings.get('end_hour', 0):02d}:00",
        "watering_mode": settings.get("watering_mode", "standard"),
        "water_amount": int(settings.get("water_seconds", 1)),
        "light_intensity": float(settings.get("light_intensity", 0)),
        "DayOfWeek": [day_map.get(day, str(day)) for day in settings.get("watering_days", [])]
    }

    #group_id = mapped["setting_id"]
    url = f"{BASE_URL}/updateSetting/group-A1"

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

