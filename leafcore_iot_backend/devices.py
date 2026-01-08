# devices.py
import os
import random
import time
from typing import Tuple, Optional

# =============================================================================
# KONFIGURACJA: Ustaw 0 aby wymusić Mock, 1 aby użyć prawdziwego hardware (gpiod)
# =============================================================================
USE_HARDWARE = 1  # 0 = Mock, 1 = Hardware (gpiod)
# =============================================================================

try:
    import config  # expects pins: TEMP_HUMIDITY_SENSOR_PIN, FAN_PIN, LIGHT_PIN, PUMP_PIN
except Exception as e:
    raise RuntimeError("Brak pliku config.py z definicją pinów!") from e


# --- Backendy ---------------------------------------------------------------

class BaseBackend:
    def __init__(self):
        self._fan_state = False
        self._light_state = False
        self._pump_state = False

    # OUTPUTS
    def set_fan(self, state: bool) -> None:
        self._fan_state = bool(state)

    def set_light(self, state: bool) -> None:
        self._light_state = bool(state)

    def set_pump(self, state: bool) -> None:
        self._pump_state = bool(state)

    # INPUTS
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (temperature_C, humidity_percent) or (None, None) if unavailable."""
        return None, None

    def cleanup(self) -> None:
        pass


class MockBackend(BaseBackend):
    """Działa wszędzie (Windows/Linux) bez GPIO - losowe wartości."""
    def __init__(self):
        super().__init__()
        self._temp = 22.0 + random.uniform(-1.0, 1.0)
        self._hum = 60.0 + random.uniform(-3.0, 3.0)
        self._last_update = 0.0

    def _drift(self):
        # lekki dryf co ~1 s
        now = time.time()
        if now - self._last_update > 1.0:
            self._last_update = now
            #  wiatrak ON -> obniż wilgotność delikatnie
            if self._fan_state:
                self._hum += random.uniform(-0.6, 0.0)
            else:
                self._hum += random.uniform(-0.2, 0.3)

            # światło ON -> lekko podnosi temperaturę
            if self._light_state:
                self._temp += random.uniform(0.0, 0.15)
            else:
                self._temp += random.uniform(-0.08, 0.05)

            # pompka ON -> chwilowo podnosi wilgotność
            if self._pump_state:
                self._hum += random.uniform(0.3, 0.8)

            # ograniczenia
            self._temp = max(10.0, min(35.0, self._temp))
            self._hum = max(20.0, min(95.0, self._hum))

    def read_sensor(self) -> Tuple[float, float]:
        self._drift()
        return round(self._temp, 1), round(self._hum, 1)


class GPIOdBackend(BaseBackend):
    """Backend dla Orange Pi Zero 2W z biblioteką gpiod. Steruje wyjściami i próbuje odczytu DHT."""
    def __init__(self):
        super().__init__()

        import gpiod  # type: ignore
        from gpiod.line import Direction, Value  # type: ignore
        
        self.gpiod = gpiod
        self.Direction = Direction
        self.Value = Value

        # Chip GPIO - zwykle gpiochip0, ale może być inny (sprawdź: gpioinfo)
        chip_name = os.getenv("GPIO_CHIP", "gpiochip0")
        self._chip = gpiod.Chip(chip_name)

        # Mapowanie pinów fizycznych (BOARD) na linie GPIO
        # Orange Pi Zero 2W - przykładowe mapowanie (SPRAWDŹ dla Twojego modelu!)
        # Pin fizyczny -> numer linii GPIO
        self._pin_to_line = {
            3: 229,   # I2C SDA (przykład)
            5: 228,   # I2C SCL (przykład)
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
            # Dodaj więcej według potrzeb
        }

        # Konfiguracja pinów wyjściowych
        self._fan_line = self._setup_output(config.FAN_PIN, "FAN")
        self._light_line = self._setup_output(config.LIGHT_PIN, "LIGHT")
        self._pump_line = self._setup_output(config.PUMP_PIN, "PUMP")

        # SENSORY (DHT)
        self._dht_pin = getattr(config, "TEMP_HUMIDITY_SENSOR_PIN", None)
        self._dht = None
        self._dht_sensor_type = os.getenv("DHT_SENSOR", "DHT22").upper()

        # Próba inicjalizacji biblioteki DHT
        try:
            import OrangePi_DHT  # type: ignore
            sensor_map = {
                "DHT11": OrangePi_DHT.DHT11,
                "DHT22": OrangePi_DHT.DHT22,
                "AM2302": OrangePi_DHT.DHT22,
            }
            sensor_cls = sensor_map.get(self._dht_sensor_type, OrangePi_DHT.DHT22)
            dht_gpio_line = self._pin_to_line.get(self._dht_pin)
            self._dht = ("orangepi_dht", sensor_cls(dht_gpio_line if dht_gpio_line else self._dht_pin))
        except Exception:
            self._dht = None

        # Wystartuj wyjścia w pozycji OFF
        self.set_fan(False)
        self.set_light(False)
        self.set_pump(False)

    def _setup_output(self, pin: int, name: str = ""):
        """Konfiguruje pin jako wyjście."""
        gpio_line = self._pin_to_line.get(pin)
        if gpio_line is None:
            raise ValueError(f"Pin {pin} ({name}) nie ma mapowania GPIO! Sprawdź _pin_to_line.")
        
        line_settings = self.gpiod.LineSettings(
            direction=self.Direction.OUTPUT,
            output_value=self.Value.INACTIVE
        )
        line_request = self._chip.request_lines(
            consumer=f"leafcore_{name.lower()}",
            config={gpio_line: line_settings}
        )
        return line_request

    # OUTPUTS
    def _write_line(self, line_request, state: bool):
        """Zapisuje stan na linię GPIO."""
        offset = list(line_request.offsets)[0]
        value = self.Value.ACTIVE if state else self.Value.INACTIVE
        line_request.set_value(offset, value)

    def set_fan(self, state: bool) -> None:
        super().set_fan(state)
        self._write_line(self._fan_line, state)

    def set_light(self, state: bool) -> None:
        super().set_light(state)
        self._write_line(self._light_line, state)

    def set_pump(self, state: bool) -> None:
        super().set_pump(state)
        self._write_line(self._pump_line, state)

    # INPUTS
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
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

    def cleanup(self) -> None:
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


# --- Autowybór backendu -----------------------------------------------------

def _make_backend():
    """Tworzy backend na podstawie zmiennej USE_HARDWARE."""
    if USE_HARDWARE == 0:
        print("[devices.py] USE_HARDWARE=0 -> używam MockBackend")
        return MockBackend()
    
    if USE_HARDWARE == 1:
        try:
            import gpiod  # noqa: F401
            print("[devices.py] USE_HARDWARE=1 -> używam GPIOdBackend")
            return GPIOdBackend()
        except Exception as e:
            print(f"[devices.py] Błąd inicjalizacji GPIOd: {e}")
            print("[devices.py] Fallback do MockBackend")
            return MockBackend()
    
    # Jeśli USE_HARDWARE ma inną wartość, używamy Mock
    print(f"[devices.py] USE_HARDWARE={USE_HARDWARE} (nieznana wartość) -> używam MockBackend")
    return MockBackend()


_backend: BaseBackend = _make_backend()


# --- API modułu używane przez Twoją aplikację --------------------------------

def read_sensor() -> Tuple[Optional[float], Optional[float]]:
    return _backend.read_sensor()


def set_fan(state: bool) -> None:
    _backend.set_fan(state)


def set_light(state: bool) -> None:
    _backend.set_light(state)


def set_pump(state: bool) -> None:
    _backend.set_pump(state)


def get_fan_state() -> bool:
    return _backend._fan_state


def get_light_state() -> bool:
    return _backend._light_state


def get_pump_state() -> bool:
    return _backend._pump_state


def cleanup() -> None:
    _backend.cleanup()


# Opcjonalnie: sprzątanie przy wyjściu
import atexit
atexit.register(cleanup)
