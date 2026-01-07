# config.py

import json
import os
import time

TEMP_HUMIDITY_SENSOR_PIN = 4
FAN_PIN = 17
LIGHT_PIN = 27
PUMP_PIN = 22

SETTINGS_FILE = 'settings_config.json'
LIGHT_START_TIME = 8  # Godzina 6 rano - start światła

def load_settings():
    """Wczytaj ustawienia z JSON"""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_settings()

def save_settings(settings):
    """Zapisz ustawienia do JSON"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_default_settings():
    """Zwróć domyślne ustawienia"""
    return {
        "light_hours": 12.0,
        "target_temp": 25.0,
        "target_hum": 60.0,
        "water_times": 3,
        "water_seconds": 1
    }

def calculate_watering_interval(water_times):
    """
    Oblicza czas do następnego podlewania w sekundach
    water_times = liczba podlewań na tydzień
    """
    if water_times <= 0:
        return 7 * 24 * 3600  # 7 dni jeśli 0 podlewań
    
    seconds_per_week = 7 * 24 * 3600
    interval_seconds = seconds_per_week / water_times
    return int(interval_seconds)

def format_time_remaining(seconds):
    """
    Konwertuje sekundy na format { days, hours, minutes, seconds }
    """
    days = seconds // (24 * 3600)
    seconds %= (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds
    }

def should_light_be_on(light_hours):
    """
    Sprawdza czy światło powinno być włączone
    light_hours = ile godzin dziennie światło powinno być włączone
    Światło zaczyna się o 6:00 rano i trwa przez light_hours godzin
    """
    current_time = time.localtime()
    current_hour = current_time.tm_hour
    current_minute = current_time.tm_min
    
    # Konwertuj light_hours na minuty
    light_duration_minutes = int(light_hours * 60)
    
    # Oblicz końcową godzinę + minuty
    start_minutes = LIGHT_START_TIME * 60  # 6:00 = 360 minut
    end_minutes = start_minutes + light_duration_minutes
    
    # Obecny czas w minutach od północy
    current_minutes = current_hour * 60 + current_minute
    
    # Sprawdź czy obecny czas jest w przedziale
    if end_minutes < 24 * 60:  # Nie przechodzi przez północ
        return start_minutes <= current_minutes < end_minutes
    else:  # Przechodzi przez północ (np. 6:00 - 22:00)
        # Sprawdź obie części
        end_minutes_adjusted = end_minutes - (24 * 60)
        return current_minutes >= start_minutes or current_minutes < end_minutes_adjusted

def get_light_schedule(light_hours):
    """
    Zwraca harmonogram światła - kiedy się włącza i wyłącza
    """
    start_hour = LIGHT_START_TIME
    end_hour = LIGHT_START_TIME + int(light_hours)
    end_minute = int((light_hours % 1) * 60)  # minuty z części ułamkowej
    
    # Obsłuż przechodzenie przez północ
    if end_hour >= 24:
        end_hour = end_hour - 24
    
    return {
        "start_hour": start_hour,
        "start_minute": 0,
        "end_hour": end_hour,
        "end_minute": end_minute,
        "light_hours": light_hours
    }


