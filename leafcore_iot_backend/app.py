# app.py

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import devices
import threading
import time
from config import load_settings, save_settings, calculate_watering_interval, format_time_remaining, should_light_be_on, get_light_schedule

app = Flask(__name__)

# Konfiguruj CORS z wymaganymi headers
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Stan dla histerezi wentylatora
fan_hysteresis_state = {
    'is_on': False  # True = wentylator włączony, False = wentylator wyłączony
}

@app.route("/")
def index():
    temp, hum = devices.read_sensor()
    return render_template("index.html", temperature=temp, humidity=hum)

# API endpoints dla React Native panelu
@app.route("/api/sensors", methods=["GET"])
def get_sensors():
    """Zwraca aktualne wartości czujników"""
    temp, hum = devices.read_sensor()
    return jsonify({
        "temperature": temp,
        "humidity": hum
    })

@app.route("/api/status", methods=["GET"])
def get_status():
    """Zwraca status wszystkich urządzeń"""
    # Pobierz ustawienia i dane czujników
    settings = load_settings()
    temp, hum = devices.read_sensor()
    
    # Sprawdź czy światło powinno być włączone
    light_hours = settings.get("light_hours", 12)
    light_should_be_on = should_light_be_on(light_hours)
    devices.set_light(light_should_be_on)
    
    # Wentylator z hysterezą - włącza się przy +5%, wyłącza się przy target
    target_hum = settings.get("target_hum", 60)
    if hum is not None:
        if fan_hysteresis_state['is_on']:
            # Wentylator jest ON - wyłącz jeśli wilgotność spadnie do target
            if hum <= target_hum:
                fan_hysteresis_state['is_on'] = False
                devices.set_fan(False)
        else:
            # Wentylator jest OFF - włącz jeśli wilgotność przekroczy target + 5%
            if hum > (target_hum + 5):
                fan_hysteresis_state['is_on'] = True
                devices.set_fan(True)
    
    return jsonify({
        "fan": devices.get_fan_state(),
        "light": devices.get_light_state(),
        "pump": devices.get_pump_state()
    })

@app.route("/api/control", methods=["POST"])
def control():
    """Steruj urządzeniami"""
    data = request.json
    
    if "fan" in data:
        devices.set_fan(data["fan"])
    if "light" in data:
        devices.set_light(data["light"])
    if "pump" in data:
        devices.set_pump(data["pump"])
    
    return jsonify({"status": "OK"})

@app.route("/api/control/<device>/<state>", methods=["POST"])
def control_device(device, state):
    """Steruj konkretnym urządzeniem: /api/control/light/on"""
    state_bool = state.lower() in ["on", "true", "1"]
    
    if device == "fan":
        devices.set_fan(state_bool)
    elif device == "light":
        devices.set_light(state_bool)
    elif device == "pump":
        devices.set_pump(state_bool)
    else:
        return jsonify({"error": "Unknown device"}), 400
    
    return jsonify({"status": "OK", "device": device, "state": state_bool})

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Zwraca aktualne ustawienia docelowe"""
    settings = load_settings()
    return jsonify({
        "target_temp": settings.get("target_temp", 25),
        "target_hum": settings.get("target_hum", 60),
        "light_hours": settings.get("light_hours", 12),
        "water_times": settings.get("water_times", 3),
        "water_seconds": settings.get("water_seconds", 1)
    })

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Aktualizuje ustawienia"""
    data = request.json
    settings = load_settings()
    
    if "target_temp" in data:
        settings["target_temp"] = float(data["target_temp"])
    if "target_hum" in data:
        settings["target_hum"] = float(data["target_hum"])
    if "light_hours" in data:
        settings["light_hours"] = float(data["light_hours"])
    if "water_times" in data:
        settings["water_times"] = int(data["water_times"])
    if "water_seconds" in data:
        settings["water_seconds"] = float(data["water_seconds"])
    
    save_settings(settings)
    return jsonify({"status": "OK", "settings": settings})

@app.route("/api/watering-timer", methods=["GET"])
def get_watering_timer():
    """Zwraca czas do następnego podlewania"""
    settings = load_settings()
    water_times = settings.get("water_times", 3)
    
    # Oblicz interwał w sekundach
    interval_seconds = calculate_watering_interval(water_times)
    
    # Konwertuj na format dni:godziny:minuty:sekundy
    time_remaining = format_time_remaining(interval_seconds)
    
    return jsonify({
        "interval_seconds": interval_seconds,
        "days": time_remaining["days"],
        "hours": time_remaining["hours"],
        "minutes": time_remaining["minutes"],
        "seconds": time_remaining["seconds"],
        "water_times_per_week": water_times
    })

@app.route("/api/light-schedule", methods=["GET"])
def get_light_schedule_info():
    """Zwraca harmonogram światła"""
    settings = load_settings()
    light_hours = settings.get("light_hours", 12)
    schedule = get_light_schedule(light_hours)
    
    return jsonify({
        "light_hours": schedule["light_hours"],
        "start_hour": schedule["start_hour"],
        "start_minute": schedule["start_minute"],
        "end_hour": schedule["end_hour"],
        "end_minute": schedule["end_minute"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
