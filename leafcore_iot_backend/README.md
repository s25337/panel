# Leafcore IoT Backend

Smart greenhouse controller backend built with Flask.

## Project Structure

```
leafcore_iot_backend/
├── src/
│   ├── devices/              # Device control layer
│   │   ├── base.py          # Abstract base class
│   │   ├── mock.py          # Mock backend (for testing)
│   │   ├── hardware.py      # GPIO hardware backend
│   │   └── manager.py       # Device manager (unified interface)
│   ├── services/            # Business logic layer
│   │   ├── settings_service.py    # Settings management
│   │   ├── control_service.py     # Control logic & automation
│   │   └── sensor_service.py      # Sensor reading
│   └── api/                 # API layer
│       └── routes.py        # Flask routes
├── app.py                   # Flask application factory
├── run.py                   # Development server launcher
├── config/                  # Configuration files
│   ├── settings_config.json
│   └── manual_settings.json
├── templates/               # HTML templates
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Features

- **Device Control**: Fan, light, pump, heater, sprinkler
- **Sensor Reading**: Temperature, humidity, light intensity
- **Automation**: Auto-control with hysteresis, light scheduling
- **Settings Management**: Persistent JSON-based settings
- **Manual & Auto Modes**: Toggle between manual and automatic control
- **RESTful API**: Full API for remote control

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Development Server

```bash
# With mock backend (no hardware needed)
python run.py

# With hardware backend (Orange Pi Zero 2W)
USE_HARDWARE=1 python run.py
```

### 3. Access the API

- Web UI: `http://localhost:5000/`
- API: `http://localhost:5000/api/`
- Health check: `http://localhost:5000/health`

## API Endpoints

### Sensors
- `GET /api/sensors` - Get current sensor readings

### Status
- `GET /api/status` - Get device states and sensor readings
- `GET /api/devices` - Get all device states
- `GET /api/devices/<device>` - Get specific device state

### Control
- `POST /api/control` - Control multiple devices
- `POST /api/control/<device>/<state>` - Control single device

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings
- `GET /api/settings/<key>` - Get specific setting
- `POST /api/settings/<key>` - Set specific setting

### Manual Control
- `GET /api/manual-settings` - Get manual settings
- `POST /api/manual-settings` - Update manual settings

### Watering
- `GET /api/watering-timer` - Get watering schedule info

### Light Schedule
- `GET /api/light-schedule` - Get light on/off schedule

## Environment Variables

- `USE_HARDWARE` - Use real GPIO (1) or mock backend (0, default)
- `DEBUG` - Enable debug mode (1, default)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 5000)
- `DHT_SENSOR` - DHT sensor type: DHT11, DHT22, AM2302 (default: DHT22)
- `GPIO_CHIP` - GPIO chip name (default: gpiochip0)

## Device Control Examples

### Control Fan
```bash
# Turn on
curl -X POST http://localhost:5000/api/control/fan/on

# Turn off
curl -X POST http://localhost:5000/api/control/fan/off
```

### Control Light
```bash
# Set intensity to 75%
curl -X POST http://localhost:5000/api/control/light/75

# Turn off
curl -X POST http://localhost:5000/api/control/light/0
```

### Control Multiple Devices
```bash
curl -X POST http://localhost:5000/api/control \
  -H "Content-Type: application/json" \
  -d '{
    "fan": true,
    "light": 50,
    "pump": false
  }'
```

### Update Settings
```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "target_temp": 25,
    "target_hum": 60,
    "light_hours": 12
  }'
```

## Architecture

### Device Layer (`src/devices/`)
Abstraction for device control with pluggable backends:
- **BaseBackend**: Abstract interface
- **MockBackend**: Simulated devices (for development/testing)
- **GPIOdBackend**: Real GPIO control for Orange Pi
- **DeviceManager**: Unified interface for all backends

### Service Layer (`src/services/`)
Business logic and automation:
- **SettingsService**: Load/save settings and manual controls
- **ControlService**: Device automation logic and state management
- **SensorService**: Sensor reading and caching

### API Layer (`src/api/`)
RESTful API routes using Flask Blueprints

## Configuration Files

### `config/settings_config.json`
Application settings:
```json
{
  "light_hours": 12.0,
  "target_temp": 22.0,
  "target_hum": 60.0,
  "water_times": 3,
  "water_seconds": 10,
  "light_intensity": 50.0
}
```

### `config/manual_settings.json`
Manual device control states:
```json
{
  "is_manual": false,
  "fan": false,
  "light": false,
  "pump": false,
  "heater": false,
  "sprinkler": false
}
```

## Development

### Running Tests
```bash
python -m pytest
```

### Code Style
```bash
# Format code
black src/ app.py run.py

# Lint
flake8 src/ app.py run.py
```

## License

MIT
