
# Windowing System for MicroPython

from display import Display

import micropython
from util import *
from touch_manager import TouchManager, TouchEvent
from visual_dialog import *
from machine import Timer


# A window chain is a collection of windows that you can scroll horizontally through
class WindowChain:
    def __init__(self, name, window_list):
        self.name = name
        self.window_list = window_list
        self.current_window = self.window_list[0]

    def scroll_left(self):
        current_index = self.window_list.index(self.current_window)
        left_index = (current_index - 1) % len(self.window_list)
        self.current_window = self.window_list[left_index]

    def scroll_right(self):
        current_index = self.window_list.index(self.current_window)
        right_index = (current_index + 1) % len(self.window_list)
        self.current_window = self.window_list[right_index]

    def set_current_window(self, window):
        self.current_window = window

    def size(self):
        return len(self.window_list)

    def is_scrollable(self):
        return self.size() > 1


class WindowManager:
    def __init__(self, display):
        self.debug = False
        self.display = display
        self.window_stack = []
        self.screensaver_timer = None
        self.screensaver_enabled = True
        self.touch_manager = TouchManager()
        # Set the screensaver callbacks with the touch manager
        self.touch_manager.cancel_screensaver_timer_with(self.cancel_screensaver_timer_callback)
        self.touch_manager.setup_screensaver_timer_with(self.reinstate_screensaver_timer_callback)
        # Force it to happen the first time manually
        self.reinstate_screensaver_timer_callback()

    # Answer the top of stack window chain current window
    def current_window(self):
        if len(self.window_stack) == 0:
            return None
        return self.current_chain().current_window

    # Answer the top of stack window chain
    def current_chain(self):
        if len(self.window_stack) == 0:
            return None
        return self.window_stack[-1]

    # Set the current window in the current chain
    def set_current_window(self, window):
        chain = self.current_chain()
        if chain is not None:
            chain.set_current_window(window)

    # Debug function
    def print_window_stack(self, text):
        if not self.debug:
            return
        print('Printing Window Stack for {}'.format(text))
        for chain in self.window_stack:
            cw = 'None' if chain.current_window is None else chain.current_window.name
            print('---{} current: {}'.format(chain.name, cw))
            for window in chain.window_list:
                print('------{}'.format(window.name))

    # Push a single window, which just builds a 1-window chain and pushes that
    def push_window(self, window):
        self.push_window_chain(WindowChain(window.name, [window]))

    # Push window chain is used to add a new 'level' to the window system
    def push_window_chain(self, window_chain):
        old_current = self.current_window()
        for window in window_chain.window_list:
            # Only add bottom slider if there's a window chain to pop to
            if len(self.window_stack) > 0:
                self.add_bottom_slider_to(window)
            if window_chain.is_scrollable():
                self.add_side_sliders_to(window)
        self.select_window(window_chain.current_window, old_current)
        self.window_stack.append(window_chain)

    # The user swiped up - remove the current chain from the top of the stack
    # If this is the last chain in the stack, I assume you're going to immediately
    # push a new one...
    def pop_window(self, arg=None):
        old_window = self.current_window()
        self.window_stack.pop()
        if len(self.window_stack) > 0:
            # This is a bit of trickery. We want to select the new window,
            # but we can't use select_window() as is because we need to pop
            # the chain in between closing the old window and selecting
            # the new one.
            self.select_window(self.current_window(), old_window)
        else:
            old_window.about_to_close()
        self.print_window_stack('end of pop_window')

    # Pop the current chain, and decrement the schedule counter
    # This is used so we can schedule the pop, so the current drag operation finishes on the current window chain.
    # See the scroll_up() method below.
    def pop_window_special(self, arg=None):
        self.pop_window()

    # You can only select windows from the currently active chain
    def select_window(self, window, old_window):
        self.print_window_stack('beginning of select_window')
        # We're selecting a different window - tell the old current one it is closing
        if old_window is not None:
            old_window.about_to_close()
        self.touch_manager.initialize_registry()
        window.activate()
        window.draw()
        window.register_touch_handlers(self.touch_manager)
        self.print_window_stack('end of select_window')

    # Note - this is final, touch will no longer work after this
    def deregister_touch_handler(self):
        self.touch_manager.deregister_touch_handler()

    # The system is shutting down (Control-C on REPL). Turn off the touch handler interrupt,
    # notify the current window it is closing.
    def shutdown(self):
        self.deregister_touch_handler()
        window = self.current_window()
        # Allow the current window to kill any active timers or other resources as needed
        if window is not None:
            window.about_to_close()

    # Add a slider (drag) button (with its own view) to the given window.
    def add_slider_button(self, window, name, origin, extent, click_handler):
        view = View('{} Slider'.format(name), origin, extent)
        local_box = Rectangle(Point(0, 0), extent)
        window.add_view(view)
        button = VisualDragButton(local_box, '{} Slider'.format(name))
        view.add_component(button)
        button.register_click_handler(click_handler)

    # We have a window chain. Add left and right side slider buttons. Don't add them if they are already there.
    def add_side_sliders_to(self, window):
        if window.has_side_sliders():
            return
        print('**** - Adding side sliders to window {}'.format(window.name))
        self.add_slider_button(window, 'Left', Point(0, 80), Point(30, 80), self.scroll_left)
        self.add_slider_button(window, 'Right', Point(210, 80), Point(30, 80), self.scroll_right)

    # Add a bottom slider button to the given window. Don't add it if it is already there.
    def add_bottom_slider_to(self, window):
        if window.has_bottom_slider():
            return
        print('**** - Adding bottom slider to window {}'.format(window.name))
        self.add_slider_button(window, 'Bottom', Point(80, 210), Point(80, 30), self.scroll_up)

    # Event handler for bottom slider button.
    # The touch manager sends the DRAG_STOP event to the button, followed by the TOUCH_RELEASE.
    # We can't switch immediately because then the TOUCH_RELEASE will get sent to whatever widget
    # is under the user's finger on the new window.
    def scroll_up(self):
        print('scroll_up')
        callback = self.pop_window_special
        # we need to do this here so the touch drag stop handler sends touch release to us instead of the new window
        micropython.schedule(callback, 'pop')

    # Not sure why we don't need the above mechanism when srolling left/right
    def scroll_left(self):
        print('Scroll Left')
        old_current = self.current_window()
        self.current_chain().scroll_left()
        self.select_window(self.current_window(), old_current)

    # Not sure why we don't need the above mechanism when srolling left/right
    def scroll_right(self):
        print('Scroll Right')
        old_current = self.current_window()
        self.current_chain().scroll_right()
        self.select_window(self.current_window(), old_current)

    # Disable the screensaver (i.e., turn it off).
    # Tell the touch manager. Kill the timer, if it is running. Turn on the screen.
    def disable_screensaver(self):
        self.screensaver_enabled = False
        self.touch_manager.disable_screensaver()
        # if we've already got a timer running, kill it
        if self.screensaver_timer is not None:
            self.screensaver_timer.deinit()
        # Make sure the screen is on
        self.display.turn_on_screen()
 
    # Enable the screensaver(i.e., turn on the functionality).
    # Tell the touch manager.
    def enable_screensaver(self):
        self.screensaver_enabled = True
        self.touch_manager.enable_screensaver()
 
    # Callback from the window manager when the screensaver timer expires.
    def screensaver_callback(self, timer):
        self.display.turn_off_screen()
        self.current_window().screensaver_turned_on()
        self.touch_manager.turn_on_screen_with(self.screensaver_cancelled_callback)

    # Callback from the touch manager when the user touches a blacked out screen
    # The screensaver was active (screen was off). Turn it back on.
    def screensaver_cancelled_callback(self):
        self.display.turn_on_screen()
        self.current_window().screensaver_turned_off()
        self.reinstate_screensaver_timer_callback()

    # Callback from the touch manager. The user is actively interacting with the screen. Cancel the timer.
    def cancel_screensaver_timer_callback(self):
        if not self.screensaver_enabled:
            return
        if self.screensaver_timer is not None:
            # print('Screensaver timer cancelled')
            self.screensaver_timer.deinit()
            self.screensaver_timer = None

    # Callback from the touch manager, but also called directly from the window manager.
    # The user has stopped interacting with the screen and/or we need to restart the timer.
    def reinstate_screensaver_timer_callback(self):
        if not self.screensaver_enabled:
            return
        # print('Screensaver timer created')
        if self.screensaver_timer is not None:
            self.screensaver_timer.deinit()
        self.screensaver_timer = Timer(0, period=60000, mode=Timer.ONE_SHOT, callback=self.screensaver_callback)


class Window:
    def __init__(self, display, name):
        self.display = display
        self.screen = display.screen
        self.name = name
        self.views = []
        self.close_handler = None
        self.activate_handler = None
        self.screensaver_activate = None
        self.screensaver_deactivate = None

    # Register callback for when this window is activated (selected).
    def register_activate(self, activate_callback):
        self.activate_handler = activate_callback

    # Register callback for when this window is about to close.
    def register_about_to_close(self, close_callback):
        self.close_handler = close_callback

    # Register callback to get notified when the screensaver turns on.
    # This can be used for stopping timers that run while a window is active.
    def register_screensaver_activate(self, callback):
        self.screensaver_activate = callback

    # Register callback to get notified when the screensaver turns off.
    # This can be used to restart timers that are stopped when the screensaver activates.
    def register_screensaver_deactivate(self, callback):
        self.screensaver_deactivate = callback

    # Add a view to the window.
    def add_view(self, view):
        self.views.append(view)
        view.set_window(self)

    # Draw the window from scratch
    def draw(self):
        self.screen.fill(Color.BACKGROUND.as565())
        for each in self.views:
            each.draw_on(self.display)

    # Draw a single view. This is used for updating dirty components (see View >> draw_on())
    def draw_view(self, view):
        view.draw_on(self.display)

    # Ask each view to register for touch events.
    def register_touch_handlers(self, touch_manager):
        for each_view in self.views:
            each_view.register_for_touch_events(touch_manager)

    # Test to see if side sliders have already been added.
    def has_side_sliders(self):
        for each in self.views:
            if each.name == 'Left Slider' or each.name == 'Right Slider':
                return True
        return False

    # Test to see if bottom slider has already been added.
    def has_bottom_slider(self):
        for each in self.views:
            if each.name == 'Bottom Slider':
                return True
        return False

    # The window is about to close. If anyone registered a callback, execute it.
    def about_to_close(self):
        if self.close_handler is not None:
            self.close_handler(self)

    # The screensaver turned on. Execute the callback if it is there.
    def screensaver_turned_on(self):
        if self.screensaver_activate is not None:
            self.screensaver_activate(self)

    # The screensaver turned off. Execute the callback if it is there.
    def screensaver_turned_off(self):
        if self.screensaver_deactivate is not None:
            self.screensaver_deactivate(self)

    # The window was just opened. Execute the callback if it is there.
    def activate(self):
        if self.activate_handler is not None:
            self.activate_handler(self)


# A View represents an area of the window. Visual Components are added to views,
# and their coordinate system is local to the view's origin. Views can overlap.
class View:
    def __init__(self, name, origin, extent):
        self.name = name
        self.origin = origin
        self.extent = extent
        self.components = []
        self.window = None
        self.dirty_component = None

    # Draw either a single component, or all the components.
    def draw_on(self, display):
        if self.dirty_component is not None:
            self.dirty_component.draw_on(display, self.origin, self.extent)
        else:
            for each in self.components:
                each.draw_on(display, self.origin, self.extent)

    # Add the given component to the view's list
    def add_component(self, component):
        self.components.append(component)
        component.set_view(self)

    # Remove the given component from the view's list
    def remove_component(self, component):
        self.components.remove(component)

    # Set the window.
    def set_window(self, window):
        self.window = window

    # Return whether or not the view contains the given point, which is in screen coordinates.
    def contains_point(self, point):
        return Rectangle(self.origin, self.extent).contains_point(point)

    # As the window to re-draw the view. If we're only redrawing a single component, do that instead.
    def redraw(self, component=None):
        self.dirty_component = component
        self.window.draw_view(self)
        self.dirty_component = None

    # Forward the touch registry request to all components.
    def register_for_touch_events(self, touch_manager):
        for each in self.components:
            each.register_for_touch_events(touch_manager)


# A VisualComponent is a widget that lives inside a View.
# Visual components have to handle drawing themselves, handling touch events,
# and forwarding component-level events to whoever registers for them.
# Most visual components have a 'display_box' attribute that is set the first
# time it is drawn - this box is a Rectangle in screen coordinates.
# In general, components can overlap, but for a given point on the screen,
# there should be only one component that does touch interaction.
class VisualComponent:
    def __init__(self, origin):
        self.origin = origin
        self.display_box = None
        self.view = None

    def __repr__(self):
        return '{}: {}'.format(self.__class__.__name__, self.display_box)

    def set_view(self, view):
        self.view = view

    # Register with the touch manager for raw touch events.
    def register_for_touch_events(self, touch_manager):
        pass

    def redraw(self):
        self.view.redraw(self)


# VisualLabel prints a label on the screen. If you pass in a Rectangle for origin instead of a Point,
# also draw a box around the text. If you specify center_x, ignore the x-component of origin and draw
# the label centered horizontally in its view. No user interaction, just drawn.
class VisualLabel(VisualComponent):
    def __init__(self, origin, text, font, center_x=False, color=None, box_color=None):
        if isinstance(origin, Rectangle):
            self.box = origin
            super().__init__(origin.origin + Point(3, 3))
        else:
            self.box = None
            super().__init__(origin)
        self.text = text
        self.font = font
        if color is None:
            self.color = Color.LABEL
        else:
            self.color = color
        if box_color is None:
            self.box_color = self.color
        else:
            self.box_color = box_color
        self.center_x = center_x

    def draw_on(self, display, view_origin, view_extent):
        text_width = display.text_width(self.text, self.font)
        if self.box is not None:
            global_box = self.box.offset_by(view_origin)
            inner_box = global_box.inset_by(1)
            display.screen.fill_rect(inner_box.origin.x, inner_box.origin.y, inner_box.extent.x, inner_box.extent.y, Color.BACKGROUND.as565())
            display.screen.rect(global_box.left(), global_box.top(), global_box.width(), global_box.height(), self.box_color.as565())
        if self.center_x:
            x = view_origin.x + (view_extent.x // 2) - (text_width // 2)
            y = view_origin.y + self.origin.y
            display.draw_text(self.text, self.font, x, y, self.color)
            self.display_box = Rectangle(Point(x, y), Point(text_width, self.font.HEIGHT))
        else:
            display.draw_text(self.text, self.font, self.origin.x + view_origin.x, self.origin.y + view_origin.y, self.color)
            self.display_box = Rectangle(Point(self.origin.x + view_origin.x, self.origin.y + view_origin.y), Point(text_width, self.font.HEIGHT))

    # Update the text. Force a redraw of just this component.
    def set_text(self, new_text):
        if not (self.text == new_text):
            self.text = new_text
            self.view.redraw(self)

    # # Update the text color. Force a redraw of just this component.
    def set_color(self, new_color):
        if not (self.color == new_color):
            self.color = new_color
            self.view.redraw(self)

    # Return whether the given point (in screen coordinates) is inside the label.
    def contains_point(self, point):
        return self.display_box.contains_point(point)


# VisualJpgImage draws the jpg image from the given filename in the box. No user interaction, just drawn.
class VisualJpgImage(VisualComponent):
    def __init__(self, box, filename):
        super().__init__(box.origin)
        self.box = box
        self.filename = filename

    # Draw the jpg image.
    def draw_on(self, display, view_origin, view_extent, inverted=False):
        self.display_box = Rectangle(Point(self.box.origin.x + view_origin.x, self.box.origin.y + view_origin.y), Point(self.box.extent.x, self.box.extent.y))
        display.jpg(self.filename, self.display_box.left(), self.display_box.top())

    # Return whether the given point (in screen coordinates) is inside the image.
    def contains_point(self, point):
        return self.display_box.contains_point(point)


# VisualBox is like a VisualLabel with a rectangle and no text. No user interaction, just drawn.
class VisualBox(VisualComponent):
    def __init__(self, box, frame_color=None):
        super().__init__(box.origin)
        self.box = box
        if frame_color is None:
            self.frame_color = Color.LABEL
        else:
            self.frame_color = frame_color

    # Draw the box. Buttons are subclasses, so also pass in an option inverted flag.
    def draw_on(self, display, view_origin, view_extent, inverted=False):
        self.display_box = Rectangle(Point(self.box.origin.x + view_origin.x, self.box.origin.y + view_origin.y), Point(self.box.extent.x, self.box.extent.y))
        inner_box = self.display_box.inset_by(1)
        if inverted:
            display.screen.fill_rect(self.display_box.origin.x, self.display_box.origin.y, self.display_box.extent.x, self.display_box.extent.y, self.frame_color.as565())
        else:
            display.screen.fill_rect(inner_box.origin.x, inner_box.origin.y, inner_box.extent.x, inner_box.extent.y, Color.BACKGROUND.as565())
            display.screen.rect(self.display_box.origin.x, self.display_box.origin.y, self.display_box.extent.x, self.display_box.extent.y, self.frame_color.as565())

    # Return whether the given point (in screen coordinates) is inside the box.
    def contains_point(self, point):
        return self.display_box.contains_point(point)


# VisualButton represents a button you can see on the screen, and push.
# The clicked handler gets called on touch release.
# Setting draw to False makes it a completely transparent button, but still
# handles the same touch interactions.
class VisualButton(VisualBox):
    def __init__(self, box, text, font, color=None, draw=True):
        if color is None:
            color = Color.BUTTON
        super().__init__(box, color)
        self.text = text
        self.font = font
        self.highlighted = False
        self.click_callback = None
        self.draw = draw

    # Draw a simple box with the button label. If the user is currently touching the button,
    # draw it highlighted.
    def draw_on(self, display, view_origin, view_extent):
        if self.draw:
            super().draw_on(display, view_origin, view_extent, self.highlighted)
            text_width = display.text_width(self.text, self.font)
            text_height = self.font.HEIGHT
            x = view_origin.x + self.box.origin.x + (self.box.extent.x // 2) - (text_width // 2)
            y = view_origin.y + self.box.origin.y + (self.box.extent.y // 2) - (text_height // 2)
            if self.highlighted:
                display.draw_text(self.text, self.font, x, y, Color.BACKGROUND, self.frame_color)
            else:
                display.draw_text(self.text, self.font, x, y, self.frame_color)
        else:
            self.display_box = Rectangle(Point(self.box.origin.x + view_origin.x, self.box.origin.y + view_origin.y), Point(self.box.extent.x, self.box.extent.y))

    # Register to get notified when the user touches the button. Optional argument can be provided.
    def register_click_handler(self, click_callback, argument=None):
        self.click_callback = click_callback
        self.click_argument = argument

    # Register with the touch manager for touch press and release events.
    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_PRESS, self.display_box, self.handle_touch_press)
        touch_manager.register_interest_in(TouchEvent.TOUCH_RELEASE, self.display_box, self.handle_touch)

    # Callback from the touch manager, set the highlighted flag and redraw the button.
    def handle_touch_press(self, touch_event):
        self.highlighted = True
        if self.draw:
            self.view.redraw(self)

    # Callback from the touch manager, clear the highlighted flag, redraw the button,
    # and call the click handler callback.
    def handle_touch(self, touch_event):
        self.highlighted = False
        if self.draw:
            self.view.redraw(self)
        if self.click_callback is not None:
            if self.click_argument is None:
                self.click_callback()
            else:
                self.click_callback(self.click_argument)


# VisualDragButton is a special kind of button, that is activated (clicked) by dragging.
class VisualDragButton(VisualButton):
    def __init__(self, box, name):
        super().__init__(box, name, None)
        self.initial_drag_point = None
        self.finished_drag = False
        self.drag_vertical = box.width() > box.height()

    # we only draw to fill half the display box
    def draw_on(self, display, view_origin, view_extent):
        self.display_box = Rectangle(Point(self.box.origin.x + view_origin.x, self.box.origin.y + view_origin.y), Point(self.box.extent.x, self.box.extent.y))
        color = Color.SCROLL
        fade_to_color = Color.BACKGROUND
        if self.drag_vertical:    # Button visual layout is horizontal, i.e., at the bottom center of the screen
            if self.display_box.top() < 120:
                draw_box = Rectangle(self.display_box.origin, Point(self.display_box.width(), self.display_box.height() // 2))
                y_range = range(draw_box.top(), draw_box.bottom())
            else:
                draw_box = Rectangle(Point(self.display_box.left(), self.display_box.top() + (self.display_box.height() // 2)), Point(self.display_box.width(), self.display_box.height() // 2))
                y_range = range(draw_box.bottom() - 1, draw_box.top() - 1, -1)
            width = draw_box.width()
            height = draw_box.height()
            fade_triple = color.fade_values_to(fade_to_color, height)
            left = draw_box.left()
            for y in y_range:
                display.screen.hline(left, y, width, color.as565())
                color = color.fade_by(fade_triple)
        else:    # Button visual layout is vertical, i.e., at the left or right side of the screen
            if self.display_box.left() < 120:
                draw_box = Rectangle(self.display_box.origin, Point(self.display_box.width() // 2, self.display_box.height()))
                x_range = range(draw_box.left(), draw_box.right())
            else:
                draw_box = Rectangle(Point(self.display_box.left() + (self.display_box.width() // 2), self.display_box.top()), Point(self.display_box.width() // 2, self.display_box.height()))
                x_range = range(draw_box.right() - 1, draw_box.left() - 1, -1)
            width = draw_box.width()
            height = draw_box.height()
            fade_triple = color.fade_values_to(fade_to_color, width)
            top = draw_box.top()
            for x in x_range:
                display.screen.vline(x, top, height, color.as565())
                color = color.fade_by(fade_triple)

    # Touch manager callback. Keep track of where the drag started from.
    def handle_touch_drag_start(self, touch_event):
        self.initial_drag_point = touch_event.touch_point()

    # Touch manager callback. See if we've moved far enough to consider it a "click".
    def handle_touch_drag(self, touch_event):
        if self.initial_drag_point is not None:
            delta = self.initial_drag_point.distance_to(touch_event.touch_point())
            # Whether we trigger is not just the distance the touch drag has travelled - if you move sideways
            # from the button, and it is a drag_vertical button, then it should not be a trigger
            if self.drag_vertical:
                on_track = abs(self.initial_drag_point.x - touch_event.touch_point().x) < 30
            else:
                on_track = abs(self.initial_drag_point.y - touch_event.touch_point().y) < 30
            if on_track and delta >= (Display.SCREEN_WIDTH // 2):
                self.finished_drag = True

    # Touch manager callback. The drag finished, so trigger the callback.
    def handle_touch_drag_stop(self, touch_event):
        if self.click_callback is not None:
            self.initial_drag_point = None
            self.click_callback()

    # Register with the touch manager to get all the drag events.
    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_START, self.display_box, self.handle_touch_drag_start)
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_CONTINUE, self.display_box, self.handle_touch_drag)
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_STOP, self.display_box, self.handle_touch_drag_stop)


# VisualList is a box with a list of items. The list may be longer than will fit in the space on screen,
# in which case the user can scroll the list with their finger. Allows selection and double-click.
class VisualList(VisualBox):
    def __init__(self, box, items, font, color=None):
        if color is None:
            color = Color.LIST
        super().__init__(box, color)
        self.items = items
        self.font = font
        self.top_index = 0
        self.selected_index = None
        self.display_count = (box.height() - 4) // font.HEIGHT
        self.click_callback = None

    # top_index is the index of the item that is at the top of the visible list on screen.
    def set_top_index(self, index):
        self.top_index = index

    # Return a collection of the items that are visible on the screen.
    def visible_items(self):
        start = self.top_index
        stop = min(self.top_index + self.display_count, len(self.items))
        return self.items[start:stop]

    # Draw the visible items. Highlight if the current selection is visible.
    def draw_on(self, display, view_origin, view_extent):
        super().draw_on(display, view_origin, view_extent)
        x = view_origin.x + self.box.origin.x + 2
        y = view_origin.y + self.box.origin.y + 2
        for index, item in enumerate(self.visible_items()):
            if self.selected_index is not None and index == (self.selected_index - self.top_index):
                display.screen.fill_rect(x, y, self.display_box.extent.x - 4, self.font.HEIGHT, self.frame_color.as565())
                display.draw_text(item, self.font, x, y, Color.BACKGROUND, self.frame_color)
            else:
                display.draw_text(item, self.font, x, y, self.frame_color, Color.BACKGROUND)
            y += self.font.HEIGHT

    # Answer the currently selected item, or None if there isn't one.
    def selected_item(self):
        if self.selected_index is None:
            return None
        return self.items[self.selected_index]

    # Register a callback for click (double-click, really).
    def register_click_handler(self, click_callback):
        self.click_callback = click_callback

    # Register with the touch manager for touch events.
    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_PRESS, self.display_box, self.handle_touch_press)
        touch_manager.register_interest_in(TouchEvent.TOUCH_DOUBLE, self.display_box, self.handle_touch_double)
        if self.display_count < len(self.items):
            touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_START, self.display_box, self.handle_touch_drag_start)
            touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_CONTINUE, self.display_box, self.handle_touch_drag)

    # Callback from touch manager. Select whatever is under the user's finger.
    def handle_touch_press(self, touch_event):
        y_index = (touch_event.y // self.font.HEIGHT) + self.top_index
        if not (self.selected_index == y_index):
            self.selected_index = min(max(0, y_index), len(self.items) - 1)
            self.view.redraw(self)

    # Callback from touch manager. If there is a callback registered for click, execute it.
    # If there is no callback, deselect the selected item.
    def handle_touch_double(self, touch_event):
        if self.click_callback is not None:
            if self.selected_index is not None:
                if 0 <= self.selected_index < len(self.items):
                    self.click_callback(self.selected_item())
                else:
                    self.selected_index = None

    # Callback from the touch mamager. Start a scroll.
    def handle_touch_drag_start(self, touch_event):
        self.initial_drag_point = touch_event.touch_point()
        self.initial_drag_top_index = self.top_index
        self.last_delta_index = 0

    # Callback from the touch manager. Continue a scroll.
    def handle_touch_drag(self, touch_event):
        current_point = touch_event.touch_point()
        delta = self.initial_drag_point.y - current_point.y
        delta_index = delta // self.font.HEIGHT
        if not (delta_index == self.last_delta_index):
            self.last_delta_index = delta_index
            max_top_index = len(self.items) - self.display_count
            self.top_index = min(max(0, self.initial_drag_top_index + delta_index), max_top_index)
            self.view.redraw(self)


# VisualRollerList is like a combo box, except there is no drop down.
# The user drags vertically to select amongst the items in the list.
class VisualRollerList(VisualBox):
    def __init__(self, box, items, font, color=None):
        if color is None:
            color = Color.LIST
        super().__init__(box, color)
        if len(items) == 0:
            raise ValueError('VisualRollerList doesn''t work on an empty list.')
        self.items = items
        self.font = font
        self.selected_index = 0
        self.click_callback = None
        self.drag_events = False
        self.highlighted = False

    # Draw the current item in the list, with a box and a caret on top and underneath.
    def draw_on(self, display, view_origin, view_extent):
        super().draw_on(display, view_origin, view_extent)
        peak = self.display_box.top_center() + Point(0, -5)
        display.screen.line(self.display_box.left(), self.display_box.top(), peak.x, peak.y, self.frame_color.as565())
        display.screen.line(peak.x, peak.y, self.display_box.right(), self.display_box.top(), self.frame_color.as565())
        peak = self.display_box.bottom_center() + Point(0, 5)
        display.screen.line(self.display_box.left(), self.display_box.bottom(), peak.x, peak.y, self.frame_color.as565())
        display.screen.line(peak.x, peak.y, self.display_box.right(), self.display_box.bottom(), self.frame_color.as565())
        item = self.items[self.selected_index]
        text_height = self.font.HEIGHT
        text_width = display.text_width(item, self.font)
        text_box = Rectangle(self.box.origin, Point(text_width, text_height))
        text_box = text_box.center_in(self.display_box)
        if self.highlighted:
            display.screen.fill_rect(self.display_box.left(), self.display_box.top(), self.display_box.width(), self.display_box.height(), self.frame_color.as565())
            display.draw_text(item, self.font, text_box.left(), text_box.top(), Color.BACKGROUND, self.frame_color)
        else:
            display.draw_text(item, self.font, text_box.left(), text_box.top(), self.frame_color, Color.BACKGROUND)

    # Return the currently selected item.
    def selected_item(self):
        return self.items[self.selected_index]

    # Register to get notified when a new item is selected.
    def register_click_handler(self, click_callback):
        self.click_callback = click_callback

    # Update registration to get notified (or not) as the user is dragging.
    def set_drag_events(self, flag):
        self.drag_events = flag

    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_START, self.display_box, self.handle_touch_drag_start)
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_CONTINUE, self.display_box, self.handle_touch_drag)
        if not self.drag_events:
            touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_STOP, self.display_box, self.handle_touch_drag_stop)

    # Callback from the touch manager. Dragging has started.
    def handle_touch_drag_start(self, touch_event):
        self.initial_drag_point = touch_event.touch_point()
        self.initial_drag_selected_index = self.selected_index
        self.last_delta_index = 0
        self.highlighted = True

    # Callback from the touch manager. Update the display. Notify the callback if they
    # asked for drag events.
    def handle_touch_drag(self, touch_event):
        current_point = touch_event.touch_point()
        delta = self.initial_drag_point.y - current_point.y
        delta_index = delta // 10
        if not (delta_index == self.last_delta_index):
            self.last_delta_index = delta_index
            self.selected_index = (self.initial_drag_selected_index + delta_index) % len(self.items)
            if self.drag_events:
                self.click_callback(self.selected_item())
            self.view.redraw(self)

    # Callback from the touch manager. Notify the callback of the new selection.
    def handle_touch_drag_stop(self, touch_event):
        self.click_callback(self.selected_item())
        self.highlighted = False
        self.view.redraw(self)


# VisualSlider is like a horizontal scroll bar that the user can drag. Pass in a range, which can have a start, stop, and step value.
class VisualSlider(VisualBox):
    def __init__(self, box, item_range, font, color=None):
        if color is None:
            color = Color.LIST
        super().__init__(box, color)
        self.item_range = item_range
        self.font = font
        self.selected_value = item_range.start
        self.click_callback = None
        self.start_point = None
        self.end_point = None
        self.drag_events = False
        self.last_selected_value = None

    # Register to be notified when the slider changes.
    def register_click_handler(self, click_callback):
        self.click_callback = click_callback

    # Update registration to get notified (or not) as the user is dragging.
    def set_drag_events(self, flag):
        self.drag_events = flag

    # Draw the slider. A box, a horizontal line in the middle, and a square that represents the "handle"
    def draw_on(self, display, view_origin, view_extent):
        super().draw_on(display, view_origin, view_extent)
        inner_box = self.box.inset_by(2).center_in(self.display_box)
        handle_width = 20
        handle_offset = handle_width // 2
        self.start_point = Point(inner_box.left_center().x + handle_offset, inner_box.left_center().y)
        self.end_point = self.start_point + Point(inner_box.width() - handle_width, 0)
        handle_position = arduino_map(self.selected_value, self.item_range.start, self.item_range.stop, self.start_point.x, self.end_point.x)
        handle_box = Rectangle(Point(handle_position - handle_offset, inner_box.top()), Point(handle_width, inner_box.height()))
        display.screen.hline(self.start_point.x, self.start_point.y, inner_box.width() - handle_width, self.frame_color.as565())
        display.screen.fill_rect(handle_box.left(), handle_box.top(), handle_box.width(), handle_box.height(), self.frame_color.as565())

    # Register for touch manager events.
    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_START, self.display_box, self.handle_touch_drag_start)
        touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_CONTINUE, self.display_box, self.handle_touch_drag)
        if not self.drag_events:
            touch_manager.register_interest_in(TouchEvent.TOUCH_DRAG_STOP, self.display_box, self.handle_touch_drag_stop)

    # Callback from touch manager. A drag has started.
    def handle_touch_drag_start(self, touch_event):
        if self.drag_events:
            self.click_callback(self.selected_value)
        self.last_value = self.selected_value

    # Callback from touch manager. The user is dragging the slider. Constrain it to the given range.
    def handle_touch_drag(self, touch_event):
        current_point = touch_event.touch_point().x
        start_x = self.start_point.x - self.display_box.origin.x  # start_x and end_x have to be in widget coordinates
        end_x = self.end_point.x - self.display_box.origin.x
        current_value = arduino_map(current_point, start_x, end_x, self.item_range.start, self.item_range.stop)
        current_value = (current_value // self.item_range.step) * self.item_range.step
        current_value = min(max(current_value, self.item_range.start), self.item_range.stop)
        if not(self.last_selected_value == current_value):
            self.last_selected_value = current_value
            self.selected_value = current_value
            self.click_callback(self.selected_value)
            self.view.redraw(self)

    # Callback from touch manager. The user has stopped dragging. Notify the click callback.
    def handle_touch_drag_stop(self, touch_event):
        self.click_callback(self.selected_value)
        self.view.redraw(self)

# VisualCanvas is like a VisualBox that clients can draw on. Clients can also register for touch events.
class VisualCanvas(VisualComponent):
    def __init__(self, box, draw_callback=None):
        super().__init__(box.origin)
        self.box = box
        self.draw_callback = draw_callback

    # Draw the box. Buttons are subclasses, so also pass in an option inverted flag.
    def draw_on(self, display, view_origin, view_extent):
        self.display_box = Rectangle(Point(self.box.origin.x + view_origin.x, self.box.origin.y + view_origin.y), Point(self.box.extent.x, self.box.extent.y))
        if self.draw_callback is not None:
            self.draw_callback(display, self.display_box)

    # Return whether the given point (in screen coordinates) is inside the box.
    def contains_point(self, point):
        return self.display_box.contains_point(point)

    # Register to get notified when the user touches the button. Callback should take a Point argument.
    def register_click_handler(self, click_callback):
        self.click_callback = click_callback

    # Register with the touch manager for touch press and release events.
    def register_for_touch_events(self, touch_manager):
        touch_manager.register_interest_in(TouchEvent.TOUCH_RELEASE, self.display_box, self.handle_touch)

    # Callback from the touch manager, call the click handler callback.
    def handle_touch(self, touch_event):
        if self.click_callback is not None:
            self.click_callback(touch_event.touch_point())
