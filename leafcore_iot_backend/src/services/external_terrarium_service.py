# src/services/external_terrarium_service.py
"""
External Terrarium Server Integration
Sends sensor data and settings to external terrarium server (31.11.238.45:8081)
"""
import requests
import logging
import threading
import time
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
    SYNC_INTERVAL = 300  # 5 minutes in seconds
    
    def __init__(self, settings_service=None, sensor_service: Optional['SensorService'] = None, 
                 sensor_reading_service=None):
        """Initialize with settings service and sensor service"""
        self.settings_service = settings_service
        self.sensor_service = sensor_service
        self.sensor_reading_service = sensor_reading_service
        
        # Background sync thread
        self._sync_running = False
        self._sync_thread: Optional[threading.Thread] = None
    
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
    
    def send_sensor_data_by_group(self, group_id: str) -> bool:
        """
        Send last 5 minutes of sensor data to group-specific endpoint
        Gets data from sensor_reading_service cache (updated every 2 seconds)
        """
        if not self.sensor_reading_service:
            logger.warning("SensorReadingService not initialized, cannot get historical data")
            return False
        
        try:
            # Get last 5 minutes of sensor data from cache
            recent_data = self.sensor_reading_service.get_recent_sensor_history(minutes=5)
            
            if not recent_data:
                logger.warning("No sensor data available in last 5 minutes")
                return False
            
            # Ensure all readings have required fields in correct format
            formatted_data = []
            for entry in recent_data:
                formatted_entry = {
                    "temperature": float(entry.get('temperature', 0)),
                    "moisture": float(entry.get('humidity', 0)),  # humidity → moisture
                    "brightness": float(entry.get('brightness', 0)),
                    "timestamp": entry.get('timestamp', datetime.now().isoformat())
                }
                formatted_data.append(formatted_entry)
            
            # Send array of sensor readings
            endpoint = f"{self.ENDPOINT_SEND_DATA}/{group_id}"
            response = requests.post(
                endpoint,
                json=formatted_data,  # Send array of readings
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"✅ Posted {len(formatted_data)} sensor readings to group '{group_id}' (last 5 min)")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending sensor data to group '{group_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error in send_sensor_data_by_group: {e}")
            return False
    
    # ========== BACKGROUND SYNC (5 MINUTES) ==========
    
    def start_background_sync(self, group_id: str = "group-A1"):
        """
        Start background task to send sensor data every 5 minutes
        
        Args:
            group_id: Group ID to send data to (default: group-A1)
        """
        if self._sync_running:
            logger.warning("Background sync already running")
            return
        
        self._sync_running = True
        self._group_id = group_id
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            daemon=True
        )
        self._sync_thread.start()
        logger.info(f"🚀 Background sync started (interval: {self.SYNC_INTERVAL}s to group '{group_id}')")
    
    def stop_background_sync(self):
        """Stop background sync task"""
        self._sync_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=2.0)
        logger.info("🛑 Background sync stopped")
    
    def _background_sync_loop(self):
        """
        Background loop: send sensor data every 5 minutes
        Uses efficient chunked sleep to respond to stop signal
        """
        logger.info(f"[Sync] Background loop started - will sync every {self.SYNC_INTERVAL}s")
        
        while self._sync_running:
            try:
                # Send sensor data to group endpoint
                self.send_sensor_data_by_group(self._group_id)
                
                # Sleep in 1-second chunks so we can respond to stop signal quickly
                for _ in range(self.SYNC_INTERVAL):
                    if not self._sync_running:
                        break
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"[Sync] Background loop error: {e}")
                time.sleep(5)  # Brief delay before retry
