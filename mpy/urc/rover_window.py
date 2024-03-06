from display import Display
from util import *
from window import *
import NotoSans_15 as font_15
import NotoSans_20 as font_20
import NotoSans_25 as font_25
import NotoSans_32 as font_32
from machine import Pin, Timer
import time
import gc


TRIGGER_PIN = 15
TRIGGER_CONNECTED_PIN = 16


class RoverWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_root_window()

    def build_root_window(self):
        self.root_window = Window(self.display, "Rover")

        box = Rectangle(Point(0, 0), Point(240, 240))
        main_view = View("Top", box.origin, box.extent)
        self.root_window.add_view(main_view)

        image = VisualJpgImage(box, 'CabraRobot-240.jpg')
        main_view.add_component(image)

        button = VisualButton(Rectangle(Point(0, 78), Point(160, 80)), '', font_15, Color.CYAN, False)
        main_view.add_component(button)
        button.register_click_handler(self.open_rover_window)

    def open_rover_window(self):
        RoverChooseWindow(self.window_manager, self.display)


class RoverChooseWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_rover_choose_window()
        self.window_manager.push_window(self.choose_window)

    def build_rover_choose_window(self):
        self.choose_window = Window(self.display, 'Rover Choose')

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 124))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        self.choose_window.add_view(top_view)
        self.choose_window.add_view(middle_view)
        self.choose_window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.YELLOW)
        top_view.add_component(label)

        button_y = 20
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "MISSION", font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_mission)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "SENSORS", font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_sensors)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "MOTORS", font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_motors)

    def clicked_mission(self):
        print('Rover Missions')
        RoverMissionWindow(self.window_manager, self.display)

    def clicked_sensors(self):
        print('Rover Sensors')
        RoverSensorWindow(self.window_manager, self.display)

    def clicked_motors(self):
        print('Rover Motors')
        RoverMotorWindow(self.window_manager, self.display)


class RoverMissionWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_main_window()
        self.paused = True
        self.running_mission = False
        self.cone_sets = []

    def build_main_window(self):
        mission_names = ['Magellan', 'Waypoint', 'Wander']
        windows = []
        for name in mission_names:
            windows.append(self.build_window_for_mission(name))
        chain = WindowChain('Mission Chooser', windows)
        self.window_manager.push_window_chain(chain)

    def build_window_for_mission(self, mission_name):
        window = Window(self.display, 'Mission: {}'.format(mission_name))

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 120))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        window.add_view(top_view)
        window.add_view(middle_view)
        window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.YELLOW)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), 'Mission: {}'.format(mission_name), font_20, True, Color.CYAN)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "RUN", font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_run_mission, mission_name)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "CONFIGURE", font_25, Color.YELLOW)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_edit_mission, mission_name)

        return window

    def build_rover_mission_run_window(self, mission_name):
        self.run_window = Window(self.display, "{} Run".format(mission_name))

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 124))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        self.run_window.add_view(top_view)
        self.run_window.add_view(middle_view)
        self.run_window.add_view(bottom_view)

        self.running_label = VisualLabel(Rectangle(Point(55, 20), Point(75, 20)), 'PAUSED', font_15, False, Color.RED, Color.BLACK)
        top_view.add_component(self.running_label)

        self.timer_label = VisualLabel(Rectangle(Point(135, 20), Point(50, 20)), '00:00', font_15, False, Color.YELLOW, Color.BLACK)
        top_view.add_component(self.timer_label)

        self.gps_label = VisualLabel(Rectangle(Point(0, 40), Point(160, 20)), 'GPS sat: 7 fix: DGPS', font_15, True, Color.YELLOW, Color.BLACK)
        top_view.add_component(self.gps_label)

        self.nav_label = VisualLabel(Rectangle(Point(0, 10), Point(160, 20)), 'NAV: Waypoint', font_15, True, Color.CYAN, Color.BLACK)
        middle_view.add_component(self.nav_label)

        self.state_label = VisualLabel(Rectangle(Point(0, 30), Point(160, 20)), 'FSM: Start', font_15, True, Color.CYAN, Color.BLACK)
        middle_view.add_component(self.state_label)

        self.target_label = VisualLabel(Rectangle(Point(0, 50), Point(160, 20)), 'Target: 10 @ 120 (BC#1)', font_15, True, Color.CYAN, Color.BLACK)
        middle_view.add_component(self.target_label)

        self.position_label = VisualLabel(Rectangle(Point(0, 80), Point(160, 20)), 'Position: 0 @ 0', font_15, True, Color.WHITE, Color.BLACK)
        middle_view.add_component(self.position_label)

        self.heading_label = VisualLabel(Rectangle(Point(0, 100), Point(160, 20)), 'Heading: 325', font_15, True, Color.WHITE, Color.BLACK)
        middle_view.add_component(self.heading_label)

        self.voltage_label = VisualLabel(Rectangle(Point(0, 10), Point(240, 20)), 'Robot: 12.3 volts', font_15, True, Color.GREEN, Color.BLACK)
        bottom_view.add_component(self.voltage_label)

        self.run_window.register_about_to_close(self.about_to_close_run_mission)
        return self.run_window

    def update_trigger(self):
        if self.trigger_connected_pin.value() == 1:
            self.mission.set_has_failsafe(False)
            self.paused = None
        else:
            self.mission.set_has_failsafe(True)
            self.mission.set_paused(self.trigger_pin.value() == 1)

    def update_window(self):
        if not self.mission.paused:
            self.mission.increment_run_time_tenths()
        pair = self.mission.running_string_and_color()
        self.running_label.set_text(pair[0])
        self.running_label.set_color(pair[1])
        self.timer_label.set_text(self.mission.run_time_string())
        self.gps_label.set_text(self.mission.gps_string())
        self.nav_label.set_text(self.mission.navigator_string())
        self.state_label.set_text(self.mission.current_state_string())
        self.target_label.set_text(self.mission.target_string())
        self.position_label.set_text(self.mission.position_string())
        self.heading_label.set_text(self.mission.heading_string())
        self.voltage_label.set_text(self.mission.voltage_string())

    def update(self, timer):
        self.update_trigger()
        self.update_window()

    def about_to_close_run_mission(self, window):
        print('Finished Mission: {}'.format(window.name))
        self.window_manager.enable_screensaver()
        self.update_timer.deinit()
        self.running_mission = False

    def clicked_run_mission(self, mission_name):
        print('Run Mission: {}'.format(mission_name))
        self.window_manager.disable_screensaver()
        self.mission = RoverMission()
        self.window_manager.push_window(self.build_rover_mission_run_window(mission_name))
        self.trigger_pin = Pin(TRIGGER_PIN, Pin.IN, Pin.PULL_UP)
        self.trigger_connected_pin = Pin(TRIGGER_CONNECTED_PIN, Pin.IN, Pin.PULL_UP)
        self.update_timer = Timer(1, mode=Timer.PERIODIC, freq=10, callback=self.update)
        self.running_mission = True

    def clicked_edit_mission(self, mission_name):
        print('Edit Mission: {}'.format(mission_name))
        RoverEditMissionWindow(self.window_manager, self.display)


class RoverEditMissionWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_rover_choose_window()
        self.window_manager.push_window(self.choose_window)

    def build_rover_choose_window(self):
        self.choose_window = Window(self.display, 'Rover Edit Mission')

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 124))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        self.choose_window.add_view(top_view)
        self.choose_window.add_view(middle_view)
        self.choose_window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.YELLOW)
        top_view.add_component(label)

        button = VisualButton(Rectangle(Point(0, 20), Point(160, 35)), "CONE SETS", font_25, Color.GREEN)
        middle_view.add_component(button)
        # button.register_click_handler(self.clicked_edit_cone_sets)

        label = VisualLabel(Point(0, 70), 'Max Speed:', font_20, False, Color.CYAN)
        middle_view.add_component(label)

        tens_box = Rectangle(Point(120, 68), Point(20, 24))
        items = [str(x) for x in range(0, 10)]
        tens_roller = VisualRollerList(tens_box, items, font_20, Color.CYAN)
        middle_view.add_component(tens_roller)
        ones_box = tens_box.offset_by(Point(25, 0))
        ones_roller = VisualRollerList(ones_box, items, font_20, Color.CYAN)
        middle_view.add_component(ones_roller)
        ones_roller.register_click_handler(self.clicked_ones_roller)
        tens_roller.register_click_handler(self.clicked_tens_roller)


    def clicked_tens_roller(self, item):
        print('Chose {} as tens digit'.format(item))

    def clicked_ones_roller(self, item):
        print('Chose {} as ones digit'.format(item))


class RoverEditConeSetWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_main_window()

    def build_main_window(self):
        cone_sets = [
            RoverConeSet('Start', 'BC#1'),
            RoverConeSet('Start', 'BC#2'),
            RoverConeSet('Start', 'Finish'),
            RoverConeSet('BC#1', 'BC#2'),
            RoverConeSet('BC#2', 'BC#1'),
            RoverConeSet('BC#1', 'Finish'),
            RoverConeSet('BC#2', 'Finish')
        ]
        windows = []
        for cone_set in cone_sets:
            windows.append(self.build_window_for_cone_set(cone_set))
        chain = WindowChain('Cone Set Chooser', windows)
        self.window_manager.push_window_chain(chain)

    def build_window_for_cone_set(self, cone_set):
        window = Window(self.display, 'Cone Set: {}'.format(cone_set))

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 120))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        window.add_view(top_view)
        window.add_view(middle_view)
        window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.YELLOW)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), cone_set.name(), font_20, True, Color.CYAN)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "INCLUDE", font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_include, cone_set)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "EXCLUDE", font_25, Color.YELLOW)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_exclude, cone_set)

        return window


class RoverConeSet:
    def __init__(self, start_cone, finish_cone):
        self.start_cone = start_cone
        self.finish_cone = finish_cone

    def name(self):
        return '{} -> {}'.format(self.start_cone, self.finish_cone)


class RoverMission:
    def __init__(self):
        self.has_failsafe = False
        self.paused = True
        self.run_time = 0
        self.run_time_tenths = 0
        self.gps_satellite_count = 0
        self.gps_satellite_fix = 0
        self.navigator = 'None'
        self.current_state = 'None'
        self.target_position = Point(0.0, 0.0)
        self.target_name = 'None'
        self.position = Point(0.0, 0.0)
        self.heading = 0
        self.voltage = 0.0

    # Call this at 10Hz
    def increment_run_time_tenths(self):
        self.run_time_tenths += 1
        if self.run_time_tenths == 10:
            self.run_time_tenths = 0
            self.run_time += 1

    def set_has_failsafe(self, flag):
        self.has_failsafe = flag

    def set_paused(self, flag):
        self.paused = flag

    def run_time_string(self):
        seconds = self.run_time % 60
        minutes = self.run_time // 60
        return '{:02d}:{:02d}'.format(minutes, seconds)

    def running_string_and_color(self):
        if self.has_failsafe:
            if self.paused:
                return ('PAUSED', Color.RED)
            else:
                return ('RUNNING', Color.GREEN)
        else:
            return ('N/C', Color.RED)

    # This is specific to the Adafruit Ultimate GPS
    def gps_fix_quality(self):
        return ['None', 'GPS', 'DGPS'][self.gps_satellite_fix]

    def gps_string(self):
        return 'GPS sat: {} fix: {}'.format(self.gps_satellite_count, self.gps_fix_quality())

    def target_string(self):
        return 'Target: {:.1f} @ {:.1f} ({})'.format(self.target_position.x, self.target_position.y, self.target_name)

    def position_string(self):
        return 'Position: {:.1f} @ {:.1f}'.format(self.position.x, self.position.y)

    def current_state_string(self):
        return 'FSM: {}'.format(self.current_state)

    def navigator_string(self):
        return 'NAV: {}'.format(self.navigator)

    def heading_string(self):
        return 'Heading: {}'.format(self.heading)

    def voltage_string(self):
        return 'Robot: {:.1f} volts'.format(self.voltage)


class RoverSensorWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.window = Window(self.display, "Sensors")

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 124))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        self.window.add_view(top_view)
        self.window.add_view(middle_view)
        self.window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), "Sensors", font_32, True, Color.YELLOW)
        top_view.add_component(label)

        box = Rectangle(Point(0, 0), Point(160, 124))
        items = ['Obstacle', 'Laser', 'IMU', 'GPS']
        self.vlist = VisualList(box, items, font_25, Color.CYAN)
        middle_view.add_component(self.vlist)
        self.vlist.register_click_handler(self.list_click)

        text_height = font_25.HEIGHT
        width = self.display.text_width("CHOOSE", font_25) + 10
        x = self.display.SCREEN_WIDTH // 2 - (width // 2)
        button = VisualButton(Rectangle(Point(x, 5), Point(width, text_height + 4)), "CHOOSE", font_25, Color.GREEN)
        bottom_view.add_component(button)
        button.register_click_handler(self.button_click)
        self.window_manager.push_window(self.window)

    def button_click(self):
        print('CHOOSE button clicked on Sensor Window')

    def list_click(self, item):
        print('Chose {} from Sensor list'.format(item))


class RoverMotorWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_main_window()

    def build_main_window(self):
        names = ['Main', 'Steering', 'R/C']
        windows = []
        for name in names:
            windows.append(self.build_window_for_motor(name))
        chain = WindowChain('Motor Chooser', windows)
        self.window_manager.push_window_chain(chain)

    def build_window_for_motor(self, motor_name):
        window = Window(self.display, 'Motor: {}'.format(motor_name))

        top_view = View("Top", Point(0, 0), Point(240, 58))
        middle_view = View("Middle", Point(40,58), Point(160, 120))
        bottom_view = View("Bottom", Point(0, 182), Point(240, 58))

        window.add_view(top_view)
        window.add_view(middle_view)
        window.add_view(bottom_view)

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.YELLOW)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), 'Motor: {}'.format(motor_name), font_25, True, Color.CYAN)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), 'TEST', font_25, Color.GREEN)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_test_motor, motor_name)

        return window

    def clicked_test_motor(self, motor_name):
        if motor_name == 'Main':
            self.test_main_motor()
        elif motor_name == 'Steering':
            self.test_steering()
        elif motor_name == 'R/C':
            self.test_rc_mode()
        else:
            print('Unknown motor type: {}'.format(motor_name))

    def test_main_motor(self):
        print('Test Main Motor')

    def test_steering(self):
        print('Test Steering')

    def test_rc_mode(self):
        print('Test R/C Mode')
