
import math
import gc9a01
from micropython import const


def arduino_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


class Color:
    BLACK = const(0x0000)
    BLUE = const(0x001F)
    RED = const(0xF800)
    GREEN = const(0x07E0)
    CYAN = const(0x07FF)
    MAGENTA = const(0xF81F)
    YELLOW = const(0xFFE0)
    WHITE = const(0xFFFF)

    def __init__(self, r, g, b):
        self.red = r
        self.green = g
        self.blue = b

    def as565(self):
        return gc9a01.color565(self.red, self.green, self.blue)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __repr__(self):
        return '({} @ {})'.format(self.x, self.y)

    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


class Rectangle:
    def __init__(self, origin, extent):
        self.origin = origin
        self.extent = extent

    def __repr__(self):
        return '(Rectangle origin: {} extent: {})'.format(self.origin, self.extent)

    def corner(self):
        return self.origin + self.extent

    def width(self):
        return self.extent.x

    def height(self):
        return self.extent.y

    def left_center(self):
        return Point(self.origin.x, self.origin.y + (self.extent.y // 2))

    def right_center(self):
        return Point(self.corner().x, self.origin.y + (self.extent.y // 2))

    def top_center(self):
        return self.origin + Point(self.extent.x // 2, 0)

    def bottom_center(self):
        return self.origin + Point(self.extent.x // 2, self.extent.y)

    def center(self):
        return Point(self.origin.x + (self.extent.x // 2), self.origin.y + (self.extent.y // 2))

    def left(self):
        return self.origin.x

    def right(self):
        return self.origin.x + self.extent.x

    def top(self):
        return self.origin.y

    def bottom(self):
        return self.origin.y + self.extent.y

    def inset_by(self, value):
        return Rectangle(Point(self.origin.x + value, self.origin.y + value), Point(self.extent.x - (2 * value), self.extent.y - (2 * value)))

    def offset_by(self, point):
        return Rectangle(self.origin + point, self.extent)

    def center_in(self, other):
        x = (other.extent.x // 2) - (self.extent.x // 2)
        y = (other.extent.y // 2) - (self.extent.y // 2)
        return Rectangle(Point(other.origin.x + x, other.origin.y + y), self.extent)

    def contains_point(self, point):
        return self.origin.x <= point.x and self.corner().x >= point.x and self.origin.y <= point.y and self.corner().y >= point.y
