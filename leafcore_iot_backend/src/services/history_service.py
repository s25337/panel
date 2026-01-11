# src/services/history_service.py
"""
History Service
Stores and manages sensor data history (last 24 hours)
Periodically saves to disk for persistence across restarts
"""
import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

if TYPE_CHECKING:
    from src.services.sensor_service import SensorService

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Manages sensor data history (24-hour rolling window)
    
    Features:
    - In-memory circular buffer (last 24 hours)
    - Persistent storage to JSON file
    - Background thread to capture data every 60 seconds
    - Automatic cleanup of data older than 24 hours
    """
    
    # Store data point every 30 minutes
    CAPTURE_INTERVAL = 30 * 60  # seconds (30 minutes)
    
    # Keep data for 24 hours
    HISTORY_DURATION = 24 * 60 * 60  # seconds
    
    # Max data points (24h / 30min = 48 points)
    MAX_POINTS = int(HISTORY_DURATION / CAPTURE_INTERVAL)
    
    def __init__(self, sensor_service: Optional['SensorService'] = None, data_dir: str = "."):
        """
        Initialize history service
        
        Args:
            sensor_service: SensorService to read current values
            data_dir: Directory to store history JSON file
        """
        self.sensor_service = sensor_service
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.history_file = self.data_dir / "sensor_history.json"
        
        # In-memory circular buffers for each sensor
        self.temperature_history: deque = deque(maxlen=self.MAX_POINTS)
        self.humidity_history: deque = deque(maxlen=self.MAX_POINTS)
        self.brightness_history: deque = deque(maxlen=self.MAX_POINTS)
        self.timestamps: deque = deque(maxlen=self.MAX_POINTS)
        
        # Background thread
        self._background_thread = None
        self._running = False
        
        # Load existing history from disk
        self._load_history_from_disk()
    
    def _load_history_from_disk(self) -> None:
        """Load history from JSON file if it exists"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # Only load data from last 24 hours
                cutoff_time = datetime.now() - timedelta(seconds=self.HISTORY_DURATION)
                
                for entry in data:
                    try:
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if entry_time > cutoff_time:
                            self.temperature_history.append(entry['temperature'])
                            self.humidity_history.append(entry['humidity'])
                            self.brightness_history.append(entry['brightness'])
                            self.timestamps.append(entry['timestamp'])
                    except (ValueError, KeyError):
                        continue
                
                logger.info(f"📂 Loaded {len(self.timestamps)} history points from disk")
            else:
                logger.info("📂 No existing history file found, starting fresh")
        
        except Exception as e:
            logger.error(f"❌ Error loading history from disk: {e}")
    
    def _save_history_to_disk(self) -> None:
        """Save current history to JSON file"""
        try:
            data = []
            for i, timestamp in enumerate(self.timestamps):
                data.append({
                    "timestamp": timestamp,
                    "temperature": self.temperature_history[i],
                    "humidity": self.humidity_history[i],
                    "brightness": self.brightness_history[i]
                })
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"💾 Saved {len(data)} history points to disk")
        
        except Exception as e:
            logger.error(f"❌ Error saving history to disk: {e}")
    
    def add_data_point(self, temperature: float, humidity: float, brightness: float) -> None:
        """
        Add a new data point to history
        
        Args:
            temperature: Temperature reading
            humidity: Humidity reading
            brightness: Brightness reading
        """
        try:
            timestamp = datetime.now().isoformat()
            
            self.temperature_history.append(temperature)
            self.humidity_history.append(humidity)
            self.brightness_history.append(brightness)
            self.timestamps.append(timestamp)
            
            logger.debug(f"✅ Added history point: T={temperature}°C, H={humidity}%, B={brightness}")
        
        except Exception as e:
            logger.error(f"❌ Error adding history point: {e}")
    
    def get_history(self) -> Dict[str, Any]:
        """
        Get complete history data (24 hours)
        
        Returns:
            Dict with temperature, humidity, brightness, and timestamps
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "temperature": list(self.temperature_history),
            "humidity": list(self.humidity_history),
            "brightness": list(self.brightness_history),
            "timestamps": list(self.timestamps),
            "count": len(self.timestamps)
        }
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the latest data point"""
        if not self.timestamps:
            return None
        
        return {
            "timestamp": self.timestamps[-1],
            "temperature": self.temperature_history[-1],
            "humidity": self.humidity_history[-1],
            "brightness": self.brightness_history[-1]
        }
    
    def get_average(self) -> Optional[Dict[str, float]]:
        """Get average values for last 24 hours"""
        if not self.timestamps:
            return None
        
        return {
            "temperature": sum(self.temperature_history) / len(self.temperature_history),
            "humidity": sum(self.humidity_history) / len(self.humidity_history),
            "brightness": sum(self.brightness_history) / len(self.brightness_history)
        }
    
    def get_min_max(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Get min/max values for last 24 hours"""
        if not self.timestamps:
            return None
        
        return {
            "temperature": {
                "min": min(self.temperature_history),
                "max": max(self.temperature_history)
            },
            "humidity": {
                "min": min(self.humidity_history),
                "max": max(self.humidity_history)
            },
            "brightness": {
                "min": min(self.brightness_history),
                "max": max(self.brightness_history)
            }
        }
    
    # ========== BACKGROUND DATA CAPTURE ==========
    
    def start_background_capture(self) -> None:
        """
        Start background thread to capture sensor data every 60 seconds
        """
        if self._running:
            logger.warning("⚠️ Background capture already running")
            return
        
        if not self.sensor_service:
            logger.warning("⚠️ SensorService not available, cannot start background capture")
            return
        
        self._running = True
        self._background_thread = threading.Thread(
            target=self._background_capture_loop,
            daemon=True,
            name="HistoryCapture"
        )
        self._background_thread.start()
        logger.info(f"🚀 Started background history capture (interval: {self.CAPTURE_INTERVAL}s)")
    
    def stop_background_capture(self) -> None:
        """Stop background capture thread"""
        if not self._running:
            logger.warning("⚠️ Background capture not running")
            return
        
        self._running = False
        if self._background_thread:
            self._background_thread.join(timeout=5)
        
        # Save history before shutdown
        self._save_history_to_disk()
        logger.info("⏹️ Stopped background history capture and saved to disk")
    
    def _background_capture_loop(self) -> None:
        """Background thread loop - captures sensor data every 60 seconds"""
        logger.debug("🔄 Background history capture loop started")
        
        while self._running:
            try:
                # Wait before first capture
                time.sleep(self.CAPTURE_INTERVAL)
                
                if not self._running:
                    break
                
                # Read sensor values
                temp = self.sensor_service.get_temperature()
                humidity = self.sensor_service.get_humidity()
                light = self.sensor_service.get_light_intensity()
                
                # Only add if all values are available
                if temp is not None and humidity is not None and light is not None:
                    self.add_data_point(
                        temperature=float(temp),
                        humidity=float(humidity),
                        brightness=float(light)
                    )
                    
                    # Save to disk every 10 captures (10 minutes)
                    if len(self.timestamps) % 10 == 0:
                        self._save_history_to_disk()
                else:
                    logger.warning(f"⚠️ Incomplete sensor data: T={temp}, H={humidity}, L={light}")
            
            except Exception as e:
                logger.error(f"❌ Background capture error: {e}")
                time.sleep(5)  # Wait before retry
        
        logger.debug("🔄 Background history capture loop stopped")
