FAN_PIN = 271
PUMP_PIN = 268
SPRINKLER_PIN = 258
HEATING_MAT_PIN = 272
LIGHT_PIN = 269

SCL_PIN = 263
SDA_PIN = 264

CHIP_PATH = "/dev/gpiochip0"

COMPONENT_MAP = {
    "fan": FAN_PIN,
    "pump": PUMP_PIN,
    "sprinkler": SPRINKLER_PIN,
    "heat_mat": HEATING_MAT_PIN,
    "light": LIGHT_PIN
}