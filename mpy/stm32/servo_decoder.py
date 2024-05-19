
from pyb import Pin, Timer


# Requires Timer2

class ServoDecoder:

    def __init__(self, servo_pin, timer_number, channel_number):
        self.timer = Timer(timer_number, prescaler=83, period=0x0fffffff)
        self.ic_pin = servo_pin
        self.ic_pin.init(Pin.AF_PP, pull=Pin.PULL_NONE, alt=Pin.AF1_TIM2)
        self.ic = self.timer.channel(channel_number, Timer.IC, pin=self.ic_pin, polarity=Timer.BOTH)
        self.ic_start = 0
        self.pulse_width = 0
        self.ic.callback(self.ic_cb)


    def ic_cb(self, tim):
        # Read the GPIO pin to figure out if this was a rising or falling edge
        if self.ic_pin.value():
            # Rising edge - start of the pulse
            self.ic_start = self.ic.capture()
        else:
            # Falling edge - end of the pulse
            self.pulse_width = self.ic.capture() - self.ic_start & 0x0fffffff

