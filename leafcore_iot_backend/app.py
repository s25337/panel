# app.py - Refactored main application
"""
Leafcore IoT Backend - Flask application
"""
import logging
from flask import Flask, render_template
from flask_cors import CORS

from src.devices import DeviceManager
from src.services import SettingsService, ControlService, SensorService, SyncService, BluetoothService, SensorReadingService
from src.api import create_api_routes

logger = logging.getLogger(__name__)


def create_app(use_hardware: bool = True) -> Flask:
    """Application factory"""
    app = Flask(__name__)
    
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
    settings_service = SettingsService()
    sensor_service = SensorService(device_manager)
    control_service = ControlService(device_manager, settings_service)
    sync_service = SyncService(settings_service, app_dir=".")
    sensor_reading_service = SensorReadingService(device_manager, app_dir=".")
    
    # Initialize Bluetooth service for Wi-Fi configuration
    bluetooth_service = BluetoothService(
        devices_info_file="source_files/devices_info.json",
        settings_service=settings_service
    )
    if use_hardware:
        bluetooth_service.start()
    
    # Start sensor reading service (for continuous sensor monitoring and cloud posting)
    sensor_reading_service.start()
    
    # Start background sync
    sync_service.start_background_sync()
    
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
        sensor_reading_service=sensor_reading_service
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
        sync_service.stop_background_sync()
    
    import atexit
    atexit.register(shutdown_handler)
    
    return app


if __name__ == "__main__":
    app = create_app(use_hardware=False)  # Use MockBackend for development
    app.run(host="0.0.0.0", port=5000, debug=True)

