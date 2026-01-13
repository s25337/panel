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
    
    def __init__(self, device_manager, control_service, settings_service):
        """
        Args:
            device_manager: DeviceManager instance with hardware backend
            control_service: ControlService for device state management
            settings_service: SettingsService for settings and sensor data
        """
        self.device_manager = device_manager
        self.control_service = control_service
        self.settings_service = settings_service
        
        self._running = False
        self._automation_thread: Optional[threading.Thread] = None
        
        print("✅ GPIOAutomationService.__init__() called")
    
    def start(self):
        """Start the automation loop in background thread"""
        if self._running:
            print("⚠ GPIOAutomationService already running")
            return
        
        self._running = True
        self._automation_thread = threading.Thread(
            target=self._automation_loop,
            daemon=True
        )
        self._automation_thread.start()
        print("🚀 GPIOAutomationService.start() - background thread launched!")
    
    def stop(self):
        """Stop the automation loop"""
        self._running = False
        if self._automation_thread:
            self._automation_thread.join(timeout=2.0)
        print("🛑 GPIOAutomationService.stop() - automation stopped")
    
    def _automation_loop(self):
        """
        Main automation loop
        Runs continuously, checking sensor data and updating device states
        """
        print(f"[GPIO Automation] Loop started at {datetime.now().isoformat()}")
        
        while self._running:
            try:
                # Get latest sensor data
                sensor_data = self.settings_service.get_sensor_data()
                print(f"[GPIO] Sensor data: {sensor_data}")
                
                if sensor_data:
                    # Latest sensor reading (usually first in list)
                    sensor = sensor_data[0] if isinstance(sensor_data, list) else sensor_data
                    
                    temp = sensor.get('temperature')
                    humid = sensor.get('humidity')
                    bright = sensor.get('brightness')
                    
                    print(f"[GPIO] Got readings: temp={temp}, humid={humid}, bright={bright}")
                    
                    # Let control_service handle ALL auto-mode devices (heater, fan, sprinkler, light)
                    result = self.control_service.update_auto_devices(temp, humid, bright)
                    print(f"[GPIO] Update result: {result}")
                else:
                    print(f"[GPIO] No sensor data available")
                
                # Sleep before next cycle (10 seconds = responsive but not CPU intensive)
                for _ in range(10):
                    if not self._running:
                        break
                    time.sleep(0.1)
            
            except Exception as e:
                print(f"[GPIO] Automation loop error: {e}")
                time.sleep(1.0)
