# src/api/routes.py
"""
Flask API routes
"""
from flask import Blueprint, jsonify, request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.devices import DeviceManager
    from src.services import SettingsService, ControlService, SensorService, SyncService, SensorReadingService


def create_api_routes(device_manager: 'DeviceManager',
                      settings_service: 'SettingsService',
                      control_service: 'ControlService',
                      sensor_service: 'SensorService',
                      sync_service: 'SyncService' = None,
                      sensor_reading_service: 'SensorReadingService' = None) -> Blueprint:
    """Create API routes with dependency injection"""
    
    api = Blueprint('api', __name__, url_prefix='/api')

    # ========== SENSORS ==========
    
    @api.route('/sensors', methods=['GET'])
    def get_sensors():
        """
        Get current sensor readings from cache
        ⚠️ IMPORTANT: Reads from SensorReadingService (updated every 2s background thread)
        This ensures consistent readings across all endpoints
        """
        data = sensor_service.refresh_all()
        return jsonify(data)

    # ========== STATUS ==========
    
    @api.route('/status', methods=['GET'])
    def get_status():
        """Get status of all devices and sensors"""
        is_manual = settings_service.is_manual_mode()
        
        if is_manual:
            # Manual mode - return manual settings WITHOUT applying any auto control
            manual = settings_service.get_manual_settings()
            return jsonify({
                "fan": manual.get("fan", False),
                "light": manual.get("light", 0),  # Return light intensity from manual settings
                "pump": manual.get("pump", False),
                "heater": manual.get("heater", False),
                "sprinkler": manual.get("sprinkler", False),
                "manual_mode": True
            })
        
        # Auto mode - apply control logic
        temp, hum = sensor_service.get_temperature_humidity()
        light_sensor = sensor_service.get_light_intensity()
        
        # Apply auto control
        control_service.control_fan_auto(hum)
        control_service.control_light_auto(light_sensor)
        
        return jsonify({
            **control_service.get_device_states(),
            "manual_mode": False,
            "temperature": temp,
            "humidity": hum,
            "light_sensor": light_sensor
        })

    # ========== CONTROL DEVICES ==========
    
    @api.route('/control', methods=['POST'])
    def control_devices():
        """Control devices via JSON"""
        data = request.json or {}
        
        for device, state in data.items():
            control_service.set_device(device, state)
        
        return jsonify({"status": "OK"})

    @api.route('/control/<device>/<state>', methods=['POST'])
    def control_device(device, state):
        """Control single device"""
        # Parse state
        if state.lower() in ['on', 'true', '1']:
            parsed_state = True
        elif state.lower() in ['off', 'false', '0']:
            parsed_state = False
        else:
            try:
                parsed_state = float(state)
            except ValueError:
                return jsonify({"error": "Invalid state"}), 400
        
        if not control_service.set_device(device, parsed_state):
            return jsonify({"error": f"Unknown device: {device}"}), 400
        
        # Save to manual settings
        manual = settings_service.get_manual_settings()
        if device in manual:
            manual[device] = parsed_state
            settings_service.update_manual_settings(manual)
        
        return jsonify({"status": "OK", "device": device, "state": state})

    # ========== SETTINGS ==========
    
    @api.route('/settings', methods=['GET'])
    def get_settings():
        """Get current settings"""
        return jsonify(settings_service.get_settings())

    @api.route('/settings', methods=['POST'])
    def update_settings():
        """Update settings"""
        data = request.json or {}
        updated = settings_service.update_settings(data)
        return jsonify({"status": "OK", "settings": updated})

    @api.route('/settings/<key>', methods=['GET'])
    def get_setting(key):
        """Get specific setting"""
        value = settings_service.get_setting(key)
        if value is None:
            return jsonify({"error": f"Setting not found: {key}"}), 404
        return jsonify({key: value})

    @api.route('/settings/<key>', methods=['POST'])
    def set_setting(key):
        """Set specific setting"""
        data = request.json or {}
        if 'value' not in data:
            return jsonify({"error": "Missing 'value' field"}), 400
        
        settings_service.set_setting(key, data['value'])
        return jsonify({"status": "OK", key: data['value']})

    # ========== MANUAL SETTINGS ==========
    
    @api.route('/manual-settings', methods=['GET'])
    def get_manual_settings():
        """Get manual settings with current device states"""
        manual = settings_service.get_manual_settings()
        # Return actual device states from device manager
        if settings_service.is_manual_mode():
            # In manual mode, return actual device states
            return jsonify({
                **control_service.get_device_states(),
                "is_manual": True
            })
        else:
            # In auto mode, return the stored manual settings
            return jsonify(manual)

    @api.route('/manual-settings', methods=['POST'])
    def update_manual_settings():
        """Update manual settings"""
        data = request.json or {}
        updated = settings_service.update_manual_settings(data)
        return jsonify({"status": "OK", "settings": updated})

    @api.route('/manual-mode/<state>', methods=['POST'])
    def set_manual_mode(state):
        """Toggle manual mode on/off"""
        is_manual = state.lower() in ['on', 'true', '1']
        settings_service.set_manual_setting('is_manual', is_manual)
        return jsonify({"status": "OK", "manual_mode": is_manual})

    # ========== WATERING TIMER ==========
    
    @api.route('/watering-timer', methods=['GET'])
    def get_watering_timer():
        """Get watering schedule info"""
        interval_seconds = control_service.get_watering_interval()
        water_times = settings_service.get_setting("water_times", 3)
        time_remaining = control_service.format_time_remaining(interval_seconds)
        
        return jsonify({
            "interval_seconds": interval_seconds,
            **time_remaining,
            "water_times_per_week": water_times
        })

    # ========== LIGHT SCHEDULE ==========
    
    @api.route('/light-schedule', methods=['GET'])
    def get_light_schedule():
        """Get light on/off schedule"""
        schedule = control_service.get_light_schedule()
        return jsonify(schedule)

    # ========== DEVICE STATES ==========
    
    @api.route('/devices', methods=['GET'])
    def get_devices():
        """Get all device states"""
        return jsonify(control_service.get_device_states())

    @api.route('/devices/<device>', methods=['GET'])
    def get_device(device):
        """Get specific device state"""
        state = control_service.get_device_state(device)
        if state is None:
            return jsonify({"error": f"Unknown device: {device}"}), 404
        return jsonify({device: state})

    # ========== SYNC WITH EXTERNAL SERVER ==========
    
    @api.route('/sync/fetch', methods=['POST'])
    def sync_fetch_external():
        """Fetch settings from external server and update local settings"""
        if not sync_service:
            return jsonify({"error": "Sync service not initialized"}), 503
        
        success = sync_service.sync_external_to_local()
        if success:
            return jsonify({
                "status": "OK",
                "message": "Settings synced from external server",
                "settings": settings_service.get_settings()
            })
        else:
            return jsonify({
                "status": "ERROR",
                "message": "Failed to fetch from external server"
            }), 503
    
    @api.route('/sync/push', methods=['POST'])
    def sync_push_to_external():
        """Push local settings to external server and add to queue if offline"""
        if not sync_service:
            return jsonify({"error": "Sync service not initialized"}), 503
        
        data = request.json or {}
        local_settings = settings_service.get_settings()
        local_settings.update(data)
        
        # Try to send immediately
        success = sync_service.send_to_external(local_settings)
        
        # Also queue the change for later if offline
        sync_service.add_change_to_queue(local_settings)
        
        return jsonify({
            "status": "OK" if success else "QUEUED",
            "message": "Settings pushed" if success else "Settings queued (offline)",
            "settings": local_settings
        })
    
    @api.route('/sync/status', methods=['GET'])
    def sync_status():
        """Get sync status"""
        if not sync_service:
            return jsonify({"error": "Sync service not initialized"}), 503
        
        return jsonify({
            "running": sync_service.running,
            "last_sync": sync_service.last_sync.isoformat() if sync_service.last_sync else None,
            "sync_interval": sync_service.sync_interval,
            "queue_size": sync_service.change_queue.qsize()
        })

    # ========== DEVICE CONTROL (from gpio_manager) ==========
    
    @api.route('/device-control', methods=['POST'])
    def device_control():
        """Control individual device (on/off or intensity)"""
        data = request.json or {}
        component = data.get("component")
        action = data.get("action")  # "on"/"off" or intensity value
        
        if not component:
            return jsonify({"error": "Missing component"}), 400
        
        try:
            if component == "light":
                # Light control with intensity
                intensity = data.get("intensity")
                if intensity is not None:
                    intensity = float(intensity)
                    control_service.set_device("light", intensity)
                else:
                    # Toggle based on action
                    current = device_manager.get_light_state()
                    control_service.set_device("light", 100.0 if action == "on" else 0.0)
            else:
                # Binary devices
                state = action == "on"
                control_service.set_device(component, state)
            
            states = control_service.get_device_states()
            return jsonify({
                "state": "success",
                "current_states": states,
                "component": component
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @api.route('/device-mode-edit', methods=['POST'])
    def device_mode_edit():
        """Change device mode (auto/manual)"""
        data = request.json or {}
        component = data.get("type")  # device type
        mode = data.get("mode")  # "auto" or "manual"
        state = data.get("state")  # for manual mode: desired state
        
        if not component or not mode:
            return jsonify({"error": "Missing component or mode"}), 400
        
        try:
            # Set the mode
            control_service.set_device_mode(component, mode)
            
            # If manual mode with a state, apply it
            if mode == "manual" and state is not None:
                if component == "light":
                    intensity = data.get("intensity")
                    control_service.set_device("light", intensity or 0.0)
                else:
                    control_service.set_device(component, state)
            
            modes = control_service.get_device_modes()
            states = control_service.get_device_states()
            
            return jsonify({
                "state": "success",
                "current_mode": modes.get(component, {}).get("mode"),
                "current_state": states.get(component),
                "component": component
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @api.route('/device-state', methods=['GET'])
    def device_state():
        """Get state of all devices"""
        states = control_service.get_device_states()
        modes = control_service.get_device_modes()
        
        return jsonify({
            "states": states,
            "modes": modes
        })

    # ========== SENSOR READING SERVICE ENDPOINTS ==========
    
    @api.route('/sensor-reading/device-info', methods=['GET'])
    def get_device_info():
        """Get device information"""
        if not sensor_reading_service:
            return jsonify({"error": "Sensor reading service not available"}), 503
        
        return jsonify(sensor_reading_service.get_device_info())
    
    @api.route('/sensor-reading/device-info', methods=['POST'])
    def set_device_info():
        """Update device information"""
        if not sensor_reading_service:
            return jsonify({"error": "Sensor reading service not available"}), 503
        
        data = request.get_json()
        sensor_reading_service.save_device_info(data)
        return jsonify({"status": "ok"})
    
    @api.route('/sensor-reading/current', methods=['GET'])
    def get_current_sensor_data():
        """Get current sensor readings from cache"""
        if not sensor_reading_service:
            return jsonify({"error": "Sensor reading service not available"}), 503
        
        return jsonify(sensor_reading_service.get_sensor_data())

    return api
