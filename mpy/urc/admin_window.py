from display import Display
from util import *
from window import *
import NotoSans_15 as font_15
import NotoSans_20 as font_20
import NotoSans_25 as font_25
import NotoSans_32 as font_32
import time
import gc
from machine import Pin, Timer, ADC


class AdminWindow:

    BATTERY_DEFICIT_VOL = 1750
    BATTERY_FULL_VOL = 2100

    def __init__(self, window_manager, display, main_chain):
        self.window_manager = window_manager
        self.display = display
        self.main_chain = main_chain
        self.window = Window(self.display, "Admin")
        self.window.register_activate(self.window_activated)

        main_view = View("Top", Point(40, 0), Point(160, 240))
        self.window.add_view(main_view)

        label = VisualLabel(Point(0, 80), "UNIVERSAL", font_25, True, Color.YELLOW)
        main_view.add_component(label)
        label = VisualLabel(Point(0, 108), "ROBOT", font_25, True, Color.YELLOW)
        main_view.add_component(label)
        label = VisualLabel(Point(0, 136), "CONFIGURER", font_25, True, Color.YELLOW)
        main_view.add_component(label)

        battery_y = 180
        label = VisualLabel(Point(10, battery_y), "Batt:", font_25, False, Color.WHITE)
        main_view.add_component(label)

        label_box = Rectangle(Point(75, battery_y - 2), Point(70, 30))
        self.battery_label = VisualLabel(label_box, "", font_25, False, Color.WHITE)
        main_view.add_component(self.battery_label)

        self.charging_label = VisualLabel(Point(0, battery_y + 35), '', font_15, Color.RED)
        main_view.add_component(self.charging_label)

        self.battery = ADC(Pin(1))
        self.battery.atten(ADC.ATTN_11DB)  # get the full range 0 - 3.3v

        # Make an invisible button
        button = VisualButton(Rectangle(Point(0, 78), Point(160, 80)), '', font_15, Color.CYAN, False)
        main_view.add_component(button)
        button.register_click_handler(self.enter_urc)

    def enter_urc(self):
        print('Entering Robots from Admin')
        self.window_manager.push_window_chain(self.main_chain)

    def get_battery_level(self):
        millivolts = 0
        for index in range(10):
            millivolts += self.battery.read_uv() / 1000
            time.sleep_us(100)
        millivolts /= 10
        # This is supposed to have a 200K/100K voltage divider, but in reality
        # the resistors aren't quite that (on my board, the values are off by about 8%)
        volts = millivolts / 1000 * 3 * (3 / 2.762)
        return volts

    def update_battery(self, timer):
        voltage = self.get_battery_level()
        if voltage >= 3.7:
            color = Color.GREEN
        elif voltage >= 3.4:
            color = Color.YELLOW
        else:
            color = Color.RED
        self.battery_label.set_text('{:.2f}v'.format(voltage))
        self.battery_label.set_color(color)
        if voltage > 4.3:
            self.charging_label.set_text('charging')
            self.charging_label.set_color(Color.RED)
        else:
            self.charging_label.set_text('                  ')
            self.charging_label.set_color(Color.BLACK)

    def cancel_battery_timer(self, window):
        self.battery_timer.deinit()
        print('Admin window - about to close')

    def setup_battery_timer(self, window):
        self.battery_timer = Timer(2, mode=Timer.PERIODIC, freq=1, callback=self.update_battery)

    def window_activated(self, window):
        print('Admin Window activated')
        self.setup_battery_timer(None)
        self.window.register_about_to_close(self.cancel_battery_timer)
        self.window.register_screensaver_activate(self.cancel_battery_timer)
        self.window.register_screensaver_deactivate(self.setup_battery_timer)
