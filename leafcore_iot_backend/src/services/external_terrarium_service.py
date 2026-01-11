# src/services/external_terrarium_service.py
"""
External Terrarium Server Integration
Sends sensor data and settings to external terrarium server (31.11.238.45:8081)
"""
import requests
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from src.services.sensor_service import SensorService

logger = logging.getLogger(__name__)


class ExternalTerriumService:
    """Communicates with external Terrarium server"""
    
    # External terrarium server endpoints
    BASE_URL = "http://31.11.238.45:8081/terrarium"
    ENDPOINT_ADD_MODULE = f"{BASE_URL}/module"
    ENDPOINT_SEND_DATA = f"{BASE_URL}/dataTerrarium"
    
    TIMEOUT = 5
    
    def __init__(self, settings_service=None, sensor_service: Optional['SensorService'] = None):
        """Initialize with settings service and sensor service"""
        self.settings_service = settings_service
        self.sensor_service = sensor_service
    
    def add_module(self, device_name: str, device_type: str, user_id: Optional[int] = None, 
                   group_id: Optional[str] = None, status: str = "active", mode: str = "auto") -> bool:
        """
        Register a new module/device on the external server
        
        CreateModuleDto fields:
        - deviceName: str
        - type: str
        - userId: int (optional)
        - groupId: str (optional)
        - status: str
        - mode: str
        - lastEditDate: str (optional)
        - isRegistered: bool
        """
        try:
            module_data = {
                "deviceName": device_name,
                "type": device_type,
                "status": status,
                "mode": mode,
                "isRegistered": False
            }
            
            if user_id is not None:
                module_data["userId"] = user_id
            if group_id is not None:
                module_data["groupId"] = group_id
            
            response = requests.post(
                self.ENDPOINT_ADD_MODULE,
                json=module_data,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"✅ Module registered: {device_name} ({device_type})")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error registering module {device_name}: {e}")
            return False
    
    def send_sensor_data(self) -> bool:
        """
        Send current sensor readings to Terrarium server
        
        TerrariumDataDto fields:
        - temperature: double
        - moisture: double
        - brightness: double
        - timestamp: LocalDateTime (ISO format)
        """
        if not self.sensor_service:
            logger.warning("SensorService not initialized, skipping sensor data upload")
            return False
        
        try:
            # Read current sensor values
            temp = self.sensor_service.get_temperature()
            humidity = self.sensor_service.get_humidity()
            light = self.sensor_service.get_light_intensity()
            
            # If any sensor is None, skip upload
            if temp is None or humidity is None or light is None:
                logger.warning(f"Sensor data incomplete: temp={temp}, hum={humidity}, light={light}")
                return False
            
            # Create TerrariumDataDto
            sensor_data = {
                "temperature": float(temp),
                "moisture": float(humidity),
                "brightness": float(light),
                "timestamp": datetime.now().isoformat()
            }
            
            # Send POST request
            response = requests.post(
                self.ENDPOINT_SEND_DATA,
                json=sensor_data,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"Posted sensor data: T={temp}°C, H={humidity}%, B={light}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending sensor data: {e}")
            return False
