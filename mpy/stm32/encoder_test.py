

from encoder import Encoder
from pyb import Pin
import time

a_pin = Pin(Pin.cpu.A0, Pin.IN)
b_pin = Pin(Pin.cpu.A1, Pin.IN)

encoder = Encoder(a_pin, b_pin)

while True:
    print('Encoder: {}'.format(encoder.value()))
    time.sleep_ms(100)
