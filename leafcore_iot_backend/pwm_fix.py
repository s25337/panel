import os
import time

# --- CONSTANTS ---
PWM_FREQUENCY = 100
PWM_PERIOD_NS = int(1_000_000_000 / PWM_FREQUENCY) 

# Your Master Chip
CHIP_PATH = "/sys/class/pwm/pwmchip0"

# Your Specific Pin (PWM3 corresponds to Channel 3)
CHANNEL_ID = "3"
CHANNEL_PATH = f"{CHIP_PATH}/pwm{CHANNEL_ID}"

def setup_pwm():
    # 1. Export Channel 3
    if not os.path.exists(CHANNEL_PATH):
        print(f"Exporting Channel {CHANNEL_ID}...")
        try:
            with open(f"{CHIP_PATH}/export", "w") as f:
                f.write(CHANNEL_ID) 
        except OSError:
            print("Warning: Channel already exported or busy.")

    # Wait for OS to create the folder
    time.sleep(0.5)

    # 2. Set Frequency (Period)
    print(f"Setting Period to {PWM_PERIOD_NS}...")
    try:
        with open(f"{CHANNEL_PATH}/period", "w") as f:
            f.write(str(PWM_PERIOD_NS))
    except OSError as e:
        print(f"❌ Error setting period: {e}")
        return

    # 3. Enable
    print("Enabling...")
    try:
        with open(f"{CHANNEL_PATH}/enable", "w") as f:
            f.write("1")
    except OSError as e:
        print(f"❌ Error enabling: {e}")
        return
    
    print("✅ PWM3 Setup Complete!")

def set_brightness(intensity):
    intensity = max(0.0, min(intensity, 1.0))
    duty_ns = int(PWM_PERIOD_NS * intensity)
    
    try:
        with open(f"{CHANNEL_PATH}/duty_cycle", "w") as f:
            f.write(str(duty_ns))
    except OSError:
        pass

if __name__ == "__main__":
    setup_pwm()
    print("Turning light to 100%...")
    set_brightness(1.0)
    
    # Optional: Fade test
    # for i in range(10, -1, -1):
    #     set_brightness(i / 10.0)
    #     time.sleep(0.5)
