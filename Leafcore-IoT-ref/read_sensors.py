import sys
import os

import requests
import config
import json
import datetime
import time
import gpiod
from gpiod.line import Direction, Value, Bias

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    import adafruit_ahtx0
    import adafruit_veml7700
except ImportError as e:
    print(f"Library Error: {e}")
    exit()


CHIP_PATH = "/dev/gpiochip0"

class SoftwareI2CBridge:
    def __init__(self, chip_path, scl, sda):
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

    # --- Low Level ---
    def _set(self, pin, val):
        if val: self.req.reconfigure_lines({pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)})
        else: self.req.reconfigure_lines({pin: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)})

    def _get(self, pin): return self.req.get_value(pin) == Value.ACTIVE

    def _start(self):
        self._set(self.sda, 1); self._set(self.scl, 1); time.sleep(0.0001)
        self._set(self.sda, 0); time.sleep(0.0001); self._set(self.scl, 0)

    def _stop(self):
        self._set(self.scl, 0); self._set(self.sda, 0); time.sleep(0.0001)
        self._set(self.scl, 1); time.sleep(0.0001); self._set(self.sda, 1)

    def _write_byte(self, byte):
        for i in range(8):
            self._set(self.sda, (byte >> (7 - i)) & 1); time.sleep(0.00005)
            self._set(self.scl, 1); time.sleep(0.00005); self._set(self.scl, 0)
        self._set(self.sda, 1); time.sleep(0.00005); self._set(self.scl, 1); time.sleep(0.00005)
        ack = not self._get(self.sda); self._set(self.scl, 0); return ack

    def _read_byte(self, ack):
        byte = 0; self._set(self.sda, 1)
        for i in range(8):
            self._set(self.scl, 1); time.sleep(0.00005)
            if self._get(self.sda): byte |= (1 << (7 - i))
            self._set(self.scl, 0)
        self._set(self.sda, 0 if ack else 1); self._set(self.scl, 1); time.sleep(0.00005)
        self._set(self.scl, 0); self._set(self.sda, 1); return byte

    # --- API Compliance ---
    def try_lock(self): return True
    def unlock(self): pass

    def writeto(self, address, buffer, start=0, end=None, stop=True):
        if end is None: end = len(buffer)
        self._start()
        if not self._write_byte((address << 1) | 0):
            self._stop(); raise OSError(f"No ACK from 0x{address:02X}")
        for i in range(start, end):
            if not self._write_byte(buffer[i]): self._stop(); raise OSError("NACK")
        if stop: self._stop()

    def readfrom_into(self, address, buffer, start=0, end=None, stop=True):
        if end is None: end = len(buffer)
        self._start()
        if not self._write_byte((address << 1) | 1):
            self._stop(); raise OSError(f"No ACK from 0x{address:02X}")
        count = end - start
        for i in range(count):
            buffer[start + i] = self._read_byte(i < count - 1)
        if stop: self._stop()

    def writeto_then_readfrom(self, address, out_buffer, in_buffer, out_start=0, out_end=None, in_start=0, in_end=None,stop=True):
        self.writeto(address, out_buffer, start=out_start, end=out_end, stop=False)
        self.readfrom_into(address, in_buffer, start=in_start, end=in_end, stop=stop)
try:
    i2c = SoftwareI2CBridge(CHIP_PATH, config.SCL_PIN, config.SDA_PIN)
    # 1. AHT10
    try:
        sensor_aht = adafruit_ahtx0.AHTx0(i2c)
        print("SUCCESS: AHT10 Connected.")
    except Exception as e:
        print(f"Warning: AHT10 Error ({e})")
        sensor_aht = None

    # 2. VEML7700
    try:
        sensor_veml = adafruit_veml7700.VEML7700(i2c)
        print("SUCCESS: VEML7700 Connected.")
    except Exception as e:
        print(f"Warning: VEML7700 Error ({e})")
        sensor_veml = None

    print("-" * 40)
    OUTPUT_FILE = os.path.join(current_dir, "sensor_data.json")

    while True:
        data = {"temperature": None, "humidity": None, "brightness": None}

        if sensor_aht:
            try:
                data["temperature"] = round(sensor_aht.temperature, 2)
                data["humidity"] = round(sensor_aht.relative_humidity, 2)
            except Exception:
                data["temperature"] = None
                data["humidity"] = None

        if sensor_veml:
            try:
                lux = sensor_veml.lux
                brightness = min(max(lux / 500.0, 0.0), 1.0)
                data["brightness"] = round(brightness, 2)
            except Exception:
                data["brightness"] = None

        data["timestamp"] = datetime.datetime.fromtimestamp(time.time()).isoformat()

        try:
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, "r") as f:
                    data_list = json.load(f)
                    if not isinstance(data_list, list):
                        data_list = []
            else:
                data_list = []
            data_list.insert(0, data)
    
            with open(OUTPUT_FILE, "w") as f:
                json.dump(data_list, f, indent=4)
        except Exception as e:
            print(f"File update error: {e}")

        with open("sensor_data.json", "r") as f:
            data = json.load(f) 
            url = "http://172.19.14.15:8080/terrarium/dataTerrarium"
            try:
                response = requests.post(url, json=data) 
                print(f"Status: {response.status_code}")
            except Exception as e:
                print(f"Sending sensor data error: {e}")

        time.sleep(2)

except Exception as e:
    print(f"Bridge Crash: {e}")
