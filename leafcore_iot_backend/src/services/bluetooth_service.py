"""
Bluetooth Service for Wi-Fi Configuration
Handles BLE advertising for device setup and registration
"""

import logging
import signal
import subprocess
import requests
import json
import os
import datetime
import threading
from typing import Optional, Dict, Any

try:
    from bluezero import peripheral, adapter, async_tools
    BLUEZERO_AVAILABLE = True
except ImportError:
    BLUEZERO_AVAILABLE = False
    logging.warning("bluezero library not available - Bluetooth disabled")

# BLE Service & Characteristic UUIDs
LEAFCORE_SERVICE_UUID = "c62a771b-095e-4f60-a383-bca1f8f96210"
SSID_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f1"
PASS_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f2"
SSID_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f3"
PASS_EXEC_CHAR_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f4"
USER_ID_UUID = "5c3dc741-7850-4b0a-ac77-1ea26bdb73f5"
DEVICE_NAME = "LC_Greenhouse"

# Server URLs
CLOUD_SERVER_URL = "http://33.11.238.45:8081/terrarium/"
LOCAL_SERVER_URL = "http://172.19.14.15:8080/terrarium/"


class WifiConfigurator:
    """Manages Wi-Fi configuration via BLE"""
    
    def __init__(self, devices_info_file: str, settings_service: Optional[Any] = None):
        self.ssid_buffer = b""
        self.pass_buffer = b""
        self.ssid: Optional[str] = None
        self.password: Optional[str] = None
        self.userid: Optional[str] = None
        self.devices_info_file = devices_info_file
        self.settings_service = settings_service
        self.logger = logging.getLogger("WifiConfigurator")

    def on_ssid_write(self, value: bytes, options: Dict[str, Any]) -> None:
        """Handle SSID characteristic write"""
        self.ssid_buffer += bytes(value)
        self.logger.info(f"Appended SSID chunk. Buffer: {len(self.ssid_buffer)} bytes")

    def on_pass_write(self, value: bytes, options: Dict[str, Any]) -> None:
        """Handle Password characteristic write"""
        self.pass_buffer += bytes(value)
        self.logger.info(f"Appended Password chunk. Buffer: {len(self.pass_buffer)} bytes")

    def on_ssid_execute(self, value: bytes, options: Dict[str, Any]) -> None:
        """Handle SSID execute command"""
        self.logger.info("SSID Execute received. Decoding buffer...")
        try:
            self.ssid = self.ssid_buffer.decode('utf-8')
            self.logger.info(f"Decoded SSID: {self.ssid}")
        except Exception as e:
            self.logger.error(f"Error decoding SSID: {e}")
        finally:
            self.ssid_buffer = b""
            self.attempt_connect()

    def on_pass_execute(self, value: bytes, options: Dict[str, Any]) -> None:
        """Handle Password execute command"""
        self.logger.info("Password Execute received. Decoding buffer...")
        try:
            self.password = self.pass_buffer.decode('utf-8')
            self.logger.info("Decoded Password (hidden)")
        except Exception as e:
            self.logger.error(f"Error decoding password: {e}")
        finally:
            self.pass_buffer = b""
            self.attempt_connect()

    def on_user_id(self, value: bytes, options: Dict[str, Any]) -> None:
        """Handle User ID characteristic write"""
        self.logger.info("User ID received")
        try:
            self.userid = value.decode('utf-8') if isinstance(value, bytes) else str(value)
        except Exception as e:
            self.logger.error(f"Error decoding User ID: {e}")

    def attempt_connect(self) -> None:
        """Attempt Wi-Fi connection with received credentials"""
        if not self.ssid or not self.password:
            self.logger.warning("Missing credentials, waiting for both...")
            return

        self.logger.info(f"Attempting to connect to SSID: {self.ssid}")
        try:
            # Check if already connected
            cmd = ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']
            check_connection = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if check_connection.returncode == 0 and 'yes' in check_connection.stdout:
                self.logger.info("Already connected to a network. Skipping connection.")
            else:
                # Connect to new network
                cmd = ['nmcli', 'dev', 'wifi', 'connect', self.ssid, 'password', self.password]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.logger.info("Successfully connected to Wi-Fi!")
                    self._register_device()
                else:
                    self.logger.error(f"Wi-Fi connection failed: {result.stderr}")

        except FileNotFoundError:
            self.logger.error("nmcli command not found")
        except subprocess.TimeoutExpired:
            self.logger.error("Wi-Fi connection timed out")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to connect to Wi-Fi: {e.stderr}")
        finally:
            self.ssid = None
            self.password = None

    def _register_device(self) -> None:
        """Register device with cloud server"""
        self.logger.info("Sending device data to server...")
        
        try:
            with open(self.devices_info_file, 'r') as f:
                devices_info = json.load(f)

            # Update device info
            for device_key, device in devices_info.items():
                device["is_registered"] = 1
                device["user_id"] = self.userid
                device["last_edit_date"] = datetime.datetime.now().isoformat()

            # Send to cloud server
            try:
                response = requests.post(
                    f"{CLOUD_SERVER_URL}module",
                    json=devices_info,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.logger.info("Cloud registration successful. Saving device info...")
                    with open(self.devices_info_file, 'w') as f:
                        json.dump(devices_info, f, indent=4)
                else:
                    self.logger.error(f"Cloud registration failed: {response.status_code}")
            except requests.RequestException as e:
                self.logger.error(f"Cloud server error: {e}")

        except FileNotFoundError as e:
            self.logger.error(f"Device info file not found: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in device info file: {e}")


class BluetoothService:
    """Manages Bluetooth LE advertising and configuration"""
    
    def __init__(self, devices_info_file: str, settings_service: Optional[Any] = None):
        self.devices_info_file = devices_info_file
        self.settings_service = settings_service
        self.logger = logging.getLogger("BluetoothService")
        self.running = False
        self.ble_thread: Optional[threading.Thread] = None
        self._ble_ready = threading.Event()  # Signal when BLE server is successfully started
        
        if not BLUEZERO_AVAILABLE:
            self.logger.warning("Bluetooth service disabled - bluezero not available")

    def start(self) -> bool:
        """Start Bluetooth service in background thread. Returns True if successful, False otherwise."""
        if not BLUEZERO_AVAILABLE:
            self.logger.warning("Cannot start Bluetooth service - bluezero not installed")
            return False

        if self.running:
            self.logger.warning("Bluetooth service already running")
            return False

        self.running = True
        self._ble_ready.clear()  # Reset ready flag
        self.ble_thread = threading.Thread(target=self._run_ble_server, daemon=True)
        self.ble_thread.start()
        
        # Wait up to 5 seconds for BLE server to be ready
        if self._ble_ready.wait(timeout=5):
            self.logger.info("Bluetooth service started successfully")
            return True
        else:
            self.logger.error("Bluetooth service failed to start within timeout")
            self.running = False
            return False

    def stop(self) -> None:
        """Stop Bluetooth service"""
        self.running = False
        if self.ble_thread:
            self.ble_thread.join(timeout=5)
        self.logger.info("Bluetooth service stopped")

    def _run_ble_server(self) -> None:
        """Run BLE advertising server"""
        if not BLUEZERO_AVAILABLE:
            return

        self.logger.info("Starting BLE server...")
        mainloop = async_tools.EventLoop()
        config = WifiConfigurator(self.devices_info_file, self.settings_service)

        try:
            # Get adapter
            dongle = adapter.Adapter()
            self.logger.info(f"Using Bluetooth adapter: {dongle.address}")

            # Create peripheral
            my_server = peripheral.Peripheral(
                adapter_address=dongle.address,
                local_name=DEVICE_NAME
            )

            # Add service
            my_server.add_service(
                srv_id=0,
                uuid=LEAFCORE_SERVICE_UUID,
                primary=True
            )

            # Add characteristics
            self.logger.info("Adding BLE characteristics...")
            
            my_server.add_characteristic(
                srv_id=0, chr_id=0, uuid=SSID_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_ssid_write
            )

            my_server.add_characteristic(
                srv_id=0, chr_id=1, uuid=PASS_CHAR_UUID, value=[], notifying=False,
                flags=['write', 'write-without-response'],
                read_callback=None,
                write_callback=config.on_pass_write
            )

            my_server.add_characteristic(
                srv_id=0, chr_id=2, uuid=SSID_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_ssid_execute
            )

            my_server.add_characteristic(
                srv_id=0, chr_id=3, uuid=PASS_EXEC_CHAR_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_pass_execute
            )

            my_server.add_characteristic(
                srv_id=0, chr_id=4, uuid=USER_ID_UUID, value=[], notifying=False,
                flags=['write'],
                read_callback=None,
                write_callback=config.on_user_id
            )

            # Publish and run
            my_server.publish()
            self.logger.info(f"BLE server published as '{DEVICE_NAME}'")
            self.logger.info("Waiting for Wi-Fi configuration via Bluetooth...")
            
            # Signal that BLE server is ready
            self._ble_ready.set()
            
            mainloop.run()

        except Exception as e:
            self.logger.error(f"BLE server error: {e}")
            self._ble_ready.clear()  # Clear ready flag on error
        finally:
            if 'mainloop' in locals() and mainloop.is_running():
                mainloop.quit()
            self.running = False
            self._ble_ready.clear()
