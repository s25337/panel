"""
Current Setting Importer
Fetches settings from remote server and updates local configuration
"""
import requests
import json
import os
import logging
from src.json_manager import save_json_secure, load_json_secure

logger = logging.getLogger(__name__)
SERVER_URL = os.getenv('TARGET_IP', '127.0.0.1')
SETTING_IMPORT_ENDPOINT = f"http://{SERVER_URL}:8081/terrarium/dataTerrarium"


def import_current_settings(output_file):
    """
    Fetch settings from remote server and save to file
    
    Args:
        output_file: Path to save the settings JSON
    """
    try:
        logger.info(f"Importing settings from {SETTING_IMPORT_ENDPOINT}...")
        response = requests.get(SETTING_IMPORT_ENDPOINT, timeout=(3.05, 5))
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Received config: {data}")

        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        save_json_secure(output_file,data)
        
        logger.info(f"Settings saved to {output_file}")
        return data
        
    except requests.exceptions.Timeout:
        logger.warning("Server didn't reply in time. Keeping old config.")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Network connection error.")
        return None
    except Exception as e:
        logger.error(f"Error importing settings: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(current_dir, "source_files", "settings_config.json")
    import_current_settings(output_file)
