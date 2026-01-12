# src/services/settings_service.py
"""
Settings management service with generic JSON store
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Manages application settings with generic JSON store pattern
    Eliminates code duplication between settings and manual_settings
    """
    
    # Store configurations: name -> {file, defaults}
    STORES = {
        "settings": {
            "file": "settings_config.json",
            "defaults": {
                "setting_id": "1",
                "plant_name": "default plant",
                "target_temp": 25.0,
                "target_hum": 60.0,
                "watering_days": ["MONDAY", "WEDNESDAY", "FRIDAY"],
                "water_seconds": 1,
                "watering_mode": "standard",
                "light_intensity": 50.0,
                "start_hour": 6,
                "end_hour": 18
            }
        },
        "manual": {
            "file": "manual_settings.json",
            "defaults": {
                "is_manual": False,
                "light": False,
                "heater": False,
                "fan": False,
                "pump": False,
                "sprinkler": False
            }
        }
    }
    
    def __init__(self, settings_file: str = "settings_config.json", 
                 manual_settings_file: str = "manual_settings.json",
                 external_terrarium_service=None):
        """Initialize settings service with generic store pattern"""
        # Convert to absolute paths if relative
        from pathlib import Path
        settings_file = str(Path(settings_file).resolve())
        manual_settings_file = str(Path(manual_settings_file).resolve())
        
        # Override file paths if provided
        self.STORES["settings"]["file"] = settings_file
        self.STORES["manual"]["file"] = manual_settings_file
        
        # External terrarium service for syncing settings
        self.external_terrarium_service = external_terrarium_service
        
        # Load all stores
        self._stores = {}
        for store_name, config in self.STORES.items():
            self._stores[store_name] = self._load_store(
                config["file"],
                config["defaults"]
            )

    # ========== GENERIC STORE OPERATIONS ==========
    
    def _load_store(self, filepath: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Generic load for any JSON store"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                # Fix potential JSON corruption (duplicate braces)
                while '}}' in content:
                    content = content.replace('}}', '}')
                data = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            data = defaults.copy()
            self._save_store(filepath, data)
        
        # Merge with defaults (ensure all keys exist)
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        
        return data

    def _save_store(self, filepath: str, data: Dict[str, Any]) -> None:
        """Generic save for any JSON store"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"✅ Saved settings to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save settings to {filepath}: {e}")


    def _get_store(self, store: str) -> Dict[str, Any]:
        """Get store data"""
        return self._stores.get(store, {})

    def _set_store(self, store: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update store with validation against defaults"""
        if store not in self.STORES:
            return {}
        
        defaults = self.STORES[store]["defaults"]
        store_data = self._stores[store]
        
        # Only update keys that exist in defaults
        for key, value in updates.items():
            if key in defaults:
                store_data[key] = value
        
        # Persist to disk
        filepath = self.STORES[store]["file"]
        self._save_store(filepath, store_data)
        
        # Notify external terrarium service of settings changes
        if store == "settings" and self.external_terrarium_service:
            logger.info(f"[SettingsService] Settings updated, notifying external service...")
            try:
                self.external_terrarium_service.notify_settings_changed(updates)
            except Exception as e:
                logger.warning(f"Failed to notify external terrarium service: {e}")
        elif store == "settings":
            logger.warning(f"[SettingsService] external_terrarium_service is None - cannot notify")
        
        return store_data.copy()

    # ========== SETTINGS API (backward compatible) ==========
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._get_store("settings").copy()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get specific setting"""
        return self._get_store("settings").get(key, default)

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update multiple settings"""
        return self._set_store("settings", updates)

    def set_setting(self, key: str, value: Any) -> None:
        """Set individual setting"""
        self._set_store("settings", {key: value})

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save complete settings dict"""
        self._stores["settings"] = settings
        self._save_store(self.STORES["settings"]["file"], settings)

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from disk (refresh)"""
        self._stores["settings"] = self._load_store(
            self.STORES["settings"]["file"],
            self.STORES["settings"]["defaults"]
        )
        return self.get_settings()

    # ========== MANUAL SETTINGS API (backward compatible) ==========
    
    def get_manual_settings(self) -> Dict[str, Any]:
        """Get all manual settings"""
        return self._get_store("manual").copy()

    def get_manual_setting(self, key: str, default: Any = None) -> Any:
        """Get specific manual setting"""
        return self._get_store("manual").get(key, default)

    def update_manual_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update multiple manual settings"""
        return self._set_store("manual", updates)

    def set_manual_setting(self, key: str, value: Any) -> None:
        """Set individual manual setting"""
        self._set_store("manual", {key: value})

    def save_manual_settings(self, settings: Dict[str, Any]) -> None:
        """Save complete manual settings dict"""
        self._stores["manual"] = settings
        self._save_store(self.STORES["manual"]["file"], settings)

    def is_manual_mode(self) -> bool:
        """Check if manual mode is enabled"""
        return self._get_store("manual").get("is_manual", False)

    def calculate_light_hours(self) -> float:
        """
        Calculate light hours based on start_hour and end_hour
        If end_hour > start_hour: simple difference
        If end_hour < start_hour: assumes light goes through midnight (24 - start + end)
        """
        settings = self.get_settings()
        start = int(settings.get("start_hour", 6))
        end = int(settings.get("end_hour", 18))
        
        if end > start:
            return float(end - start)
        else:
            # Light goes through midnight
            return float(24 - start + end)
