# src/services/sensor_service.py
"""
Sensor reading and processing service
Reads from SensorReadingService cache (2s interval background update)
"""
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.devices import DeviceManager
    from src.services.sensor_reading_service import SensorReadingService


class SensorService:
    """
    Manages sensor readings and processing
    
    ⚠️ IMPORTANT: This service reads from SensorReadingService cache, NOT from hardware directly.
    SensorReadingService is the single source of truth for sensor data (updates every 2s).
    This ensures consistent readings across the app.
    """
    
    def __init__(self, device_manager: 'DeviceManager', 
                 sensor_reading_service: Optional['SensorReadingService'] = None):
        """
        Initialize sensor service
        
        Args:
            device_manager: DeviceManager instance
            sensor_reading_service: SensorReadingService instance (for cache reads)
        """
        self.device_manager = device_manager
        self.sensor_reading_service = sensor_reading_service
        
        # Cached values (updated by SensorReadingService)
        self._last_temp: Optional[float] = None
        self._last_hum: Optional[float] = None
        self._last_light: Optional[float] = None
    
    # ========== TEMPERATURE & HUMIDITY ==========
    
    def get_temperature_humidity(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get current temperature and humidity from SensorReadingService cache
        Falls back to direct reading if SensorReadingService not available
        """
        if self.sensor_reading_service:
            # Read from SensorReadingService cache (updated every 2s)
            data = self.sensor_reading_service.get_sensor_data()
            self._last_temp = data.get("temperature")
            self._last_hum = data.get("humidity")
        else:
            # Fallback: direct reading (should not happen in normal operation)
            self._last_temp, self._last_hum = self.device_manager.read_sensor()
        
        return self._last_temp, self._last_hum

    def get_temperature(self) -> Optional[float]:
        """Get current temperature from cache"""
        if self._last_temp is None and self.sensor_reading_service:
            self.get_temperature_humidity()  # Populate cache
        return self._last_temp

    def get_humidity(self) -> Optional[float]:
        """Get current humidity from cache"""
        if self._last_hum is None and self.sensor_reading_service:
            self.get_temperature_humidity()  # Populate cache
        return self._last_hum
    
    # ========== LIGHT INTENSITY ==========

    def get_light_intensity(self) -> Optional[float]:
        """
        Get current light intensity from SensorReadingService cache
        Falls back to direct reading if SensorReadingService not available
        """
        if self.sensor_reading_service:
            # Read from SensorReadingService cache (updated every 2s)
            data = self.sensor_reading_service.get_sensor_data()
            self._last_light = data.get("brightness")
        else:
            # Fallback: direct reading
            self._last_light = self.device_manager.read_light_intensity()
        
        return self._last_light
    
    # ========== REFRESH ALL ==========

    def refresh_all(self) -> dict:
        """Refresh all sensor readings from cache"""
        temp, hum = self.get_temperature_humidity()
        light = self.get_light_intensity()
        
        return {
            "temperature": temp,
            "humidity": hum,
            "light_intensity": light
        }

