# src/services/external_terrarium_service.py
"""
External Terrarium Server Integration
Sends settings to external terrarium server (172.19.14.15:8081)
"""
import requests
import logging
from typing import Dict, Any, Optional
from datetime import time

logger = logging.getLogger(__name__)


class ExternalTerriumService:
    """Communicates with external Terrarium server"""
    
    TERRARIUM_SERVER_URL = "http://31.11.238.45:8081/terrarium/dataTerrarium"
    TIMEOUT = 5
    
    # Fixed configuration for leafcore
    SETTING_ID = "67"
    PLANT_NAME = "six seven"
    
    def __init__(self, settings_service=None):
        """Initialize with settings service"""
        self.settings_service = settings_service
    
    def map_local_to_terrarium(self, local_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map our local settings format to TerriumDataSendDto format
        
        Local format:
        {
            "target_temp": 25,
            "target_hum": 60,
            "light_intensity": 50,
            "light_hours": 12,
            "water_times": 3,
            "water_seconds": 1
        }
        
        Terrarium format:
        {
            "setting_id": "67",
            "plant_name": "six seven",
            "optimal_temperature": 25.0,
            "optimal_humidity": 60.0,
            "optimal_brightness": 50.0,
            "light_schedule_start_time": "06:00",
            "light_schedule_end_time": "18:00",
            "watering_mode": "AUTO",
            "water_amount": 3,
            "light_intensity": 75.0,
            "DayOfWeek": ["MONDAY", "WEDNESDAY", "FRIDAY"]
        }
        """
        # Extract settings with defaults
        target_temp = float(local_settings.get("target_temp", 25.0))
        target_hum = float(local_settings.get("target_hum", 60.0))
        light_intensity = float(local_settings.get("light_intensity", 50.0))
        light_hours = float(local_settings.get("light_hours", 12.0))
        watering_days = local_settings.get("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        water_seconds = int(local_settings.get("water_seconds", 1))
        
        # Calculate light schedule times (assuming start at 06:00)
        light_start_hour = 6
        light_end_hour = (light_start_hour + int(light_hours)) % 24
        light_end_minute = int((light_hours % 1) * 60)
        
        # Format times
        start_time = f"{light_start_hour:02d}:00"
        end_time = f"{light_end_hour:02d}:{light_end_minute:02d}"
        
        # Build TerriumDataSendDto
        terrarium_data = {
            "setting_id": self.SETTING_ID,
            "plant_name": self.PLANT_NAME,
            "optimal_temperature": target_temp,
            "optimal_humidity": target_hum,
            "optimal_brightness": light_intensity,
            "light_schedule_start_time": start_time,
            "light_schedule_end_time": end_time,
            "watering_mode": "AUTO",
            "water_amount": len(watering_days),  # Number of watering days
            "light_intensity": light_intensity,
            "DayOfWeek": watering_days
        }
        
        return terrarium_data
    
    def send_settings(self, local_settings: Dict[str, Any]) -> bool:
        """
        Send local settings to external Terrarium server
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Map local settings to Terrarium format
            terrarium_data = self.map_local_to_terrarium(local_settings)
            
            # Send POST request
            response = requests.post(
                self.TERRARIUM_SERVER_URL,
                json=terrarium_data,
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
