# src/api/routes.py
"""
Flask API routes
"""
from flask import Blueprint, jsonify, request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.devices import DeviceManager
    from src.services import SettingsService, ControlService, SensorService, SensorReadingService, ExternalTerriumService


def create_api_routes(device_manager: 'DeviceManager',
                      settings_service: 'SettingsService',
                      control_service: 'ControlService',
                      sensor_service: 'SensorService',
                      sensor_reading_service: 'SensorReadingService' = None,
                      external_terrarium_service: 'ExternalTerriumService' = None,
                      bluetooth_service: 'BluetoothService' = None) -> Blueprint:
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
        
        # Apply auto control for all devices based on current sensor readings
        control_service.update_auto_devices(temp, hum, light_sensor)
        
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
        """Update settings and send to external server"""
        data = request.json or {}
        updated = settings_service.update_settings(data)
        
        # Auto-send to external Terrarium server
        if external_terrarium_service:
            try:
                result = external_terrarium_service.send_settings(updated)
                print(f"✓ Settings sent to external server: {result}")
            except Exception as e:
                import logging
                logging.warning(f"Failed to send settings to external server: {e}")
                print(f"✗ Failed to send: {e}")
        else:
            print("⚠ External terrarium service not initialized")
        
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
        """Set specific setting and send to external server"""
        data = request.json or {}
        if 'value' not in data:
            return jsonify({"error": "Missing 'value' field"}), 400
        
        settings_service.set_setting(key, data['value'])
        updated = settings_service.get_all_settings()
        
        # Auto-send to external Terrarium server
        if external_terrarium_service:
            try:
                result = external_terrarium_service.send_settings(updated)
                print(f"✓ Settings sent to external server: {result}")
            except Exception as e:
                import logging
                logging.warning(f"Failed to send settings to external server: {e}")
                print(f"✗ Failed to send: {e}")
        else:
            print("⚠ External terrarium service not initialized")
        
        return jsonify({"status": "OK", key: data['value']})

    @api.route('/watering-days', methods=['GET'])
    def get_watering_days():
        """Get watering days list"""
        days = settings_service.get_setting("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        return jsonify({"watering_days": days})

    @api.route('/watering-days', methods=['POST'])
    def update_watering_days():
        """Update watering days list"""
        data = request.json or {}
        days = data.get('watering_days', [])
        
        # Validate days
        valid_days = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"}
        invalid = [d for d in days if d not in valid_days]
        
        if invalid:
            return jsonify({"error": f"Invalid days: {invalid}"}), 400
        
        settings_service.set_setting("watering_days", days)
        return jsonify({"status": "OK", "watering_days": days})

    # ========== MANUAL SETTINGS ==========
    
    @api.route('/manual-settings', methods=['GET'])
    def get_manual_settings():
        """Get manual settings with current device states"""
        # Always return actual device states from device manager (for auto-mode GPIO automation)
        return jsonify(control_service.get_device_states())

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
        """Get next watering time based on watering_days schedule"""
        # Get next watering time (exact time with days, hours, minutes, seconds)
        next_watering = control_service.get_next_watering_time()
        
        # Also get watering days for UI display
        watering_days = settings_service.get_setting("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        
        return jsonify({
            "days": next_watering["days"],
            "hours": next_watering["hours"],
            "minutes": next_watering["minutes"],
            "seconds": next_watering["seconds"],
            "watering_days": watering_days,
            "next_watering_at": "12:00"
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

    # ========== EXTERNAL TERRARIUM SERVER ==========
    
    @api.route('/terrarium/send', methods=['POST'])
    def send_to_terrarium():
        """Send current settings to external Terrarium server (172.19.14.15:8081)"""
        if not external_terrarium_service:
            return jsonify({"error": "Terrarium service not initialized"}), 503
        
        success = external_terrarium_service.send_current_settings()
        
        if success:
            return jsonify({
                "status": "OK",
                "message": "Settings sent to Terrarium server"
            })
        else:
            return jsonify({
                "status": "ERROR",
                "message": "Failed to send to Terrarium server"
            }), 503

    # ========== MODULES - PAIRING ==========
    
    @api.route('/modules/pair', methods=['POST'])
    def pair_modules():
        """
        Start Bluetooth pairing for Wi-Fi configuration.
        Flow:
        1. Start BLE advertising server to wait for Wi-Fi configuration from phone
        2. Phone sends SSID + Password via Bluetooth
        3. Orange Pi connects to Wi-Fi
        4. After Wi-Fi connection → automatically sends devices_info to cloud
        """
        if not bluetooth_service:
            return jsonify({
                "status": "ERROR",
                "message": "Bluetooth service not available"
            }), 503
        
        try:
            # Start Bluetooth pairing - will handle Wi-Fi connection and cloud registration
            started = bluetooth_service.start()
            
            if not started:
                return jsonify({
                    "status": "ERROR",
                    "message": "Failed to start Bluetooth service. Check if bluezero is installed."
                }), 500
            
            return jsonify({
                "status": "OK",
                "message": "Bluetooth pairing started. Waiting for Wi-Fi configuration from phone...",
                "waiting_for": "SSID + Password via BLE"
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "ERROR",
                "message": f"Failed to start Bluetooth pairing: {str(e)}"
            }), 500
    
    @api.route('/modules', methods=['GET'])
    def get_modules():
        """
        Get all paired/registered modules from devices_info.json
        """
        try:
            import os
            import json
            
            devices_info_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'source_files',
                'devices_info.json'
            )
            
            if not os.path.exists(devices_info_path):
                return jsonify({
                    "status": "ERROR",
                    "message": "devices_info.json not found"
                }), 404
            
            with open(devices_info_path, 'r') as f:
                devices_info = json.load(f)
            
            # Count registered modules
            registered = sum(1 for d in devices_info.values() if d.get("is_registered") == 1)
            total = len(devices_info)
            
            return jsonify({
                "modules": devices_info,
                "registered_count": registered,
                "total_count": total
            }), 200
        
        except Exception as e:
            return jsonify({
                "status": "ERROR",
                "message": str(e)
            }), 500

    # ========== HISTORY ==========

    # ========== EXTERNAL SERVER WEBHOOK ==========
    
    @api.route('/external/settings', methods=['POST'])
    def receive_external_settings():
        """
        Webhook endpoint for external Terrarium server to send updated settings
        Receives settings in Terrarium format and updates local settings
        
        Expected JSON format (from Terrarium server):
        {
            "setting_id": "123",
            "plant_name": "Monstera",
            "optimal_temperature": 24.5,
            "optimal_humidity": 65.0,
            "light_intensity": 80.0,
            "light_schedule_start_time": "08:00",
            "light_schedule_end_time": "18:00",
            "watering_mode": "auto",
            "water_amount": 30,
            "dayOfWeek": ["MONDAY", "WEDNESDAY", "FRIDAY"]
        }
        """
        try:
            data = request.json or {}
            
            if not data:
                return jsonify({
                    "status": "ERROR",
                    "message": "No data provided"
                }), 400
            
            # Map Terrarium format to local format
            local_settings = {}
            
            # Direct mappings
            if "setting_id" in data:
                local_settings["setting_id"] = str(data["setting_id"])
            
            if "plant_name" in data:
                local_settings["plant_name"] = data["plant_name"]
            
            if "optimal_temperature" in data:
                local_settings["target_temp"] = float(data["optimal_temperature"])
            
            if "optimal_humidity" in data:
                local_settings["target_hum"] = float(data["optimal_humidity"])
            
            if "light_intensity" in data:
                local_settings["light_intensity"] = float(data["light_intensity"])
            
            if "watering_mode" in data:
                local_settings["watering_mode"] = data["watering_mode"]
            
            if "water_amount" in data:
                local_settings["water_seconds"] = int(data["water_amount"])
            
            # Parse time strings (HH:MM format)
            if "light_schedule_start_time" in data:
                try:
                    start_time = str(data["light_schedule_start_time"])
                    start_hour = int(start_time.split(":")[0])
                    local_settings["start_hour"] = start_hour
                except (ValueError, IndexError) as e:
                    pass  # Skip on parse error
            
            if "light_schedule_end_time" in data:
                try:
                    end_time = str(data["light_schedule_end_time"])
                    end_hour = int(end_time.split(":")[0])
                    local_settings["end_hour"] = end_hour
                except (ValueError, IndexError) as e:
                    pass  # Skip on parse error
            
            # Map dayOfWeek array
            if "dayOfWeek" in data:
                days = data["dayOfWeek"]
                if isinstance(days, list):
                    local_settings["watering_days"] = days
            
            # Update local settings
            if local_settings:
                updated = settings_service.update_settings(local_settings)
                return jsonify({
                    "status": "OK",
                    "message": f"Updated {len(local_settings)} settings",
                    "updated_settings": list(local_settings.keys())
                }), 200
            else:
                return jsonify({
                    "status": "WARNING",
                    "message": "No valid settings to update"
                }), 200
        
        except Exception as e:
            import logging
            logging.error(f"Error in /api/external/settings: {e}")
            return jsonify({
                "status": "ERROR",
                "message": str(e)
            }), 500

    # ========== EXTERNAL WATERING CONTROL ==========
    
    @api.route('/external/watering', methods=['POST'])
    def external_watering_control():
        """
        Webhook endpoint for external server to control watering
        
        Expected JSON format:
        {
            "component": "pump",
            "action": "on",
            "duration": 5
        }
        
        Or array format:
        ["pump", "on", 5]
        """
        try:
            data = request.json or {}
            
            # Handle array format ["pump", "on", 5]
            if isinstance(data, list) and len(data) >= 3:
                component = data[0]
                action = data[1]
                duration = data[2]
            # Handle dict format
            elif isinstance(data, dict):
                component = data.get("component", "").lower()
                action = data.get("action", "").lower()
                duration = int(data.get("duration", 0))
            else:
                return jsonify({
                    "status": "ERROR",
                    "message": "Invalid format. Use {component, action, duration} or [component, action, duration]"
                }), 400
            
            # Validate inputs
            if not component or not action:
                return jsonify({
                    "status": "ERROR",
                    "message": "component and action are required"
                }), 400
            
            valid_components = ["pump", "sprinkler", "fan", "heater", "light"]
            valid_actions = ["on", "off"]
            
            if component not in valid_components:
                return jsonify({
                    "status": "ERROR",
                    "message": f"Invalid component. Valid: {valid_components}"
                }), 400
            
            if action not in valid_actions:
                return jsonify({
                    "status": "ERROR",
                    "message": f"Invalid action. Valid: {valid_actions}"
                }), 400
            
            # Control the device
            try:
                control_service.set_device(component, action == "on")
            except Exception as e:
                return jsonify({
                    "status": "ERROR",
                    "message": f"Failed to control device: {str(e)}"
                }), 500
            
            # If duration specified and action is "on", turn off after duration
            if duration > 0 and action == "on":
                import threading
                def auto_off():
                    import time
                    time.sleep(duration)
                    try:
                        control_service.set_device(component, False)
                    except Exception as e:
                        logging.error(f"Error auto-turning off {component}: {e}")
                
                thread = threading.Thread(target=auto_off, daemon=True)
                thread.start()
            
            return jsonify({
                "status": "OK",
                "message": f"{component} turned {action} for {duration}s" if duration > 0 else f"{component} turned {action}",
                "component": component,
                "action": action,
                "duration": duration
            }), 200
        
        except Exception as e:
            import logging
            logging.error(f"Error in /api/external/watering: {e}")
            return jsonify({
                "status": "ERROR",
                "message": str(e)
            }), 500
    
    return api
