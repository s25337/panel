
import threading
from src.bluetooth_service import BluetoothService
from datetime import datetime, timedelta, time as dtime
from flask import Blueprint, jsonify, request, current_app
import json
import os

api_frontend = Blueprint('frontend', __name__, url_prefix='/api')

bluetooth_thread = None
bluetooth_event = None


@api_frontend.route('/bluetooth/start', methods=['POST'])
def start_bluetooth():
    global bluetooth_thread, bluetooth_event
    if bluetooth_thread and bluetooth_thread.is_alive():
        return jsonify({'status': 'ok', 'message': 'Bluetooth already running'})
    try:
        devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
        bluetooth_event = threading.Event()
        bluetooth_thread = BluetoothService(devices_info_file, connection_event=bluetooth_event)
        bluetooth_thread.start()
        # Wait for connection event (client connects and sends credentials)
        connected = bluetooth_event.wait(timeout=30)
        if connected:
            return jsonify({'status': 'ok', 'message': 'Bluetooth client connected'})
        else:
            return jsonify({'status': 'error', 'message': 'No client connected within timeout'}), 504
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@api_frontend.route("/sensors", methods=["GET"])
def get_sensors():
    sensor_data_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data.json")
    with open(sensor_data_file, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            data = data[0] if data else {}
    return jsonify(data)

@api_frontend.route("/status", methods=["GET"])
def get_status():
    """Get device states + sensor data"""
    sensor_data_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "sensor_data.json")
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    
    with open(sensor_data_file, 'r') as f:
        sensor_data = json.load(f)
        if isinstance(sensor_data, list):
            sensor_data = sensor_data[0] if sensor_data else {}
    
    with open(devices_info_file, 'r') as f:
        devices_info = json.load(f)
    
    return jsonify({
        "temperature": sensor_data.get("temperature"),
        "humidity": sensor_data.get("humidity"),
        "brightness": sensor_data.get("brightness"),
        "devices": devices_info
    })

@api_frontend.route("/watering", methods=["POST"])
def control_watering():
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    
    # Pobierz świeże dane z pliku
    with open(devices_info_file, 'r') as f:
        devices_info = json.load(f)
    
    # Włącz pompę
    devices_info["pump"]["state"] = "on"
    
    with open(devices_info_file, 'w') as f:
        json.dump(devices_info, f, indent=2)
    
    return jsonify({"status": "OK", "device": "pump", "action": "on"})

@api_frontend.route("/settings", methods=["GET"])
def get_settings():
    """Get settings"""
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    return jsonify(settings)

@api_frontend.route("/settings", methods=["POST"])
def update_settings():
    """Update settings"""
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    data = request.json or {}
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    settings.update(data)
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    # Automatycznie wywołaj endpoint od aktualizacji ustawień w backendzie zuzi
    try:
        from requests import post
        backend_url = "http://localhost:5000/api/updateSetting"
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



