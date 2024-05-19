
from servo import Servo
from pyb import Pin
import time


servo_pin = Pin(Pin.cpu.A6, Pin.OUT)
servo_timer = 3
servo_channel = 1

#pot_pin = Pin(Pin.cpu.A4)
#pot = ADC(pot_pin)

servo = Servo(servo_pin, servo_timer, servo_channel)

amount = 3
offset = 400
delta = amount

print("Servo Test")

while True:
    position = 1100 + offset
    servo.position(position)
    offset += delta
    if offset >= 800:
        delta = -amount
    if offset <= 0:
        delta = amount
    time.sleep_ms(10)
