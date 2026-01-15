import OPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)
PIN=13
GPIO.setup(PIN, GPIO.OUT)
print("on")

while True:
    try:
        print("ok")
    except KeyboardInterrupt:
        break

    GPIO.output(PIN, GPIO.LOW)
    GPIO.cleanup()