"""
API External Server Routes
Endpoints dla zewnętrznego serwera
"""
from flask import Blueprint, jsonify, request
import json
import os

api_external = Blueprint('external', __name__)


@api_external.route('/device-control', methods=['POST'])
def update_device():
    """Legacy endpoint for device control from external server"""
    data = request.json or {}
    component = data.get("component")
    action = data.get("action")
    devices_info = current_app.config['DEVICES_INFO']
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")

    if component not in devices_info:
        return jsonify({"error": "Invalid component"}), 400

    if component == "light":
        intensity = data.get("intensity")
        devices_info["light"]["state"] = action
        if intensity is not None:
            devices_info[component]["intensity"] = max(0.0, min(1.0, float(intensity)))
    else:
        devices_info[component]["state"] = action

    with open(devices_info_file, 'w') as f:
        json.dump(devices_info, f, indent=2)

    return jsonify({"state": "success", "current_state": devices_info[component]})


@api_external.route('/device-mode-edit', methods=['POST'])
def device_mode_edit():
    """Change device mode (auto/manual)"""
    data = request.json or {}
    component = data.get("type")
    mode = data.get("mode")
    state = data.get("state")
    devices_info = current_app.config['DEVICES_INFO']
    devices_info_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "devices_info.json")

    if component not in devices_info:
        return jsonify({"error": "Invalid component"}), 400

    devices_info[component]["mode"] = mode
    devices_info[component]["state"] = state
    
    if component == "light":
        intensity = data.get("intensity")
        if intensity is not None:
            devices_info[component]["intensity"] = max(0.0, min(1.0, float(intensity)))
    
    with open(devices_info_file, 'w') as f:
        json.dump(devices_info, f, indent=2)

    return jsonify({
        "state": "success",
        "current_mode": devices_info[component]["mode"],
        "current_state": devices_info[component]["state"]
    })


@api_external.route('/device-state', methods=['GET'])
def get_device_state():
    """Get all device states"""
    return jsonify(current_app.config['DEVICES_INFO'])


@api_external.route('/current-setting', methods=['POST'])
def receive_settings():
    """External server sends settings to update"""
    import datetime
    data = request.json or {}
    settings_file = os.path.join(current_app.config['CURRENT_DIR'], "source_files", "settings_config.json")
    
    with open(settings_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return jsonify({
        "status": "success",
        "message": "Settings received and updated"
    }), 200
