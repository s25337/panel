# gui_tk.py
import json
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import devices

SETTINGS_PATH = Path(__file__).with_name("settings_config.json")

DEFAULT_SETTINGS = {
    "light_hours": 12.0,
    "target_temp": 22.0,
    "target_hum": 60.0,
    "water_times": 3,
    "water_seconds": 10,
}

def _parse_float(s, default=None):
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return default

def _parse_int(s, default=None):
    try:
        return int(str(s).strip())
    except Exception:
        return default

class GreenhouseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Szklarnia (tk)")
        self.root.geometry("540x560")

        # Stany
        self.fan_on = False
        self.light_on = False
        self.pump_on = False
        self.auto_mode = tk.BooleanVar(value=False)

        # Parametry (stringi do walidacji)
        self.var_light_hours = tk.StringVar(value=str(DEFAULT_SETTINGS["light_hours"]))
        self.var_target_temp = tk.StringVar(value=str(DEFAULT_SETTINGS["target_temp"]))
        self.var_target_hum  = tk.StringVar(value=str(DEFAULT_SETTINGS["target_hum"]))
        self.var_water_times = tk.StringVar(value=str(DEFAULT_SETTINGS["water_times"]))
        self.var_water_secs  = tk.StringVar(value=str(DEFAULT_SETTINGS["water_seconds"]))

        self.last_watering_days: list[date] = []
        self._pump_off_job = None  # id zaplanowanego wyłączenia pompki

        self._build_ui()

        # Wczytaj ustawienia z JSON przy starcie
        self.load_settings(apply_to_fields=True)
        self._tick()  # pętla 1 Hz

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        title = ttk.Label(self.root, text="Leafcore", font=("Segoe UI", 18))
        title.pack(pady=10)

        frm = ttk.Frame(self.root)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="Temperatura:", width=20).grid(row=0, column=0, sticky="w")
        self.lbl_temp = ttk.Label(frm, text="–")
        self.lbl_temp.grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Wilgotność:", width=20).grid(row=1, column=0, sticky="w")
        self.lbl_hum = ttk.Label(frm, text="–")
        self.lbl_hum.grid(row=1, column=1, sticky="w")

        # Sterowanie ręczne
        frm_btn = ttk.Frame(self.root)
        frm_btn.pack(fill="x", **pad)

        self.btn_fan   = tk.Button(frm_btn, text="Wiatrak OFF", width=12,
                                   fg="white", bg="red", command=self.toggle_fan)
        self.btn_light = tk.Button(frm_btn, text="Światło OFF", width=12,
                                   fg="white", bg="red", command=self.toggle_light)
        self.btn_pump  = tk.Button(frm_btn, text="Pompka OFF", width=12,
                                   fg="white", bg="red", command=self.toggle_pump)

        self.btn_fan.grid(row=0, column=0, padx=4, pady=2)
        self.btn_light.grid(row=0, column=1, padx=4, pady=2)
        self.btn_pump.grid(row=0, column=2, padx=4, pady=2)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=8)

        # Ustawienia automatyczne
        frm_auto = ttk.Frame(self.root)
        frm_auto.pack(fill="x", **pad)

        chk = ttk.Checkbutton(frm_auto, text="Tryb automatyczny",
                              variable=self.auto_mode, command=self.on_auto_toggle)
        chk.grid(row=0, column=0, sticky="w", pady=(0,6))

        ttk.Label(frm_auto, text="Światło (godzin/24h):").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm_auto, textvariable=self.var_light_hours, width=8).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(frm_auto, text="Temperatura docelowa (°C):").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm_auto, textvariable=self.var_target_temp, width=8).grid(row=2, column=1, sticky="w", padx=6)

        ttk.Label(frm_auto, text="Wilgotność docelowa (%):").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm_auto, textvariable=self.var_target_hum, width=8).grid(row=3, column=1, sticky="w", padx=6)

        ttk.Label(frm_auto, text="Nawodnienie (razy/tydzień):").grid(row=4, column=0, sticky="w")
        ttk.Entry(frm_auto, textvariable=self.var_water_times, width=8).grid(row=4, column=1, sticky="w", padx=6)

        ttk.Label(frm_auto, text="Czas podlewania (sekundy):").grid(row=5, column=0, sticky="w")
        ttk.Entry(frm_auto, textvariable=self.var_water_secs, width=8).grid(row=5, column=1, sticky="w", padx=6)

        # Odśwież + ręczny zapis/odczyt
        frm_actions = ttk.Frame(self.root)
        frm_actions.pack(fill="x", **pad)
        ttk.Button(frm_actions, text="Odśwież dane", command=self.update_sensor_labels).grid(row=0, column=0, padx=4)
        ttk.Button(frm_actions, text="Zapisz ustawienia", command=self.save_settings_from_fields).grid(row=0, column=1, padx=4)
        ttk.Button(frm_actions, text="Wczytaj ustawienia", command=lambda: self.load_settings(apply_to_fields=True)).grid(row=0, column=2, padx=4)

        # Log
        frm_log = ttk.Frame(self.root)
        frm_log.pack(fill="both", expand=True, **pad)

        ttk.Label(frm_log, text="Log:").pack(anchor="w")
        self.txt_log = tk.Text(frm_log, height=8, state="disabled")
        self.txt_log.pack(fill="both", expand=True)

    # ---------- Log ----------
    def log(self, msg: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"{datetime.now().strftime('%H:%M:%S')}  {msg}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # ---------- Sensory ----------
    def update_sensor_labels(self):
        temp, hum = devices.read_sensor()
        self.lbl_temp.config(text=(f"{temp:.1f} °C" if temp is not None else "Brak odczytu"))
        self.lbl_hum.config(text=(f"{hum:.1f} %" if hum is not None else "Brak odczytu"))
        return temp, hum

    # ---------- Sterowanie wyjściami ----------
    def _set_button_visual(self, btn: tk.Button, is_on: bool, on_txt: str, off_txt: str):
        btn.configure(text=(on_txt if is_on else off_txt),
                      bg=("green" if is_on else "red"))

    def toggle_fan(self):
        self.fan_on = not self.fan_on
        devices.set_fan(self.fan_on)
        self._set_button_visual(self.btn_fan, self.fan_on, "Wiatrak ON", "Wiatrak OFF")

    def toggle_light(self):
        self.light_on = not self.light_on
        devices.set_light(self.light_on)
        self._set_button_visual(self.btn_light, self.light_on, "Światło ON", "Światło OFF")

    def toggle_pump(self):
        self.pump_on = not self.pump_on
        devices.set_pump(self.pump_on)
        self._set_button_visual(self.btn_pump, self.pump_on, "Pompka ON", "Pompka OFF")
        if self.pump_on:
            # auto-off po 2 s jako bezpiecznik
            if self._pump_off_job:
                self.root.after_cancel(self._pump_off_job)
            self._pump_off_job = self.root.after(2000, self._pump_off)

    def _pump_off(self):
        self.pump_on = False
        devices.set_pump(False)
        self._set_button_visual(self.btn_pump, False, "Pompka ON", "Pompka OFF")
        self._pump_off_job = None

    # ---------- JSON settings ----------
    def load_settings(self, apply_to_fields: bool = False) -> dict:
        cfg = DEFAULT_SETTINGS.copy()
        if SETTINGS_PATH.exists():
            try:
                with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg.update({k: data[k] for k in DEFAULT_SETTINGS.keys() if k in data})
                self.log(f"Wczytano ustawienia z {SETTINGS_PATH.name}")
            except Exception as e:
                self.log(f"Błąd wczytywania {SETTINGS_PATH.name}: {e}")
        else:
            self.log("Brak settings_config.json – używam domyślnych.")

        if apply_to_fields:
            self.var_light_hours.set(str(cfg["light_hours"]))
            self.var_target_temp.set(str(cfg["target_temp"]))
            self.var_target_hum.set(str(cfg["target_hum"]))
            self.var_water_times.set(str(cfg["water_times"]))
            self.var_water_secs.set(str(cfg["water_seconds"]))
        return cfg

    def save_settings(self, cfg: dict):
        try:
            with SETTINGS_PATH.open("w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self.log(f"Zapisano ustawienia do {SETTINGS_PATH.name}")
        except Exception as e:
            self.log(f"Błąd zapisu {SETTINGS_PATH.name}: {e}")

    def _collect_settings_from_fields(self) -> Optional[dict]:
        # walidacja
        light_hours = _parse_float(self.var_light_hours.get(), None)
        target_temp = _parse_float(self.var_target_temp.get(), None)
        target_hum  = _parse_float(self.var_target_hum.get(), None)
        water_times = _parse_int(self.var_water_times.get(), None)
        water_secs  = _parse_int(self.var_water_secs.get(), None)

        errors = []
        if light_hours is None or not (0 <= light_hours <= 24):
            errors.append("Światło (0–24 h)")
        if target_temp is None or not (0 <= target_temp <= 60):
            errors.append("Temperatura (0–60 °C)")
        if target_hum is None or not (0 <= target_hum <= 100):
            errors.append("Wilgotność (0–100 %)")
        if water_times is None or not (0 <= water_times <= 50):
            errors.append("Nawodnienie (0–50 razy/tydz.)")
        if water_secs is None or not (0 <= water_secs <= 3600):
            errors.append("Czas podlewania (0–3600 s)")

        if errors:
            messagebox.showerror("Błędne wartości",
                                 "Popraw pola: " + ", ".join(errors))
            return None

        return {
            "light_hours": float(light_hours),
            "target_temp": float(target_temp),
            "target_hum": float(target_hum),
            "water_times": int(water_times),
            "water_seconds": int(water_secs),
        }

    def save_settings_from_fields(self):
        cfg = self._collect_settings_from_fields()
        if cfg is None:
            return
        self.save_settings(cfg)

    # ---------- Reakcja na checkbox „Tryb automatyczny” ----------
    def on_auto_toggle(self):
        # ZAWSZE najpierw zapisz to, co jest teraz w polach (żeby mieć aktualny JSON)
        cfg_now = self._collect_settings_from_fields()
        if cfg_now:
            self.save_settings(cfg_now)

        if self.auto_mode.get():
            # Włączasz auto → wczytaj z JSON i od razu zastosuj do pól + log
            cfg = self.load_settings(apply_to_fields=True)
            self.log("Auto: zastosowano parametry z pliku settings_config.json")
        else:
            self.log("Auto: wyłączono tryb automatyczny")

    # ---------- Automat ----------
    def _auto_control(self, temp, hum):
        # Pobierz wartości bezpośrednio z pól (one są już zsynchronizowane z JSON po kliknięciu)
        target_light_hours = _parse_float(self.var_light_hours.get(), 0.0)
        target_hum = _parse_float(self.var_target_hum.get(), None)
        water_times = _parse_int(self.var_water_times.get(), 0)
        water_seconds = _parse_int(self.var_water_secs.get(), 0)

        # Światło wg godzin
        current_hour = datetime.now().hour
        self.light_on = (current_hour < float(target_light_hours))
        devices.set_light(self.light_on)
        self._set_button_visual(self.btn_light, self.light_on, "Światło ON", "Światło OFF")

        # Wilgotność → wiatrak
        if hum is not None and target_hum is not None:
            self.fan_on = hum > float(target_hum)
            devices.set_fan(self.fan_on)
            self._set_button_visual(self.btn_fan, self.fan_on, "Wiatrak ON", "Wiatrak OFF")

        # Podlewanie wg tygodniowych częstotliwości
        today = datetime.now().date()
        self.last_watering_days = [d for d in self.last_watering_days if (today - d).days <= 7]

        if water_times > 0 and water_seconds > 0:
            need_today = self._should_water_today(self.last_watering_days, water_times)
            already_today = (len(self.last_watering_days) > 0 and self.last_watering_days[-1] == today)
            if need_today and not already_today and not self.pump_on:
                self.log(f"Automatyczne podlewanie: {water_seconds} s")
                self.pump_on = True
                devices.set_pump(True)
                self._set_button_visual(self.btn_pump, True, "Pompka ON", "Pompka OFF")
                if self._pump_off_job:
                    self.root.after_cancel(self._pump_off_job)
                self._pump_off_job = self.root.after(water_seconds * 1000, self._finish_watering)

    def _finish_watering(self):
        devices.set_pump(False)
        self.pump_on = False
        self._set_button_visual(self.btn_pump, False, "Pompka ON", "Pompka OFF")
        self.last_watering_days.append(datetime.now().date())
        self._pump_off_job = None

    @staticmethod
    def _should_water_today(water_days: list[date], water_times_per_week: int) -> bool:
        if water_times_per_week <= 0:
            return False
        interval_days = 7 / water_times_per_week
        if not water_days:
            return True
        delta = (date.today() - water_days[-1]).days
        return delta >= interval_days

    # ---------- Pętla 1 Hz ----------
    def _tick(self):
        temp, hum = self.update_sensor_labels()
        if self.auto_mode.get():
            self._auto_control(temp, hum)
        self.root.after(1000, self._tick)

    def on_close(self):
        try:
            devices.cleanup()
        finally:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # ładniejszy wygląd przycisków ttka na Windowsie
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    style = ttk.Style()
    try:
        style.theme_use("vista")
    except Exception:
        pass

    app = GreenhouseApp(root)
    root.mainloop()
