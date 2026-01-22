# Webhook do zdalnego podlewania
import requests as ext_requests
import os
import json
from flask import Blueprint, request, jsonify
from flask import current_app

api_webhooks = Blueprint('api_webhooks', __name__)
# Webhook do odbioru ustawień z Terrarium
@api_webhooks.route('/external/settings', methods=['POST'])
def receive_external_settings():
    """
    Webhook endpoint for external Terrarium server to send updated settings
    Receives settings in Terrarium format and updates local settings
    """
    data = request.get_json(force=True)
    print(f"[webhook] Otrzymano settings z Terrarium: {data}")
    # Mapowanie dayOfWeek na watering_days
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
        "setting_id": data.get("setting_id", "0"),
        "plant_name": data.get("plant_name", "Unknown"),
        "target_temp": data.get("optimal_temperature", 0),
        "target_hum": data.get("optimal_humidity", 0),
        "light_intensity": data.get("light_intensity", 0),
        "start_hour": int(data.get("light_schedule_start_time", "00:00").split(":")[0]),
        "end_hour": int(data.get("light_schedule_end_time", "00:00").split(":")[0]),
        "watering_mode": data.get("watering_mode", "standard"),
        "water_seconds": data.get("water_amount", 1),
        "watering_days": [day_map_rev.get(day, 1) for day in data.get("dayOfWeek", [])],
    }
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    try:
        with open(settings_file, 'w') as f:
            json.dump(new_settings, f, indent=2)
        print(f"[webhook] Zaktualizowano settings_config.json: {new_settings}")
        return jsonify({"status": "OK", "saved": new_settings})
    except Exception as e:
        print(f"[webhook] Błąd zapisu settings_config.json: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api_webhooks.route('/external/watering', methods=['POST'])
def external_watering_control():
    """
    Wywołuje lokalny endpoint /api/watering niezależnie od danych wejściowych, might change 
    """
    try:
        resp = ext_requests.post('http://localhost:5001/api/watering') ##5001 nie 5000
        print(f"[webhook] Wywołano /api/watering, status: {resp.status_code}, body: {resp.text}")
        return (resp.text, resp.status_code, resp.headers.items())
    except Exception as e:
        print(f"[webhook] Błąd wywołania /api/watering: {e}")
        return {"status": "ERROR", "message": str(e)}, 500

@api_webhooks.route('/webhook/test', methods=['POST'])
def webhook_test():
    data = request.get_json(force=True)
    print(f"[webhook] Otrzymano dane: {data}")
    return jsonify({"status": "OK", "received": data})

@api_webhooks.route('/external/devices/unregister/<groupId>', methods=['POST'])
def register_device_webhook():
    """
    Webhook endpoint for external Terrarium server to register devices
    Receives user_id and is_registered, updates all devices with these values
    """
    data = request.get_json(force=True)
    print(f"[webhook] Otrzymano rejestrację urządzeń z Terrarium: {data}")
    group_id =  data.get("group_id", None)
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    try:
       devices_info = load_json_secure(devices_info_file)
       if devices_info["light"]["group_id"] == group_id:
          for device in devices_info.items():
               device["user_id"] = None
               device["is_registered"] = False
    except Exception as e:
        print(f"[webhook] Błąd odczytu devices_info.json: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500    
    try:
        save_json_secure(devices_info_file)
        print(f"[webhook] Zaktualizowano wszystkie urządzenia: user_id={user_id}, is_registered={is_registered}")
        return jsonify({"status": "OK", "updated": devices_info})
    except Exception as e:
        print(f"[webhook] Błąd zapisu devices_info.json: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@api_webhooks.route('/external/light', methods=['POST'])
def external_light_control():

    data = request.get_json(force=True)
    print(f"[webhook] Otrzymano kontrolę światła: {data}")
    intensity_value = data.get("intensity", 0)  
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        settings["light_intensity"] = intensity_value
        print(f"[webhook] Ustawiono light_intensity w settings na: {intensity_value}")
        
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
            
        return jsonify({"status": "OK", "intensity": intensity_value})
    except Exception as e:
        print(f"[webhook] Błąd kontroli światła: {e}")
