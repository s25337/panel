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
        HEATING_MAT_PIN = 272
        LIGHT_PIN = 269
        SCL_PIN = 263
        SDA_PIN = 264

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PWM_FREQUENCY = 100
PWM_PERIOD = int(1_000_000_000 / PWM_FREQUENCY)

# File paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sensor_data_file = os.path.join(current_dir, "source_files", "sensor_data.json")
settings_file = os.path.join(current_dir, "source_files", "settings_config.json")
devices_info_file = os.path.join(current_dir, "source_files", "devices_info.json")


def load_json_secure(file_path):

    """Safely reads JSON by waiting for a lock."""

    lock_path = file_path + ".lock"

    with open(lock_path, "w") as lockfile:

        fcntl.flock(lockfile, fcntl.LOCK_SH)

        try:

            with open(file_path, "r") as f:

                return json.load(f)

        except (json.JSONDecodeError, FileNotFoundError):

            return {}

        finally:

            fcntl.flock(lockfile, fcntl.LOCK_UN)


def save_json_secure(file_path, data):

    """Safely writes JSON by locking the file exclusively."""

    lock_path = file_path + ".lock"

    with open(lock_path, "w") as lockfile:

        fcntl.flock(lockfile, fcntl.LOCK_EX)

        try:

            with open(file_path, "w") as f:

                json.dump(data, f, indent=4)

                f.flush()

                os.fsync(f.fileno())

        finally:

            fcntl.flock(lockfile, fcntl.LOCK_UN)

devices_info = load_json_secure(devices_info_file)

def setup_pwm():
    if not os.path.exists("/sys/class/pwm/pwmchip0/pwm3"):
        try:
            with open("/sys/class/pwm/pwmchip0/export", "w") as f:
                f.write("0")
        except OSError:
            print("PWM0 already exported or busy.")

    time.sleep(0.8) 
    with open("/sys/class/pwm/pwmchip0/pwm3/period", "w") as f:
        f.write(str(PWM_PERIOD))

    with open("/sys/class/pwm/pwmchip0/pwm3/enable", "w") as f:
        f.write("1")

def set_brightness(intensity):
    intensity = max(0.0, min(intensity, 1.0))
    duty_ns = int(PWM_PERIOD * intensity)
    
    with open("/sys/class/pwm/pwmchip0/pwm3/duty_cycle", "w") as f:
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
                    config.SPRINKLER_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    config.HEATING_MAT_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
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
                        logger.info(f"{water_seconds}")
                        elapsed = time.time() - devices_info["pump"]["turned_on_at"]
                        logger.info(f"{elapsed}")
                        if elapsed > water_seconds:
                            devices_info["pump"]["state"] = "off"
                            logger.info("finished watering")
                            del devices_info["pump"]["turned_on_at"]
                    
                    # Save updated device states
                    save_json_secure(devices_info_file, devices_info)
            
            except Exception as e:
                print(f"Automation error: {e}")
                logger.error(f"Automation error: {e}")
            
            # Apply GPIO states
            try:
                fan_val = Value.ACTIVE if devices_info.get("fan", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.FAN_PIN, fan_val)

                pump_val = Value.ACTIVE if devices_info.get("pump", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.PUMP_PIN, pump_val)

                sprinkler_val = Value.ACTIVE if devices_info.get("sprinkler", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.SPRINKLER_PIN, sprinkler_val)

                heat_val = Value.ACTIVE if devices_info.get("heat_mat", {}).get("state") == "on" else Value.INACTIVE
                request.set_value(config.HEATING_MAT_PIN, heat_val)

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

    def _run_mock(self):
        """Mock loop without gpiod"""
        while self.running:
            try:
                # Czytaj devices_info z pliku co pętlę
                with open(devices_info_file, 'r') as f:
                    devices_info = json.load(f)
                
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                with open(sensor_data_file, 'r') as f:
                    sensor_list = json.load(f)
                
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
                    with open(devices_info_file, 'w') as f:
                        json.dump(devices_info, f, indent=2)
            
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

setup_pwm()
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
    
    logger.info("All services stopped")


if __name__ == "__main__":
    import atexit
    atexit.register(shutdown)
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

