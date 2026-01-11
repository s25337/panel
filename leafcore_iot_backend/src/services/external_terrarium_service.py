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
    
    # Note: /dataTerrarium only accepts POST but returns 403 (likely Spring Security issue)
    # /sendData accepts GET and returns 200 OK - using this endpoint instead
    TERRARIUM_SERVER_URL = "http://31.11.238.45:8081/terrarium/sendData"
    TIMEOUT = 5
    
    # Fixed configuration for leafcore
    SETTING_ID = "67"
    PLANT_NAME = "six seven"
    
    def __init__(self, settings_service=None, sensor_service: Optional['SensorService'] = None):
        """Initialize with settings service and sensor service"""
        self.settings_service = settings_service
        self.sensor_service = sensor_service
        self._background_thread = None
        self._running = False
        self._sensor_upload_interval = 30  # seconds
    
    def map_local_to_terrarium(self, local_settings: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime
        
        # Extract settings with defaults
        target_temp = float(local_settings.get("target_temp", 25.0))
        target_hum = float(local_settings.get("target_hum", 60.0))
        light_intensity = float(local_settings.get("light_intensity", 50.0))
        
        # Convert to sensor data format
        terrarium_data = {
            "temperature": target_temp,
            "moisture": target_hum,
            "brightness": light_intensity,  
            "timestamp": datetime.now().isoformat()
        }
        
        return terrarium_data
    
    def send_settings(self, local_settings: Dict[str, Any]) -> bool:

        try:
            # Map local settings to Terrarium format
            terrarium_data = self.map_local_to_terrarium(local_settings)
            
            # Send GET request with query parameters
            response = requests.get(
                self.TERRARIUM_SERVER_URL,
                params=terrarium_data,
                timeout=self.TIMEOUT
            )
            
            response.raise_for_status()
            logger.info(f"✅ Sent settings to Terrarium server: {terrarium_data}")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Failed to connect to Terrarium server: {self.TERRARIUM_SERVER_URL}")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout connecting to Terrarium server (timeout={self.TIMEOUT}s)")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP error from Terrarium server: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending to Terrarium server: {e}")
            return False
    
    def send_current_settings(self) -> bool:
        """
        Send current settings from SettingsService to Terrarium server
        
        Returns:
            True if successful, False otherwise
        """
        if not self.settings_service:
            logger.error("❌ SettingsService not initialized")
            return False
        
        try:
            current_settings = self.settings_service.get_settings()
            return self.send_settings(current_settings)
        except Exception as e:
            logger.error(f"❌ Error sending current settings: {e}")
            return False
    
    def send_sensor_data(self) -> bool:
        """
        Send current sensor readings to Terrarium server
        Reads: temperature, humidity (moisture), light intensity (brightness)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.sensor_service:
            logger.warning("⚠️ SensorService not initialized, skipping sensor data upload")
            return False
        
        try:
            # Read current sensor values
            temp = self.sensor_service.get_temperature()
            humidity = self.sensor_service.get_humidity()
            light = self.sensor_service.get_light_intensity()
            
            # If any sensor is None, skip upload
            if temp is None or humidity is None or light is None:
                logger.warning(f"⚠️ Sensor data incomplete: temp={temp}, hum={humidity}, light={light}")
                return False
            
            # Convert to Terrarium format
            sensor_data = {
                "temperature": float(temp),
                "moisture": float(humidity),
                "brightness": float(light) * 10,  # Scale to 0-1000
                "timestamp": datetime.now().isoformat()
            }
            
            # Send GET request with sensor data
            response = requests.get(
                self.TERRARIUM_SERVER_URL,
                params=sensor_data,
                timeout=self.TIMEOUT
            )
            
            response.raise_for_status()
            logger.info(f"✅ Sent sensor data to Terrarium server: {sensor_data}")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Failed to connect to Terrarium server: {self.TERRARIUM_SERVER_URL}")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout connecting to Terrarium server (timeout={self.TIMEOUT}s)")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP error from Terrarium server: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending sensor data: {e}")
            return False
    
    # ========== BACKGROUND SENSOR UPLOAD ==========
    
    def start_background_sensor_upload(self) -> None:
        """
        Start background thread to upload sensor data every 30 seconds
        """
        if self._running:
            logger.warning("⚠️ Background sensor upload already running")
            return
        
        if not self.sensor_service:
            logger.warning("⚠️ SensorService not available, cannot start background upload")
            return
        
        self._running = True
        self._background_thread = threading.Thread(
            target=self._background_upload_loop,
            daemon=True,
            name="TerriumSensorUpload"
        )
        self._background_thread.start()
        logger.info(f"🚀 Started background sensor upload (interval: {self._sensor_upload_interval}s)")
    
    def stop_background_sensor_upload(self) -> None:
        """
        Stop background sensor upload thread
        """
        if not self._running:
            logger.warning("⚠️ Background sensor upload not running")
            return
        
        self._running = False
        if self._background_thread:
            self._background_thread.join(timeout=5)
        logger.info("⏹️ Stopped background sensor upload")
    
    def _background_upload_loop(self) -> None:
        """
        Background thread loop - uploads sensor data every 30 seconds
        """
        logger.debug("🔄 Background sensor upload loop started")
        
        while self._running:
            try:
                # Wait before first upload
                time.sleep(self._sensor_upload_interval)
                
                if not self._running:
                    break
                
                # Send sensor data
                self.send_sensor_data()
                
            except Exception as e:
                logger.error(f"❌ Background upload error: {e}")
                time.sleep(5)  # Wait before retry
        
        logger.debug("🔄 Background sensor upload loop stopped")
