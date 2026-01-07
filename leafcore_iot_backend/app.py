# app.py

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import devices

app = Flask(__name__)
CORS(app)  # Włącz CORS dla React Native

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
