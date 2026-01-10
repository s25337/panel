# src/services/settings_service.py
"""
Settings management service
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


class SettingsService:
    """Manages application settings (persistent storage)"""
    
    DEFAULT_SETTINGS = {
        "light_hours": 23.0,
        "target_temp": 39.0,
        "target_hum": 38.0,
        "water_times": 3,
        "water_seconds": 1,
        "light_intensity": 50.0
    }
    
    DEFAULT_MANUAL_SETTINGS = {
        "is_manual": False,
        "light": False,
        "heater": False,
        "fan": False,
        "pump": False,
        "sprinkler": False
    }
    
    def __init__(self, settings_file: str = "settings_config.json", 
                 manual_settings_file: str = "manual_settings.json"):
        """Initialize settings service"""
        self.settings_file = Path(settings_file)
        self.manual_settings_file = Path(manual_settings_file)
        self._settings = self._load_settings()
        self._manual_settings = self._load_manual_settings()

    # ========== SETTINGS ==========
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        except FileNotFoundError:
            settings = self.DEFAULT_SETTINGS.copy()
            self._save_settings_to_file(settings)
        
        # Ensure all required keys exist
        for key, value in self.DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
        
        return settings

    def _save_settings_to_file(self, settings: Dict[str, Any]) -> None:
        """Save settings to JSON file"""
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

    def get_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._settings.copy()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get specific setting"""
        return self._settings.get(key, default)

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings"""
        for key, value in updates.items():
            if key in self.DEFAULT_SETTINGS:
                self._settings[key] = value
        
        self._save_settings_to_file(self._settings)
        return self._settings.copy()

    def set_setting(self, key: str, value: Any) -> None:
        """Set individual setting"""
        if key in self.DEFAULT_SETTINGS:
            self._settings[key] = value
            self._save_settings_to_file(self._settings)

    # ========== MANUAL SETTINGS ==========
    
    def _load_manual_settings(self) -> Dict[str, Any]:
        """Load manual settings from JSON file"""
        try:
            with open(self.manual_settings_file, 'r') as f:
                content = f.read()
                # Fix potential duplicates
                while '}}\n' in content or '}}' in content:
                    content = content.replace('}}', '}')
                manual_settings = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            manual_settings = self.DEFAULT_MANUAL_SETTINGS.copy()
            self._save_manual_settings_to_file(manual_settings)
        
        # Ensure all required keys exist
        for key, value in self.DEFAULT_MANUAL_SETTINGS.items():
            if key not in manual_settings:
                manual_settings[key] = value
        
        return manual_settings

    def _save_manual_settings_to_file(self, settings: Dict[str, Any]) -> None:
        """Save manual settings to JSON file"""
        with open(self.manual_settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

    def get_manual_settings(self) -> Dict[str, Any]:
        """Get all manual settings"""
        return self._manual_settings.copy()

    def get_manual_setting(self, key: str, default: Any = None) -> Any:
        """Get specific manual setting"""
        return self._manual_settings.get(key, default)

    def update_manual_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update manual settings"""
        for key, value in updates.items():
            if key in self.DEFAULT_MANUAL_SETTINGS:
                self._manual_settings[key] = value
        
        self._save_manual_settings_to_file(self._manual_settings)
        return self._manual_settings.copy()

    def set_manual_setting(self, key: str, value: Any) -> None:
        """Set individual manual setting"""
        if key in self.DEFAULT_MANUAL_SETTINGS:
            self._manual_settings[key] = value
            self._save_manual_settings_to_file(self._manual_settings)

    def is_manual_mode(self) -> bool:
        """Check if manual mode is enabled"""
        return self._manual_settings.get("is_manual", False)
