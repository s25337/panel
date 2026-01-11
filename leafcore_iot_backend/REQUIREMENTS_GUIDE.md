# Requirements Guide

## Installation

### Basic Setup (MockBackend - works everywhere)
```bash
pip install -r requirements.txt
```

This installs core dependencies only:
- **Flask 2.3.3** - Web framework
- **Flask-CORS 4.0.0** - Cross-origin requests
- **requests** - HTTP library for cloud sync

### Hardware Setup (Orange Pi Zero 2W with GPIO)

All dependencies in `requirements.txt` already include optional hardware packages:

```bash
# Install everything (including hardware support)
pip install -r requirements.txt
```

#### What Each Optional Package Does:

| Package | Purpose | Required For |
|---------|---------|--------------|
| **gpiod** | GPIO control via gpiod library | Orange Pi/Raspberry Pi GPIO control |
| **bluezero** | Bluetooth LE support | Wi-Fi configuration via BLE |
| **adafruit-circuitpython-ahtx0** | AHT10 temperature/humidity sensor | Temperature & humidity readings |
| **adafruit-circuitpython-veml7700** | VEML7700 light sensor | Brightness readings (lux) |

#### Optional Dependencies Behavior:

If a package fails to install:
1. **Backend still starts** (uses MockBackend fallback)
2. **Sensors gracefully degrade** (print warnings, return None)
3. **Logging indicates which sensors are unavailable**

Example:
```
⚠ AHT10 error: ModuleNotFoundError
⚠ VEML7700 error: ModuleNotFoundError
Backend will use mock sensor data
```

---

## Troubleshooting Installation

### Issue: `gpiod` build fails on Raspberry Pi
**Cause:** Missing build dependencies
```bash
# Install build tools first
sudo apt-get install build-essential python3-dev
pip install -r requirements.txt
```

### Issue: `bluezero` fails on non-Bluetooth systems
**Solution:** Optional - backend works without it. For Bluetooth:
```bash
sudo apt-get install bluez python3-bluez
pip install bluezero
```

### Issue: `adafruit` packages missing on Orange Pi
**Solution:** They're optional. Sensors will fall back gracefully:
```bash
# Try install, but backend will work if it fails
pip install adafruit-circuitpython-ahtx0 adafruit-circuitpython-veml7700
```

---

## Running Backend

### With MockBackend (Default - Development)
```bash
source venv/bin/activate
python3 run.py
# or
USE_HARDWARE=0 python3 run.py
```

### With Hardware (Orange Pi)
```bash
source venv/bin/activate
USE_HARDWARE=1 python3 run.py
```

---

## Architecture

### MockBackend (`src/devices/mock.py`)
- ✅ Works on Windows, Mac, Linux
- ✅ No GPIO required
- ✅ Realistic sensor simulation
- ✅ Perfect for development & testing

### HardwareBackend (`src/devices/hardware.py`)
- ✅ Real GPIO control via gpiod
- ✅ Real sensor readings (AHT10 + VEML7700)
- ✅ Software I2C bridge (if hardware I2C not available)
- ✅ Orange Pi Zero 2W optimized

### Automatic Fallback
`DeviceManager` automatically:
1. Tries to load HardwareBackend if `USE_HARDWARE=1`
2. Falls back to MockBackend if hardware unavailable
3. Prints status to console

```python
# From manager.py
if not use_hardware:
    return MockBackend()

try:
    return GPIOdBackend(...)
except Exception:
    print("Hardware failed, using MockBackend")
    return MockBackend()
```

---

## Dependency Details

### Core Dependencies (Always Installed)
```
Flask==2.3.3          # Web server
Flask-CORS==4.0.0     # Enable cross-origin requests
requests>=2.31.0      # HTTP client for cloud API
```

### Optional - GPIO Control
```
gpiod>=2.0.0          # Linux GPIO daemon interface
```
- Required for: Real GPIO control on Orange Pi/Raspberry Pi
- Fallback: MockBackend (no error if missing)

### Optional - Sensors
```
adafruit-circuitpython-ahtx0>=1.0.0     # AHT10 (temp/humidity)
adafruit-circuitpython-veml7700>=1.0.0  # VEML7700 (light)
```
- Required for: Real sensor readings
- Fallback: Sensor read returns `None`, gracefully handled
- Both: Optional, can be installed separately

### Optional - Bluetooth
```
bluezero>=0.1.3       # BLE for Wi-Fi configuration
```
- Required for: Bluetooth LE pairing setup
- Fallback: Available but not critical

---

## Virtual Environment Setup

### Create & Activate
```bash
cd leafcore_iot_backend

# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### Install & Verify
```bash
pip install -r requirements.txt

# Verify Flask
python3 -c "import flask; print(f'Flask {flask.__version__} OK')"

# Verify gpiod (if on Linux with GPIO)
python3 -c "import gpiod; print('gpiod OK')" || echo "gpiod not available"
```

---

## Migration: MockBackend → Hardware

### Before Switching to Real Hardware:
1. ✅ Backend works with MockBackend
2. ✅ All tests pass with `USE_HARDWARE=0`
3. ✅ Frontend connects and controls devices
4. ✅ Automation logic verified

### Switching to Hardware:
```bash
# Step 1: Install hardware dependencies (if needed)
pip install gpiod adafruit-circuitpython-ahtx0 adafruit-circuitpython-veml7700

# Step 2: Run with hardware enabled
USE_HARDWARE=1 python3 run.py

# Step 3: Monitor logs for GPIO initialization
# Expected output:
#   ✓ GPIO setup complete
#   ✓ AHT10 sensor initialized
#   ✓ VEML7700 sensor initialized
#   🚀 GPIOAutomationService started
```

### If Hardware Fails:
```bash
# Backend automatically falls back to MockBackend
# Check logs for error messages
# Example: "GPIO setup error: Permission denied"

# Solution: Run with sudo
sudo USE_HARDWARE=1 python3 run.py
```

---

## Pin Configuration (Orange Pi Zero 2W)

Default GPIO pin mapping (in `hardware.py`):
```python
fan_pin = 271        # Fan control
light_pin = 269      # Light (with PWM dimming)
pump_pin = 268       # Pump/sprinkler
heater_pin = 272     # Heating mat
sprinkler_pin = 258  # Secondary sprinkler

# I2C Bridge (Software I2C)
scl_pin = 263        # SCL line
sda_pin = 264        # SDA line
```

All pins use:
- **Chip:** `/dev/gpiochip0` (Orange Pi default)
- **Library:** gpiod v2.0+
- **Mode:** Output (most), Input+Pull-up (I2C)

---

## Services Overview

### Automation Services

| Service | Purpose | Backend | Runs When |
|---------|---------|---------|-----------|
| **AutomationService** | Scheduled watering at 12:00 | Both | Always (if enabled) |
| **GPIOAutomationService** | Real-time auto-mode (temp/humidity/light) | Hardware only | `USE_HARDWARE=1` |
| **SensorReadingService** | Background sensor reading & cloud sync | Both | Always |

### On Orange Pi (USE_HARDWARE=1):
- ✅ AutomationService - checks watering schedule
- ✅ GPIOAutomationService - controls fan/heater/sprinkler/light based on sensors
- ✅ SensorReadingService - reads real sensors, posts to cloud

### On Development (USE_HARDWARE=0):
- ✅ AutomationService - simulated
- ⚠ GPIOAutomationService - disabled (hardware only)
- ✅ SensorReadingService - uses mock sensor data

---

## Debugging

### Check Which Backend is Active
```bash
# In app.py logs (first startup line)
# [DeviceManager] Using MockBackend
# or
# [DeviceManager] Using GPIOdBackend
```

### Verify Sensor Readings
```bash
curl http://localhost:5000/api/sensors
```

### Check GPIO Automation Logs
```bash
USE_HARDWARE=1 python3 run.py 2>&1 | grep "GPIO"
```

Expected output (every 10 seconds):
```
[GPIO] Light ON (auto): 75.5%
[GPIO] Fan ON (auto): temp 26.5°C > 25.0°C
[GPIO] Heater OFF (auto): temp 24.0°C < 25.0°C
```

---

## Summary Checklist

- [ ] `pip install -r requirements.txt` works
- [ ] Flask runs: `python3 run.py` (MockBackend)
- [ ] Hardware packages installed (optional): `pip install gpiod`
- [ ] Backend can switch: `USE_HARDWARE=1 python3 run.py`
- [ ] GPIO initialization: check logs for `✓` marks
- [ ] Sensor readings: check `/api/sensors` endpoint
- [ ] Automation logs: grep for `[GPIO]` or `[Automation]` lines
