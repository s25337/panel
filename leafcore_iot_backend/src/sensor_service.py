"""
Sensor Reading Service
Handles AHT10 (temperature/humidity) and VEML7700 (brightness) sensors
via Software I2C bridge using gpiod
"""
import sys
import os
import json
import datetime
import time
import threading
import logging
import board
import busio
try:
    import gpiod
    from gpiod.line import Direction, Value, Bias
    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    import adafruit_ahtx0
    import adafruit_veml7700
    SENSORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sensor libraries not available: {e}")
    SENSORS_AVAILABLE = False


class SoftwareI2CBridge:
    """Software I2C implementation using gpiod for sensor communication"""
    
    def __init__(self, chip_path, scl, sda):
        if not GPIOD_AVAILABLE:
            raise RuntimeError("gpiod not available")
        
        self.chip = gpiod.Chip(chip_path)
        self.req = self.chip.request_lines(
            consumer="MultiSensor_Bridge",
            config={
                scl: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP),
                sda: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)
            }
        )
        self.scl = scl
        self.sda = sda

    def _set(self, pin, val):
        if val:
            self.req.reconfigure_lines({pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)})
        else:
            self.req.reconfigure_lines({pin: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)})

    def _get(self, pin):
        return self.req.get_value(pin) == Value.ACTIVE

    def _start(self):
        self._set(self.sda, 1)
        self._set(self.scl, 1)
        time.sleep(0.0001)
        self._set(self.sda, 0)
        time.sleep(0.0001)
        self._set(self.scl, 0)

    def _stop(self):
        self._set(self.scl, 0)
        self._set(self.sda, 0)
        time.sleep(0.0001)
        self._set(self.scl, 1)
        time.sleep(0.0001)
        self._set(self.sda, 1)

    def _write_byte(self, byte):
        for i in range(8):
            self._set(self.sda, (byte >> (7 - i)) & 1)
            time.sleep(0.00005)
            self._set(self.scl, 1)
            time.sleep(0.00005)
            self._set(self.scl, 0)
        self._set(self.sda, 1)
        time.sleep(0.00005)
        self._set(self.scl, 1)
        time.sleep(0.00005)
        ack = not self._get(self.sda)
        self._set(self.scl, 0)
        return ack

    def _read_byte(self, ack):
        byte = 0
        self._set(self.sda, 1)
        for i in range(8):
            self._set(self.scl, 1)
            time.sleep(0.00005)
            if self._get(self.sda):
                byte |= (1 << (7 - i))
            self._set(self.scl, 0)
        self._set(self.sda, 0 if ack else 1)
        self._set(self.scl, 1)
        time.sleep(0.00005)
        self._set(self.scl, 0)
        self._set(self.sda, 1)
        return byte

    def try_lock(self):
        return True

    def unlock(self):
        pass

    def writeto(self, address, buffer, start=0, end=None, stop=True):
        if end is None:
            end = len(buffer)
        self._start()
        if not self._write_byte((address << 1) | 0):
            self._stop()
            raise OSError(f"No ACK from 0x{address:02X}")
        for i in range(start, end):
            if not self._write_byte(buffer[i]):
                self._stop()
                raise OSError("NACK")
        if stop:
            self._stop()

    def readfrom_into(self, address, buffer, start=0, end=None, stop=True):
        if end is None:
            end = len(buffer)
        self._start()
        if not self._write_byte((address << 1) | 1):
            self._stop()
            raise OSError(f"No ACK from 0x{address:02X}")
        count = end - start
        for i in range(count):
            buffer[start + i] = self._read_byte(i < count - 1)
        if stop:
            self._stop()

    def writeto_then_readfrom(self, address, out_buffer, in_buffer, out_start=0, out_end=None, in_start=0, in_end=None, stop=True):
        self.writeto(address, out_buffer, start=out_start, end=out_end, stop=False)
        self.readfrom_into(address, in_buffer, start=in_start, end=in_end, stop=stop)


class SensorService(threading.Thread):
    """Sensor reading thread - collects data from AHT10 and VEML7700"""
    
    def __init__(self, chip_path, scl_pin, sda_pin, output_file, poll_interval=2.0, water_min_pin=None, water_max_pin=None):
        super().__init__()
        self.daemon = True
        self.running = True
        self.chip_path = chip_path
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.output_file = output_file
        self.poll_interval = poll_interval
        self.water_min_pin = water_min_pin
        self.water_max_pin = water_max_pin

        self.water_min = None  # For water level pins    
        self.water_max = None       
        self.sensor_aht = None
        self.sensor_veml = None
        self.i2c = None
        
    def _initialize_sensors(self):
        """Initialize I2C bridge and sensors"""
        try:
            self.i2c = SoftwareI2CBridge(self.chip_path, self.scl_pin, self.sda_pin)
            #self.i2c = busio.I2C(board.SCL, board.SDA)
            logger.info("I2C Bridge initialized")
            
            # Initialize AHT10
            try:
                self.sensor_aht = adafruit_ahtx0.AHTx0(self.i2c)
                logger.info("✓ AHT10 (Temperature/Humidity) Connected")
            except Exception as e:
                logger.warning(f"AHT10 Error: {e}")
                self.sensor_aht = None

            # Initialize VEML7700
            try:
                self.sensor_veml = adafruit_veml7700.VEML7700(self.i2c)
                logger.info("✓ VEML7700 (Brightness) Connected")
            except Exception as e:
                logger.warning(f"VEML7700 Error: {e}")
                self.sensor_veml = None
                
            # Initialize water level sensors
            try:
                if self.water_min_pin is not None:
                    self.water_min = gpiod.Chip(self.chip_path).request_lines(
                        consumer="water_min_sensor",
                        config={self.water_min_pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)}
                    )
                    logger.info("✓ Water Min Sensor Connected")
                if self.water_max_pin is not None:
                    self.water_max = gpiod.Chip(self.chip_path).request_lines(
                        consumer="water_max_sensor",
                        config={self.water_max_pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)}
                    )
                    logger.info("✓ Water Max Sensor Connected")
            except Exception as e:
                logger.warning(f"Water Level Sensor Error: {e}")
                self.water_min = None
                self.water_max = None

            return self.sensor_aht or self.sensor_veml or self.water_min or self.water_max

            
        except Exception as e:
            logger.error(f"Sensor initialization failed: {e}")
            return False

    def run(self):
        if not SENSORS_AVAILABLE:
            logger.warning("Sensor libraries not installed - running in mock mode")
            self._run_mock()
            return
        if not self._initialize_sensors():
            logger.warning("No sensors available - running in mock mode")
            self._run_mock()
            return

        logger.info("Sensor Service started - collecting data...")
        last_save = 0
        last_history_save = 0
        while self.running:
            try:
                now = time.time()
                if now - last_save >= 2:
                    last_save = now
                    data = {
                        "temperature": None,
                        "humidity": None,
                        "brightness": None,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    if self.sensor_aht:
                        try:
                            data["temperature"] = round(self.sensor_aht.temperature, 2)
                            data["humidity"] = round(self.sensor_aht.relative_humidity, 2)
                        except Exception as e:
                            logger.debug(f"AHT10 read error: {e}")
                    if self.sensor_veml:
                        try:
                            lux = self.sensor_veml.lux
                            brightness = min(max(lux / 500.0, 0.0), 1.0)
                            data["brightness"] = round(brightness, 2)
                        except Exception as e:
                            logger.debug(f"VEML7700 read error: {e}")

                    # Read water level sensors
                    try:
                        if self.water_min:
                            min_state = self.water_min.get_value(self.water_min_pin)
                            data["water_min"] = "low" if min_state == Value.INACTIVE else "ok"
                        if self.water_max:
                            max_state = self.water_max.get_value(self.water_max_pin)
                            data["water_max"] = "high" if max_state == Value.INACTIVE else "ok"     
                    except Exception as e:
                        logger.debug(f"Water level sensor read error: {e}")

                    # Save to file
                    try:
                        with open(self.output_file, "w") as f:
                            json.dump(data, f, indent=4)
                    except Exception as e:
                        logger.error(f"File update error: {e}")
                    # Every 20s save to sensor_data_history.json (rolling 50)
                    if now - last_history_save >= 20:
                        last_history_save = now
                        try:
                            history_file = "source_files/sensor_data_history.json"
                            if os.path.exists(history_file):
                                with open(history_file, "r") as f:
                                    data_list = json.load(f)
                                    if not isinstance(data_list, list):
                                        data_list = []
                            else:
                                data_list = []
                            data_list.insert(0, data)
                            data_list = data_list[:50]
                            with open(history_file, "w") as f:
                                json.dump(data_list, f, indent=4)
                        except Exception as e:
                            logger.error(f"History file update error: {e}")
            except Exception as e:
                logger.error(f"Sensor reading error: {e}")
            time.sleep(self.poll_interval)

    def _run_mock(self):
        """Mock sensor data generation"""
        logger.info("Mock Sensor Service started")
        import random
        
        last_save = 0
        last_history_save = 0
        while self.running:
            try:
                now = time.time()
                data = {
                    "temperature": round(20 + random.uniform(-2, 2), 2),
                    "humidity": round(60 + random.uniform(-10, 10), 2),
                    "brightness": round(random.uniform(0.3, 1.0), 2),
                    "timestamp": datetime.datetime.now().isoformat()
                }
                # Zapisz tylko jeden rekord do sensor_data.json
                try:
                    with open(self.output_file, "w") as f:
                        json.dump(data, f, indent=4)
                except Exception as e:
                    logger.error(f"Mock file update error: {e}")
                # Co 20s dodaj do sensor_data_history.json (rolling 50)
                if now - last_history_save >= 20:
                    last_history_save = now
                    try:
                        history_file = "source_files/sensor_data_history.json"
                        if os.path.exists(history_file):
                            with open(history_file, "r") as f:
                                data_list = json.load(f)
                                if not isinstance(data_list, list):
                                    data_list = []
                        else:
                            data_list = []
                        data_list.insert(0, data)
                        data_list = data_list[:50]
                        with open(history_file, "w") as f:
                            json.dump(data_list, f, indent=4)
                    except Exception as e:
                        logger.error(f"Mock history file update error: {e}")
            except Exception as e:
                logger.error(f"Mock sensor error: {e}")
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
