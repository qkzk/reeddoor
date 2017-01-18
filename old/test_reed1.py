import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
n=0
while True:
    input_state = GPIO.input(18)
    if input_state == False:
        print('Button Pressed'+n)
        n=n+1
        time.sleep(0.2)