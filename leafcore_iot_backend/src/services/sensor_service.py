# src/services/sensor_service.py
"""
Sensor reading and processing service
"""
import time
from typing import Optional, Tuple
from src.devices import DeviceManager


class SensorService:
    """Manages sensor readings and processing"""
    
    def __init__(self, device_manager: DeviceManager):
        """Initialize sensor service"""
        self.device_manager = device_manager
        self._last_temp: Optional[float] = None
        self._last_hum: Optional[float] = None
        self._last_light: Optional[float] = None

    def get_temperature_humidity(self) -> Tuple[Optional[float], Optional[float]]:
        """Get current temperature and humidity"""
        temp, hum = self.device_manager.read_sensor()
        self._last_temp = temp
        self._last_hum = hum
        return temp, hum

    def get_temperature(self) -> Optional[float]:
        """Get current temperature"""
        return self._last_temp

    def get_humidity(self) -> Optional[float]:
        """Get current humidity"""
        return self._last_hum

    def get_light_intensity(self) -> Optional[float]:
        """Get current light intensity from sensor"""
        light = self.device_manager.read_light_intensity()
        self._last_light = light
        return light

    def refresh_all(self) -> dict:
        """Refresh all sensor readings"""
        temp, hum = self.get_temperature_humidity()
        light = self.get_light_intensity()
        
        return {
            "temperature": temp,
            "humidity": hum,
            "light_intensity": light
        }
