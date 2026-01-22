# config.py - Konfiguracja GPIO i stałe dla Orange Pi Zero 2W
"""
GPIO pins and constants for Leafcore IoT Backend
"""

# ========== GPIO PINS (Orange Pi Zero 2W) ==========
FAN_PIN = 271
LIGHT_PIN = 269
PUMP_PIN = 268
HEATING_MAT_PIN = 270
SPRINKLER_PIN = 258
WATER_MIN_PIN = 259
WATER_MAX_PIN = 260
# I2C pins for Software I2C Bridge (AHT10 + VEML7700)
SCL_PIN = 263
SDA_PIN = 264

CHIP_PATH = "/dev/gpiochip0"

# ========== DEVICE NAMES ==========
COMPONENT_MAP = {
    "fan": FAN_PIN,
    "pump": PUMP_PIN,
    "sprinkler": SPRINKLER_PIN,
    "heat_mat": HEATING_MAT_PIN,
    "light": LIGHT_PIN
}

# ========== PWM CONFIGURATION ==========
PWM_FREQUENCY = 100  # 100 Hz
PWM_PERIOD = 1.0 / PWM_FREQUENCY  # 0.01 seconds

# ========== SENSOR SIMULATION (mock fallback) ==========
MOCK_TEMP_START = 22.0
MOCK_HUMIDITY_START = 60.0
MOCK_LIGHT_START = 45.0

# ========== FILE PATHS ==========
SOURCE_FILES_DIR = "source_files"
SENSOR_DATA_FILE = f"{SOURCE_FILES_DIR}/sensor_data.json"
SENSOR_HISTORY_FILE = f"{SOURCE_FILES_DIR}/sensor_data_history.json"
SETTINGS_FILE = f"{SOURCE_FILES_DIR}/settings_config.json"
DEVICES_INFO_FILE = f"{SOURCE_FILES_DIR}/devices_info.json"

# ========== SETTINGS DEFAULTS ==========
DEFAULT_SETTINGS = {
    "setting_id": "1",
    "plant_name": "default plant",
    "target_temp": 25.0,
    "target_hum": 60.0,
    "watering_days": ["MONDAY", "WEDNESDAY", "FRIDAY"],
    "water_seconds": 1,
    "watering_mode": "standard",
    "light_intensity": 50.0,
    "start_hour": 6,
    "end_hour": 18,
    "light_schedule": {
        "start_time": "06:00",
        "end_time": "18:00"
    }
}

DEFAULT_DEVICES_INFO = {
    "fan": {"state": False, "mode": "auto"},
    "light": {"state": False, "mode": "auto", "intensity": 0.0},
    "pump": {"state": False, "mode": "manual"},
    "heating_mat": {"state": False, "mode": "auto"},
    "sprinkler": {"state": False, "mode": "auto"}
}
