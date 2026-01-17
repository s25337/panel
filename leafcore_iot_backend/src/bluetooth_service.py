"""
Bluetooth WiFi Configurator Service
Handles WiFi credential configuration via BLE
"""
import sys
import logging
import signal
import subprocess
import requests
import json
import os
import datetime
import threading

logging.basicConfig(level=logging.INFO)

# 2. DEBUG: Print exactly which Python executable is running
# This will tell us if we are in the venv or system python
print(f"DEBUG: Running Python from: {sys.executable}", flush=True)

try:
    from bluezero import peripheral, localGATT, async_tools, adapter
    BLUEZERO_AVAILABLE = True
    print("DEBUG: Bluezero Import SUCCESS", flush=True)
except ImportError as e:
    BLUEZERO_AVAILABLE = False
    print(f"DEBUG: Bluezero Import FAILED. Error: {e}", flush=True)
    # Print the path so we see where it tried to look
    print(f"DEBUG: sys.path is: {sys.path}", flush=True)

LEAFCORE_SERVICE_UUID = "c62a771b-095e-4f60-a383-bca1f8f96210"
SSID_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f1"
PASS_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f2"
SSID_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f3"
PASS_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f4"
USER_ID_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f5"
DEVICE_NAME_PREFIX = "LC_Greenhouse"

logger = logging.getLogger(__name__)


class WifiConfigurator:
    def __init__(self, devices_info_file, connection_event=None, logs=None):
        self.ssid_buffer = b"" 
        self.pass_buffer = b""
        self.ssid = None
        self.password = None
        self.userid = None
        self.devices_info_file = devices_info_file
        self.server_url = "http://33.11.238.45:8081/terrarium/"
        self.connection_event = connection_event
        self.logs = logs or []

    def on_ssid_write(self, value, options):
        self.ssid_buffer += bytes(value)
        msg = f"Appended SSID chunk. Buffer is now {len(self.ssid_buffer)} bytes."
        logging.info(msg)
        self.logs.append(msg)

    def on_pass_write(self, value, options):
        self.pass_buffer += bytes(value)
        msg = f"Appended Password chunk. Buffer is now {len(self.pass_buffer)} bytes."
        logging.info(msg)
        self.logs.append(msg)

    def on_ssid_execute(self, value, options):
        msg = "SSID Execute received. Decoding buffer..."
        logging.info(msg)
        self.logs.append(msg)
        try:
            self.ssid = self.ssid_buffer.decode('utf-8')
            msg = f"Decoded SSID: {self.ssid}"
            logging.info(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = f"Error decoding SSID: {e}"
            logging.error(msg)
            self.logs.append(msg)
        finally:
            self.ssid_buffer = b""
            self.attempt_connect()

    def on_pass_execute(self, value, options):
        msg = "Password Execute received. Decoding buffer..."
        logging.info(msg)
        self.logs.append(msg)
        try:
            self.password = self.pass_buffer.decode('utf-8')
            msg = "Decoded Password (hidden)"
            logging.info(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = f"Error decoding password: {e}"
            logging.error(msg)
            self.logs.append(msg)
        finally:
            self.pass_buffer = b""
            self.attempt_connect()

    def on_user_id(self, value, options):
        msg = "User ID received"
        logging.info(msg)
        self.logs.append(msg)
        self.userid = value

    def attempt_connect(self):
        if not self.ssid or not self.password:
            msg = "Missing credentials, waiting for both..."
            logging.warning(msg)
            self.logs.append(msg)
            return

        msg = f"Attempting to connect to SSID: {self.ssid}"
        logging.info(msg)
        self.logs.append(msg)
        if self.connection_event:
            self.connection_event.set()
        try:
            cmd = ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']
            check_connection = subprocess.run(cmd, capture_output=True, text=True)
            if check_connection.returncode == 0 and 'yes' in check_connection.stdout:
                msg = "Device is already connected to a network. Skipping Wi-Fi connection attempt."
                logging.info(msg)
                self.logs.append(msg)
            else:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', self.ssid, 'password', self.password]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                msg = f"NetworkManager output: {result.stdout}"
                logging.info(msg)
                self.logs.append(msg)
                msg = "--- Successfully connected to Wi-Fi! ---"
                logging.info(msg)
                self.logs.append(msg)
                msg = "--- Sending device data to server... ---"
                logging.info(msg)
                self.logs.append(msg)
                url = self.server_url + "module"
                try:
                    with open(self.devices_info_file, 'r') as f:
                        devices_info = json.load(f)
        
                    for device in devices_info.values():
                        device["is_registered"] = 1
                        device["user_id"] = self.userid
                        device["last_edit_date"] = datetime.datetime.now().isoformat()
                    
                    response = requests.post(url, json=devices_info)
                    
                    if response.status_code == 200:
                        msg = "Server response: 200 OK. Saving updated device info to file."
                        logging.info(msg)
                        self.logs.append(msg)
                        with open(self.devices_info_file, 'w') as f:
                            json.dump(devices_info, f, indent=4)
                    else:
                        msg = f"Server response: {response.status_code}. Failed to register devices."
                        logging.error(msg)
                        self.logs.append(msg)
                        msg = "Please try again."
                        logging.error(msg)
                        self.logs.append(msg)
                except Exception as e:
                    msg = f"Error sending device data: {e}"
                    logging.error(msg)
                    self.logs.append(msg)
        except FileNotFoundError:
            msg = "--- 'nmcli' command not found. ---"
            logging.error(msg)
            self.logs.append(msg)
        except subprocess.TimeoutExpired:
            msg = "--- Wi-Fi connection timed out. ---"
            logging.error(msg)
            self.logs.append(msg)
        except subprocess.CalledProcessError as e:
            msg = "--- Failed to connect to Wi-Fi. ---"
            logging.error(msg)
            self.logs.append(msg)
            msg = f"nmcli error: {e.stderr}"
            logging.error(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = f"Connection logic error: {e}"
            logging.error(msg)
            self.logs.append(msg)
        finally:
            self.ssid = None
            self.password = None
            try:
                msg = "Configuration attempt finished. Stopping Bluetooth."
                logging.info(msg)
                self.logs.append(msg)
                async_tools.EventLoop().quit()
            except Exception:
                pass


class BluetoothService(threading.Thread):
    """Bluetooth BLE service for WiFi configuration"""
    def __init__(self, devices_info_file, connection_event=None):
        super().__init__()
        self.daemon = True
        self.devices_info_file = devices_info_file
        #self.running = True
        self.connection_event = connection_event or threading.Event()
        self.mainloop = None
        self.logs = []

    def run(self):
        if not BLUEZERO_AVAILABLE:
            msg = "Bluezero not installed - Bluetooth service disabled"
            logging.warning(msg)
            self.logs.append(msg)
            return
        
        logging.basicConfig(level=logging.INFO)
        self.mainloop = async_tools.EventLoop()
        config = WifiConfigurator(self.devices_info_file, connection_event=self.connection_event, logs=self.logs)

        try:
            dongle = adapter.Adapter()
            msg = f"Using adapter: {dongle.address}"
            logging.info(msg)
            self.logs.append(msg)
            my_server = peripheral.Peripheral(
                adapter_address=dongle.address,
                local_name="LC_Greenhouse"
            )
            msg = f"Adding service: {LEAFCORE_SERVICE_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_service(
                srv_id=0,
                uuid=LEAFCORE_SERVICE_UUID,
                primary=True
            )

            msg = f"Adding SSID characteristic: {SSID_CHAR_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_characteristic(
                srv_id=0, chr_id=0, uuid=SSID_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_ssid_write
            )

            msg = f"Adding Password characteristic: {PASS_CHAR_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_characteristic(
                srv_id=0, chr_id=1, uuid=PASS_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_pass_write
            )

            msg = f"Adding SSID Execute characteristic: {SSID_EXEC_CHAR_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_characteristic(
                srv_id=0, chr_id=2, uuid=SSID_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_ssid_execute
            )

            msg = f"Adding Password Execute characteristic: {PASS_EXEC_CHAR_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_characteristic(
                srv_id=0, chr_id=3, uuid=PASS_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_pass_execute
            )

            msg = f"Adding User ID characteristic: {USER_ID_UUID}"
            logging.info(msg)
            self.logs.append(msg)
            my_server.add_characteristic(
                srv_id=0, chr_id=4, uuid=USER_ID_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_user_id
            )
            msg = "Bluetooth server is published and broadcasting. Waiting for WiFi config..."
            logging.info(msg)
            self.logs.append(msg)
            my_server.publish()
        except Exception as e:
            msg = f"Bluetooth Service Error: {e}"
            logging.error(msg)
            self.logs.append(msg)

        except adapter.AdapterError as e:
            msg = f"Bluetooth Error: {e}"
            logging.error(msg)
            self.logs.append(msg)

    def stop(self):
        if self.mainloop:
            try:
                msg = "Force stopping Bluetooth service..."
                logging.info(msg)
                self.logs.append(msg)
                self.mainloop.quit()
            except Exception:
                pass

    def getLogs(self):
        return self.logs
