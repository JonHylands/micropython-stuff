from util import *
from window import *
from telemetry import Telemetry
import NotoSans_15 as font_15
import NotoSans_20 as font_20
import NotoSans_25 as font_25
import NotoSans_32 as font_32
from machine import Pin, Timer, ADC
from example_secret import *


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

        button = VisualButton(Rectangle(Point(0, 78), Point(160, 80)), '', font_15, Color.LABEL, False)
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

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.TITLE)
        top_view.add_component(label)

        button_y = 20
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "MISSION", font_25, Color.BUTTON)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_mission)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "SENSORS", font_25, Color.BUTTON)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_sensors)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "MOTORS", font_25, Color.BUTTON)
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

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.TITLE)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), 'Mission: {}'.format(mission_name), font_20, True, Color.LABEL)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "RUN", font_25, Color.BUTTON)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_run_mission, mission_name)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "CONFIGURE", font_25, Color.BUTTON)
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

        self.running_label = VisualLabel(Rectangle(Point(55, 20), Point(75, 20)), 'PAUSED', font_15, False, Color.ALERT_LABEL, Color.BACKGROUND)
        top_view.add_component(self.running_label)

        self.timer_label = VisualLabel(Rectangle(Point(135, 20), Point(50, 20)), '00:00', font_15, False, Color.LABEL, Color.BACKGROUND)
        top_view.add_component(self.timer_label)

        self.gps_label = VisualLabel(Rectangle(Point(0, 40), Point(160, 20)), 'GPS sat: 7 fix: DGPS', font_15, True, Color.LABEL, Color.BACKGROUND)
        top_view.add_component(self.gps_label)

        self.nav_label = VisualLabel(Rectangle(Point(0, 10), Point(160, 20)), 'NAV: Waypoint', font_15, True, Color.LABEL, Color.BACKGROUND)
        middle_view.add_component(self.nav_label)

        self.state_label = VisualLabel(Rectangle(Point(0, 30), Point(160, 20)), 'FSM: Start', font_15, True, Color.LABEL, Color.BACKGROUND)
        middle_view.add_component(self.state_label)

        self.target_label = VisualLabel(Rectangle(Point(0, 60), Point(160, 20)), '(BC#1): 27.3m, 322', font_15, True, Color.LABEL, Color.BACKGROUND)
        middle_view.add_component(self.target_label)

        self.position_label = VisualLabel(Rectangle(Point(0, 80), Point(160, 20)), 'Position: 0 @ 0', font_15, True, Color.LABEL, Color.BACKGROUND)
        middle_view.add_component(self.position_label)

        self.heading_label = VisualLabel(Rectangle(Point(0, 100), Point(160, 20)), 'Heading: 325', font_15, True, Color.LABEL, Color.BACKGROUND)
        middle_view.add_component(self.heading_label)

        self.robot_voltage_label = VisualLabel(Rectangle(Point(37, 10), Point(90, 20)), 'Robot 12.3v', font_15, False, Color.GOOD_LABEL, Color.BACKGROUND)
        bottom_view.add_component(self.robot_voltage_label)

        self.urc_voltage_label = VisualLabel(Rectangle(Point(127, 10), Point(90, 20)), 'URC 4.15v', font_15, False, Color.GOOD_LABEL, Color.BACKGROUND)
        bottom_view.add_component(self.urc_voltage_label)

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
        self.robot_voltage_label.set_text(self.mission.robot_voltage_string())
        self.robot_voltage_label.set_color(self.voltage_color(self.mission.robot_voltage, 3))
        self.urc_voltage_label.set_text(self.mission.urc_voltage_string())
        self.urc_voltage_label.set_color(self.voltage_color(self.mission.urc_voltage, 1))

    def update(self, timer):
        self.update_trigger()
        self.mission.update()
        self.update_window()

    def voltage_color(self, voltage, cell_count):
        cell_voltage = voltage / cell_count
        if cell_voltage < 3.4:
            return Color.ALERT_LABEL
        if cell_voltage < 3.7:
            return Color.WARNING_LABEL
        return Color.GOOD_LABEL

    def get_telemetry_packet(self, packet):
        self.mission.process_telemetry_packet(packet)

    def about_to_close_run_mission(self, window):
        print('Finished Mission: {}'.format(window.name))
        self.window_manager.enable_screensaver()
        self.update_timer.deinit()
        self.telemetry.shutdown()
        self.running_mission = False

    def clicked_run_mission(self, mission_name):
        print('Run Mission: {}'.format(mission_name))
        self.window_manager.disable_screensaver()
        self.mission = RoverMission()
        self.window_manager.push_window(self.build_rover_mission_run_window(mission_name))
        self.trigger_pin = Pin(TRIGGER_PIN, Pin.IN, Pin.PULL_UP)
        self.trigger_connected_pin = Pin(TRIGGER_CONNECTED_PIN, Pin.IN, Pin.PULL_UP)
        self.update_timer = Timer(1, mode=Timer.PERIODIC, freq=10, callback=self.update)
        self.telemetry = Telemetry(ROVER_MAC_ADDRESS)
        self.telemetry.register_telemetry_callback(self.get_telemetry_packet)
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

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.TITLE)
        top_view.add_component(label)

        button = VisualButton(Rectangle(Point(0, 20), Point(160, 35)), "CONE SETS", font_25, Color.BUTTON)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_edit_cone_sets)

        label = VisualLabel(Point(0, 70), 'Max Speed:', font_20, False, Color.LABEL)
        middle_view.add_component(label)

        tens_box = Rectangle(Point(120, 68), Point(20, 24))
        items = [str(x) for x in range(0, 10)]
        tens_roller = VisualRollerList(tens_box, items, font_20, Color.LIST)
        middle_view.add_component(tens_roller)
        ones_box = tens_box.offset_by(Point(25, 0))
        ones_roller = VisualRollerList(ones_box, items, font_20, Color.LIST)
        middle_view.add_component(ones_roller)
        ones_roller.register_click_handler(self.clicked_ones_roller)
        tens_roller.register_click_handler(self.clicked_tens_roller)


    def clicked_tens_roller(self, item):
        print('Chose {} as tens digit'.format(item))

    def clicked_ones_roller(self, item):
        print('Chose {} as ones digit'.format(item))

    def clicked_edit_cone_sets(self):
        RoverTestCanvasWindow(self.window_manager, self.display)


class RoverTestCanvasWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_main_window()
        self.read_gps_locations()
        self.window_manager.push_window(self.canvas_window)

    def build_main_window(self):
        self.canvas_window = Window(self.display, 'Canvas')
        box = Rectangle(Point(0, 0), Point(240, 210))
        main_view = View("Main", box.origin, box.extent)
        self.canvas_window.add_view(main_view)

        self.canvas = VisualCanvas(box, self.draw_canvas)
        self.canvas.register_click_handler(self.click_canvas)
        main_view.add_component(self.canvas)

    def read_gps_locations(self):
        file = io.open('gps-01.json', mode='r')
        map = json.load(file)
        file.close()
        self.cone_names = map['coneNames']
        self.gps_coordinates = []
        for lat, long in map['gpsCoordinates']:
            self.gps_coordinates.append(GpsCoordinate(lat, long))
        self.compute_local_coordinates()

    def compute_local_coordinates(self):
        results = []
        results.append(Point(0, 0))
        # First, calculate local coordinates in world space (meters) for each gps coordinate
        # bearing_to and distance_to are relative to the source location, so we keep adding
        # the new delta to the last point to get the new point
        for index in range(0, len(self.gps_coordinates) - 1):
            first = self.gps_coordinates[index]
            second = self.gps_coordinates[index + 1]
            distance = first.distance_to(second)
            bearing = first.bearing_to(second)
            new_location = Point.r_degrees(distance, bearing + 90) + results[-1]
            results.append(new_location)
        # Find a rectangle that ecompasses all the points
        box = Rectangle.encompassing(results)
        e = max(box.width(), box.height())
        # Figure out the scale factor needed to put all the points into a 160 x 160 box
        self.scale_factor = 160.0 / e
        # Turn the rectangle into a square
        box = Rectangle.center_extent(box.center(), Point(e, e))
        # Scale the square, so it is now in screen coordinates instead of world coordinates
        box = box.scale_by(self.scale_factor)
        # Take each world point, scale it and offset it to screen coordinates
        points = [Point(each.x * self.scale_factor, each.y * self.scale_factor) - box.origin for each in results]
        # Flip the y-value since the screen is positive down
        points = [Point(int(each.x), int(160 - each.y)) for each in points]
        # Offset the points so they are centered on the screen, still inside the 160 x 160 box
        inner_box = Rectangle(Point(0, 0), Point(160, 160)).center_in(Rectangle(Point(0, 0), Point(240, 240)))
        self.local_coordinates = [each + inner_box.origin for each in points]

    def draw_canvas(self, display, display_box):
        self.display.clear_screen()
        self.draw_grid(display, display_box)
        last_point = None
        for point in self.local_coordinates:
            if last_point is not None:
                self.display.screen.line(last_point.x, last_point.y, point.x, point.y, Color.WARNING_LABEL.as565())
            last_point = point
        for name, point in zip(self.cone_names, self.local_coordinates):
            self.display.screen.fill_circle(point.x, point.y, 12, Color.LABEL.as565())
            width = self.display.text_width(name, font_20) // 2
            self.display.screen.write(font_20, name, point.x - width, point.y - (font_20.HEIGHT // 2) + 2, 
                                      Color.BACKGROUND.as565(), Color.LABEL.as565())

    def draw_grid(self, display, display_box):
        origin = self.local_coordinates[0]
        space = 100 * self.scale_factor
        height = 240
        width = 240
        for i in range(-2, 2):
            display.screen.vline(origin.x + i, 0, height, M_GREY.as565())
        for i in range(-2, 2):
            display.screen.hline(0, origin.y + i, height, M_GREY.as565())
        x = origin.x + space
        while x < width:
            display.screen.vline(int(x), 0, height, M_GREY.as565())
            x += space
        x = origin.x - space
        while x > 0:
            display.screen.vline(int(x), 0, height, M_GREY.as565())
            x -= space
        y = origin.y + space
        while y < height:
            display.screen.hline(0, int(y), width, M_GREY.as565())
            y += space
        y = origin.y - space
        while y > 0:
            display.screen.hline(0, int(y), width, M_GREY.as565())
            y -= space

    def click_canvas(self, touch_point):
        self.canvas.redraw()


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

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.TITLE)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), cone_set.name(), font_20, True, Color.LABEL)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "INCLUDE", font_25, Color.BUTTON)
        middle_view.add_component(button)
        button.register_click_handler(self.clicked_include, cone_set)

        button_y += 40
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), "EXCLUDE", font_25, Color.BUTTON)
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
        self.urc_voltage = 3.9
        self.battery = ADC(Pin(1))
        self.battery.atten(ADC.ATTN_11DB)  # get the full range 0 - 3.3v
        self.update_count = 0
        # Telemetry updated values below
        self.gps_satellite_count = 0
        self.gps_satellite_fix = 0
        self.navigator = 'None'
        self.current_state = 'None'
        self.target_position = Point(150.0, 125.0)
        self.target_name = 'Finish'
        self.position = Point(0.0, 0.0)
        self.heading = 0
        self.robot_voltage = 12.4

    def update(self):
        self.update_count += 1
        if self.update_count == 10:
            self.update_count = 0
            # Update the URC voltage once per second
            self.urc_voltage = get_battery_level(self.battery)

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
                return ('PAUSED', Color.ALERT_LABEL)
            else:
                return ('RUNNING', Color.GOOD_LABEL)
        else:
            return ('N/C', Color.ALERT_LABEL)

    def target_heading(self):
        return self.position.compass_heading_to(self.target_position)

    def target_range(self):
        return self.position.distance_to(self.target_position)

    # This is specific to the Adafruit Ultimate GPS
    def gps_fix_quality(self):
        return ['None', 'GPS', 'DGPS'][self.gps_satellite_fix]

    def gps_string(self):
        return 'GPS sat: {} fix: {}'.format(self.gps_satellite_count, self.gps_fix_quality())

    def target_string(self):
        return '{}: {:.1f}m @ {} deg'.format(self.target_name, self.target_range(), int(self.target_heading()))

    def position_string(self):
        return 'Position: {:.1f} @ {:.1f}'.format(self.position.x, self.position.y)

    def current_state_string(self):
        return 'FSM: {}'.format(self.current_state)

    def navigator_string(self):
        return 'NAV: {}'.format(self.navigator)

    def heading_string(self):
        return 'Heading: {} deg'.format(self.heading)

    def robot_voltage_string(self):
        return 'Robot {:.1f}v'.format(self.robot_voltage)

    def urc_voltage_string(self):
        return 'URC {:.2f}v'.format(self.urc_voltage)

    def process_telemetry_packet(self, packet):
        if 'rv' in packet:
            self.robot_voltage = packet['rv']
        if 'heading' in packet:
            self.heading = packet['heading']
        if 'pos' in packet:
            elements = packet['pos']
            self.position = Point(elements[0], elements[1])
        if 'gps_sc' in packet:
            self.gps_satellite_count = packet['gps_sc']
        if 'gps_sf' in packet:
            self.gps_satellite_fix = packet['gps_sf']
        if 't_pos' in packet:
            elements = packet['t_pos']
            self.target_position = Point(elements[0], elements[1])
        if 't_name' in packet:
            self.target_name = packet['t_name']
        if 'nav' in packet:
            self.navigator = packet['nav']
        if 'state' in packet:
            self.current_state = packet['state']


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

        label = VisualLabel(Point(0, 20), "Sensors", font_32, True, Color.TITLE)
        top_view.add_component(label)

        box = Rectangle(Point(0, 0), Point(160, 124))
        items = ['Obstacle', 'Laser', 'IMU', 'GPS']
        self.vlist = VisualList(box, items, font_25, Color.LIST)
        middle_view.add_component(self.vlist)
        self.vlist.register_click_handler(self.list_click)

        text_height = font_25.HEIGHT
        width = self.display.text_width("CHOOSE", font_25) + 10
        x = self.display.SCREEN_WIDTH // 2 - (width // 2)
        button = VisualButton(Rectangle(Point(x, 5), Point(width, text_height + 4)), "CHOOSE", font_25, Color.BUTTON)
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

        label = VisualLabel(Point(0, 20), 'ROVER', font_32, True, Color.TITLE)
        top_view.add_component(label)

        label = VisualLabel(Point(0, 20), 'Motor: {}'.format(motor_name), font_25, True, Color.LABEL)
        middle_view.add_component(label)

        button_y = 60
        button = VisualButton(Rectangle(Point(0, button_y), Point(160, 35)), 'TEST', font_25, Color.BUTTON)
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
