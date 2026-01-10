# src/devices/manager.py
"""
Device manager - unified interface for device control
"""
import os
import atexit
from typing import Optional, Tuple
from .base import BaseBackend
from .mock import MockBackend
from .hardware import GPIOdBackend


class DeviceManager:
    """Unified interface for device control"""
    
    def __init__(self, use_hardware: bool = True, 
                 fan_pin: int = 17, light_pin: int = 27, pump_pin: int = 22,
                 dht_pin: Optional[int] = 4):
        """
        Initialize device manager
        
        Args:
            use_hardware: Use real GPIO (True) or Mock backend (False)
            fan_pin: GPIO pin for fan
            light_pin: GPIO pin for light
            pump_pin: GPIO pin for pump
            dht_pin: GPIO pin for DHT sensor (optional)
        """
        self._backend = self._create_backend(
            use_hardware=use_hardware,
            fan_pin=fan_pin,
            light_pin=light_pin,
            pump_pin=pump_pin,
            dht_pin=dht_pin
        )
        
        # Register cleanup on exit
        atexit.register(self.cleanup)

    @staticmethod
    def _create_backend(use_hardware: bool, fan_pin: int, light_pin: int, 
                        pump_pin: int, dht_pin: Optional[int]) -> BaseBackend:
        """Factory method for backend selection"""
        
        if not use_hardware:
            print("[DeviceManager] Using MockBackend")
            return MockBackend()
        
        # Try to use hardware backend
        try:
            import gpiod  # noqa: F401
            print("[DeviceManager] Using GPIOdBackend")
            return GPIOdBackend(
                fan_pin=fan_pin,
                light_pin=light_pin,
                pump_pin=pump_pin,
                dht_pin=dht_pin
            )
        except Exception as e:
            print(f"[DeviceManager] Failed to initialize hardware: {e}")
            print("[DeviceManager] Falling back to MockBackend")
            return MockBackend()

    # ========== DEVICE CONTROL ==========
    
    def set_fan(self, state: bool) -> None:
        """Control fan"""
        self._backend.set_fan(state)

    def set_light(self, intensity: float) -> None:
        """Control light (0-100)"""
        self._backend.set_light(intensity)

    def set_pump(self, state: bool) -> None:
        """Control pump"""
        self._backend.set_pump(state)

    def set_heater(self, state: bool) -> None:
        """Control heater"""
        self._backend.set_heater(state)

    def set_sprinkler(self, state: bool) -> None:
        """Control sprinkler"""
        self._backend.set_sprinkler(state)

    # ========== SENSOR READING ==========
    
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Read temperature and humidity"""
        return self._backend.read_sensor()

    def read_light_intensity(self) -> Optional[float]:
        """Read light intensity from sensor"""
        return self._backend.read_light_intensity()

    # ========== STATE GETTERS ==========
    
    def get_fan_state(self) -> bool:
        """Get fan state"""
        return self._backend.get_fan_state()

    def get_light_state(self) -> float:
        """Get light intensity (0-100)"""
        return self._backend.get_light_state()

    def get_pump_state(self) -> bool:
        """Get pump state"""
        return self._backend.get_pump_state()

    def get_heater_state(self) -> bool:
        """Get heater state"""
        return self._backend.get_heater_state()

    def get_sprinkler_state(self) -> bool:
        """Get sprinkler state"""
        return self._backend.get_sprinkler_state()

    # ========== LIFECYCLE ==========
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._backend.cleanup()
