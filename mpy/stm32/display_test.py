
from display import Display
from pyb import Pin

import vga2_16x32 as font
from imu import BNO085_IMU

reset_pin = Pin(Pin.cpu.C7, Pin.OUT)
cs_pin = Pin(Pin.cpu.B12, Pin.OUT)
dc_pin = Pin(Pin.cpu.C6, Pin.OUT)

display = Display(2, reset_pin, cs_pin, dc_pin)
screen = display.screen

screen.init()
screen.fill(Display.BLUE)
screen.fill_rect(10, 10, 300, 152, Display.BLACK)

imu = BNO085_IMU(3)

s = 'IMU TEST'
screen.text(font, s, 95, 20, Display.WHITE, Display.BLACK)

old_yaw = 0

while True:
    if imu.ready():
        imu.update()
        yaw = imu.yaw
        if yaw != old_yaw:
            s = 'HEADING: {:.2f}'.format(yaw)
            screen.fill_rect(160, 80, 150, 40, Display.BLACK)
            screen.text(font, s, 30, 92, Display.YELLOW, Display.BLACK)
            old_yaw = yaw

