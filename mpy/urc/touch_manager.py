

from machine import Pin
import micropython
import time
from fsm import State, FiniteStateMachine
from util import *
from cst816 import CST816


# TouchEvents are sent to the touch callback handlers (see TouchManager >> register_interest_in()).
class TouchEvent:
    TOUCH_PRESS = 1
    TOUCH_RELEASE = 2
    TOUCH_LONG = 3
    TOUCH_DOUBLE = 4
    TOUCH_DRAG_START = 5
    TOUCH_DRAG_CONTINUE = 6
    TOUCH_DRAG_STOP = 7

    def update_values(self, new_mode, new_x, new_y):
        self.mode = new_mode
        self.x = new_x
        self.y = new_y

    def is_touch_press(self):
        return self.mode == self.TOUCH_PRESS

    def is_touch_release(self):
        return self.mode == self.TOUCH_RELEASE

    def is_long_touch(self):
        return self.mode == self.TOUCH_LONG

    def is_double_touch(self):
        return self.mode == self.TOUCH_DOUBLE

    def is_drag_start(self):
        return self.mode == self.TOUCH_DRAG_START

    def is_drag_stop(self):
        return self.mode == self.TOUCH_DRAG_STOP

    def touch_point(self):
        return Point(self.x, self.y)


class TouchManager:

    # TOUCH_ID = 0x2E   # Seeed Studio Round Display
    TOUCH_ID = 0x15     # Waveshare ESP32-S3 Round Touch Display
    TOUCH_MAX_POINTS_NUM = 1
    TOUCH_READ_POINT_LEN = 5

    # Waveshare ESP32-S3 Round Touch Display
    TOUCH_I2C_PORT = 0
    TOUCH_INTERRUPT_PIN = 5
    TOUCH_SDA_PIN = 6
    TOUCH_SCL_PIN = 7

    # Raw event types from the touch chip
    TOUCH_NONE = 0
    TOUCH_DOWN = 1
    TOUCH_UP = 2

    LONG_TOUCH_THRESHOLD = 1000  # ms
    DOUBLE_TOUCH_THRESHOLD = 500  # ms
    DRAG_THRESHOLD = 5  # pixels

    def __init__(self):
        micropython.alloc_emergency_exception_buf(100)
        self.touch_interrupt = Pin(self.TOUCH_INTERRUPT_PIN, Pin.IN, Pin.PULL_UP)
        # Seeed Studio round display uses a different chip
        self.cst816 = CST816()
        self.touch_type = self.TOUCH_NONE
        self.touch_position_x = 0
        self.touch_position_y = 0
        self.touch_interrupt_time = 0
        self.last_touch_interrupt_time = 0
        self.touch_event = self.TOUCH_NONE
        self.touch_handler = self.handle_touch
        self.touch_event = TouchEvent()
        self.initial_touch_point = None
        self.handler_available = True
        # Screensaver Callback Support
        # screen_on_callback is called to physically turn the screen back on when the user touches a powered-off screen
        # setup_screensaver_timer_callback is called when the user stops interacting with the screen
        # cancel_screensaver_timer_callback is called if the screen is still on, and the user starts interacting with it
        self.screen_on_callback = None
        self.setup_screensaver_timer_callback = None
        self.cancel_screensaver_timer_callback = None
        self.screensaver_enabled = True

        self.initialize_touch_fsm()
        self.initialize_registry()
        # On the Seeed Studio round display, you need to use IRQ_FALLING
        self.touch_interrupt.irq(handler=self.touch_callback, trigger=Pin.IRQ_RISING)

    # Touch pin ISR callback
    def touch_callback(self, pin):
        self.touch_interrupt_time = time.ticks_ms()
        try:
            touching = self.cst816.get_touch()
        except:
            return
        # Some functionality to support screensaver. See WindowManager for details.
        if self.screensaver_enabled:
            if self.screen_on_callback is not None:
                # swallow touch events, if the screen is off.
                # wait for touch lift to turn screen back on
                if not touching:
                    self.screen_on_callback()
                    self.screen_on_callback = None
                return
        # If we're in the middle of handling the last touch event interrupt, ignore this one
        if self.handler_available:
            if touching:
                self.touch_type = self.TOUCH_DOWN
                self.cst816.get_point()
                self.touch_position_x = self.cst816.x_point
                self.touch_position_y = self.cst816.y_point
            else:
                self.touch_type = self.TOUCH_UP
            try:
                micropython.schedule(self.touch_handler, self)
            except RuntimeError:
                pass

    # Touch handler callback from the ISR, using micropython.schedule()
    # Mark the system as not available while the FSM executes
    def handle_touch(self, ignore):
        self.handler_available = False
        self.fsm.update()
        self.handler_available = True

    # This shuts off the touch interrupt entirely
    def deregister_touch_handler(self):
        self.touch_interrupt.irq(handler=None)

    # Register an interest for specific events inside a box (a Rectangle)
    # event_mode should be one of the TouchEvent.TOUCH_... constants
    def register_interest_in(self, event_mode, box, callback):
        self.registry.append((event_mode, box, callback))

    def initialize_registry(self):
        self.registry = []

    # We got a touch event, and need to send it to interested parties. Called from the FSM.
    def do_send_event(self, event_mode):
        local_touch_event = TouchEvent()
        local_touch_event.update_values(event_mode, self.touch_position_x, self.touch_position_y)
        # We've got a touch event, so set the timer if it is a release, otherwise cancel it
        if local_touch_event.is_touch_release():
            self.setup_screensaver_timer()
        else:
            self.cancel_screensaver_timer()
        # If we already have a live touch event set going, keep sending to the same widget
        if self.initial_touch_point is None:
            point = local_touch_event.touch_point()
        else:
            point = self.initial_touch_point
        for mode, box, callback in self.registry:
            if mode == event_mode and box.contains_point(point):
                # fix touch position in local coords
                local_x = self.touch_position_x - box.origin.x
                local_y = self.touch_position_y - box.origin.y
                local_touch_event.update_values(event_mode, local_x, local_y)
                callback(local_touch_event)

    # The user has lifted their finger, inform the setup callback
    def setup_screensaver_timer(self):
        if self.screensaver_enabled and self.setup_screensaver_timer_callback is not None:
            self.setup_screensaver_timer_callback()

    # The user has touched the screen, inform the cancel callback
    def cancel_screensaver_timer(self):
        if self.screensaver_enabled and self.cancel_screensaver_timer_callback is not None:
            self.cancel_screensaver_timer_callback()

    # Register a callback that will turn on the screen
    def turn_on_screen_with(self, callback):
        self.screen_on_callback = callback

    # Register a callback that will be called when there is user interaction
    def cancel_screensaver_timer_with(self, callback):
        self.cancel_screensaver_timer_callback = callback

    # Register a callback that will be called when user interaction stops
    def setup_screensaver_timer_with(self, callback):
        self.setup_screensaver_timer_callback = callback

    # Globally enable the screensaver
    def enable_screensaver(self):
        self.screensaver_enabled = True

    # Globally disable the screensave
    def disable_screensaver(self):
        self.screensaver_enabled = False

    # Set up the touch FSM
    def initialize_touch_fsm(self):
        self.wait_for_touch_state = State('wait_for_touch', self.enter_wait_for_touch, self.handle_wait_for_touch, None)
        self.wait_for_first_release_state = State('wait_for_first_release', None, self.handle_wait_for_first_release, None)
        self.continue_drag_state = State('continue_drag', None, self.handle_continue_drag, None)
        self.wait_for_second_touch_state = State('wait_for_second_touch', None, self.handle_wait_for_second_touch, None)
        self.wait_for_second_release_state = State('wait_for_second_release', None, self.handle_wait_for_second_release, None)
        self.fsm = FiniteStateMachine(self.wait_for_touch_state)


    # Normal state when the user isn't touching the screen
    def enter_wait_for_touch(self):
        self.initial_touch_point = None

    def handle_wait_for_touch(self):
        if self.touch_type == self.TOUCH_DOWN:
            self.initial_touch_point = Point(self.touch_position_x, self.touch_position_y)
            #print('TM initial_touch_point: {}'.format(self.initial_touch_point))
            #print('IT')
            self.initial_touch_time = self.touch_interrupt_time
            self.do_send_event(TouchEvent.TOUCH_PRESS)
            self.fsm.transitionTo(self.wait_for_first_release_state)

    # The user has touched the screen, now wait for either a release or a drag.
    # Handle long touch, touch release, and drag start
    def handle_wait_for_first_release(self):
        if self.touch_type == self.TOUCH_UP:
            delta_time = self.touch_interrupt_time - self.initial_touch_time
            if delta_time >= self.LONG_TOUCH_THRESHOLD:
                self.do_send_event(TouchEvent.TOUCH_LONG)
                self.setup_screensaver_timer()
                self.fsm.transitionTo(self.wait_for_touch_state)
            else:
                self.do_send_event(TouchEvent.TOUCH_RELEASE)
                self.lift_time = time.ticks_ms()
                self.fsm.transitionTo(self.wait_for_second_touch_state)
        if self.touch_type == self.TOUCH_DOWN:
            touch_point = Point(self.touch_position_x, self.touch_position_y)
            #print('TM dist: {} tp: {} itp: {}'.format(touch_point.distance_to(self.initial_touch_point), touch_point, self.initial_touch_point))
            #print('DW')
            if touch_point.distance_to(self.initial_touch_point) > self.DRAG_THRESHOLD:
                #print('DT')
                self.do_send_event(TouchEvent.TOUCH_DRAG_START)
                self.fsm.transitionTo(self.continue_drag_state)

    # The user is dragging - send drag continue events, and wait until they lift their finger
    def handle_continue_drag(self):
        #print('CD')
        if self.touch_type == self.TOUCH_UP:
            self.do_send_event(TouchEvent.TOUCH_DRAG_STOP)
            self.touch_position_x = self.initial_touch_point.x
            self.touch_position_y = self.initial_touch_point.y
            self.do_send_event(TouchEvent.TOUCH_RELEASE)
            self.setup_screensaver_timer()
            self.fsm.transitionTo(self.wait_for_touch_state)
            return
        #print('TM  tp: {} itp: {}'.format(Point(self.touch_position_x, self.touch_position_y), self.initial_touch_point))
        #print('CD2')
        self.do_send_event(TouchEvent.TOUCH_DRAG_CONTINUE)

    # The user released after a simple touch, wait a specific amount of time to see if they double-touch
    def handle_wait_for_second_touch(self):
        if time.ticks_ms() - self.lift_time > self.DOUBLE_TOUCH_THRESHOLD:
            self.setup_screensaver_timer()
            self.fsm.transitionTo(self.wait_for_touch_state)
            return
        if self.touch_type == self.TOUCH_DOWN:
            self.initial_touch_x = self.touch_position_x
            self.initial_touch_y = self.touch_position_y
            self.initial_touch_time = self.touch_interrupt_time
            self.fsm.transitionTo(self.wait_for_second_release_state)

    # Send the double touch event once they lift their finger a second time
    def handle_wait_for_second_release(self):
        if self.touch_type == self.TOUCH_UP:
            self.do_send_event(TouchEvent.TOUCH_DOUBLE)
            self.setup_screensaver_timer()
            self.fsm.transitionTo(self.wait_for_touch_state)
