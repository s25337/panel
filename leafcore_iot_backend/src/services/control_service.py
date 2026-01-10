# src/services/control_service.py
"""
Device control and automation service
"""
import time
from typing import Optional, Dict, Any
from src.devices import DeviceManager
from src.services.settings_service import SettingsService


class ControlService:
    """Manages device control logic and automation"""
    
    LIGHT_START_TIME = 8  # Light starts at 8:00 AM
    
    # Device type mapping: device_name -> (setter_method, type_parser)
    DEVICE_MAP = {
        "fan": ("set_fan", bool),
        "light": ("set_light", float),
        "pump": ("set_pump", bool),
        "heater": ("set_heater", bool),
        "sprinkler": ("set_sprinkler", bool),
    }
    
    def __init__(self, device_manager: DeviceManager, settings_service: SettingsService):
        """Initialize control service"""
        self.device_manager = device_manager
        self.settings_service = settings_service
        
        # Hysteresis state for fan (prevents rapid switching)
        self._fan_hysteresis_on = False
        
        # Current light intensity based on sensor
        self._light_intensity = 0.0

    # ========== FAN CONTROL WITH HYSTERESIS ==========
    
    def control_fan_auto(self, current_humidity: Optional[float]) -> bool:
        """
        Auto control fan with hysteresis
        Turns on at target_hum + 5%, turns off at target_hum
        """
        if current_humidity is None:
            return self._fan_hysteresis_on
        
        target_hum = self.settings_service.get_setting("target_hum", 60)
        
        if self._fan_hysteresis_on:
            # Fan is ON - turn off at target humidity
            if current_humidity <= target_hum:
                self._fan_hysteresis_on = False
                self.device_manager.set_fan(False)
        else:
            # Fan is OFF - turn on if humidity exceeds target + 5%
            if current_humidity > (target_hum + 5):
                self._fan_hysteresis_on = True
                self.device_manager.set_fan(True)
        
        return self._fan_hysteresis_on

    # ========== LIGHT CONTROL WITH AUTO-INTENSITY ==========
    
    def should_light_be_on(self) -> bool:
        """
        Check if light should be on based on schedule
        Light starts at LIGHT_START_TIME and runs for light_hours
        """
        light_hours = self.settings_service.get_setting("light_hours", 12)
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min
        
        # Convert light_hours to minutes
        light_duration_minutes = int(light_hours * 60)
        
        # Calculate start and end times in minutes from midnight
        start_minutes = self.LIGHT_START_TIME * 60
        end_minutes = start_minutes + light_duration_minutes
        
        # Current time in minutes from midnight
        current_minutes = current_hour * 60 + current_minute
        
        # Check if current time is within schedule
        if end_minutes < 24 * 60:  # Normal case (doesn't cross midnight)
            return start_minutes <= current_minutes < end_minutes
        else:  # Crosses midnight
            end_minutes_adjusted = end_minutes - (24 * 60)
            return current_minutes >= start_minutes or current_minutes < end_minutes_adjusted

    def control_light_auto(self, light_sensor_reading: Optional[float]) -> float:
        """
        Auto control light with sensor feedback
        If light should be on: intensity = 100 - sensor_reading
        If light should be off: intensity = 0
        """
        if not self.should_light_be_on():
            self._light_intensity = 0.0
            self.device_manager.set_light(0.0)
            return 0.0
        
        if light_sensor_reading is None:
            # No sensor, use default intensity
            default_intensity = self.settings_service.get_setting("light_intensity", 50)
            self.device_manager.set_light(default_intensity)
            return default_intensity
        
        # Inverse logic: if sensor reads high (bright), reduce light
        # If sensor reads low (dark), increase light
        intensity = 100.0 - light_sensor_reading
        intensity = max(0.0, min(100.0, intensity))
        
        self._light_intensity = intensity
        self.device_manager.set_light(intensity)
        return intensity

    # ========== GET LIGHT SCHEDULE ==========
    
    def get_light_schedule(self) -> Dict[str, Any]:
        """Get light on/off schedule"""
        light_hours = self.settings_service.get_setting("light_hours", 12)
        
        start_hour = self.LIGHT_START_TIME
        end_hour = self.LIGHT_START_TIME + int(light_hours)
        end_minute = int((light_hours % 1) * 60)
        
        # Handle crossing midnight
        if end_hour >= 24:
            end_hour = end_hour - 24
        
        return {
            "start_hour": start_hour,
            "start_minute": 0,
            "end_hour": end_hour,
            "end_minute": end_minute,
            "light_hours": light_hours
        }

    # ========== WATERING CONTROL ==========
    
    def should_water_today(self) -> bool:
        """
        Check if today is a watering day and current time is around 12:00
        Returns True if should water now
        """
        import time
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min
        day_of_week = current_time.tm_wday  # 0=Monday, 6=Sunday
        
        # Get watering days list
        watering_days_names = self.settings_service.get_setting("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        
        # Map day names to weekday numbers (0=Monday)
        day_map = {
            "MONDAY": 0,
            "TUESDAY": 1,
            "WEDNESDAY": 2,
            "THURSDAY": 3,
            "FRIDAY": 4,
            "SATURDAY": 5,
            "SUNDAY": 6
        }
        
        # Get numeric days
        watering_day_numbers = [day_map.get(day, -1) for day in watering_days_names]
        
        # Check if today is watering day
        if day_of_week not in watering_day_numbers:
            return False
        
        # Check if time is around 12:00 (between 11:50 and 12:10)
        if current_hour == 12 and 50 <= current_minute <= 10:
            return True
        
        return False
    
    def get_watering_interval(self) -> int:
        """
        Get watering interval in seconds (for legacy support)
        Now based on number of watering days per week
        """
        watering_days = self.settings_service.get_setting("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        water_times = len(watering_days)  # Number of days per week
        
        if water_times <= 0:
            return 7 * 24 * 3600  # 7 days if no watering days
        
        seconds_per_week = 7 * 24 * 3600
        return int(seconds_per_week / water_times)

    def get_next_watering_time(self) -> Dict[str, int]:
        """
        Calculate exact time until next watering (12:00 on next scheduled day)
        Returns dict with days, hours, minutes, seconds
        """
        import time
        from datetime import datetime, timedelta
        
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_second = current_time.second
        day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday
        
        # Get watering days list
        watering_days_names = self.settings_service.get_setting("watering_days", ["MONDAY", "WEDNESDAY", "FRIDAY"])
        
        # Map day names to weekday numbers (0=Monday)
        day_map = {
            "MONDAY": 0,
            "TUESDAY": 1,
            "WEDNESDAY": 2,
            "THURSDAY": 3,
            "FRIDAY": 4,
            "SATURDAY": 5,
            "SUNDAY": 6
        }
        
        # Get numeric days
        watering_day_numbers = sorted([day_map.get(day, -1) for day in watering_days_names if day_map.get(day, -1) >= 0])
        
        if not watering_day_numbers:
            # No watering days configured, return 7 days
            return self.format_time_remaining(7 * 24 * 3600)
        
        # Watering happens at 12:00
        target_hour = 12
        target_minute = 0
        target_second = 0
        
        # Calculate time until 12:00 today
        target_time_today = current_time.replace(hour=target_hour, minute=target_minute, second=target_second, microsecond=0)
        
        # Find next watering day
        next_watering_day = None
        
        # Check if today is watering day and 12:00 hasn't passed yet
        if day_of_week in watering_day_numbers and current_time < target_time_today:
            next_watering_day = current_time
        else:
            # Find next watering day in this week
            for offset in range(1, 8):
                next_day = day_of_week + offset
                if next_day % 7 in watering_day_numbers:
                    next_watering_day = current_time + timedelta(days=offset)
                    break
        
        if next_watering_day is None:
            # Shouldn't happen, but fallback to 7 days
            return self.format_time_remaining(7 * 24 * 3600)
        
        # Set next watering to 12:00 on that day
        next_watering = next_watering_day.replace(hour=target_hour, minute=target_minute, second=target_second, microsecond=0)
        
        # Calculate time remaining
        time_remaining = (next_watering - current_time).total_seconds()
        
        # Make sure it's positive
        if time_remaining < 0:
            time_remaining = 0
        
        return self.format_time_remaining(int(time_remaining))

    @staticmethod
    def format_time_remaining(seconds: int) -> Dict[str, int]:
        """Convert seconds to days, hours, minutes, seconds"""
        days = seconds // (24 * 3600)
        seconds %= (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        return {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds
        }

    # ========== MANUAL DEVICE CONTROL ==========
    
    def set_device(self, device: str, state: Any) -> bool:
        """
        Set device state (manual control)
        Uses DEVICE_MAP for dispatch (eliminates switch statement)
        Returns True if successful
        """
        if device not in self.DEVICE_MAP:
            return False
        
        try:
            setter_name, parser = self.DEVICE_MAP[device]
            
            # Special handling for light (preserve intensity)
            if device == "light":
                intensity = float(state) if isinstance(state, (int, float)) else (100.0 if state else 0.0)
                intensity = max(0.0, min(100.0, intensity))
                getattr(self.device_manager, setter_name)(intensity)
            else:
                # Binary devices: parse as bool
                parsed_state = parser(state)
                getattr(self.device_manager, setter_name)(parsed_state)
            
            return True
        except (ValueError, AttributeError):
            return False

    # ========== STATE QUERIES ==========
    
    def get_device_states(self) -> Dict[str, Any]:
        """Get current state of all devices"""
        return {
            "fan": self.device_manager.get_fan_state(),
            "light": self.device_manager.get_light_state(),
            "pump": self.device_manager.get_pump_state(),
            "heater": self.device_manager.get_heater_state(),
            "sprinkler": self.device_manager.get_sprinkler_state(),
        }

    def get_device_state(self, device: str) -> Any:
        """Get state of specific device"""
        states = self.get_device_states()
        return states.get(device)

    # ========== AUTO-MODE CONTROL ==========
    
    def update_auto_devices(self, temperature: Optional[float], humidity: Optional[float],
                           brightness: Optional[float]) -> Dict[str, Any]:
        """
        Update device states based on current sensor readings and auto-mode settings
        Returns dict with updated device states
        """
        settings = self.settings_service.get_settings()
        modes = self.settings_service.get_manual_settings().get("modes", {})
        
        updated_states = {}
        
        # Heater control (based on temperature)
        if modes.get("heat_mat", {}).get("mode") == "auto" and temperature is not None:
            target_temp = settings.get("target_temp", 25)
            heater_on = temperature < target_temp
            self.device_manager.set_heater(heater_on)
            updated_states["heater"] = heater_on
        
        # Fan control (based on temperature + humidity)
        if modes.get("fan", {}).get("mode") == "auto":
            fan_on = self.control_fan_auto(humidity)
            if temperature is not None:
                target_temp = settings.get("target_temp", 25)
                if temperature > target_temp:
                    fan_on = True
            if fan_on:
                self.device_manager.set_fan(True)
            updated_states["fan"] = fan_on
        
        # Sprinkler control (based on humidity)
        if modes.get("sprinkler", {}).get("mode") == "auto" and humidity is not None:
            target_hum = settings.get("target_hum", 60)
            sprinkler_on = humidity < (target_hum - 5)
            self.device_manager.set_sprinkler(sprinkler_on)
            updated_states["sprinkler"] = sprinkler_on
        
        # Light control (schedule + sensor feedback)
        if modes.get("light", {}).get("mode") == "auto":
            self.control_light_auto(brightness)
            updated_states["light"] = {
                "intensity": self._light_intensity,
                "on": self._light_intensity > 0
            }
        
        return updated_states

    def get_device_modes(self) -> Dict[str, Dict[str, Any]]:
        """Get current modes for all devices"""
        manual = self.settings_service.get_manual_settings()
        modes = manual.get("modes", {})
        
        return {
            "fan": modes.get("fan", {"mode": "auto"}),
            "light": modes.get("light", {"mode": "auto"}),
            "pump": modes.get("pump", {"mode": "manual"}),
            "heater": modes.get("heat_mat", {"mode": "auto"}),
            "sprinkler": modes.get("sprinkler", {"mode": "auto"}),
        }

    def set_device_mode(self, device: str, mode: str) -> bool:
        """Set device mode (auto/manual)"""
        try:
            manual = self.settings_service.get_manual_settings()
            modes = manual.get("modes", {})
            
            if device == "heater":
                device_key = "heat_mat"
            else:
                device_key = device
            
            modes[device_key] = {"mode": mode}
            manual["modes"] = modes
            self.settings_service.save_manual_settings(manual)
            return True
        except Exception:
            return False
