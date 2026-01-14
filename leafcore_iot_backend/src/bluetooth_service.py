"""
Bluetooth WiFi Configurator Service
Handles WiFi credential configuration via BLE
"""
import logging
import signal
import subprocess
import requests
import json
import os
import datetime
import threading

try:
    from bluezero import peripheral, localGATT, async_tools, adapter
    BLUEZERO_AVAILABLE = True
except ImportError:
    BLUEZERO_AVAILABLE = False

LEAFCORE_SERVICE_UUID = "c62a771b-095e-4f60-a383-bca1f8f96210"
SSID_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f1"
PASS_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f2"
SSID_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f3"
PASS_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f4"
USER_ID_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f5"
DEVICE_NAME_PREFIX = "LC_Greenhouse"

logger = logging.getLogger(__name__)


class WifiConfigurator:
    def __init__(self, devices_info_file):
        self.ssid_buffer = b"" 
        self.pass_buffer = b""
        self.ssid = None
        self.password = None
        self.userid = None
        self.devices_info_file = devices_info_file
        self.server_url = "http://33.11.238.45:8081/terrarium/"

    def on_ssid_write(self, value, options):
        self.ssid_buffer += bytes(value)
        logging.info(f"Appended SSID chunk. Buffer is now {len(self.ssid_buffer)} bytes.")

    def on_pass_write(self, value, options):
        self.pass_buffer += bytes(value)
        logging.info(f"Appended Password chunk. Buffer is now {len(self.pass_buffer)} bytes.")

    def on_ssid_execute(self, value, options):
        logging.info("SSID Execute received. Decoding buffer...")
        try:
            self.ssid = self.ssid_buffer.decode('utf-8')
            logging.info(f"Decoded SSID: {self.ssid}")
        except Exception as e:
            logging.error(f"Error decoding SSID: {e}")
        finally:
            self.ssid_buffer = b""
            self.attempt_connect()

    def on_pass_execute(self, value, options):
        logging.info("Password Execute received. Decoding buffer...")
        try:
            self.password = self.pass_buffer.decode('utf-8')
            logging.info("Decoded Password (hidden)")
        except Exception as e:
            logging.error(f"Error decoding password: {e}")
        finally:
            self.pass_buffer = b""
            self.attempt_connect()

    def on_user_id(self, value, options):
        logging.info("User ID received")
        self.userid = value

    def attempt_connect(self):
        if not self.ssid or not self.password:
            logging.warning("Missing credentials, waiting for both...")
            return

        logging.info(f"Attempting to connect to SSID: {self.ssid}")
        try:
            cmd = ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']
            check_connection = subprocess.run(cmd, capture_output=True, text=True)
            if check_connection.returncode == 0 and 'yes' in check_connection.stdout:
                logging.info("Device is already connected to a network. Skipping Wi-Fi connection attempt.")
            else:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', self.ssid, 'password', self.password]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                logging.info(f"NetworkManager output: {result.stdout}")
                logging.info("--- Successfully connected to Wi-Fi! ---")
                logging.info("--- Sending device data to server... ---")
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
                        logging.info("Server response: 200 OK. Saving updated device info to file.")
                        with open(self.devices_info_file, 'w') as f:
                            json.dump(devices_info, f, indent=4)
                    else:
                        logging.error(f"Server response: {response.status_code}. Failed to register devices.")
                        logging.error("Please try again.")
                except Exception as e:
                    logging.error(f"Error sending device data: {e}")
        except FileNotFoundError:
            logging.error("--- 'nmcli' command not found. ---")
        except subprocess.TimeoutExpired:
            logging.error("--- Wi-Fi connection timed out. ---")
        except subprocess.CalledProcessError as e:
            logging.error("--- Failed to connect to Wi-Fi. ---")
            logging.error(f"nmcli error: {e.stderr}")
        finally:
            self.ssid = None
            self.password = None


class BluetoothService(threading.Thread):
    """Bluetooth BLE service for WiFi configuration"""
    
    def __init__(self, devices_info_file):
        super().__init__()
        self.daemon = True
        self.devices_info_file = devices_info_file
        self.running = True
        
    def run(self):
        if not BLUEZERO_AVAILABLE:
            logging.warning("Bluezero not installed - Bluetooth service disabled")
            return
        
        logging.basicConfig(level=logging.INFO)
        mainloop = async_tools.EventLoop()
        config = WifiConfigurator(self.devices_info_file)

        try:
            dongle = adapter.Adapter()
            logging.info(f"Using adapter: {dongle.address}")
            my_server = peripheral.Peripheral(
                adapter_address=dongle.address,
                local_name="LC_Greenhouse"
            )
            logging.info(f"Adding service: {LEAFCORE_SERVICE_UUID}")
            my_server.add_service(
                srv_id=0,
                uuid=LEAFCORE_SERVICE_UUID,
                primary=True
            )

            logging.info(f"Adding SSID characteristic: {SSID_CHAR_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=0, uuid=SSID_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_ssid_write
            )

            logging.info(f"Adding Password characteristic: {PASS_CHAR_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=1, uuid=PASS_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_pass_write
            )

            logging.info(f"Adding SSID Execute characteristic: {SSID_EXEC_CHAR_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=2, uuid=SSID_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_ssid_execute
            )

            logging.info(f"Adding Password Execute characteristic: {PASS_EXEC_CHAR_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=3, uuid=PASS_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_pass_execute
            )

            logging.info(f"Adding User ID characteristic: {USER_ID_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=4, uuid=USER_ID_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_user_id
            )

            my_server.publish()
            logging.info("Bluetooth server is published and broadcasting. Waiting for WiFi config...")
            
            while self.running:
                try:
                    mainloop.run()
                    break
                except KeyboardInterrupt:
                    break

        except adapter.AdapterError as e:
            logging.error(f"Bluetooth Error: {e}")
        except Exception as e:
            logging.error(f"Bluetooth Service Error: {e}")
        finally:
            logging.info("Shutting down Bluetooth service...")
            try:
                if 'mainloop' in locals() and mainloop.is_running():
                    mainloop.quit()
            except:
                pass

    def stop(self):
        self.running = False
