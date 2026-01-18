import argparse
import gpiod
from gpiod.line import Direction, Value
import config

parser = argparse.ArgumentParser()
parser.add_argument(
    "--component",
    type=str,
    required=True,
    help="The component name (e.g., fan, pump, light)"
)
parser.add_argument(
    "--action",
    type=str,
    choices=["on", "off"],
    required=True,
    help="Action to perform: 'on' or 'off'"
)

args = parser.parse_args()

if args.component not in config.COMPONENT_MAP:
    print(f"Error: '{args.component}' is not a valid component.")
    print(f"Available components: {list(config.COMPONENT_MAP.keys())}")
target_value = Value.ACTIVE if args.action == "on" else Value.INACTIVE

print(f"Setting {args.component} (Pin {PIN_NUMBER}) to {args.action.upper()}...")

try:
    with gpiod.request_lines(
        path=config.CHIP_PATH,
        consumer="device_control",
        config={
            PIN_NUMBER: gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=target_value
            )
        },
    ) as request:
        print("Done.")

except OSError as e:
    print(f"Failed to access GPIO chip: {e}")
except KeyboardInterrupt:
    print("\nStopped.")