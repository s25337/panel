# src/devices/base.py
"""
Base abstract class for device backends
"""
from typing import Tuple, Optional


class BaseBackend:
    """Abstract base class for device control backends"""
    
    def __init__(self):
        self._fan_state = False
        self._light_state = 0.0  # 0-100: intensywność światła
        self._pump_state = False
        self._heater_state = False
        self._sprinkler_state = False

    # ========== OUTPUTS ==========
    
    def set_fan(self, state: bool) -> None:
        """Set fan state"""
        self._fan_state = bool(state)

    def set_light(self, intensity: float) -> None:
        """Set light intensity 0-100 (0 = off, 100 = full brightness)"""
        self._light_state = max(0.0, min(100.0, float(intensity)))

    def set_pump(self, state: bool) -> None:
        """Set pump state"""
        self._pump_state = bool(state)

    def set_heater(self, state: bool) -> None:
        """Set heater state"""
        self._heater_state = bool(state)

    def set_sprinkler(self, state: bool) -> None:
        """Set sprinkler state"""
        self._sprinkler_state = bool(state)

    # ========== INPUTS ==========
    
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (temperature_C, humidity_percent) or (None, None) if unavailable."""
        return None, None

    def read_light_intensity(self) -> Optional[float]:
        """Return light intensity (0-100) or None if unavailable."""
        return None

    # ========== STATE GETTERS ==========
    
    def get_fan_state(self) -> bool:
        return self._fan_state

    def get_light_state(self) -> float:
        """Return current light intensity 0-100"""
        return self._light_state

    def get_pump_state(self) -> bool:
        return self._pump_state

    def get_heater_state(self) -> bool:
        return self._heater_state

    def get_sprinkler_state(self) -> bool:
        return self._sprinkler_state

    # ========== LIFECYCLE ==========
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        pass
