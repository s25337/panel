# app.py - Leafcore IoT Backend
"""
Leafcore IoT Backend - Full integration of iot-ref with API endpoints
Includes GPIO control, sensor reading, Bluetooth WiFi config
"""
import time
import threading
import json
import os
import fcntl
import datetime
import logging
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from src.json_manager import load_json_secure, save_json_secure
# Gpiod for GPIO control
try:
    import gpiod
    from gpiod.line import Direction, Value
    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False

# Local modules
sys_path = os.path.dirname(__file__)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from src.bluetooth_service import BluetoothService
from src.sensor_service import SensorService
from src.gpio_manager import apply_automation_rules

from src.api_frontend import api_frontend
from src.api_external import api_external
from src.api_webhooks import api_webhooks

# Load config
try:
    import config
except ImportError:
    # Fallback config
    class config:
        CHIP_PATH = "/dev/gpiochip0"
        FAN_PIN = 271
        PUMP_PIN = 268
        SPRINKLER_PIN = 258
        HEATING_MAT_PIN = 270
        LIGHT_PIN = 269
        SCL_PIN = 263
        SDA_PIN = 264
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PWM_FREQUENCY = 100
PWM_PERIOD = int(1_000_000_000 / PWM_FREQUENCY)
bluetooth_thread = None
# File paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sensor_data_file = os.path.join(current_dir, "source_files", "sensor_data.json")
settings_file = os.path.join(current_dir, "source_files", "settings_config.json")
devices_info_file = os.path.join(current_dir, "source_files", "devices_info.json")

devices_info = load_json_secure(devices_info_file)

def setup_pwm(chip_num, channel_num):
    base_path = f"/sys/class/pwm/pwmchip{chip_num}"
    export_path = f"{base_path}/export"
    channel_path = f"{base_path}/pwm{channel_num}"

    if not os.path.exists(channel_path):
        print(f"PWM Channel {channel_num} missing. Creating it...")
        try:
            with open(export_path, 'w') as f:
                f.write(str(channel_num))

        except PermissionError:
            print("ERROR: Permission denied. You must run with 'sudo' or fix uDev rules.")
            raise
        except OSError as e:
            print(f"Warning during export: {e}")
    time.sleep(0.5)
    print(f"PWM Channel {channel_num} is ready.")
    try:
        with open(f"{channel_path}/enable", "w") as f:
            f.write("0")
    except OSError:
        pass

    with open(f"{channel_path}/period", "w") as f:
        f.write(str(PWM_PERIOD))

    with open(f"{channel_path}/enable", "w") as f:
        f.write("1")

    print(f"PWM Configured: Period={PWM_PERIOD}ns")

def set_brightness(intensity):
    intensity = max(0.0, min(intensity, 1.0))
    duty_ns = int(PWM_PERIOD * intensity)

    with open("/sys/class/pwm/pwmchip0/pwm3/duty_cycle", "w") as f:
        f.write(str(duty_ns))

def set_heat(intensity):
    intensity = max(0.0, min(intensity, 1.0))
    duty_ns = int(PWM_PERIOD * intensity)

    with open("/sys/class/pwm/pwmchip0/pwm4/duty_cycle", "w") as f:
        f.write(str(duty_ns))

class GPIOController(threading.Thread):

    def __init__(self):
        super().__init__()
        self.running = True
        self.daemon = True
        self.gpio_available = GPIOD_AVAILABLE

    def run(self):
        print("GPIO Started")

        # Mock mode if gpiod not available
        if not self.gpio_available:
            print("⚠️  Running in MOCK MODE (gpiod not available)")
            self._run_mock()
            return

        try:
            with gpiod.request_lines(
                path=config.CHIP_PATH,
                consumer="gpio_service",
                config={
                    config.FAN_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.PUMP_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.SPRINKLER_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)
                },
            ) as request:
                self._run_gpio(request)

        except Exception as e:
            print(f"GPIO Thread Crashed: {e}")
            logger.error(f"GPIO Thread Crashed: {e}")
            self._run_mock()

    def _run_gpio(self, request):
        """GPIO loop with actual hardware"""
        while self.running:
            try:
                # Czytaj devices_info z pliku co pętlę
                devices_info = load_json_secure(devices_info_file)
                settings = load_json_secure(settings_file)
                sensor_list = load_json_secure(sensor_data_file)
                devices_changes_made = False
                if sensor_list:
                    newest = sensor_list[0] if isinstance(sensor_list, list) else sensor_list

                    # Apply automation rules
                    apply_automation_rules(devices_info, newest, settings, settings_file, devices_info_file)

                    # Jeśli pompa ON, zapisz czas włączenia
                    if devices_info.get("pump", {}).get("state") == "on":
                        if not devices_info.get("pump", {}).get("turned_on_at"):
                            devices_info["pump"]["turned_on_at"] = time.time()
                            devices_changes_made = True
                    else:
                        # Pompa OFF, usuń timestamp
                        if "turned_on_at" in devices_info.get("pump", {}):
                            del devices_info["pump"]["turned_on_at"]
                            devices_changes_made = True

                    # Sprawdź czy pompa ma być wyłączona po watering_time
                    if devices_info.get("pump", {}).get("turned_on_at"):
                        watering_time = settings.get('watering_time', 3)
                        logger.info(f"{watering_time}")
                        elapsed = time.time() - devices_info["pump"]["turned_on_at"]
                        logger.info(f"{elapsed}")
                        devices_info["fan"]["state"] = "off"
                        devices_info["heat_mat"]["state"] = "off"
                        save_json_secure(devices_info_file, devices_info)
                        if elapsed > watering_time:
                            devices_info["pump"]["state"] = "off"
                            if devices_info.get("pump", {}).get("manual_trigger"):
                               del devices_info["pump"]["manual_trigger"]
                            logger.info("finished watering")
                            del devices_info["pump"]["turned_on_at"]
                            devices_changes_made = True

                    if devices_changes_made:
                       save_json_secure(devices_info_file, devices_info)

            except Exception as e:
                print(f"Automation error: {e}")
                logger.error(f"Automation error: {e}")

            # Apply GPIO states
            try:
                devices_info = load_json_secure(devices_info_file)
                fan_val = Value.ACTIVE if devices_info.get("fan", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.FAN_PIN, fan_val)
                sprinkler_val = Value.ACTIVE if devices_info.get("sprinkler", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.SPRINKLER_PIN, sprinkler_val)
                time.sleep(0.5)
                if devices_info["heat_mat"]["state"] == "off" and devices_info["fan"]["state"] == "off":
                  pump_val = Value.ACTIVE if devices_info.get("pump", {}).get("state") == "on" else Value.INACTIVE
                  request.set_value(config.PUMP_PIN, pump_val)

                heat = devices_info.get("heat_mat", {})
                if heat.get("state") == "on":
                   set_heat(0.3)

                light_conf = devices_info.get("light", {})
                if light_conf.get("state") == "on":
                    intensity = light_conf.get("intensity", 1.0)
                    if intensity >= 1.0: intensity = 1.0
                    if intensity <= 0.0: intensity = 0.0
                    set_brightness(intensity)
                else:
                    set_brightness(0.0)
            except Exception as e:
                logger.error(f"GPIO error: {e}")
                time.sleep(0.1)
            time.sleep(0.1)
    def _run_mock(self):
        """Mock loop without gpiod"""
        while self.running:
            try:
                # Czytaj devices_info z pliku co pętlę
                devices_info = load_json_secure(devices_info_file)
                settings = load_json_secure(settings_file)
                sensor_list = load_json_secure(sensor_data_file)
                if sensor_list:
                    newest = sensor_list[0] if isinstance(sensor_list, list) else sensor_list

                    # Apply automation rules
                    apply_automation_rules(devices_info, newest, settings, settings_file, devices_info_file)

                    # Jeśli pompa ON, zapisz czas włączenia
                    if devices_info.get("pump", {}).get("state") == "on":
                        if not devices_info.get("pump", {}).get("turned_on_at"):
                            devices_info["pump"]["turned_on_at"] = time.time()
                    else:
                        # Pompa OFF, usuń timestamp
                        if "turned_on_at" in devices_info.get("pump", {}):
                            del devices_info["pump"]["turned_on_at"]

                    # Sprawdź czy pompa ma być wyłączona po water_seconds
                    if devices_info.get("pump", {}).get("turned_on_at"):
                        water_seconds = settings.get('water_seconds', 30)
                        elapsed = time.time() - devices_info["pump"]["turned_on_at"]
                        if elapsed > water_seconds:
                                devices_info["pump"]["state"] = "off"
                                del devices_info["pump"]["turned_on_at"]
                    # Save updated device states
                    save_json_secure(devices_info_file, devices_info)

            except Exception as e:
                logger.error(f"Mock automation error: {e}")

            time.sleep(1)  # Mock loop slower than GPIO loop


# ========== FLASK APP ==========

app = Flask(__name__)
app.config['CURRENT_DIR'] = current_dir
app.config['DEVICES_INFO'] = devices_info

CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
            }
})

# Register blueprints

app.register_blueprint(api_frontend)
app.register_blueprint(api_external)
app.register_blueprint(api_webhooks)

setup_pwm(0,3)
setup_pwm(0,4)

# Start GPIO thread
gpio_thread = GPIOController()
gpio_thread.start()
print("✓ GPIO Controller thread started")
# Start periodic data sender thread (after app is created)
from src.periodic_data_sender import start_periodic_sender
start_periodic_sender(app)

# Start Sensor Service thread
sensor_thread = SensorService(
    chip_path=config.CHIP_PATH,
    scl_pin=config.SCL_PIN,
    sda_pin=config.SDA_PIN,
        output_file=sensor_data_file,
    save_callback=save_json_secure,
    read_callback=load_json_secure,
    poll_interval=2.0
)
sensor_thread.start()
print("✓ Sensor Service thread started")


# ========== SHUTDOWN ==========

def shutdown():
    logger.info("Shutting down services...")

    # Stop GPIO thread
    gpio_thread.running = False
    gpio_thread.join(timeout=2)

    # Stop Sensor thread
    sensor_thread.running = False
    sensor_thread.join(timeout=2)

    # Stop Bluetooth thread if running
    if bluetooth_thread:
        bluetooth_thread.stop()
        bluetooth_thread.join(timeout=2)
    try:
        devices_info = load_json_secure(devices_info_file)
        for device in devices_info.items():
           device["state"] = "off"
        save_json_secure(devices_info_file, devices_info)
        logger.info("All services stopped")
    except Exception as e:
        print("Couldn't read or save file")

if __name__ == "__main__":
    import atexit
    atexit.register(shutdown)
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
