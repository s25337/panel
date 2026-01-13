# app.py - Refactored main application
"""
Leafcore IoT Backend - Flask application
"""
import logging
from flask import Flask, render_template
from flask_cors import CORS

from src.devices import DeviceManager
from src.services import SettingsService, ControlService, SensorService, BluetoothService, SensorReadingService, ExternalTerriumService, GPIOAutomationService
from src.api import create_api_routes

logger = logging.getLogger(__name__)


def create_app(use_hardware: bool = True) -> Flask:
    """Application factory"""
    app = Flask(__name__)
    app.config['ENV'] = 'production'  # Disable Flask debug mode and auto-reloading
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Initialize services
    device_manager = DeviceManager(use_hardware=use_hardware)
    
    # Initialize SensorReadingService FIRST (it's the single source of truth)
    sensor_reading_service = SensorReadingService(device_manager, app_dir=".")
    
    # SensorService reads from SensorReadingService cache
    sensor_service = SensorService(device_manager, sensor_reading_service=sensor_reading_service)
    
    control_service = ControlService(device_manager, None)  # Temporarily None
    external_terrarium_service = ExternalTerriumService(
        None,  # Will be set later
        sensor_service=sensor_service,
        sensor_reading_service=sensor_reading_service
    )
    
    # Initialize SettingsService with ExternalTerriumService reference
    settings_service = SettingsService(
        settings_file="source_files/settings_config.json",
        manual_settings_file="source_files/manual_settings.json",
        external_terrarium_service=external_terrarium_service
    )
    
    # NOW set the settings_service references (after SettingsService is created)
    control_service.settings_service = settings_service
    external_terrarium_service.settings_service = settings_service
    
    # Initialize GPIO automation service (for hardware backend auto-mode control)
    gpio_automation_service = None
    if use_hardware:
        gpio_automation_service = GPIOAutomationService(device_manager, control_service, settings_service)
    
    # Initialize Bluetooth service for Wi-Fi configuration
    bluetooth_service = BluetoothService(
        devices_info_file="source_files/devices_info.json",
        settings_service=settings_service
    )
    if use_hardware:
        bluetooth_service.start()
    
    # Start sensor reading service (for continuous sensor monitoring and cloud posting)
    sensor_reading_service.start()
    
    # Start watering automation (checks at 12:00 daily)
    control_service.start_watering_automation()
    
    # Start GPIO automation service (hardware-specific auto-mode control)
    if gpio_automation_service:
        gpio_automation_service.start()
    
    logger.info("✅ All automation services started")
    
    # Start external terrarium server sync (every 5 minutes)
    logger.info("🚀 Starting background sync service...")
    print("[DEBUG] About to call start_background_sync()")
    external_terrarium_service.start_background_sync(group_id="group-A1")
    print("[DEBUG] start_background_sync() called")
    logger.info("🚀 Background sync service started")
    
    # Send initial history file and sensor data on startup
    import threading
    def send_startup_data():
        """
        Send settings and sensor data on startup
        """
        import time
        print("[STARTUP] Thread started - Waiting 25 seconds for initial sensor readings...")
        logger.info("[STARTUP] Thread started - Waiting 25 seconds for initial sensor readings...")
        time.sleep(25)  # Wait 25s for at least one sensor read (interval=20s)
        
        print("[STARTUP] 25 seconds passed - Sending current settings...")
        logger.info("[STARTUP] 25 seconds passed - Sending current settings...")
        try:
            # Send current settings configuration to /updateSetting endpoint
            current_settings = settings_service.get_settings()
            print(f"[STARTUP] Current settings before send: {current_settings}")
            logger.info(f"[STARTUP] Current settings before send: {current_settings}")
            result = external_terrarium_service.send_settings(current_settings, group_id="group-A1")
            print(f"[STARTUP] Settings send result: {result}")
            logger.info(f"[STARTUP] Settings send result: {result}")
        except Exception as e:
            print(f"[STARTUP] Error sending settings: {e}")
            logger.error(f"[STARTUP] Error sending settings: {e}")
        
        print("[STARTUP] Sending sensor data (last 5 minutes)...")
        logger.info("[STARTUP] Sending sensor data (last 5 minutes)...")
        try:
            # Send last 5 minutes of sensor data
            result = external_terrarium_service.send_sensor_data_by_group(group_id="group-A1")
            print(f"[STARTUP] Sensor data send result: {result}")
            logger.info(f"[STARTUP] Sensor data send result: {result}")
        except Exception as e:
            print(f"[STARTUP] Error sending sensor data: {e}")
            logger.error(f"[STARTUP] Error sending sensor data: {e}")
        
        print("[STARTUP] All startup tasks completed!")
        logger.info("[STARTUP] All startup tasks completed!")
    
    threading.Thread(target=send_startup_data, daemon=False).start()
    
    # Initialize devices from saved manual settings on startup
    manual_settings = settings_service.get_manual_settings()
    if manual_settings.get('is_manual', False):
        # Restore device states from manual settings
        if manual_settings.get('fan'):
            device_manager.set_fan(True)
        if manual_settings.get('light'):
            light_state = manual_settings.get('light')
            if isinstance(light_state, bool):
                device_manager.set_light(100.0 if light_state else 0.0)
            else:
                device_manager.set_light(float(light_state))
        if manual_settings.get('pump'):
            device_manager.set_pump(True)
        if manual_settings.get('heater'):
            device_manager.set_heater(True)
        if manual_settings.get('sprinkler'):
            device_manager.set_sprinkler(True)
    
    # Register API routes
    api_blueprint = create_api_routes(
        device_manager=device_manager,
        settings_service=settings_service,
        control_service=control_service,
        sensor_service=sensor_service,
        sensor_reading_service=sensor_reading_service,
        external_terrarium_service=external_terrarium_service,
        bluetooth_service=bluetooth_service
    )
    app.register_blueprint(api_blueprint)
    
    # Web routes
    @app.route("/")
    def index():
        """Serve index.html"""
        temp, hum = device_manager.read_sensor()
        return render_template("index.html", temperature=temp, humidity=hum)
    
    # Health check
    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        return {"status": "OK"}, 200
    
    # Shutdown handler
    def shutdown_handler():
        """Stop background services on shutdown"""
        logger.info("🛑 Shutting down...")
        sensor_reading_service.stop()
        control_service.stop_watering_automation()
        if gpio_automation_service:
            gpio_automation_service.stop()
        external_terrarium_service.stop_background_sync()
    
    import atexit
    atexit.register(shutdown_handler)
    
    return app


if __name__ == "__main__":
    app = create_app(use_hardware=False)  # Use MockBackend for development
    # Enable debug for better error messages, but disable auto-reload to keep background threads alive
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

