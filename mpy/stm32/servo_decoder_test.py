

from pyb import Pin
from servo_decoder import ServoDecoder
import time
import micropython


micropython.alloc_emergency_exception_buf(100)

steering_pin = Pin(Pin.cpu.A2)
motor_pin = Pin(Pin.cpu.A3)

steering_decoder = ServoDecoder(steering_pin, 2, 3)
motor_decoder = ServoDecoder(motor_pin, 2, 4)

while True:
    print('Steering: {} Motor: {}'.format(steering_decoder.pulse_width, motor_decoder.pulse_width))
    time.sleep_ms(100)
