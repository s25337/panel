# src/services/sensor_reading_service.py
"""
Sensor Reading Service - continuous sensor data collection and posting
Reads sensors every 2 seconds and POSTs to cloud + local servers
"""
import os
import json
import time
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from src.devices import DeviceManager


class SensorReadingService:
    """Background service for continuous sensor reading and cloud posting"""
    
    # Server endpoints
    CLOUD_URL = "http://33.11.238.45:8081/terrarium"
    LOCAL_URL = "http://172.19.14.15:8080/terrarium/dataTerrarium"  # Match sync_service.py
    READ_INTERVAL = 2.0  # Read every 2 seconds
    
    def __init__(self, device_manager: DeviceManager, app_dir: str = "."):
        """
        Initialize sensor reading service
        
        Args:
            device_manager: DeviceManager instance
            app_dir: Application directory for storing config files
        """
        self.device_manager = device_manager
        self.app_dir = app_dir
        self.source_files_dir = os.path.join(app_dir, "source_files")
        
        # Create source_files directory if needed
        os.makedirs(self.source_files_dir, exist_ok=True)
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_temp: Optional[float] = None
        self._last_humidity: Optional[float] = None
        self._last_brightness: Optional[float] = None
        self._last_post_time: float = time.time()
        
        # Load device info
        self._device_info = self._load_device_info()
    
    # ========== LIFECYCLE ==========
    
    def start(self):
        """Start sensor reading background thread"""
        if self._running:
            print("[SensorReadingService] Already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        print("[SensorReadingService] Started sensor reading loop (2s interval)")
    
    def stop(self):
        """Stop sensor reading background thread"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[SensorReadingService] Stopped")
    
    def _read_loop(self):
        """Main sensor reading loop"""
        while self._running:
            try:
                # Read sensors
                temp, humidity = self.device_manager.read_sensor()
                brightness = self.device_manager.read_light_intensity()
                
                self._last_temp = temp
                self._last_humidity = humidity
                self._last_brightness = brightness
                
                # Save to local JSON
                self._save_sensor_data(temp, humidity, brightness)
                
                # POST to servers (with rate limiting - post every 5 readings = 10s)
                if time.time() - self._last_post_time >= 10.0:
                    self._post_sensor_data(temp, humidity, brightness)
                    self._last_post_time = time.time()
                
                time.sleep(self.READ_INTERVAL)
            except Exception as e:
                print(f"[SensorReadingService] Error in read loop: {e}")
                time.sleep(self.READ_INTERVAL)
    
    # ========== SENSOR DATA I/O ==========
    
    def _save_sensor_data(self, temp: Optional[float], humidity: Optional[float], 
                         brightness: Optional[float]):
        """Save sensor data to JSON file"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "temperature": temp,
                "humidity": humidity,
                "brightness": brightness,
                "device_id": self._device_info.get("device_id", "unknown")
            }
            
            file_path = os.path.join(self.source_files_dir, "sensor_data.json")
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving sensor data: {e}")
    
    def _post_sensor_data(self, temp: Optional[float], humidity: Optional[float], 
                         brightness: Optional[float]):
        """POST sensor data to cloud and local servers"""
        if temp is None or humidity is None or brightness is None:
            return
        
        payload = {
            "device_id": self._device_info.get("device_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "temperature": float(temp),
            "humidity": float(humidity),
            "brightness": float(brightness),
            "status": "ok"
        }
        
        # Try posting to servers (non-blocking)
        for url_name, base_url in [("CLOUD", self.CLOUD_URL), ("LOCAL", self.LOCAL_URL)]:
            try:
                endpoint = f"{base_url}/sensor-data"
                response = requests.post(endpoint, json=payload, timeout=3.0)
                if response.status_code == 200:
                    print(f"✓ Posted sensor data to {url_name}")
                else:
                    print(f"⚠ {url_name} returned {response.status_code}")
            except Exception as e:
                print(f"⚠ Failed to post to {url_name}: {e}")
    
    # ========== CONFIG FILE MANAGEMENT ==========
    
    def _load_device_info(self) -> Dict[str, Any]:
        """Load device info from JSON config"""
        file_path = os.path.join(self.source_files_dir, "devices_info.json")
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading device info: {e}")
        
        # Default device info
        return {
            "device_id": "leafcore-001",
            "device_name": "Terrarium Panel",
            "location": "Local",
            "model": "Orange Pi Zero 2W",
            "version": "1.0.0"
        }
    
    def save_device_info(self, info: Dict[str, Any]):
        """Save device info to JSON config"""
        try:
            file_path = os.path.join(self.source_files_dir, "devices_info.json")
            with open(file_path, 'w') as f:
                json.dump(info, f, indent=2)
            self._device_info = info
            print(f"✓ Saved device info")
        except Exception as e:
            print(f"Error saving device info: {e}")
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device info"""
        return self._device_info.copy()
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get last sensor readings"""
        return {
            "temperature": self._last_temp,
            "humidity": self._last_humidity,
            "brightness": self._last_brightness,
            "timestamp": datetime.now().isoformat()
        }
