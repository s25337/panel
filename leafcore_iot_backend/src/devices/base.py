# src/devices/base.py
"""
Base abstract class for device backends


OUTPUTS (set_*):
- set_light(intensity: float) - Controls LED PWM (0-100%)
- set_fan(state: bool) - Controls fan relay (on/off)
- set_pump(state: bool) - Controls pump relay (on/off)
- set_heater(state: bool) - Controls heater relay (on/off)
- set_sprinkler(state: bool) - Controls sprinkler relay (on/off)

INPUTS (read_*):
- read_sensor() -> (temp, hum) - Returns external sensors (AHT10)
- read_light_intensity() -> brightness - Returns LIGHT SENSOR (VEML7700), NOT LED state

STATE GETTERS (get_*_state):
- get_light_state() -> intensity - Returns CURRENT LED intensity
- get_*_state() -> bool - Returns current relay state 

KEY DISTINCTION:
- get_light_state() = LED intensity (what we CONTROL)
- read_light_intensity() = Environmental brightness (what we MEASURE)

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
        self._fan_state = bool(state)

    def set_light(self, intensity: float) -> None:
        self._light_state = max(0.0, min(100.0, float(intensity)))

    def set_pump(self, state: bool) -> None:
        self._pump_state = bool(state)

    def set_heater(self, state: bool) -> None:
        self._heater_state = bool(state)

    def set_sprinkler(self, state: bool) -> None:
        self._sprinkler_state = bool(state)

    # ========== INPUTS ==========
    
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        return None, None

    def read_light_intensity(self) -> Optional[float]:
        return None

    # ========== STATE GETTERS ==========
    
    def get_fan_state(self) -> bool:
        return self._fan_state

    def get_light_state(self) -> float:
        return self._light_state

    def get_pump_state(self) -> bool:
        return self._pump_state

    def get_heater_state(self) -> bool:
        return self._heater_state

    def get_sprinkler_state(self) -> bool:
        return self._sprinkler_state

    # ========== LIFECYCLE ==========
    
    def cleanup(self) -> None:
        pass
