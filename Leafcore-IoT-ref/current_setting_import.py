import requests
import json
import os
import sys

setting_import_endpoint_url = "http://172.19.14.15:8080/terrarium/dataTerrarium"

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

OUTPUT_FILE = os.path.join(current_dir, "sensor_data.json")

try:
    response = requests.get(setting_import_endpoint_url, timeout=(3.05, 5))
    
    response.raise_for_status()
    
    data = response.json()
    
    print(f"Received config: {data}")

    with open(OUTPUT_FILE, "w") as f:
         json.dump(data, f, indent=4)
except Exception as e:
    print(f"File update error: {e}")



except requests.exceptions.Timeout:
    print("Server didn't reply in time. Keeping old config.")
except requests.exceptions.ConnectionError:
    print("Network down.")
except Exception as e:
    print(f"Error: {e}")