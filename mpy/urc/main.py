
from window import *
from util import *
from display import Display
from rover_window import RoverWindow
from roz_window import RozWindow
from ttrobot_window import TTRobotWindow
from admin_window import AdminWindow
from machine import Pin
import NotoSans_15 as font_15
import NotoSans_20 as font_20
import NotoSans_25 as font_25
import NotoSans_32 as font_32
import radiostars_32 as rfont_32
import time
import gc



def free(full=False):
    gc.collect()
    F = gc.mem_free()
    A = gc.mem_alloc()
    T = F+A
    P = '{0:.2f}%'.format(F/T*100)
    if not full:
        return P
    else :
        return ('Total:{0} Free:{1} ({2})'.format(T,F,P))


class Failsafe:
    def __init__(self):
        print('Cabra Failsafe Handheld')
        self.display = Display()
        print('Display initialized')

        self.display.jpg('CabraRobot-240.jpg', 0, 0)
        print('JPG Displayed')
        time.sleep_ms(1000)
        self.display.screen.fill(Color.BLACK)
        print('Screen cleared')

        self.window_manager = WindowManager(self.display)
        print('Window Manager initialized')

        self.rover = RoverWindow(self.window_manager, self.display)
        self.roz = RozWindow(self.window_manager, self.display)
        self.ttrobot = TTRobotWindow(self.window_manager, self.display)
        chain = WindowChain('Robots', [self.rover.root_window, self.roz.root_window, self.ttrobot.root_window])
        self.admin = AdminWindow(self.window_manager, self.display, chain)
        self.window_manager.push_window_chain(WindowChain('Admin', [self.admin.window]))

    def shutdown(self):
        self.window_manager.deregister_touch_handler()


#=================================================



failsafe = Failsafe()

try:
    while True:
        time.sleep_ms(1000)
except KeyboardInterrupt:
    failsafe.shutdown()
