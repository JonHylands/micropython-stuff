from util import *
from window import *


class RozWindow:
    def __init__(self, window_manager, display):
        self.window_manager = window_manager
        self.display = display
        self.build_root_window()

    def build_root_window(self):
        self.root_window = Window(self.display, "Roz")

        box = Rectangle(Point(0, 0), Point(240, 240))
        main_view = View("Top", box.origin, box.extent)
        self.root_window.add_view(main_view)

        image = VisualJpgImage(box, 'RozRobot-240.jpg')
        main_view.add_component(image)
