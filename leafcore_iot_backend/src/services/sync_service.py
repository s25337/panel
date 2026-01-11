import requests
import logging
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class SyncService:
    """Synchronizes settings with external cloud server"""
    
    def __init__(self, settings_service, app_dir: str = "."):
        self.settings_service = settings_service
        self.external_url = "http://172.19.14.15:8080/terrarium/dataTerrarium"
        self.timeout = 5  # seconds
        self.last_sync = None
        self.sync_interval = 30  # seconds between syncs
        self.running = False
        self.sync_thread = None
        self.app_dir = Path(app_dir)
        self.queue_file = self.app_dir / "sync_queue.json"
        self.last_server_state = {}
        
        # Offline change queue
        self.change_queue = Queue()
        self.load_offline_queue()
        
    def load_offline_queue(self):
        """Load offline changes from disk if they exist"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    changes = json.load(f)
                    for change in changes:
                        self.change_queue.put(change)
                    logger.info(f" Loaded {len(changes)} offline changes from queue")
        except Exception as e:
            logger.error(f"❌ Error loading offline queue: {e}")
    
    def save_offline_queue(self):
        """Save pending changes to disk"""
        try:
            changes = []
            temp_queue = Queue()
            
            # Extract all items from queue
            while not self.change_queue.empty():
                try:
                    change = self.change_queue.get_nowait()
                    changes.append(change)
                    temp_queue.put(change)
                except Empty:
                    break
            
            # Put items back
            while not temp_queue.empty():
                self.change_queue.put(temp_queue.get_nowait())
            
            # Save to file
            if changes:
                with open(self.queue_file, 'w') as f:
                    json.dump(changes, f, indent=2)
                logger.info(f"💾 Saved {len(changes)} changes to offline queue")
        except Exception as e:
            logger.error(f"❌ Error saving offline queue: {e}")
    
    def add_change_to_queue(self, change: Dict[str, Any]):
        """Add a local change to the offline queue for later sync"""
        change['timestamp'] = datetime.now().isoformat()
        self.change_queue.put(change)
        self.save_offline_queue()
        logger.debug(f"📝 Added change to queue: {change}")
        
        
    def fetch_from_external(self) -> Optional[Dict[str, Any]]:
        """
        Fetch settings from external server
        Returns parsed JSON or None if failed
        """
        try:
            response = requests.get(self.external_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            self.last_sync = datetime.now()
            logger.info("✅ Fetched settings from external server")
            return data
        except requests.exceptions.ConnectionError:
            logger.warning("❌ External server connection failed")
            return None
        except requests.exceptions.Timeout:
            logger.warning("❌ External server timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching from external server: {e}")
            return None
    
    def map_external_to_local(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map external server format to local settings format
        
        External format:
        {
            "optimal_temperature": 22.0,
            "optimal_humidity": 55.0,
            "optimal_light": 50.0,
            "light_schedule": {
                "start_time": "06:00",
                "end_time": "18:00"
            },
            "water_amount": 150,
            "scheduled_days": ["MONDAY", "THURSDAY"]
        }
        
        Local format:
        {
            "target_temp": 25,
            "target_hum": 60,
            "light_intensity": 50,
            "light_hours": 12,
            "water_seconds": 1,
            "water_times": 3
        }
        """
        local_settings = {}
        
        # Temperature
        if "optimal_temperature" in external_data:
            local_settings["target_temp"] = float(external_data["optimal_temperature"])
        
        # Humidity
        if "optimal_humidity" in external_data:
            local_settings["target_hum"] = float(external_data["optimal_humidity"])
        
        # Light intensity
        if "optimal_light" in external_data:
            local_settings["light_intensity"] = float(external_data["optimal_light"])
        
        # Light schedule - calculate light_hours from start_time and end_time
        if "light_schedule" in external_data:
            schedule = external_data["light_schedule"]
            if "start_time" in schedule and "end_time" in schedule:
                try:
                    start = datetime.strptime(schedule["start_time"], "%H:%M")
                    end = datetime.strptime(schedule["end_time"], "%H:%M")
                    hours = (end - start).total_seconds() / 3600
                    if hours > 0:
                        local_settings["light_hours"] = hours
                except ValueError:
                    logger.warning("Could not parse light_schedule times")
        
        # Watering
        if "water_amount" in external_data:
            # Map water_amount (ml) to water_seconds (rough estimate)
            # 150ml ≈ 1-2 seconds of pump runtime
            local_settings["water_seconds"] = max(1, int(external_data["water_amount"] / 100))
        
        if "scheduled_days" in external_data:
            # Count number of scheduled days = water_times per week
            local_settings["water_times"] = len(external_data["scheduled_days"])
        
        return local_settings
    
    def sync_external_to_local(self) -> bool:
        """
        Fetch from external server and update local settings
        Returns True if successful
        """
        external_data = self.fetch_from_external()
        if not external_data:
            return False
        
        local_settings = self.map_external_to_local(external_data)
        
        if local_settings:
            # Get current settings and update with external values
            current = self.settings_service.load_settings()
            current.update(local_settings)
            self.settings_service.save_settings(current)
            logger.info(f"✅ Updated local settings from external server: {local_settings}")
            return True
        
        return False
    
    def map_local_to_external(self, local_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map local settings back to external server format (for future use)
        """
        external_data = {
            "optimal_temperature": local_settings.get("target_temp", 25),
            "optimal_humidity": local_settings.get("target_hum", 60),
            "optimal_light": local_settings.get("light_intensity", 50),
            "light_schedule": {
                "start_time": "06:00",  # Could be configurable
                "end_time": "18:00"  # Could be calculated from light_hours
            },
            "water_amount": local_settings.get("water_seconds", 1) * 100,
            "scheduled_days": ["MONDAY", "THURSDAY"]  # Could come from database
        }
        return external_data
    
    def send_to_external(self, local_settings: Dict[str, Any]) -> bool:
        """
        Send local settings to external server (for future use)
        Returns True if successful
        """
        try:
            external_data = self.map_local_to_external(local_settings)
            response = requests.post(
                self.external_url,
                json=external_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("✅ Sent settings to external server")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending to external server: {e}")
            return False
    
    def resolve_conflict(self, local_setting: Dict[str, Any], 
                        external_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conflict resolution:
        - If external server has it, use external (server is source of truth)
        - If local is newer AND external is older, keep local
        
        Returns resolved setting
        """
        local_ts = local_setting.get('timestamp', '')
        external_ts = external_setting.get('timestamp', '')
        
        # Priority: External server is source of truth
        if external_ts:
            logger.debug(f"✅ Using external setting (priority), timestamp: {external_ts}")
            return external_setting
        else:
            logger.debug(f"✅ Using local setting, timestamp: {local_ts}")
            return local_setting
    
    def sync_queued_changes(self) -> bool:
        """
        Send all queued changes to external server
        Returns True if all sent successfully
        """
        all_success = True
        
        while not self.change_queue.empty():
            try:
                change = self.change_queue.get_nowait()
                success = self.send_to_external(change)
                
                if not success:
                    # Put back in queue if failed
                    self.change_queue.put(change)
                    all_success = False
                else:
                    logger.info(f"✅ Synced queued change: {change}")
                    
            except Empty:
                break
        
        self.save_offline_queue()
        return all_success
    
    def start_background_sync(self):
        """Start background sync thread (runs every 30 seconds)"""
        if self.running:
            logger.warning("⚠️ Background sync already running")
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("🔄 Background sync started (every 30s)")
    
    def stop_background_sync(self):
        """Stop background sync thread"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("🛑 Background sync stopped")
    
    def _sync_loop(self):
        """Background sync loop (runs in separate thread)"""
        while self.running:
            try:
                # 1. Sync queued changes to server
                self.sync_queued_changes()
                
                # 2. Fetch latest from external server
                external_data = self.fetch_from_external()
                if external_data:
                    local_settings = self.map_external_to_local(external_data)
                    
                    if local_settings:
                        # Get current settings
                        current = self.settings_service.load_settings()
                        
                        # Merge with conflict resolution
                        for key, external_value in local_settings.items():
                            if key in current:
                                # Conflict: resolve it
                                resolved = self.resolve_conflict(
                                    {'value': current[key], 'timestamp': self.last_sync},
                                    {'value': external_value, 'timestamp': datetime.now().isoformat()}
                                )
                                current[key] = resolved['value']
                            else:
                                current[key] = external_value
                        
                        self.settings_service.save_settings(current)
                        self.last_sync = datetime.now()
                        logger.debug(f"🔄 Background sync completed at {self.last_sync}")
                
                # Sleep before next sync
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in sync loop: {e}")
                time.sleep(self.sync_interval)  # Sleep even on error


