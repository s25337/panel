"""
GPIO Manager - Advanced GPIO automation logic
Handles device automation rules and scheduling
"""
import json
import os
import datetime
import logging
import threading
import time
from src.json_manager import load_json_secure, save_json_secure

logger = logging.getLogger(__name__)


class AutomationRules:
    """Defines automation rules for devices"""
    
    @staticmethod
    def apply_temperature_rules(devices_info, sensor_data, settings):
        temp = sensor_data.get('temperature')
        if temp is None:
            return
        
        target_temp = settings.get('target_temp', 25.0)
        
        # Fan control
        if devices_info.get("fan", {}).get("mode") == "auto":
            if temp > target_temp:
                devices_info["fan"]["state"] = "on"
            else:
                devices_info["fan"]["state"] = "off"
        
        # Heater control
        if devices_info.get("heat_mat", {}).get("mode") == "auto":
            if temp < target_temp:
                devices_info["heat_mat"]["state"] = "on"
            else:
                devices_info["heat_mat"]["state"] = "off"

    @staticmethod
    def apply_humidity_rules(devices_info, sensor_data, settings):
        """Apply humidity-based automation rules"""
        humid = sensor_data.get('humidity')
        if humid is None:
            return
        
        target_hum = settings.get('target_hum', 60.0)
        
        # Sprinkler control
        if devices_info.get("sprinkler", {}).get("mode") == "auto":
            if humid < target_hum:
                devices_info["sprinkler"]["state"] = "on"
            else:
                devices_info["sprinkler"]["state"] = "off"

    @staticmethod
    def apply_brightness_rules(devices_info, sensor_data, settings, current_time_str, devices_info_file_path):
        """Apply brightness and light schedule automation rules"""
        light_schedule = settings.get('light_schedule', {})
        start_time = light_schedule.get('start_time', '06:00')
        end_time = light_schedule.get('end_time', '18:00')
        if current_time_str != start_time and current_time_str != end_time :
            devices_info["light"]["intensity"] = int(settings.get("light_intensity"))/100
            try:
                save_json_secure(devices_info_file_path,devices_info)
                return
            except Exception as e:
                logging.error(f"Failed to save settings to file: {e}")
       
        if start_time <= current_time_str <= end_time:
            devices_info["light"]["state"] = "on"
            bright = sensor_data.get('brightness')
            if bright is not None:
                devices_info["light"]["intensity"] = min(1.0, max(0.0, bright / settings.get('optimal_light', 1.0)))
            else:
                devices_info["light"]["intensity"] = 1.0
        else:
            devices_info["light"]["state"] = "off"

    @staticmethod
    def apply_watering_schedule(devices_info, settings, sensor_data):
        """Apply watering schedule automation"""
        if devices_info.get("pump", {}).get("mode") != "auto":
            return
        if devices_info.get("pump",{}).get("state") == "on":
            return
        else:
            now = datetime.datetime.now()
            watering_days = settings.get('watering_days', [])
            current_day = int(datetime.datetime.now().strftime("%w"))
            current_time = datetime.datetime.now().strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")
            watering_time = settings.get('watering_time', '13:44')
            last_run = str(devices_info.get("pump", {}).get("last_edit_date"))[:10]
            if last_run == current_date_str:
               return
            
            if current_day in watering_days and current_time == watering_time:
               logging.info("Got here")
               if sensor_data.get("water_min_level") == "low":
                  devices_info["pump"]["last_edit_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                  #logger.info(f"Watering scheduled: {current_day} at {watering_time} but not triggered due to too little water in tank")
                  return
               devices_info["pump"]["state"] = "on"
               devices_info["pump"]["last_edit_date"] = current_date_str
               logger.info(f"Watering schedule triggered: {current_day} at {watering_time}")
               return
            

    PUMP_CAL_ML = 300.0
    PUMP_CAL_S = 21.0
    PUMP_S_PER_ML = PUMP_CAL_S / PUMP_CAL_ML

    @staticmethod
    def apply_watering_rules(devices_info, settings, settings_file_path):
       if devices_info.get("pump",{}).get("state") == "on" and str(devices_info.get("pump",{}).get("last_edit_date"))[:10] != datetime.datetime.now().strftime("%Y-%m-%d"):
            settings["water_seconds"] = (settings.get('water_seconds', 21) * AutomationRules.PUMP_S_PER_ML)
            try:
                with open(settings_file_path, 'w') as f:
                    json.dump(settings, f, indent=4)
                logging.info(f"Updated water_seconds to {settings['water_seconds']} and saved to file.")
            except Exception as e:
                logging.error(f"Failed to save settings to file: {e}")
            #time.sleep(settings.get('water_seconds', 3) * AutomationRules.PUMP_S_PER_ML)
            logging.info(f"Pump sleeping for {settings.get('water_seconds', 3) * AutomationRules.PUMP_S_PER_ML}")
            #devices_info["pump"]["state"] = "off"
            return

    

def apply_automation_rules(devices_info, sensor_data, settings, settings_file_path, devices_info_file_path):

    try:
        current_time_str = datetime.datetime.now().strftime("%H:%M")
        
        # Apply automation rules
        AutomationRules.apply_temperature_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_humidity_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_brightness_rules(devices_info, sensor_data, settings, current_time_str, devices_info_file_path)
        AutomationRules.apply_watering_rules(devices_info, settings, settings_file_path)
        AutomationRules.apply_watering_schedule(devices_info, settings, sensor_data)
    except Exception as e:
        logger.error(f"Automation rules error: {e}")
