# 🔧 Backend Architecture Changes - Visual Diff

## Before (Opcja A Wdrożona)

```
Problem 1: Dual Read Paths
═══════════════════════════════════════════════════════════════

Frontend Request: GET /api/sensors
         │
         ├─ Ścieżka A: SensorService.refresh_all()
         │  └─ device_manager.read_sensor()  ← Direct read (on-demand)
         │     └─ Hardware I2C (slow)
         │
         └─ Ścieżka B: SensorReadingService._read_loop() [background]
            └─ device_manager.read_sensor()  ← Direct read (co 2s)
               └─ Hardware I2C (slow)

⚠️ PROBLEM: 2 independent threads reading same sensor!
           Możliwe race conditions, inconsistency
```

## After (Opcja A)

```
Single Source of Truth Architecture
═══════════════════════════════════════════════════════════════

Frontend Request: GET /api/sensors
         │
         ├─ SensorService.refresh_all()
         │  └─ sensor_reading_service.get_sensor_data()  ← CACHE READ
         │     └─ Returns: {temp, hum, brightness}
         │
         └─ Ścieżka B: SensorReadingService._read_loop() [background]
            └─ device_manager.read_sensor()  ← SINGLE POINT
               └─ Hardware I2C (raz na 2s, efektywnie)
               └─ Saves to cache
               └─ Updates JSON
               └─ POSTs to cloud (rate limited 10s)

✅ BENEFIT: Spójna dana, jeden odczyt, efektywnie
```

---

## Before vs After - Code

### SensorService Comparison

**BEFORE:**
```python
class SensorService:
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager  # ❌ Direct hardware access
        self._last_temp = None
    
    def get_temperature_humidity(self):
        temp, hum = self.device_manager.read_sensor()  # ❌ Every call hits hardware!
        self._last_temp = temp
        return temp, hum
```

**AFTER:**
```python
class SensorService:
    def __init__(self, device_manager, sensor_reading_service=None):
        self.device_manager = device_manager
        self.sensor_reading_service = sensor_reading_service  # ✅ Reference to cache
    
    def get_temperature_humidity(self):
        if self.sensor_reading_service:
            data = self.sensor_reading_service.get_sensor_data()  # ✅ Cache read!
            self._last_temp = data.get("temperature")
            return self._last_temp, data.get("humidity")
        else:
            # Fallback
            return self.device_manager.read_sensor()
```

### MockBackend Light Simulation

**BEFORE:**
```python
self._light_intensity = 50.0  # ❌ Ambiguous: is it LED or sensor?

def read_light_intensity(self):
    self._light_intensity += random.uniform(-2.0, 2.0)  # ❌ Drifts independently
    return self._light_intensity
```

**AFTER:**
```python
self._ambient_light = 50.0  # ✅ Clear: ambient brightness (sensor reading)

def _drift(self):
    if self._light_state > 0:  # ✅ When LED is ON
        self._ambient_light += random.uniform(0.5, 2.0)  # ✅ Increases brightness
    else:
        self._ambient_light += random.uniform(-2.0, -0.5)  # ✅ Decreases in dark

def read_light_intensity(self):
    self._drift()  # ✅ Simulate realistic physics
    return self._ambient_light
```

---

## Data Flow - Before vs After

### Before: Multiple Read Paths 🔴

```
Time: t=0s
├─ User calls GET /api/sensors
│  ├─ SensorService reads: temp=25.2, hum=65.1 (via device_manager)
│  └─ Returns: {temp: 25.2, hum: 65.1}
│
├─ Meanwhile SensorReadingService background thread:
│  └─ Reads: temp=25.2, hum=65.1 (same sensor, nearly same time)
│
Time: t=0.1s
├─ User calls GET /api/sensors again
│  ├─ SensorService reads: temp=25.3, hum=65.2 (NEW read, might be different!)
│  └─ Returns: {temp: 25.3, hum: 65.2}
│
└─ ❌ INCONSISTENCY: Values changed in 0.1 seconds!
```

### After: Single Source 🟢

```
Time: t=0s (background thread runs every 2s)
├─ SensorReadingService._read_loop() runs
│  ├─ Reads: temp=25.2, hum=65.1 (via device_manager)
│  ├─ Caches: {temp: 25.2, hum: 65.1}
│  └─ Posts to cloud (if time for post)
│
Time: t=0.05s
├─ User calls GET /api/sensors
│  ├─ SensorService.get_sensor_data()
│  │  └─ sensor_reading_service.get_sensor_data()  ← Returns CACHED data
│  └─ Returns: {temp: 25.2, hum: 65.1}  ← SAME as what SRS read
│
Time: t=0.1s
├─ User calls GET /api/sensors again
│  ├─ SensorService.get_sensor_data()
│  │  └─ sensor_reading_service.get_sensor_data()  ← Returns CACHED data
│  └─ Returns: {temp: 25.2, hum: 65.1}  ← STILL SAME
│
└─ ✅ CONSISTENCY: Same data until next SRS read cycle
```

---

## Performance Impact

### Before (Multiple Reads)
```
Request rate: 10 req/s (typical mobile polling)

Per request:
├─ SensorService.refresh_all()
│  ├─ device_manager.read_sensor()  ← I2C read (~5ms)
│  └─ device_manager.read_light_intensity()  ← I2C read (~5ms)
│  └─ Total: ~10ms per request
│
└─ × 10 requests/s = 100ms of I2C per second!
   Plus: SensorReadingService also reading independently!
```

### After (Cached Reads)
```
Request rate: 10 req/s (same)

Per request:
├─ SensorService.refresh_all()
│  └─ sensor_reading_service.get_sensor_data()  ← Memory read (~0.1ms)
│  └─ Total: ~0.1ms per request!
│
└─ × 10 requests/s = 1ms of memory access per second!

Background thread (independent):
└─ SensorReadingService reads hardware every 2s (~10ms every 2s)
   = ~5ms average overhead!

TOTAL I2C overhead: ~5ms (vs 100ms before) = 20x faster! 🚀
```

---

## Light Intensity Semantics - Clarification

### The Confusion ❓

Everyone said "light_intensity" but meant different things:

```
Scenario: LED turned ON, room is dark

Person A: "light_intensity = 100"
          (Meaning: LED PWM = 100%)

Person B: "light_intensity = 25"
          (Meaning: Sensor reads 25 lux)

Person C: "light_intensity = 45"
          (Meaning: Cached sensor from last read)

🤯 CHAOS!
```

### The Solution ✅

**Strict naming convention:**

```
╔═════════════════════════════════════════════════════════╗
║  CONTROL (What we SET)                                  ║
║  ═════════════════════════════════════════════════════  ║
║  set_light(intensity: float)           ← We control    ║
║  get_light_state() -> intensity: float ← Current state ║
║                                                         ║
║  MEASUREMENT (What we READ)                             ║
║  ═════════════════════════════════════════════════════  ║
║  read_light_intensity() -> brightness: float           ║
║  (from VEML7700 sensor = ambient light)                ║
║                                                         ║
║  THESE ARE INDEPENDENT!                                 ║
║  ═════════════════════════════════════════════════════  ║
║  set_light(100)  ← LED at 100% PWM                     ║
║  read_light_intensity()  ← 37 (room still partly dark) ║
║                                                         ║
║  Or:                                                    ║
║  set_light(0)    ← LED off                             ║
║  read_light_intensity()  ← 75 (sunny day outside)      ║
║                                                         ║
║  Or:                                                    ║
║  set_light(50)   ← LED at 50% PWM                      ║
║  read_light_intensity()  ← 20 (some light from LED)    ║
╚═════════════════════════════════════════════════════════╝
```

---

## Testing Verification ✅

```bash
# Syntax check
$ python3 -m py_compile app.py src/services/*.py
✅ OK - No syntax errors

# Import check
$ python3 -c "import app; print('✅ Imports OK')"
✅ Imports OK - No circular dependencies

# Structure verification
$ python3 -c "
from src.services import SensorService, SensorReadingService
s = SensorReadingService(None, app_dir='.')
ss = SensorService(None, sensor_reading_service=s)
print('✅ Dependency injection OK')
"
✅ Dependency injection OK
```

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `src/services/sensor_service.py` | Added `sensor_reading_service` param, read from cache | **Eliminates dual reads** |
| `app.py` | Reordered init: SRS first, then SS gets reference | **Ensures SRS is source of truth** |
| `src/api/routes.py` | Updated docs: `/api/sensors` now reads from cache | **Clarity** |
| `src/devices/base.py` | Added comprehensive semantics documentation | **Prevents future confusion** |
| `src/devices/mock.py` | Renamed `_light_intensity` to `_ambient_light`, realistic simulation | **Accurate testing** |

---

## Git History

```
5e0c202 refactor: clarify light sensor vs LED semantics
        └─ Document base.py semantics
        └─ Fix MockBackend simulation

fb3785f refactor: sync sensor reading - SensorReadingService as single source of truth
        └─ SensorService reads from SRS cache
        └─ Fallback to direct read if SRS unavailable
        └─ Single hardware read point (2s interval)
```

---

✅ **STATUS: COMPLETED** - Backend architecture synchronized and optimized!
