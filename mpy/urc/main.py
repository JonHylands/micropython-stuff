
from window import *
from util import *
from display import Display
from rover_window import RoverWindow
from roz_window import RozWindow
from ttrobot_window import TTRobotWindow
from admin_window import AdminWindow
import time


class Failsafe:
    def __init__(self):
        print('Rover Failsafe Handheld')
        self.display = Display()
        print('Display initialized')

        self.display.jpg('CabraRobot-240.jpg', 0, 0)
        print('JPG Displayed')
        time.sleep_ms(1000)
        self.display.screen.fill(Color.BACKGROUND.as565())
        print('Screen cleared')

        self.window_manager = WindowManager(self.display)
        print('Window Manager initialized')

        self.rover = RoverWindow(self.window_manager, self.display)
        self.roz = RozWindow(self.window_manager, self.display)
        self.ttrobot = TTRobotWindow(self.window_manager, self.display)
        self.robot_chain = WindowChain('Robots', [self.rover.root_window, self.roz.root_window, self.ttrobot.root_window])
        self.admin = AdminWindow(self.window_manager, self.display, self.robot_chain)
        self.admin.register_theme_callback(self.switched_theme)
        self.admin_chain = WindowChain('Admin', [self.admin.window, self.admin.theme_window])
        self.window_manager.push_window_chain(self.admin_chain)

    def shutdown(self):
        self.window_manager.shutdown()

    def switched_theme(self):
        self.window_manager.pop_window()
        self.admin = AdminWindow(self.window_manager, self.display, self.robot_chain)
        self.admin.register_theme_callback(self.switched_theme)
        self.admin_chain = WindowChain('Admin', [self.admin.theme_window, self.admin.window])
        self.window_manager.push_window_chain(self.admin_chain)


#=================================================


theme = Theme.read_from_file('modern_dark')
theme.apply()

failsafe = Failsafe()

try:
    while True:
        time.sleep_ms(1000)
except KeyboardInterrupt:
    failsafe.shutdown()
