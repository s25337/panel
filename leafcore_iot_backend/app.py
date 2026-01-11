# app.py - Refactored main application
"""
Leafcore IoT Backend - Flask application
"""
import logging
from flask import Flask, render_template
from flask_cors import CORS

from src.devices import DeviceManager
from src.services import SettingsService, ControlService, SensorService, SyncService, BluetoothService, SensorReadingService, ExternalTerriumService, HistoryService, AutomationService, GPIOAutomationService
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
    settings_service = SettingsService(
        settings_file="source_files/settings_config.json",
        manual_settings_file="manual_settings.json"
    )
    
    # Initialize SensorReadingService FIRST (it's the single source of truth)
    sensor_reading_service = SensorReadingService(device_manager, app_dir=".")
    
    # SensorService reads from SensorReadingService cache
    sensor_service = SensorService(device_manager, sensor_reading_service=sensor_reading_service)
    
    control_service = ControlService(device_manager, settings_service)
    sync_service = SyncService(settings_service, app_dir=".")
    external_terrarium_service = ExternalTerriumService(
        settings_service, 
        sensor_service=sensor_service,
        sensor_reading_service=sensor_reading_service
    )
    
    # Initialize automation service (handles scheduled watering at 12:00 daily)
    automation_service = AutomationService(device_manager, control_service, settings_service)
    
    # Initialize GPIO automation service (for hardware backend auto-mode control)
    gpio_automation_service = None
    if use_hardware:
        gpio_automation_service = GPIOAutomationService(device_manager, control_service, settings_service)
    
    # Initialize history service (24-hour rolling window with 60s interval)
    history_service = HistoryService(sensor_service=sensor_service, data_dir=".")
    
    # Initialize Bluetooth service for Wi-Fi configuration
    bluetooth_service = BluetoothService(
        devices_info_file="source_files/devices_info.json",
        settings_service=settings_service
    )
    if use_hardware:
        bluetooth_service.start()
    
    # Start sensor reading service (for continuous sensor monitoring and cloud posting)
    sensor_reading_service.start()
    
    # Start automation service (checks at 12:00 daily for watering)
    automation_service.start()
    
    # Start GPIO automation service (hardware-specific auto-mode control)
    if gpio_automation_service:
        gpio_automation_service.start()
    
    logger.info("✅ All automation services started")
    
    # Start background sync
    sync_service.start_background_sync()
    
    # Start background history capture (every 60s)
    history_service.start_background_capture()
    
    # Start external terrarium server sync (every 5 minutes)
    external_terrarium_service.start_background_sync(group_id="group-A1")
    
    # Send initial data immediately on startup (don't wait 5 minutes)
    import threading
    def send_initial_data():
        """Send sensor data immediately on startup"""
        import time
        print("[STARTUP] Waiting 25 seconds for initial sensor readings...")
        time.sleep(25)  # Wait 25s for at least one sensor read (interval=20s)
        print("[STARTUP] Sending initial sensor data...")
        try:
            result = external_terrarium_service.send_sensor_data_by_group(group_id="group-A1")
            print(f"[STARTUP] Initial send result: {result}")
        except Exception as e:
            print(f"[STARTUP] Error sending initial data: {e}")
    
    threading.Thread(target=send_initial_data, daemon=True).start()
    
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
        sync_service=sync_service,
        sensor_reading_service=sensor_reading_service,
        external_terrarium_service=external_terrarium_service,
        history_service=history_service
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
        automation_service.stop()
        if gpio_automation_service:
            gpio_automation_service.stop()
        sync_service.stop_background_sync()
        external_terrarium_service.stop_background_sync()
    
    import atexit
    atexit.register(shutdown_handler)
    
    return app


if __name__ == "__main__":
    app = create_app(use_hardware=False)  # Use MockBackend for development
    # Enable debug for better error messages, but disable auto-reload to keep background threads alive
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

