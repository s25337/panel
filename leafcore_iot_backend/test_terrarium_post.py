#!/usr/bin/env python3
"""
Test script - POST sensor data to external Terrarium server
Reads actual data from source_files/sensor_data.json
"""
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.services import SettingsService

def main():
    print("🔄 Loading data...\n")
    
    # Load sensor data from file
    sensor_file = Path("source_files/sensor_data.json").resolve()
    print(f"📂 Reading sensor data from: {sensor_file}")
    
    try:
        with open(sensor_file, 'r') as f:
            sensor_data_file = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {sensor_file}")
        return
    
    temp = sensor_data_file.get('temperature')
    hum = sensor_data_file.get('humidity')
    light = sensor_data_file.get('brightness')
    
    print(f"📊 Sensor data from file:")
    print(f"   Temperature: {temp}°C")
    print(f"   Humidity: {hum}%")
    print(f"   Light: {light}")
    print()
    
    # Load settings
    settings_service = SettingsService(
        settings_file="source_files/settings_config.json",
        manual_settings_file="manual_settings.json"
    )
    
    settings = settings_service.get_settings()
    print("⚙️ Settings:")
    print(f"   setting_id: {settings.get('setting_id')}")
    print(f"   plant_name: {settings.get('plant_name')}")
    print()
    
    # Prepare data for Terrarium server
    terrarium_data = {
        "temperature": float(temp),
        "moisture": float(hum),
        "brightness": float(light),
        "timestamp": datetime.now().isoformat()
    }
    
    endpoint = "http://31.11.238.45:8081/terrarium/sendData"
    
    print("📤 Sending to Terrarium server...")
    print(f"   Endpoint: {endpoint}")
    print(f"\n📋 Data:")
    print(json.dumps(terrarium_data, indent=2))
    print()
    
    try:
        response = requests.post(
            endpoint,
            json=terrarium_data,
            timeout=5
        )
        response.raise_for_status()
        print(f"✅ POST successful (Status: {response.status_code})")
        print(f"\n📥 Server response:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"❌ POST failed: {e}")
    
if __name__ == "__main__":
    main()
