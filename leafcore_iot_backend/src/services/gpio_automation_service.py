# src/services/gpio_automation_service.py
"""
GPIO Automation Service for Hardware Backend
Implements auto-mode control based on sensor readings (temperature, humidity, light)
Pairs with HardwareBackend (GPIOdBackend) for Orange Pi Zero 2W
"""
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime


class GPIOAutomationService:
    """
    Runs auto-mode automation loop for hardware devices
    - Light: on/off based on schedule + PWM intensity from brightness sensor
    - Fan: on/off based on temperature and humidity
    - Heater: on/off based on temperature
    - Sprinkler: on/off based on humidity
    """
    
    def __init__(self, device_manager, control_service, settings_service, sensor_reading_service=None):
        """
        Args:
            device_manager: DeviceManager instance with hardware backend
            control_service: ControlService for device state management
            settings_service: SettingsService for settings and sensor data
            sensor_reading_service: SensorReadingService for latest sensor readings
        """
        self.device_manager = device_manager
        self.control_service = control_service
        self.settings_service = settings_service
        self.sensor_reading_service = sensor_reading_service
        
        self._running = False
        self._automation_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the automation loop in background thread"""
        if self._running:
            return
        
        self._running = True
        self._automation_thread = threading.Thread(
            target=self._automation_loop,
            daemon=True
        )
        self._automation_thread.start()
    
    def stop(self):
        """Stop the automation loop"""
        self._running = False
        if self._automation_thread:
            self._automation_thread.join(timeout=2.0)
    
    def _automation_loop(self):
        """
        Main automation loop
        Reads sensors every 2s, logs every 10s
        """
        log_counter = 0
        
        while self._running:
            try:
                # Get latest sensor data from SensorReadingService
                if not self.sensor_reading_service:
                    time.sleep(2)
                    continue
                
                sensor_data = self.sensor_reading_service.get_sensor_data()
                
                if sensor_data:
                    temp = sensor_data.get('temperature')
                    humid = sensor_data.get('humidity')
                    bright = sensor_data.get('brightness')
                    
                    # Let control_service handle ALL auto-mode devices
                    result = self.control_service.update_auto_devices(temp, humid, bright)
                    
                    # Log only every 5 cycles (5 * 2s = 10s)
                    log_counter += 1
                    if log_counter >= 5:
                        print(f"[Sensors] temp={temp}°C, humid={humid}%, light={bright}")
                        log_counter = 0
                
                # Sleep 2 seconds before next read
                time.sleep(2)
            
            except Exception as e:
                time.sleep(1.0)
