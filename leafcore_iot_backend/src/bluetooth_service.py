import sys
import logging
import signal
import subprocess
import requests
import json
import os
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
        logging.warning("Exiting Python script...")
        # os._exit(1)
    except Exception as e:
        logging.error(f"Failed to switch to terminal: {e}")

class WifiConfigurator:
    def __init__(self, devices_info_file, connection_event=None, watchdog_timer=None):
        self.ssid_buffer = b""
        self.pass_buffer = b""
        self.userid_buffer = b"" 
        self.ssid = None
        self.password = None
        self.userid = None
        self.devices_info_file = devices_info_file
        self.server_url = "http://33.11.238.45:8081/terrarium/"
        self.connection_event = connection_event
        self.watchdog_timer = watchdog_timer

    def on_ssid_write(self, value, options):
        self.ssid_buffer += bytes(value)
        logging.info(f"Appended SSID chunk. Buffer is now {len(self.ssid_buffer)} bytes.")

    def on_pass_write(self, value, options):
        self.pass_buffer += bytes(value)
        logging.info(f"Appended Password chunk. Buffer is now {len(self.pass_buffer)} bytes.")

    def on_user_id_write(self, value, options):
        self.userid_buffer += bytes(value)
        logging.info(f"Appended User ID chunk. Buffer is now {len(self.userid_buffer)} bytes.")

    def on_ssid_execute(self, value, options):
        logging.info("SSID Execute received. Decoding buffer...")
        try:
            self.ssid = self.ssid_buffer.decode('utf-8')
            logging.info(f"Decoded SSID: {self.ssid}")
        except Exception as e:
            logging.error(f"Error decoding SSID: {e}")
        finally:
            self.ssid_buffer = b""

    def on_pass_execute(self, value, options):
        logging.info("Password Execute received. Decoding buffer...")
        try:
            self.password = self.pass_buffer.decode('utf-8')
            logging.info("Decoded Password (hidden)")
        except Exception as e:
            logging.error(f"Error decoding password: {e}")
        finally:
            self.pass_buffer = b""
            t = threading.Thread(target=self.attempt_connect)
            t.start()

    def on_userid_execute(self, value, options):
        logging.info("Userid Execute received. Decoding buffer...")
        try:
            self.userid = self.userid_buffer.decode('utf-8')
            logging.info(f"Decoded userid: {self.userid}")
        except Exception as e:
            logging.error(f"Error decoding password: {e}")
        finally:
            self.userid_buffer = b""

    def attempt_connect(self):

        if not self.ssid or not self.password:
            logging.warning("Missing credentials, waiting for both...")
            return

        logging.info(f"Attempting to connect to SSID: {self.ssid}")
        if self.connection_event:
            self.connection_event.set()
        
        try:
            cmd = ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']
            check_connection = subprocess.run(cmd, capture_output=True, text=True)
            
            if check_connection.returncode == 0 and f"yes:{self.ssid}" in check_connection.stdout:
                 logging.info("Device is already connected to this network.")
            else:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', self.ssid, 'password', self.password]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                logging.info(f"NetworkManager output: {result.stdout}")
                logging.info("--- Successfully connected to Wi-Fi! ---")

            logging.info("--- Sending device data to server... ---")
            url = self.server_url + "module"
            time.sleep(5) 

            # --- Registration Logic ---
            try:
                with open(self.devices_info_file, 'r') as f:
                    devices_info = json.load(f)
                    logging.info("Loaded devices info json")

                for device in devices_info.values():
                    device["is_registered"] = 1
                    # Ensure we use the userid decoded earlier
                    device["user_id"] = self.userid 
                    device["last_edit_date"] = datetime.datetime.now().isoformat()
                    logging.info(f"Setting User ID to: {device['user_id']}")

                response = requests.post(url, json=devices_info, timeout=10)
                logging.info("Waiting for response...")

                if response.status_code == 200:
                    logging.info("Server response: 200 OK. Saving updated device info to file.")
                    with open(self.devices_info_file, 'w') as f:
                        json.dump(devices_info, f, indent=4)
                else:
                    logging.error(f"Server response: {response.status_code}. Failed to register devices.")
                    logging.error("Please try again.")

            except Exception as e:
                logging.error(f"Error sending device data: {e}")
            
            # --- Cleanup ---
            if self.watchdog_timer:
                logging.info("Cancelling Watchdog Timer.")
                self.watchdog_timer.cancel()
                
        except FileNotFoundError:
            logging.error("--- 'nmcli' command not found. ---")
        except subprocess.TimeoutExpired:
            logging.error("--- Wi-Fi connection timed out. ---")
        except subprocess.CalledProcessError as e:
            logging.error("--- Failed to connect to Wi-Fi. ---")
            logging.error(f"nmcli error: {e.stderr}")
        except Exception as e:
            logging.error(f"Connection logic error: {e}")
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
        self.watchdog = None

    def run(self):
        if not BLUEZERO_AVAILABLE:
            logging.warning("Bluezero not installed - Bluetooth service disabled")
            return

        logging.basicConfig(level=logging.INFO)
        self.mainloop = async_tools.EventLoop()
        
        logging.info("Starting 20-second Watchdog Timer...")
        self.watchdog = threading.Timer(10.0, switch_to_terminal)
        self.watchdog.start()
        
        config = WifiConfigurator(
            self.devices_info_file, 
            connection_event=self.connection_event, 
            watchdog_timer=self.watchdog
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
                flags=['write', 'write-without-response'], # Added write-without-response for chunking
                read_callback=None,
                write_callback=config.on_user_id_write # FIX: Correct callback name
            )

            logging.info(f"Adding user Execute characteristic: {USER_ID_EXEC_UUID}")
            my_server.add_characteristic(
                srv_id=0, chr_id=5, uuid=USER_ID_EXEC_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_userid_execute
            )
            
            

            logging.info("Bluetooth server is published and broadcasting. Waiting for WiFi config...")
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
