import sys
import logging
import signal
import subprocess
import requests
import json
import os
import fcntl
import datetime
import threading
import time

logging.basicConfig(level=logging.INFO)

# 2. DEBUG: Print exactly which Python executable is running
print(f"DEBUG: Running Python from: {sys.executable}", flush=True)

try:
    from bluezero import peripheral, localGATT, async_tools, adapter
    BLUEZERO_AVAILABLE = True
    print("DEBUG: Bluezero Import SUCCESS", flush=True)
except ImportError as e:
    BLUEZERO_AVAILABLE = False
    print(f"DEBUG: Bluezero Import FAILED. Error: {e}", flush=True)
    print(f"DEBUG: sys.path is: {sys.path}", flush=True)

# UUIDs
LEAFCORE_SERVICE_UUID = "c62a771b-095e-4f60-a383-bca1f8f96210"
SSID_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f1"
PASS_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f2"
SSID_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f3"
PASS_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f4"
USER_ID_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f5"
USER_ID_EXEC_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f6"

DEVICE_NAME_PREFIX = "LC_Greenhouse"

logger = logging.getLogger(__name__)


def load_json_secure(file_path):
    """Safely reads JSON by waiting for a lock."""
    lock_path = file_path + ".lock"
    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_SH) 
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)

def save_json_secure(file_path, data):
    """Safely writes JSON by locking the file exclusively."""
    lock_path = file_path + ".lock"
    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX) 
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno()) 
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)

def switch_to_terminal():
    """
    Kills the GUI/Kiosk and switches to the text terminal (TTY1).
    """
    logging.warning("!!! WATCHDOG TIMER EXPIRED: SWITCHING TO TERMINAL !!!")
    try:
        subprocess.run("sudo /bin/systemctl stop leafcore-kiosk.service", shell=True)
        # Kill the splash screen (fbi) if it's still there
        subprocess.run("sudo /usr/bin/pkill fbi", shell=True)
        subprocess.run("sudo /bin/systemctl unmask getty@tty1.service", shell=True)

        # START the login prompt
        subprocess.run("sudo /bin/systemctl start getty@tty1.service", shell=True)
        subprocess.run("sudo /usr/bin/chvt 1", shell=True)
        # os._exit(1)
    except Exception as e:
        logging.error(f"Failed to switch to terminal: {e}")

class WifiConfigurator:
    def __init__(self, devices_info_file, connection_event=None, logs=None):
        self.ssid_buffer = b""
        self.pass_buffer = b""
        self.userid_buffer = b"" 
        self.ssid = None
        self.password = None
        self.userid = None
        self.devices_info_file = devices_info_file
        self.server_url = "http://31.11.238.45:8081/terrarium/"
        self.connection_event = connection_event
        self.logs = logs or []

    def on_ssid_write(self, value, options):
        self.ssid_buffer += bytes(value)
        #logging.info(f"Appended SSID chunk. Buffer is now {len(self.ssid_buffer)} bytes.")
        msg = f"Appended SSID chunk. Buffer is now {len(self.ssid_buffer)} bytes."
        logging.info(msg)
        self.logs.append(msg)

    def on_pass_write(self, value, options):
        self.pass_buffer += bytes(value)
        #logging.info(f"Appended Password chunk. Buffer is now {len(self.pass_buffer)} bytes.")
        msg = f"Appended Password chunk. Buffer is now {len(self.pass_buffer)} bytes."
        logging.info(msg)
        self.logs.append(msg)

    def on_user_id_write(self, value, options):
        self.userid_buffer += bytes(value)
        #logging.info(f"Appended User ID chunk. Buffer is now {len(self.userid_buffer)} bytes.")
        msg = "SSID Execute received. Decoding buffer..."
        logging.info(msg)
        self.logs.append(msg)

    def on_ssid_execute(self, value, options):
        logging.info("SSID Execute received. Decoding buffer...")
        try:
            self.ssid = self.ssid_buffer.decode('utf-8')
            logging.info(f"Decoded SSID: {self.ssid}")
            msg = f"Decoded SSID: {self.ssid}"
            logging.info(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = f"Error decoding SSID: {e}"
            logging.error(msg)
            logging.error(f"Error decoding SSID: {e}")
        finally:
            self.ssid_buffer = b""

    def on_pass_execute(self, value, options):
        msg = "Password Execute received. Decoding buffer..."
        logging.error(msg)
        self.logs.append(msg)
        try:
            self.password = self.pass_buffer.decode('utf-8')
            msg = "Password Execute received. Decoding buffer..."
            logging.info(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = f"Error decoding password: {e}"
            logging.error(msg)
            self.logs.append(msg)
        finally:
            self.pass_buffer = b""
            t = threading.Thread(target=self.attempt_connect)
            t.start()

    def on_userid_execute(self, value, options):
        logging.info("Userid Execute received. Decoding buffer...")
        try:
            self.userid = self.userid_buffer.decode('utf-8')
            msg = "User ID received"
            logging.info(msg)
            self.logs.append(msg)
        except Exception as e:
            msg = "Error decoding password: {e}"
            self.logs.append(msg)
        finally:
            self.userid_buffer = b""

    def attempt_connect(self):

        if not self.ssid or not self.password:
            logging.warning("Missing credentials, waiting for both...")
            return

        msg = f"Attempting to connect to SSID: {self.ssid}"
        logging.info(msg)
        self.logs.append(msg)
        if self.connection_event:
            self.connection_event.set()
        
        try:
            cmd = ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']
            check_connection = subprocess.run(cmd, capture_output=True, text=True)
            
            if check_connection.returncode == 0 and f"yes:{self.ssid}" in check_connection.stdout:
                 logging.info("Device is already connected to this network.")
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
                logging.info(f"NetworkManager output: {result.stdout}")
                logging.info("--- Successfully connected to Wi-Fi! ---")

            logging.info("--- Sending device data to server... ---")
            url = self.server_url + "module"
            time.sleep(3) 
            # --- Registration Logic ---
            try:
                devices_info = load_json_secure(self.devices_info_file)
                devices_list = []
                for device in devices_info.values():
                    if device["is_registered"]:
                       msg = "--- This greenhouse already has an owner. Delete it from modules list first. ---"
                       logging.info(msg)
                       self.logs.append(msg)
                       return

                    device_payload = {
                    "device_name": device.get("device_name"),
                    "type": device.get("type"),
                    "user_id": int(self.userid) if self.userid else None, # Force Integer
                    "group_id": device.get("group_id"),
                    "state": device.get("state"),
                    "mode": device.get("mode"),
                    "last_edit_date":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "is_registered": True,
                    "intensity": device.get("intensity")
                    }
                    devices_list.append(device_payload)
                logging.info(f"Sent: {devices_list}")
                response = requests.post(url, json=devices_list, timeout=10)
                msg = "Waiting for response..."
                logging.info(msg)
                self.logs.append(msg)

                if response.status_code == 200:
                    msg = "Server response: 200 OK. Saving updated device info to file."
                    logging.info(msg)
                    self.logs.append(msg)
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for device in devices_info.values():
                       device["is_registered"] = True
                       device["user_id"] = int(self.userid)
                       device["last_edit_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_json_secure(self.devices_info_file, devices_info)
                else:
                    msg = f"Server response: {response.status_code}. Failed to register devices."
                    logging.error(msg)
                    self.logs.append(msg)
                    msg = "Please try again."
                    logging.error(msg)
                    self.logs.append(msg)
            except Exception as e:
                logging.error(f"Error sending device data: {e}")
                
        except FileNotFoundError:
            msg = "--- 'nmcli' command not found. ---"
            logging.error(msg)
            self.logs.append(msg)
        except subprocess.TimeoutExpired:
            logging.error("--- Wi-Fi connection timed out. ---")
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
            logging.error(f"Connection logic error: {e}")
            msg = f"Connection logic error: {e}"
            logging.error(msg)

        finally:
            self.ssid = None
            self.password = None
            self.userId = None
            try:
                logging.info("Configuration attempt finished. Stopping Bluetooth.")
                async_tools.EventLoop().quit()
            except Exception:
                pass


class BluetoothService(threading.Thread):
    """Bluetooth BLE service for WiFi configuration"""
    def __init__(self, devices_info_file, connection_event=None):
        super().__init__()
        self.daemon = True
        self.devices_info_file = devices_info_file
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
        
        config = WifiConfigurator(
            self.devices_info_file, 
            connection_event=self.connection_event, 
            logs=self.logs
        )

        try:
            dongle = adapter.Adapter()
            logging.info(f"Using adapter: {dongle.address}")
            my_server = peripheral.Peripheral(
                adapter_address=dongle.address,
                local_name=DEVICE_NAME_PREFIX
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
                flags=['write', 'write-without-response'], 
                read_callback=None,
                write_callback=config.on_user_id_write 
            )

            logging.info(f"Adding user Execute characteristic: {USER_ID_EXEC_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=5, uuid=USER_ID_EXEC_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_userid_execute
            )
            
            

            logging.info("Bluetooth server is published and broadcasting. Waiting for WiFi config...")
            msg = "Bluetooth server is published and broadcasting. Waiting for WiFi config..."
            logging.warning(msg)
            self.logs.append(msg)
            my_server.publish()
            
        except Exception as e:
            logging.error(f"Bluetooth Service Error: {e}")
        except adapter.AdapterError as e:
            logging.error(f"Bluetooth Error: {e}")

    def stop(self):
        if self.mainloop:
            try:
                if self.watchdog:
                    self.watchdog.cancel()
                logging.info("Force stopping Bluetooth service...")
                self.mainloop.quit()
            except Exception:
                pass
    def getLogs(self):
        return self.logs
