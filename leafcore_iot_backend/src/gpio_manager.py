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
    def apply_brightness_rules(devices_info, sensor_data, settings, current_time_str):
        """Apply brightness and light schedule automation rules"""
        if devices_info.get("light", {}).get("mode") != "auto":
            return
        
        light_schedule = settings.get('light_schedule', {})
        start_time = light_schedule.get('start_time', '06:00')
        end_time = light_schedule.get('end_time', '18:00')
        
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
    def apply_watering_schedule(devices_info, settings):
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
            watering_time = settings.get('watering_time', '18:10')
            last_run = devices_info.get("pump", {}).get("last_edit_date")
            if last_run == current_date_str:
               return
            #logger.info(f"Watering schedule: {watering_days},{current_time},{current_day},{watering_time}")
            if current_day in watering_days and current_time == watering_time:
               devices_info["pump"]["state"] = "on"
               devices_info["pump"]["last_edit_date"] = current_date_str
               logger.info(f"Watering schedule triggered: {current_day} at {watering_time}")
               return
            

    PUMP_CAL_ML = 300.0
    PUMP_CAL_S = 21.0
    PUMP_S_PER_ML = PUMP_CAL_S / PUMP_CAL_ML

    @staticmethod
    def apply_watering_rules(devices_info, settings):
        if devices_info.get("pump",{}).get("state") == "on":
            time.sleep(settings.get('water_seconds', 3) * AutomationRules.PUMP_S_PER_ML)
            devices_info["pump"]["state"] = "off"
            return

    

def apply_automation_rules(devices_info, sensor_data, settings):

    try:
        current_time_str = datetime.datetime.now().strftime("%H:%M")
        
        # Apply automation rules
        AutomationRules.apply_temperature_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_humidity_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_brightness_rules(devices_info, sensor_data, settings, current_time_str)
        AutomationRules.apply_watering_schedule(devices_info, settings)
        AutomationRules.apply_watering_rules(devices_info, settings)
        
        
    except Exception as e:
        logger.error(f"Automation rules error: {e}")
