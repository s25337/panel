# Webhook do zdalnego podlewania
import requests as ext_requests
import os
import json
import logging
from flask import Blueprint, request, jsonify
from flask import current_app
from src.json_manager import load_json_secure, save_json_secure

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
        save_json_secure(settings_file,new_settings)
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
        resp = ext_requests.post('http://localhost:5001/api/watering')
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

@api_webhooks.route('/external/devices/unregistered', methods=['POST'])
def register_device_webhook():
    """
    Webhook endpoint for external Terrarium server to register devices
    """
    try:
        data = request.get_json(force=True)
        print(f"[webhook] Otrzymano rejestrację urządzeń z Terrarium: {data}")
        
        group_id = data.get("groupId")
        
        if not group_id:
             return jsonify({"status": "ERROR", "message": "No group_id provided"}), 400

        devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
        devices_info = load_json_secure(devices_info_file)
        
        updates_made = False

        for name, device_data in devices_info.items():
            # Skip non-dictionary items (like timestamps)
            if not isinstance(device_data, dict):
                continue
            
            if str(device_data.get("group_id")) == str(group_id):
                device_data["user_id"] = None
                device_data["is_registered"] = False
                updates_made = True

        if updates_made:
            save_json_secure(devices_info_file, devices_info)
            print(f"[webhook] Unregistered devices for group {group_id}")
            return jsonify({"status": "OK", "updated": devices_info})
        else:
            print(f"[webhook] No matching group_id found: {group_id}")
            return jsonify({"status": "OK", "message": "No devices found for this group"}), 200

    except Exception as e:
        print(f"[webhook] Error: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500
    
@api_webhooks.route('/external/light', methods=['POST'])
def external_light_control():

    data = request.get_json(force=True)
    print(f"[webhook] Otrzymano kontrolę światła: {data}")
    intensity_value = data.get("intensity", 0)  
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    try:
        settings = load_json_secure(settings_file)
        settings["light_intensity"] = intensity_value
        print(f"[webhook] Ustawiono light_intensity w settings na: {intensity_value}")
        save_json_secure(settings_file,settings)
            
        return jsonify({"status": "OK", "intensity": intensity_value})
    except Exception as e:
        print(f"[webhook] Błąd kontroli światła: {e}")
