import gpiod
import time

# The offset for PI16 is 16 (Because 272 - 256 = 16)
TARGET_OFFSET = 16
PIN_NAME = "PI16 (Pin 37)"

print(f"🕵️‍♂️ HUNTING for {PIN_NAME} at Offset {TARGET_OFFSET}...")
print("Please watch your device connected to Pin 37.\n")

found_working = False

# Try Chips 0 through 4
for chip_num in range(5):
    chip_name = f"gpiochip{chip_num}"
    
    try:
        chip = gpiod.Chip(chip_name)
        # Check if this chip even HAS a line 16
        if chip.num_lines() <= TARGET_OFFSET:
            print(f"⏭️  Skipping {chip_name} (Only has {chip.num_lines()} lines)")
            chip.close()
            continue

        line = chip.get_line(TARGET_OFFSET)
        
        # Check if busy
        try:
            line.request(consumer="test", type=gpiod.LINE_REQ_DIR_OUT)
        except OSError:
            print(f"⚠️  {chip_name} Line {TARGET_OFFSET} is BUSY (Might be the one, but locked!)")
            chip.close()
            continue

        print(f"⚡ Testing {chip_name}, Line {TARGET_OFFSET}...")
        print("   -> BLINKING NOW! (Check device)")
        
        # Blink 3 times
        for _ in range(3):
            line.set_value(1)
            time.sleep(0.5)
            line.set_value(0)
            time.sleep(0.5)

        line.release()
        chip.close()
        
        # Ask user confirmation
        answer = input(f"❓ Did it blink on {chip_name}? (y/n): ").strip().lower()
        if answer == 'y':
            print(f"\n✅ SUCCESS! Update your code:")
            print(f"   self.chip = gpiod.Chip('{chip_name}', ...)")
            print(f"   PUMP_PIN = {TARGET_OFFSET}")
            found_working = True
            break
        else:
            print("   -> Moving to next chip...\n")

    except Exception as e:
        print(f"❌ Error accessing {chip_name}: {e}")

if not found_working:
    print("❌ Test ended. If nothing blinked, check your wiring or power.")
