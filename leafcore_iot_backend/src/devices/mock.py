# src/devices/mock.py
"""
Mock backend for testing and development
"""
import random
import time
from typing import Tuple
from .base import BaseBackend


class MockBackend(BaseBackend):
    """Mock backend - works everywhere (Windows/Linux) without GPIO"""
    
    def __init__(self):
        super().__init__()
        self._temp = 22.0 + random.uniform(-1.0, 1.0)
        self._hum = 60.0 + random.uniform(-3.0, 3.0)
        self._light_intensity = 50.0 + random.uniform(-10.0, 10.0)
        self._last_update = 0.0

    def _drift(self):
        """Simulate sensor drift based on device states"""
        now = time.time()
        if now - self._last_update > 1.0:
            self._last_update = now
            
            # Fan ON -> decrease humidity slightly
            if self._fan_state:
                self._hum += random.uniform(-0.6, 0.0)
            else:
                self._hum += random.uniform(-0.2, 0.3)

            # Light ON (intensity > 0) -> slightly increase temperature
            if self._light_state > 0:
                self._temp += random.uniform(0.0, 0.15)
            else:
                self._temp += random.uniform(-0.08, 0.05)

            # Pump ON -> briefly increase humidity
            if self._pump_state:
                self._hum += random.uniform(0.3, 0.8)

            # Constraints
            self._temp = max(10.0, min(35.0, self._temp))
            self._hum = max(20.0, min(95.0, self._hum))

    def read_sensor(self) -> Tuple[float, float]:
        """Read temperature and humidity from simulated sensor"""
        self._drift()
        return round(self._temp, 1), round(self._hum, 1)

    def read_light_intensity(self) -> float:
        """Return light intensity 0-100 with slight random variation"""
        self._light_intensity += random.uniform(-2.0, 2.0)
        self._light_intensity = max(0.0, min(100.0, self._light_intensity))
        return round(self._light_intensity, 1)
