from src.bluetooth_service import BluetoothService
import threading
from flask import Blueprint, jsonify, request, current_app
import json
import os
bluetooth_thread = None

api_frontend = Blueprint('frontend', __name__, url_prefix='/api')

@api_frontend.route('/bluetooth', methods=['POST'])
def start_bluetooth():
    global bluetooth_thread
    if bluetooth_thread and bluetooth_thread.is_alive():
        return jsonify({'status': 'ok', 'message': 'Bluetooth already running'})
    try:
        devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
        bluetooth_thread = BluetoothService(devices_info_file)
        bluetooth_thread.start()
        return jsonify({'status': 'ok', 'message': 'Bluetooth started'})
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
    devices_info = current_app.config['DEVICES_INFO']
    
    with open(sensor_data_file, 'r') as f:
        sensor_data = json.load(f)
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
    return jsonify({"status": "OK", "settings": settings})

@api_frontend.route("/devices", methods=["GET"])
def get_devices():
    """Get devices info"""
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")
    with open(devices_info_file, 'r') as f:
        devices_info = json.load(f)
    return jsonify(devices_info)




