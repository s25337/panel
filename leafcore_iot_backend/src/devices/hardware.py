# src/devices/hardware.py
"""
Hardware backend for Orange Pi Zero 2W with gpiod library
"""
import os
from typing import Optional, Tuple
from .base import BaseBackend


class GPIOdBackend(BaseBackend):
    """Backend for Orange Pi Zero 2W with gpiod library"""
    
    def __init__(self, fan_pin: int, light_pin: int, pump_pin: int, 
                 dht_pin: Optional[int] = None, chip_name: str = "gpiochip0"):
        super().__init__()

        try:
            import gpiod
            from gpiod.line import Direction, Value
        except ImportError:
            raise RuntimeError("gpiod library not installed!")

        self.gpiod = gpiod
        self.Direction = Direction
        self.Value = Value

        # GPIO chip
        self._chip = gpiod.Chip(chip_name)

        # Pin mapping for Orange Pi Zero 2W (BOARD -> GPIO line)
        self._pin_to_line = {
            3: 229,   # I2C SDA
            5: 228,   # I2C SCL
            7: 73,    # PA9
            11: 70,   # PA6
            12: 75,   # PA11
            13: 69,   # PA5
            15: 72,   # PA8
            16: 111,  # PC15
            18: 110,  # PC14
            19: 231,  # SPI MOSI
            21: 232,  # SPI MISO
            22: 71,   # PA7
            23: 230,  # SPI CLK
            24: 233,  # SPI CS
        }

        # Output pins
        self._fan_line = self._setup_output(fan_pin, "FAN")
        self._light_line = self._setup_output(light_pin, "LIGHT")
        self._pump_line = self._setup_output(pump_pin, "PUMP")

        # DHT sensor
        self._dht_pin = dht_pin
        self._dht = None
        self._dht_sensor_type = os.getenv("DHT_SENSOR", "DHT22").upper()

        # Initialize DHT sensor
        if self._dht_pin is not None:
            self._init_dht()

        # Start outputs in OFF state
        self.set_fan(False)
        self.set_light(0)
        self.set_pump(False)

    def _init_dht(self):
        """Initialize DHT sensor"""
        try:
            import OrangePi_DHT
            sensor_map = {
                "DHT11": OrangePi_DHT.DHT11,
                "DHT22": OrangePi_DHT.DHT22,
                "AM2302": OrangePi_DHT.DHT22,
            }
            sensor_cls = sensor_map.get(self._dht_sensor_type, OrangePi_DHT.DHT22)
            dht_gpio_line = self._pin_to_line.get(self._dht_pin)
            self._dht = ("orangepi_dht", sensor_cls(dht_gpio_line if dht_gpio_line else self._dht_pin))
        except Exception as e:
            print(f"Failed to initialize DHT sensor: {e}")
            self._dht = None

    def _setup_output(self, pin: int, name: str = "") -> any:
        """Setup pin as output"""
        gpio_line = self._pin_to_line.get(pin)
        if gpio_line is None:
            raise ValueError(f"Pin {pin} ({name}) not found in pin mapping!")
        
        line_settings = self.gpiod.LineSettings(
            direction=self.Direction.OUTPUT,
            output_value=self.Value.INACTIVE
        )
        line_request = self._chip.request_lines(
            consumer=f"leafcore_{name.lower()}",
            config={gpio_line: line_settings}
        )
        return line_request

    def _write_line(self, line_request, state: bool):
        """Write state to GPIO line"""
        offset = list(line_request.offsets)[0]
        value = self.Value.ACTIVE if state else self.Value.INACTIVE
        line_request.set_value(offset, value)

    # ========== OUTPUTS ==========
    
    def set_fan(self, state: bool) -> None:
        super().set_fan(state)
        self._write_line(self._fan_line, state)

    def set_light(self, intensity: float) -> None:
        super().set_light(intensity)
        # Convert intensity (0-100) to on/off for now
        state = intensity > 0
        self._write_line(self._light_line, state)

    def set_pump(self, state: bool) -> None:
        super().set_pump(state)
        self._write_line(self._pump_line, state)

    # ========== INPUTS ==========
    
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Read temperature and humidity from DHT sensor"""
        if not self._dht or self._dht_pin is None:
            return None, None

        kind = self._dht[0]

        try:
            if kind == "orangepi_dht":
                sensor = self._dht[1]
                data = sensor.read()
                if isinstance(data, dict):
                    temp = data.get("temperature")
                    hum = data.get("humidity")
                else:
                    temp, hum = data
                if temp is None or hum is None:
                    return None, None
                return float(temp), float(hum)
        except Exception:
            return None, None

        return None, None

    # ========== LIFECYCLE ==========
    
    def cleanup(self) -> None:
        """Release GPIO resources"""
        try:
            if hasattr(self, '_fan_line'):
                self._fan_line.release()
            if hasattr(self, '_light_line'):
                self._light_line.release()
            if hasattr(self, '_pump_line'):
                self._pump_line.release()
            if hasattr(self, '_chip'):
                self._chip.close()
        except Exception:
            pass
