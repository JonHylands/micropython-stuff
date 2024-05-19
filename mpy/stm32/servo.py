
from pyb import Timer


class Servo:
    def __init__(self, pin, timer_num, channel_num):
        self.pin = pin
        self.timer = Timer(timer_num)
        self.timer.init(prescaler=(int(self.timer.source_freq() / 1000000) - 1), period=19999)
        self.servo = self.timer.channel(channel_num, Timer.PWM, pin=self.pin)

    def position(self, position_us):
        self.servo.pulse_width(position_us)
