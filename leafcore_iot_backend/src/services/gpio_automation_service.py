# src/services/gpio_automation_service.py
"""
GPIO Automation Service for Hardware Backend
Implements auto-mode control based on sensor readings (temperature, humidity, light)
Pairs with HardwareBackend (GPIOdBackend) for Orange Pi Zero 2W
"""
import time
import threading
import json
from pathlib import Path
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
                settings = self.settings_service.get_settings()
                modes = self.control_service.get_device_modes()
                
                if sensor_data:
                    # Latest sensor reading (usually first in list)
                    sensor = sensor_data[0] if isinstance(sensor_data, list) else sensor_data
                    
                    temp = sensor.get('temperature')
                    humid = sensor.get('humidity')
                    bright = sensor.get('brightness')
                    
                    # Get current time
                    current_time = datetime.now()
                    current_time_str = current_time.strftime("%H:%M")
                    
                    # ========== LIGHT AUTO-MODE ==========
                    light_mode = modes.get('light', {}).get('mode', 'manual')
                    if light_mode == 'auto':
                        try:
                            start_time = settings.get('start_hour', 6)
                            end_time = settings.get('end_hour', 22)
                            
                            # Convert hours to HH:MM format
                            start_str = f"{start_time:02d}:00"
                            end_str = f"{end_time:02d}:00"
                            
                            # Check if within light hours
                            if start_time <= end_time:
                                # Normal case: 6:00-22:00
                                is_light_time = start_str <= current_time_str <= end_str
                            else:
                                # Crossing midnight: 20:00-6:00
                                is_light_time = current_time_str >= start_str or current_time_str <= end_str
                            
                            if is_light_time:
                                # Light ON - calculate intensity from brightness sensor
                                if bright is not None:
                                    optimal_light = settings.get('light_intensity', 100.0)
                                    intensity = min(100.0, max(0.0, (bright / optimal_light) * 100.0))
                                else:
                                    intensity = 100.0
                                
                                self.control_service.set_light(intensity)
                                print(f"[GPIO] Light ON (auto): {intensity:.1f}%")
                            else:
                                # Light OFF
                                self.control_service.set_light(0)
                                print(f"[GPIO] Light OFF (auto)")
                        
                        except Exception as e:
                            print(f"[GPIO] Light auto-mode error: {e}")
                    
                    # ========== FAN AUTO-MODE ==========
                    fan_mode = modes.get('fan', {}).get('mode', 'manual')
                    if fan_mode == 'auto':
                        try:
                            fan_on = self.control_service.control_fan_auto(humid)
                            print(f"[GPIO] Fan {'ON' if fan_on else 'OFF'} (auto): humidity control")
                        
                        except Exception as e:
                            print(f"[GPIO] Fan auto-mode error: {e}")
                    
                    # ========== HEATER AUTO-MODE ==========
                    heater_mode = modes.get('heater', {}).get('mode', 'manual')
                    print(f"[GPIO] Heater mode: {heater_mode}, current temp: {temp}")
                    if heater_mode == 'auto':
                        try:
                            target_temp = settings.get('target_temp', 25.0)
                            print(f"[GPIO] Heater auto-mode: target_temp={target_temp}, current_temp={temp}")
                            
                            if temp is not None:
                                heater_on = temp < target_temp
                                self.control_service.set_heater(heater_on)
                                print(f"[GPIO] Heater {'ON' if heater_on else 'OFF'} (auto): temp {temp:.1f}°C {'<' if heater_on else '>'} {target_temp}°C")
                            
                        except Exception as e:
                            print(f"[GPIO] Heater auto-mode error: {e}")
                    
                    # ========== SPRINKLER AUTO-MODE ==========
                    sprinkler_mode = modes.get('sprinkler', {}).get('mode', 'manual')
                    if sprinkler_mode == 'auto':
                        try:
                            target_humid = settings.get('target_hum', 60.0)
                            
                            if humid is not None:
                                sprinkler_on = humid < target_humid
                                self.control_service.set_sprinkler(sprinkler_on)
                                print(f"[GPIO] Sprinkler {'ON' if sprinkler_on else 'OFF'} (auto): humid {humid:.1f}% {'<' if sprinkler_on else '>'} {target_humid}%")
                            
                        except Exception as e:
                            print(f"[GPIO] Sprinkler auto-mode error: {e}")
                
                # Sleep before next cycle (10 seconds = responsive but not CPU intensive)
                for _ in range(10):
                    if not self._running:
                        break
                    time.sleep(0.1)
            
            except Exception as e:
                print(f"[GPIO] Automation loop error: {e}")
                time.sleep(1.0)
