import time
import threading
import datetime
import json
import os

try:
    import gpiod
    from gpiod.line import Direction, Value
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("gpiod not available, GPIO control disabled")

from flask import Flask, request, jsonify
import config
import requests

app = Flask(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
sensor_data_file = os.path.join(current_dir, "source_files", "sensor_data.json")
settings_file = os.path.join(current_dir, "source_files", "current_setting.json")
devices_info_file = os.path.join(current_dir, "source_files", "devices_info.json")
server_url = "http://33.11.238.45:8081/terrarium/"

PWM_FREQUENCY = 100  
PWM_PERIOD = 1.0 / PWM_FREQUENCY

with open(devices_info_file, 'r') as f:
    devices_info = json.load(f)

class GPIOController(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True
    def apply_automation(self):
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            
            with open(sensor_data_file, 'r') as f:
                sensor_list = json.load(f)
            
            if sensor_list:
                newest = sensor_list[0]
                temp = newest.get('temperature')
                humid = newest.get('humidity')
                bright = newest.get('brightness')
                
                current_time_str = datetime.datetime.now().strftime("%H:%M")
                start_time = settings['light_schedule']['start_time']
                end_time = settings['light_schedule']['end_time']
                
                if devices_info["light"]["mode"] == "auto":
                    if start_time <= current_time_str <= end_time:
                        devices_info["light"]["state"] = "on"
                        if bright is not None:
                            devices_info["light"]["intensity"] = min(1.0, max(0.0, bright / settings.get('optimal_light', 1.0)))
                        else:
                            devices_info["light"]["intensity"] = 1.0
                    else:
                        devices_info["light"]["state"] = "off"
                
                if devices_info["fan"]["mode"] == "auto" and temp is not None:
                    if temp > settings['optimal_temperature']:
                        devices_info["fan"]["state"] = "on"
                    else:
                        if humid is not None:
                            if humid > settings['optimal_humidity']:
                                devices_info["fan"]["state"] = "on"
                            else:
                                devices_info["fan"]["state"] = "off"
                else:
                    devices_info["fan"]["state"] = "off"
                
                if devices_info["heat_mat"]["mode"] == "auto" and temp is not None:
                    if temp < settings['optimal_temperature']:
                        devices_info["heat_mat"]["state"] = "on"
                    else:
                        devices_info["heat_mat"]["state"] = "off"
                
                if devices_info["sprinkler"]["mode"] == "auto" and humid is not None:
                    if humid < settings['optimal_humidity']:
                        devices_info["sprinkler"]["state"] = "on"
                    else:
                        devices_info["sprinkler"]["state"] = "off"
        
        except Exception as e:
            print(f"Automation error: {e}")

    def run(self):
        print("GPIO Started")
        if not GPIO_AVAILABLE:
            print("GPIO not available, running automation only")
            while self.running:
                self.apply_automation()
                time.sleep(1)  # Sleep to avoid busy loop
            return

        try:
            with gpiod.request_lines(
                path=config.CHIP_PATH,
                consumer="gpio_service",
                config={
                    config.FAN_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.PUMP_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.SPRINKLER_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.HEATER_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.LIGHT_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                },
            ) as request:

                while self.running:
                    self.apply_automation()
                    
                    fan_val = Value.ACTIVE if devices_info["fan"]["state"] == "on" else Value.INACTIVE
                    request.set_value(config.FAN_PIN, fan_val)

                    pump_val = Value.ACTIVE if devices_info["pump"]["state"] == "on" else Value.INACTIVE
                    request.set_value(config.PUMP_PIN, pump_val)

                    sprinkler_val = Value.ACTIVE if devices_info["sprinkler"]["state"] == "on" else Value.INACTIVE
                    request.set_value(config.SPRINKLER_PIN, sprinkler_val)

                    heat_val = Value.ACTIVE if devices_info["heat_mat"]["state"] == "on" else Value.INACTIVE
                    request.set_value(config.HEATING_MAT_PIN, heat_val)

                    light_conf = devices_info["light"]
                    if light_conf["state"] == "on":
                        intensity = light_conf.get("intensity", 1.0)

                        if intensity >= 1.0:
                            request.set_value(config.LIGHT_PIN, Value.ACTIVE)
                            time.sleep(PWM_PERIOD)
                        elif intensity <= 0.0:
                            request.set_value(config.LIGHT_PIN, Value.INACTIVE)
                            time.sleep(PWM_PERIOD)
                        else:
                            on_time = PWM_PERIOD * intensity
                            off_time = PWM_PERIOD * (1.0 - intensity)
                            request.set_value(config.LIGHT_PIN, Value.ACTIVE)
                            time.sleep(on_time)
                            request.set_value(config.LIGHT_PIN, Value.INACTIVE)
                            time.sleep(off_time)
                    else:
                        request.set_value(config.LIGHT_PIN, Value.INACTIVE)
                        time.sleep(0.01)

        except Exception as e:
            print(f"GPIO Thread Crashed: {e}")

@app.route('/device-control', methods=['POST'])
def update_device():
    data = request.json
    component = data.get("component")
    action = data.get("action")

    if component not in config.COMPONENT_MAP:
        return jsonify({"error": "Invalid component"}), 400

    if component == "light":
        intensity = data.get("intensity")
        devices_info["light"]["state"] = action
        if intensity is not None:
            devices_info["light"]["intensity"] = max(0.0, min(1.0, float(intensity)))
    else:
        devices_info[component]["state"] = action

    return jsonify({"state": "success", "current_state": devices_info[component]})

@app.route('/device-mode-edit', methods=['POST'])
def device_mode_edit():
    data = request.json
    component = data.get("type")
    action = data.get("mode")
    state = data.get("state")

    if component not in config.COMPONENT_MAP:
        return jsonify({"error": "Invalid component"}), 400

    if component == "light" or component == "pump" or component == "sprinkler":
        devices_info[component]["mode"] = "manual"
        devices_info[component]["state"] = state
        if component == "light":
                intensity = data.get("intensity")
                if intensity is not None:
                    devices_info["light"]["intensity"] = max(0.0, min(1.0, float(intensity)))
        devices_info[component]["last_edit_date"] = datetime.datetime.now().isoformat()
        return jsonify({"state": "success", "current_mode": devices_info[component]["mode"], "current_state": devices_info[component]["state"]})
    else:
        return jsonify({"error": "Invalid component for mode change"}), 400
    

@app.route('/device-state', methods=['GET'])
def get_state():
    return jsonify(devices_info)

@app.route('/current-setting', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print("Received data from backend!")
        print(data)
        
        with open(settings_file, 'w') as f:
            json.dump(data, f)
        
        url = server_url + f"setting/{data['setting_id']}"
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Data received and sent to server"}), 200
        else:
            print(f"Error: Server responded with status {response.status_code}")
            return jsonify({"status": "error", "message": f"Server error: {response.status_code}"}), 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": "An error occurred"}), 400

if __name__ == '__main__':
    def run_web_server():
     print("Starting Web Server on Port 5000...")
     app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(1)

    print("Starting GPIO Controller...")
    try:
        controller = GPIOController()
        controller.run()
    except KeyboardInterrupt:
        print("\nTurning off all devices...")
        for dev in devices_info:
            devices_info[dev]["state"] = "off"
        try:
            with gpiod.request_lines(
                path=config.CHIP_PATH,
                consumer="shutdown_cleanup",
                config={
                    config.FAN_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.PUMP_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.SPRINKLER_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.HEATING_MAT_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.LIGHT_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                },
            ) as request:
                request.set_value(config.FAN_PIN, Value.INACTIVE)
                request.set_value(config.PUMP_PIN, Value.INACTIVE)
                request.set_value(config.SPRINKLER_PIN, Value.INACTIVE)
                request.set_value(config.HEATING_MAT_PIN, Value.INACTIVE)
                request.set_value(config.LIGHT_PIN, Value.INACTIVE)
        except Exception as e:
            print(f"GPIO cleanup error: {e}")
        print("Stopping...")