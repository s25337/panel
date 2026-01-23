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
import sys
from src.json_manager import load_json_secure, save_json_secure

logger = logging.getLogger(__name__)


class AutomationRules:
    """Defines automation rules for devices"""
    PUMP_CAL_ML = 300.0
    PUMP_CAL_S = 21.0
    PUMP_ML_PER_S = PUMP_CAL_S / PUMP_CAL_ML
    @staticmethod
    def apply_temperature_rules(devices_info, sensor_data, settings):
        temp = sensor_data.get('temperature')
        if temp is None:
            return
        if devices_info.get("pump", {}).get("state") == "on":
           devices_info["fan"]["state"] = "off"
           devices_info["heat_mat"]["state"] = "off"
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
        if devices_info.get("pump", {}).get("state") == "on":
           devices_info["sprinkler"]["state"] = "off"
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
        start_time = settings.get('start_hour', 6)
        end_time = settings.get('end_hour', 18)
        is_light_time = False
        needed = 0
        if start_time == end_time:
           devices_info["light"]["intensity"] = 0.0
           devices_info["light"]["state"] = "off"
           return
        if start_time < end_time:
            if start_time <= current_time_str <= end_time:
               is_light_time = True
        else:
            if current_time_str >= start_time or current_time_str < end_time:
               is_light_time = True
        if is_light_time:
            devices_info["light"]["state"] = "on"
            bright = sensor_data.get('brightness')
            if bright is not None:
                target = float(settings.get('optimal_light', 1.0))
                if bright < target:
                   needed = target - bright
                   devices_info["light"]["intensity"] = needed
                else:
                   devices_info["light"]["intensity"] = 0.0
                   devices_info["light"]["intensity"] = min(1.0, max(0.0, bright / settings.get('optimal_light', 1.0)))
            else:
                devices_info["light"]["intensity"] = 1.0
        else:
            devices_info["light"]["intensity"] = needed
            devices_info["light"]["state"] = "off"
    @staticmethod
    def apply_watering_schedule(devices_info, settings, sensor_data, settings_file):
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
            settings["watering_time"] = settings.get('water_seconds', 3) * AutomationRules.PUMP_ML_PER_S
            try:
               save_json_secure(settings_file, settings)
            except Exception as e:
               return
            last_run = str(devices_info.get("pump", {}).get("last_edit_date"))[:10]
            if last_run == current_date_str:
               return
            if current_day in watering_days and current_time == "17:51":
               logging.info("Got here")
               if sensor_data.get("water_min_level") == "low":
                  devices_info["pump"]["last_edit_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                  logger.info(f"Watering scheduled: {current_day} but not triggered due to too little water")
                  return
               devices_info["sprinkler"]["state"] = "off"
               devices_info["heat_mat"]["state"] = "off"
               devices_info["fan"]["state"] = "off"
               time.sleep(5)
               devices_info["pump"]["state"] = "on"
               devices_info["pump"]["last_edit_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
               logger.info(f"Watering schedule triggered: {current_day} at {watering_time}")
               return

    @staticmethod
    def apply_watering_rules(devices_info, settings, settings_file_path):
       if devices_info["pump"].get("manual_trigger"):
            devices_info["sprinkler"]["state"] = "off"
            devices_info["heat_mat"]["state"] = "off"
            devices_info["fan"]["state"] = "off"
            devices_info["pump"]["state"] = "on"
            devices_info["pump"]["last_edit_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            settings["watering_time"] = settings.get('water_seconds', 3) * AutomationRules.PUMP_ML_PER_S
            logging.info("Watering started")
            try:
               save_json_secure(settings_file, settings)
            except Exception as e:
               return
            return
def apply_automation_rules(devices_info, sensor_data, settings, settings_file_path, devices_info_file_path):
    try:
        current_time_str = int(datetime.datetime.now().strftime("%H"))

        # Apply automation rules
        AutomationRules.apply_temperature_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_humidity_rules(devices_info, sensor_data, settings)
        AutomationRules.apply_brightness_rules(devices_info, sensor_data, settings, current_time_str, devices_info_file_path)
        AutomationRules.apply_watering_rules(devices_info, settings, settings_file_path)
        AutomationRules.apply_watering_schedule(devices_info, settings, sensor_data, settings_file_path)
    except Exception as e:
        logger.error(f"Automation rules error: {e}")
