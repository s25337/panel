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
        self._temp = 22.0  # Starting temperature
        self._hum = 60.0   # Starting humidity
        self._ambient_light = 45.0  # Starting ambient brightness (like daylight)
        self._last_update = 0.0

    def _drift(self):
        """Simulate subtle sensor drift based on device states"""
        now = time.time()
        if now - self._last_update > 1.0:
            self._last_update = now
            
            # Fan ON -> decrease humidity slightly
            if self._fan_state:
                self._hum -= 0.2
            else:
                self._hum += 0.1

            # Light ON (intensity > 0) -> slightly increase temperature AND ambient light sensor
            if self._light_state > 0:
                self._temp += 0.05
                # LED affects ambient light sensor reading - small increase
                self._ambient_light += 0.1
            else:
                self._temp -= 0.03
                # Without light, ambient decreases slowly
                self._ambient_light -= 0.05

            # Pump ON -> briefly increase humidity
            if self._pump_state:
                self._hum += 0.5

            # Constraints - keep values in realistic range
            self._temp = max(10.0, min(35.0, self._temp))
            self._hum = max(20.0, min(95.0, self._hum))
            self._ambient_light = max(0.0, min(100.0, self._ambient_light))

    def read_sensor(self) -> Tuple[float, float]:
        """Read temperature and humidity from simulated sensor"""
        self._drift()
        return round(self._temp, 1), round(self._hum, 1)

    def read_light_intensity(self) -> float:
        """
        Return ambient light intensity (0-100) from simulated sensor (VEML7700)
        """
        self._drift()
        return round(self._ambient_light, 1)

