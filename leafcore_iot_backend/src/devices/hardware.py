# src/devices/hardware.py
"""
Hardware backend for Orange Pi Zero 2W with gpiod library
Includes PWM support for light dimming and auto-mode control
"""
import os
import time
import threading
from typing import Optional, Tuple, Dict, Any
from .base import BaseBackend

# PWM configuration
PWM_FREQUENCY = 100  # 100 Hz
PWM_PERIOD = 1.0 / PWM_FREQUENCY  # 0.01 seconds


class GPIOdBackend(BaseBackend):
    """Backend for Orange Pi Zero 2W with gpiod library"""
    
    def __init__(self, fan_pin: int = 271, light_pin: int = 269, pump_pin: int = 268,
                 heater_pin: int = 272, sprinkler_pin: int = 258,
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

        # GPIO pin mapping for Orange Pi Zero 2W
        # Using direct GPIO line numbers (from Orange Pi Zero 2W datasheet)
        self.fan_pin = fan_pin
        self.light_pin = light_pin
        self.pump_pin = pump_pin
        self.heater_pin = heater_pin
        self.sprinkler_pin = sprinkler_pin
        
        # I2C pins for Software I2C Bridge (used for AHT10/VEML7700)
        self.scl_pin = 263  # I2C SCL line
        self.sda_pin = 264  # I2C SDA line

        # Output pins
        self._fan_line = self._setup_output(fan_pin, "FAN")
        self._light_line = self._setup_output(light_pin, "LIGHT")
        self._pump_line = self._setup_output(pump_pin, "PUMP")
        self._heater_line = self._setup_output(heater_pin, "HEATER")
        self._sprinkler_line = self._setup_output(sprinkler_pin, "SPRINKLER")

        # Light PWM control
        self._light_pwm_running = False
        self._light_pwm_thread: Optional[threading.Thread] = None
        self._light_intensity = 0.0  # 0.0 to 1.0

        # Initialize all GPIO lines at once
        self._setup_all_gpio()
        
        # Software I2C Bridge for sensor communication
        self._i2c_bridge = None
        self._aht_sensor = None
        self._veml_sensor = None
        self._init_sensors()

        # Start outputs in OFF state
        self.set_fan(False)
        self.set_light(0)
        self.set_pump(False)
        self.set_heater(False)
        self.set_sprinkler(False)

    def _setup_all_gpio(self):
        """Setup all GPIO lines as outputs"""
        try:
            line_settings = {
                self.fan_pin: self.gpiod.LineSettings(
                    direction=self.Direction.OUTPUT,
                    output_value=self.Value.INACTIVE
                ),
                self.light_pin: self.gpiod.LineSettings(
                    direction=self.Direction.OUTPUT,
                    output_value=self.Value.INACTIVE
                ),
                self.pump_pin: self.gpiod.LineSettings(
                    direction=self.Direction.OUTPUT,
                    output_value=self.Value.INACTIVE
                ),
                self.heater_pin: self.gpiod.LineSettings(
                    direction=self.Direction.OUTPUT,
                    output_value=self.Value.INACTIVE
                ),
                self.sprinkler_pin: self.gpiod.LineSettings(
                    direction=self.Direction.OUTPUT,
                    output_value=self.Value.INACTIVE
                ),
            }
            self._gpio_request = self._chip.request_lines(
                consumer="leafcore_devices",
                config=line_settings
            )
        except Exception as e:
            pass  # Silently ignore GPIO setup errors
            raise

    def _init_sensors(self):
        """Initialize I2C sensors (AHT10 + VEML7700)"""
        try:
            self._i2c_bridge = SoftwareI2CBridge(
                chip_path="/dev/gpiochip0",
                scl_pin=self.scl_pin,
                sda_pin=self.sda_pin
            )
            
            # Try to initialize AHT10
            try:
                import adafruit_ahtx0
                self._aht_sensor = adafruit_ahtx0.AHTx0(self._i2c_bridge)
                print("✓ AHT10 sensor initialized")
            except Exception as e:
                pass  # Silently ignore sensor initialization errors
                self._aht_sensor = None
            
            # Try to initialize VEML7700
            try:
                import adafruit_veml7700
                self._veml_sensor = adafruit_veml7700.VEML7700(self._i2c_bridge)
                print("✓ VEML7700 sensor initialized")
            except Exception as e:
                pass  # Silently ignore sensor initialization errors
                self._veml_sensor = None
                
        except Exception as e:
            pass  # Silently ignore I2C bridge errors
            self._i2c_bridge = None

    def _write_gpio(self, pin: int, state: bool):
        """Write state to GPIO pin"""
        try:
            value = self.Value.ACTIVE if state else self.Value.INACTIVE
            self._gpio_request.set_value(pin, value)
        except Exception as e:
            pass  # Silently ignore GPIO errors (common on non-ARM systems)

    def _pwm_control(self, pin: int, intensity: float):
        """Software PWM control for light dimming"""
        while self._light_pwm_running:
            if intensity >= 1.0:
                # Full brightness
                self._write_gpio(pin, True)
                time.sleep(PWM_PERIOD)
            elif intensity <= 0.0:
                # Off
                self._write_gpio(pin, False)
                time.sleep(PWM_PERIOD)
            else:
                # PWM
                on_time = PWM_PERIOD * intensity
                off_time = PWM_PERIOD * (1.0 - intensity)
                
                self._write_gpio(pin, True)
                time.sleep(on_time)
                
                self._write_gpio(pin, False)
                time.sleep(off_time)

    # ========== OUTPUTS ==========
    
    def set_fan(self, state: bool) -> None:
        super().set_fan(state)
        self._write_gpio(self.fan_pin, state)

    def set_heater(self, state: bool) -> None:
        super().set_heater(state)
        self._write_gpio(self.heater_pin, state)

    def set_sprinkler(self, state: bool) -> None:
        super().set_sprinkler(state)
        self._write_gpio(self.sprinkler_pin, state)

    def set_light(self, intensity: float) -> None:
        """Set light intensity with PWM (0-100 range converts to 0-1)"""
        super().set_light(intensity)
        
        # Convert 0-100 to 0-1
        pwm_intensity = max(0.0, min(1.0, intensity / 100.0))
        self._light_intensity = pwm_intensity
        
        # Stop existing PWM thread if running
        if self._light_pwm_running:
            self._light_pwm_running = False
            if self._light_pwm_thread:
                self._light_pwm_thread.join(timeout=0.1)
        
        # Start new PWM thread
        if pwm_intensity > 0:
            self._light_pwm_running = True
            self._light_pwm_thread = threading.Thread(
                target=self._pwm_control,
                args=(self.light_pin, pwm_intensity),
                daemon=True
            )
            self._light_pwm_thread.start()
        else:
            # Turn off
            self._write_gpio(self.light_pin, False)

    def set_pump(self, state: bool) -> None:
        super().set_pump(state)
        self._write_gpio(self.pump_pin, state)

    # ========== INPUTS ==========
    
    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Read temperature and humidity from AHT10 sensor"""
        if not self._aht_sensor:
            return None, None
        
        try:
            temp = self._aht_sensor.temperature
            humidity = self._aht_sensor.relative_humidity
            return float(temp), float(humidity)
        except Exception as e:
            print(f"AHT10 read error: {e}")
            return None, None
    
    def read_light_intensity(self) -> Optional[float]:
        """Read brightness (lux) from VEML7700 and convert to 0-100 scale"""
        if not self._veml_sensor:
            return None
        
        try:
            lux = self._veml_sensor.lux
            # Convert lux (0-1000+) to 0-100 scale
            brightness = min(max(lux / 10.0, 0.0), 100.0)
            return brightness
        except Exception as e:
            print(f"VEML7700 read error: {e}")
            return None

    # ========== LIFECYCLE ==========
    
    def cleanup(self) -> None:
        """Release GPIO resources"""
        try:
            # Stop PWM
            self._light_pwm_running = False
            if self._light_pwm_thread:
                self._light_pwm_thread.join(timeout=0.5)
            
            # Turn off all devices
            self._write_gpio(self.fan_pin, False)
            self._write_gpio(self.light_pin, False)
            self._write_gpio(self.pump_pin, False)
            self._write_gpio(self.heater_pin, False)
            self._write_gpio(self.sprinkler_pin, False)
            
            # Release GPIO request
            if hasattr(self, '_gpio_request'):
                self._gpio_request.release()
            
            # Close I2C bridge
            if self._i2c_bridge and hasattr(self._i2c_bridge, 'close'):
                self._i2c_bridge.close()
            
            # Close chip
            if hasattr(self, '_chip'):
                self._chip.close()
        except Exception as e:
            print(f"Cleanup error: {e}")


# ========== SOFTWARE I2C BRIDGE ==========

class SoftwareI2CBridge:
    """
    Software-based I2C implementation for Raspberry Pi
    Allows communication with I2C sensors without hardware I2C
    """
    
    def __init__(self, chip_path: str, scl_pin: int, sda_pin: int):
        """
        Initialize software I2C bridge
        Args:
            chip_path: Path to GPIO chip (e.g. "/dev/gpiochip0")
            scl_pin: GPIO line number for SCL
            sda_pin: GPIO line number for SDA
        """
        try:
            import gpiod
            from gpiod.line import Direction, Bias
        except ImportError:
            raise RuntimeError("gpiod library not installed!")
        
        self.gpiod = gpiod
        self.Direction = Direction
        self.Bias = Bias
        self.chip = gpiod.Chip(chip_path)
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        
        # Request SCL/SDA as inputs with pull-ups
        self.req = self.chip.request_lines(
            consumer="software_i2c",
            config={
                scl_pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP),
                sda_pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)
            }
        )
    
    # ========== LOW LEVEL ==========
    
    def _set(self, pin: int, val: bool):
        """Set pin high (open-drain) or low (pulled to ground)"""
        if val:
            # Open-drain (release to pull-up)
            self.req.reconfigure_lines({
                pin: self.gpiod.LineSettings(direction=self.Direction.INPUT, bias=self.Bias.PULL_UP)
            })
        else:
            # Driven low
            self.req.reconfigure_lines({
                pin: self.gpiod.LineSettings(direction=self.Direction.OUTPUT, output_value=self.gpiod.line.Value.INACTIVE)
            })
        time.sleep(0.00005)  # Small delay for electrical settling
    
    def _get(self, pin: int) -> bool:
        """Read pin state"""
        try:
            from gpiod.line import Value
            return self.req.get_value(pin) == Value.ACTIVE
        except:
            return self.req.get_value(pin) == 1
    
    def _start(self):
        """I2C START condition"""
        self._set(self.sda_pin, 1)
        self._set(self.scl_pin, 1)
        self._set(self.sda_pin, 0)
    
    def _stop(self):
        """I2C STOP condition"""
        self._set(self.sda_pin, 0)
        self._set(self.scl_pin, 1)
        self._set(self.sda_pin, 1)
    
    def _write_byte(self, byte: int) -> bool:
        """Write byte and read ACK"""
        for i in range(8):
            self._set(self.sda_pin, (byte >> (7 - i)) & 1)
            self._set(self.scl_pin, 1)
            self._set(self.scl_pin, 0)
        
        self._set(self.sda_pin, 1)  # Release SDA for ACK
        self._set(self.scl_pin, 1)
        ack = not self._get(self.sda_pin)
        self._set(self.scl_pin, 0)
        return ack
    
    def _read_byte(self, ack: bool) -> int:
        """Read byte and send ACK/NACK"""
        byte = 0
        self._set(self.sda_pin, 1)
        
        for i in range(8):
            self._set(self.scl_pin, 1)
            if self._get(self.sda_pin):
                byte |= (1 << (7 - i))
            self._set(self.scl_pin, 0)
        
        # Send ACK/NACK
        self._set(self.sda_pin, 0 if ack else 1)
        self._set(self.scl_pin, 1)
        self._set(self.scl_pin, 0)
        self._set(self.sda_pin, 1)
        return byte
    
    # ========== I2C API COMPLIANCE ==========
    
    def try_lock(self) -> bool:
        """For compatibility with adafruit libraries"""
        return True
    
    def unlock(self):
        """For compatibility with adafruit libraries"""
        pass
    
    def writeto(self, address: int, buffer, start: int = 0, end: int = None, stop: bool = True):
        """Write bytes to I2C device"""
        if end is None:
            end = len(buffer)
        
        self._start()
        
        # Send address with write bit
        addr_byte = (address << 1) | 0
        if not self._write_byte(addr_byte):
            self._stop()
            raise OSError(f"No ACK from address 0x{address:02X}")
        
        # Send data bytes
        for i in range(start, end):
            if not self._write_byte(buffer[i]):
                self._stop()
                raise OSError("NACK during write")
        
        if stop:
            self._stop()
    
    def readfrom_into(self, address: int, buffer, start: int = 0, end: int = None, stop: bool = True):
        """Read bytes from I2C device into buffer"""
        if end is None:
            end = len(buffer)
        
        self._start()
        
        # Send address with read bit
        addr_byte = (address << 1) | 1
        if not self._write_byte(addr_byte):
            self._stop()
            raise OSError(f"No ACK from address 0x{address:02X}")
        
        # Read data bytes
        count = end - start
        for i in range(count):
            buffer[start + i] = self._read_byte(i < count - 1)
        
        if stop:
            self._stop()
    
    def writeto_then_readfrom(self, address: int, out_buffer, in_buffer,
                             out_start: int = 0, out_end: int = None,
                             in_start: int = 0, in_end: int = None, stop: bool = True):
        """Combined write-then-read operation"""
        self.writeto(address, out_buffer, start=out_start, end=out_end, stop=False)
        self.readfrom_into(address, in_buffer, start=in_start, end=in_end, stop=stop)
    
    def close(self):
        """Close I2C bridge"""
        try:
            self.req.release()
            self.chip.close()
        except:
            pass

