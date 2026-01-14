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
        resp = ext_requests.post('http://localhost:5000/api/watering')
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
