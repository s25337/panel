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
    ENDPOINT_UPDATE_SETTING = f"{BASE_URL}/updateSetting"
    
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
        self._group_id: Optional[str] = None
    
    def _map_terrarium_to_local_settings(self, terrarium_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Terrarium server settings format to local settings format
        
        Terrarium format:
        - setting_id
        - plant_name
        - optimal_temperature → target_temp
        - optimal_humidity → target_hum
        - optimal_brightness (ignored, we use light_intensity)
        - light_schedule_start_time → start_hour (extract hour)
        - light_schedule_end_time → end_hour (extract hour)
        - watering_mode
        - water_amount → water_seconds
        - light_intensity
        - dayOfWeek → watering_days
        """
        local_settings = {}
        
        # Direct mappings
        if "setting_id" in terrarium_settings:
            local_settings["setting_id"] = str(terrarium_settings["setting_id"])
        
        if "plant_name" in terrarium_settings:
            local_settings["plant_name"] = terrarium_settings["plant_name"]
        
        if "optimal_temperature" in terrarium_settings:
            local_settings["target_temp"] = float(terrarium_settings["optimal_temperature"])
        
        if "optimal_humidity" in terrarium_settings:
            local_settings["target_hum"] = float(terrarium_settings["optimal_humidity"])
        
        if "light_intensity" in terrarium_settings:
            local_settings["light_intensity"] = float(terrarium_settings["light_intensity"])
        
        if "watering_mode" in terrarium_settings:
            local_settings["watering_mode"] = terrarium_settings["watering_mode"]
        
        if "water_amount" in terrarium_settings:
            local_settings["water_seconds"] = int(terrarium_settings["water_amount"])
        
        # Parse time strings (HH:MM format)
        if "light_schedule_start_time" in terrarium_settings:
            try:
                start_time = str(terrarium_settings["light_schedule_start_time"])
                start_hour = int(start_time.split(":")[0])
                local_settings["start_hour"] = start_hour
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse start_time: {terrarium_settings['light_schedule_start_time']}: {e}")
        
        if "light_schedule_end_time" in terrarium_settings:
            try:
                end_time = str(terrarium_settings["light_schedule_end_time"])
                end_hour = int(end_time.split(":")[0])
                local_settings["end_hour"] = end_hour
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse end_time: {terrarium_settings['light_schedule_end_time']}: {e}")
        
        # Map dayOfWeek array
        if "dayOfWeek" in terrarium_settings:
            days = terrarium_settings["dayOfWeek"]
            if isinstance(days, list):
                local_settings["watering_days"] = days
        
        return local_settings
    
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
        Gets data from sensor_data_history.json (maintained by SensorReadingService)
        """
        if not self.sensor_reading_service:
            logger.warning("SensorReadingService not initialized, cannot get historical data")
            return False
        
        try:
            # Get last 5 minutes of sensor data from history
            recent_data = self.sensor_reading_service.get_recent_sensor_history(minutes=5)
            
            logger.info(f"[5-min Sync] Readings count: {len(recent_data)}")
            if recent_data and len(recent_data) > 0:
                logger.info(f"[5-min Sync] Newest: {recent_data[0].get('timestamp')} | Oldest: {recent_data[-1].get('timestamp')}")
            
            if not recent_data:
                logger.warning(f"[5-min Sync] No sensor history available (history file might not exist yet)")
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
            
            logger.info(f"✅ [5-min Sync] Posted {len(formatted_data)} sensor readings to group '{group_id}'")
            
            # Extract ALL settings from response and update locally
            try:
                response_data = response.json()
                if isinstance(response_data, dict):
                    logger.debug(f"[5-min Sync] Server response received")
                    
                    # Map Terrarium format to local format
                    mapped_settings = self._map_terrarium_to_local_settings(response_data)
                    
                    if mapped_settings and self.settings_service:
                        # Update all settings at once
                        self.settings_service.update_settings(mapped_settings)
                        logger.info(f"[5-min Sync] ✅ Updated local settings: {list(mapped_settings.keys())}")
                    else:
                        logger.debug("[5-min Sync] No settings to update")
            except (ValueError, KeyError) as e:
                logger.debug(f"[5-min Sync] Could not extract settings from response: {e}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [5-min Sync] Error sending sensor data to group '{group_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [5-min Sync] Unexpected error in send_sensor_data_by_group: {e}")
            return False
    
    def send_initial_history_file(self, group_id: str) -> bool:
        """
        Send entire sensor_data_history.json file on server startup
        Called once when the server starts to sync all available historical data
        
        Args:
            group_id: Group ID to send data to
        
        Returns:
            True if successful, False otherwise
        """
        if not self.sensor_reading_service:
            logger.warning("[STARTUP] SensorReadingService not initialized, cannot send history file")
            return False
        
        try:
            # Get all available sensor history
            recent_data = self.sensor_reading_service.get_recent_sensor_history(minutes=5)
            
            if not recent_data:
                logger.warning("[STARTUP] No sensor history available to send")
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
                json=formatted_data,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"✅ [STARTUP] Successfully sent {len(formatted_data)} historical readings to group '{group_id}'")
            logger.info(f"[STARTUP] First reading: {formatted_data[0]['timestamp']} | Last reading: {formatted_data[-1]['timestamp']}")
            
            # Extract ALL settings from response and update locally
            try:
                response_data = response.json()
                if isinstance(response_data, dict):
                    logger.info(f"[STARTUP] Server response: {response_data}")
                    
                    # Map Terrarium format to local format
                    mapped_settings = self._map_terrarium_to_local_settings(response_data)
                    
                    if mapped_settings and self.settings_service:
                        # Update all settings at once
                        self.settings_service.update_settings(mapped_settings)
                        logger.info(f"[STARTUP] ✅ Updated local settings from server: {list(mapped_settings.keys())}")
                        logger.info(f"[STARTUP] Setting_id: {mapped_settings.get('setting_id')}, Plant: {mapped_settings.get('plant_name')}")
                    else:
                        logger.warning("[STARTUP] settings_service not available, cannot update settings")
            except (ValueError, KeyError) as e:
                logger.debug(f"[STARTUP] Could not extract settings from response: {e}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [STARTUP] Network error sending history file to group '{group_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [STARTUP] Unexpected error sending history file: {e}")
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
            daemon=False  # Not a daemon thread so it keeps running
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
        print(f"[Sync] Background loop started - will sync every {self.SYNC_INTERVAL}s")
        logger.info(f"[Sync] Background loop started - will sync every {self.SYNC_INTERVAL}s")
        
        iteration = 0
        while self._sync_running:
            iteration += 1
            try:
                # Log that we're about to send data
                print(f"[5-min Sync] ⏰ Starting periodic sync at {datetime.now().isoformat()}")
                logger.info(f"[5-min Sync] ⏰ Starting periodic sync at {datetime.now().isoformat()}")
                
                # Send sensor data to group endpoint
                result = self.send_sensor_data_by_group(self._group_id)
                
                if result:
                    print(f"[5-min Sync] ✅ Periodic sync completed successfully")
                    logger.info(f"[5-min Sync] ✅ Periodic sync completed successfully")
                else:
                    print(f"[5-min Sync] ⚠️ Periodic sync completed with warnings")
                    logger.warning(f"[5-min Sync] ⚠️ Periodic sync completed with warnings")
                
                # Sleep in 1-second chunks so we can respond to stop signal quickly
                # Log countdown every 60 seconds
                for i in range(self.SYNC_INTERVAL):
                    if not self._sync_running:
                        break
                    # Log every 60 seconds
                    if i > 0 and i % 60 == 0:
                        remaining = self.SYNC_INTERVAL - i
                        print(f"[5-min Sync] ⏳ Waiting... {remaining}s until next sync")
                        logger.info(f"[5-min Sync] ⏳ Waiting... {remaining}s until next sync")
                    time.sleep(1)
            
            except Exception as e:
                print(f"[Sync] Background loop error: {e}")
                logger.error(f"[Sync] Background loop error: {e}")
                time.sleep(5)  # Brief delay before retry
    
    # ========== SETTINGS SYNC ==========
    
    def _map_local_to_terrarium_settings(self, local_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local settings format to Terrarium server format
        
        Local format → Terrarium format mapping:
        - target_temp → optimal_temperature
        - target_hum → optimal_humidity
        - light_intensity → optimal_brightness (also keep light_intensity)
        - start_hour, end_hour → light_schedule_start_time, light_schedule_end_time
        - water_seconds → water_amount
        - watering_days → dayOfWeek
        
        Args:
            local_settings: Dictionary of local settings
        
        Returns:
            Dictionary in Terrarium format
        """
        terrarium_settings = {}
        
        # Direct mappings
        if "setting_id" in local_settings:
            terrarium_settings["setting_id"] = str(local_settings["setting_id"])
        if "plant_name" in local_settings:
            terrarium_settings["plant_name"] = local_settings["plant_name"]
        if "watering_mode" in local_settings:
            terrarium_settings["watering_mode"] = local_settings["watering_mode"]
        
        # Temperature mapping
        if "target_temp" in local_settings:
            terrarium_settings["optimal_temperature"] = float(local_settings["target_temp"])
        
        # Humidity mapping
        if "target_hum" in local_settings:
            terrarium_settings["optimal_humidity"] = float(local_settings["target_hum"])
        
        # Light intensity mapping
        if "light_intensity" in local_settings:
            light_val = float(local_settings["light_intensity"])
            terrarium_settings["optimal_brightness"] = light_val
            terrarium_settings["light_intensity"] = light_val
        
        # Light schedule mapping (hours → HH:MM format)
        if "start_hour" in local_settings and "end_hour" in local_settings:
            start_hour = int(local_settings["start_hour"])
            end_hour = int(local_settings["end_hour"])
            terrarium_settings["light_schedule_start_time"] = f"{start_hour:02d}:00"
            terrarium_settings["light_schedule_end_time"] = f"{end_hour:02d}:00"
        
        # Water mapping
        if "water_seconds" in local_settings:
            terrarium_settings["water_amount"] = int(local_settings["water_seconds"])
        
        # Watering days mapping
        if "watering_days" in local_settings:
            terrarium_settings["dayOfWeek"] = local_settings["watering_days"]
        
        return terrarium_settings
    
    def send_settings(self, settings: Dict[str, Any], group_id: str = "group-A1") -> bool:
        """
        Send settings to external Terrarium server
        Called whenever settings are updated
        Automatically converts local settings format to Terrarium format
        
        Args:
            settings: Dictionary of settings to send (local format)
            group_id: Group ID to send settings to
        
        Returns:
            True if successful, False otherwise
        """
        if not settings:
            logger.warning("[Settings] No settings to send")
            return False
        
        try:
            # Convert local settings format to Terrarium format
            logger.debug(f"[Settings] Converting settings: {list(settings.keys())}")
            terrarium_settings = self._map_local_to_terrarium_settings(settings)
            
            if not terrarium_settings:
                logger.warning("[Settings] No settings to send after mapping")
                return False
            
            logger.debug(f"[Settings] Converted settings: {terrarium_settings}")
            
            # Send settings to group endpoint
            endpoint = f"{self.ENDPOINT_UPDATE_SETTING}/{group_id}"
            logger.info(f"[Settings] 🚀 Sending to {endpoint}")
            response = requests.post(
                endpoint,
                json=terrarium_settings,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"✅ [Settings] Sent {len(terrarium_settings)} setting(s) to group '{group_id}': {list(terrarium_settings.keys())}")
            
            # Extract setting_id from response and update locally
            try:
                response_data = response.json()
                if isinstance(response_data, dict) and "setting_id" in response_data:
                    remote_setting_id = str(response_data.get("setting_id"))
                    logger.info(f"[Settings] Received setting_id from server: {remote_setting_id}")
                    
                    # Update local settings with server's setting_id
                    if self.settings_service:
                        self.settings_service.set_setting("setting_id", remote_setting_id)
                        logger.info(f"[Settings] ✅ Updated local setting_id to: {remote_setting_id}")
                    else:
                        logger.warning("[Settings] settings_service not available, cannot update setting_id")
            except (ValueError, KeyError) as e:
                logger.debug(f"[Settings] Could not extract setting_id from response: {e}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [Settings] Error sending settings to group '{group_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [Settings] Unexpected error sending settings: {e}")
            return False
    
    def notify_settings_changed(self, updated_settings: Dict[str, Any], group_id: str = "group-A1"):
        """
        Callback to notify external server when settings are changed
        This should be called from SettingsService whenever settings are updated
        
        Args:
            updated_settings: Dictionary of updated settings
            group_id: Group ID to send settings to
        """
        logger.info(f"[Settings Change] 🔔 Settings changed - sending to server")
        logger.info(f"[Settings Change] Updated fields: {list(updated_settings.keys())}")
        logger.info(f"[Settings Change] Values: {updated_settings}")
        
        # Send settings in background to avoid blocking the API call
        def send_in_background():
            logger.info(f"[Settings Change] 📤 Sending updated settings to {group_id}...")
            result = self.send_settings(updated_settings, group_id)
            logger.info(f"[Settings Change] ✅ Settings sent - result: {result}")
        
        threading.Thread(
            target=send_in_background,
            daemon=True
        ).start()
