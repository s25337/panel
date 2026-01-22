
import threading
from src.bluetooth_service import BluetoothService
from datetime import datetime, timedelta, time as dtime
from flask import Blueprint, jsonify, request, current_app
import json
import os
import sys
from src.json_manager import load_json_secure, save_json_secure
api_frontend = Blueprint('frontend', __name__, url_prefix='/api')

bluetooth_thread = None


@api_frontend.route('/bluetooth/start', methods=['POST'])
def start_bluetooth():
    global bluetooth_thread
    if bluetooth_thread and bluetooth_thread.is_alive():
        return jsonify({'status': 'ok', 'message': 'Bluetooth already running'})
    
    try:
        devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
        bluetooth_thread = BluetoothService(devices_info_file)
        bluetooth_thread.start()
        return jsonify({'status': 'ok', 'message': 'Bluetooth thread started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_frontend.route("/bluetooth/logs", methods=["GET"])
def get_bluetooth_logs():
    global bluetooth_thread
    if bluetooth_thread and bluetooth_thread.is_alive():
        return jsonify({'status': 'ok', 'logs': bluetooth_thread.getLogs()})
    else:
        return jsonify({'status': 'error', 'message': 'Bluetooth service not running'}), 400
    
@api_frontend.route("/sensors", methods=["GET"])
def get_sensors():
    sensor_data_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data.json")
    data = load_json_secure(sensor_data_file)
    if isinstance(data, list):
      data = data[0] if data else {}
    return jsonify(data)

@api_frontend.route("/status", methods=["GET"])
def get_status():
    """Get device states + sensor data"""
    sensor_data_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data.json")
    devices_info = current_app.config['DEVICES_INFO']
    sensor_data = load_json_secure(sensor_data_file)
    if isinstance(sensor_data, list):
      sensor_data = sensor_data[0] if sensor_data else {}
    
    return jsonify({
        "temperature": sensor_data.get("temperature"),
        "humidity": sensor_data.get("humidity"),
        "brightness": sensor_data.get("brightness"),
        "devices": devices_info
    })

@api_frontend.route("/watering", methods=["POST"])
def control_watering():
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    devices_info = load_json_secure(devices_info_file)
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if parent_dir not in sys.path:
       sys.path.insert(0, parent_dir)
    import app
    # Włącz pompę
    devices_info["pump"]["state"] = "on"
    devices_info["pump"]["manual_trigger"] = True 
    save_json_secure(devices_info_file,devices_info)
    
    return jsonify({"status": "OK", "device": "pump", "action": "on"})

@api_frontend.route("/settings", methods=["GET"])
def get_settings():
    """Get settings"""
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    try:
        settings = load_json_secure(settings_file)
    except Exception as e:
        print("read JSON error")
    return jsonify(settings)

@api_frontend.route("/settings", methods=["POST"])
def update_settings():
    """Update settings"""
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    data = request.json or {}
    try:
        settings = load_json_secure(settings_file)
    except Exception as e:
        print("read JSON error")
    settings.update(data)
    try:
        save_json_secure(settings_file, settings)
    except Exception as e:
        print("read JSON error")

    # Automatycznie wywołaj endpoint od aktualizacji ustawień w backendzie zuzi
    try:
        from requests import post
        backend_url = "http://localhost:5001/api/updateSetting"
        terrarium_response = post(backend_url, headers={"Content-Type": "application/json"}, timeout=5)
        print(f"Wywołano /updateSetting, status: {terrarium_response.status_code}, body: {terrarium_response.text}")
    except Exception as e:
        print(f"Błąd wywołania /updateSetting: {e}")

    return jsonify({"status": "OK", "settings": settings})

@api_frontend.route("/devices", methods=["GET"])
def get_devices():
    """Get devices info"""
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    with open(devices_info_file, 'r') as f:
        devices_info = json.load(f)
    return jsonify(devices_info)

@api_frontend.route("/control/<device>/<state>", methods=["POST"])
def toggle_device(device, state):
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    with open(devices_info_file, 'r') as f:
        devices_info = json.load(f)
        devices_info[device]["state"] = state 
    with open(devices_info_file, 'w') as f:
        json.dump(devices_info, f, indent=2)

## bardzo dlugi useless timer dla frontu idk


@api_frontend.route("/watering-timer", methods=["GET"])
def get_watering_timer():
    """Zwraca czas do najbliższego podlewania (dni, godziny, minuty, sekundy, interval_seconds)"""
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    watering_days = settings.get('watering_days', [])
    watering_time = settings.get('watering_time', '12:00')
    try:
        target_hour, target_minute = map(int, watering_time.split(':'))
    except Exception:
        target_hour, target_minute = 12, 0

    # Zamień dni na pythonowe (1=poniedziałek, 7=niedziela -> 0=poniedziałek, 6=niedziela)
    watering_days_py = [(d-1)%7 for d in watering_days]

    now = datetime.now()
    current_day_py = now.weekday()  # 0=poniedziałek, 6=niedziela
    current_time = now.time()

    # Szukaj najbliższego dnia podlewania
    days_until = None
    for i in range(7):
        check_day = (current_day_py + i) % 7
        if check_day in watering_days_py:
            days_until = i
            break
    if days_until is None:
        return jsonify({"days": 0, "hours": 0, "minutes": 0, "seconds": 0, "interval_seconds": 0})

    # Jeśli to dziś i godzina już minęła, to będzie dopiero za tydzień
    next_watering_date = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if days_until == 0 and current_time > dtime(target_hour, target_minute):
        days_until = 7
    next_watering_date = next_watering_date + timedelta(days=days_until)

    seconds_left = int((next_watering_date - now).total_seconds())
    days = seconds_left // 86400
    hours = (seconds_left % 86400) // 3600
    minutes = (seconds_left % 3600) // 60
    seconds = seconds_left % 60

    return jsonify({
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "interval_seconds": seconds_left
    })



