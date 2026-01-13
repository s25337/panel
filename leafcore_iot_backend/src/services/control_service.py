# src/services/control_service.py
"""
Device control and automation service
"""
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.devices import DeviceManager
from src.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


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
        
        # Watering automation
        self._watering_running = False
        self._watering_thread = None

    # ========== FAN CONTROL WITH HYSTERESIS ==========
    
    def control_fan_auto(self, current_humidity: Optional[float]) -> bool:
        """
        Auto control fan with hysteresis
        Turns on when humidity exceeds target, turns off at target
        """
        if current_humidity is None:
            return self._fan_hysteresis_on
        
        target_hum = self.settings_service.get_setting("target_hum", 60)
        
        if self._fan_hysteresis_on:
            # Fan is ON - turn off at or below target humidity
            if current_humidity <= target_hum:
                self._fan_hysteresis_on = False
                self.device_manager.set_fan(False)
        else:
            # Fan is OFF - turn on if humidity exceeds target
            if current_humidity > target_hum:
                self._fan_hysteresis_on = True
                self.device_manager.set_fan(True)
        
        return self._fan_hysteresis_on

    # ========== LIGHT CONTROL WITH AUTO-INTENSITY ==========
    
    def should_light_be_on(self) -> bool:
        """
        Check if light should be on based on schedule
        Uses start_hour and end_hour from settings
        """
        # Read schedule from settings
        start_hour = self.settings_service.get_setting("start_hour", 6)
        end_hour = self.settings_service.get_setting("end_hour", 18)
        
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min
        
        # Current time in minutes from midnight
        start_minutes = int(start_hour) * 60
        end_minutes = int(end_hour) * 60
        current_minutes = current_hour * 60 + current_minute
        
        # Check if current time is within schedule
        if end_minutes >= start_minutes:  # Normal case (doesn't cross midnight)
            return start_minutes <= current_minutes < end_minutes
        else:  # Crosses midnight (e.g., 22:00 to 06:00)
            return current_minutes >= start_minutes or current_minutes < end_minutes

    def control_light_auto(self, light_sensor_reading: Optional[float]) -> float:
        """
        Auto control light with sensor feedback
        If light should be on: intensity = 100 - sensor_reading
        If light should be off: intensity = 0
        """
        # First check if light should be on based on schedule
        if not self.should_light_be_on():
            self._light_intensity = 0.0
            self.device_manager.set_light(0.0)
            return 0.0
        
        # Light should be on - now determine intensity
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
        """Get light on/off schedule with calculated light hours"""
        start_hour = self.settings_service.get_setting("start_hour", 4)
        end_hour = self.settings_service.get_setting("end_hour", 5)
        
        # Calculate light hours
        light_hours = (end_hour - start_hour) if end_hour >= start_hour else (24 - start_hour + end_hour)
        
        return {
            "start_hour": int(start_hour),
            "start_minute": 0,
            "end_hour": int(end_hour),
            "end_minute": 0,
            "light_hours": float(light_hours)
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
        
        # Fan control (based on humidity) - SAME LOGIC AS HEATER
        if modes.get("fan", {}).get("mode") == "auto" and humidity is not None:
            target_hum = settings.get("target_hum", 60)
            fan_on = humidity > target_hum
            self.device_manager.set_fan(fan_on)
            updated_states["fan"] = fan_on
        
        # Sprinkler control (based on humidity)
        if modes.get("sprinkler", {}).get("mode") == "auto" and humidity is not None:
            target_hum = settings.get("target_hum", 60)
            sprinkler_on = humidity < target_hum
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
    
    # ========== HELPER METHODS FOR GPIO AUTOMATION SERVICE ==========
    
    def set_fan(self, state: bool) -> None:
        """Direct fan control (for GPIO automation)"""
        self.device_manager.set_fan(state)
        self.settings_service.update_manual_settings({"fan": state})
    
    def set_heater(self, state: bool) -> None:
        """Direct heater control (for GPIO automation)"""
        self.device_manager.set_heater(state)
        self.settings_service.update_manual_settings({"heater": state})
    
    def set_sprinkler(self, state: bool) -> None:
        """Direct sprinkler control (for GPIO automation)"""
        self.device_manager.set_sprinkler(state)
        self.settings_service.update_manual_settings({"sprinkler": state})
    
    def set_light(self, intensity: float) -> None:
        """Direct light intensity control (for GPIO automation)"""
        self.device_manager.set_light(intensity)
        self.settings_service.update_manual_settings({"light": intensity})
    
    # ========== WATERING AUTOMATION (formerly AutomationService) ==========
    
    def start_watering_automation(self):
        """Start watering automation background thread (checks at 12:00 daily)"""
        if self._watering_running:
            logger.warning("⚠️  Watering automation already running")
            return
        
        self._watering_running = True
        self._watering_thread = threading.Thread(target=self._watering_automation_loop, daemon=True)
        self._watering_thread.start()
        logger.info("✅ Watering automation started - will check at 12:00 daily")
    
    def stop_watering_automation(self):
        """Stop watering automation"""
        self._watering_running = False
        if self._watering_thread:
            self._watering_thread.join(timeout=5)
        logger.info("🛑 Watering automation stopped")
    
    def _watering_automation_loop(self):
        """
        Main watering automation loop
        Sleeps until 12:00, then executes watering check
        Efficient - no polling!
        """
        logger.info("🔄 Watering automation loop started")
        
        while self._watering_running:
            try:
                # Calculate seconds until 12:00 today
                seconds_until_noon = self._get_seconds_until_noon()
                
                logger.info(f"⏰ Next watering check in {seconds_until_noon} seconds ({seconds_until_noon/3600:.1f} hours)")
                
                # Sleep until it's time to check (sleep in chunks to be responsive to stop signal)
                remaining = seconds_until_noon
                while remaining > 0 and self._watering_running:
                    sleep_time = min(remaining, 60)  # Sleep max 60 seconds at a time
                    time.sleep(sleep_time)
                    remaining -= sleep_time
                
                # It's 12:00 - check and water
                if self._watering_running:
                    logger.info("🕐 Watering check time!")
                    self._check_and_water()
                
            except Exception as e:
                logger.error(f"❌ Error in watering automation loop: {e}", exc_info=True)
                # Continue running even if error occurred
                time.sleep(60)
    
    def _get_seconds_until_noon(self) -> int:
        """
        Calculate seconds until 12:00 today or tomorrow
        Returns positive integer (number of seconds)
        """
        now = datetime.now()
        noon_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if now < noon_today:
            # 12:00 hasn't happened yet today
            delta = noon_today - now
        else:
            # 12:00 already passed today, wait for tomorrow
            noon_tomorrow = noon_today + timedelta(days=1)
            delta = noon_tomorrow - now
        
        return int(delta.total_seconds())
    
    def _check_and_water(self):
        """
        Check if today is a watering day at 12:00
        If yes, trigger watering sequence
        """
        try:
            # Check if in manual mode - skip automation if manual
            if self.settings_service.is_manual_mode():
                logger.info("⏭️  Manual mode active - skipping automation")
                return
            
            # Check if should water (based on watering_days schedule)
            if self.should_water_today():
                logger.info("💧 Watering time! Starting pump...")
                self._water_plant()
            else:
                logger.info("📅 Not a watering day today")
                
        except Exception as e:
            logger.error(f"❌ Error checking watering: {e}", exc_info=True)
    
    def _water_plant(self):
        """
        Execute watering sequence:
        1. Turn on pump
        2. Wait for water_seconds duration
        3. Turn off pump
        """
        try:
            # Get watering duration from settings
            water_seconds = self.settings_service.get_setting("water_seconds", 1)
            
            logger.info(f"💧 Turning on pump for {water_seconds} second(s)...")
            self.device_manager.set_pump(True)
            
            # Wait for specified duration
            time.sleep(water_seconds)
            
            # Turn off pump
            logger.info("🛑 Turning off pump")
            self.device_manager.set_pump(False)
            
            logger.info("✅ Watering complete")
            
        except Exception as e:
            logger.error(f"❌ Error during watering: {e}", exc_info=True)
            # Ensure pump is off even if error occurs
            try:
                self.device_manager.set_pump(False)
            except:
                pass

