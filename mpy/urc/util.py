
import math
import gc9a01
import gc
import time
import io
import json
import os


def free(full=False):
    gc.collect()
    F = gc.mem_free()
    A = gc.mem_alloc()
    T = F + A
    P = '{0:.2f}%'.format(F / T * 100)
    if not full:
        return P
    else :
        return ('Total:{0} Free:{1} ({2})'.format(T, F, P))


def arduino_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


def get_battery_level(pin):
    millivolts = 0
    for index in range(10):
        millivolts += pin.read_uv() / 1000
        time.sleep_us(100)
    millivolts /= 10
    # This is supposed to have a 200K/100K voltage divider, but in reality
    # the resistors aren't quite that (on my board, the values are off by roughly 10%)
    volts = millivolts / 1000 * 3 * (3 / 2.70811)
    return volts


# HLS: Hue, Luminance, Saturation
# H: position in the spectrum
# L: color lightness
# S: color saturation

ONE_THIRD = 1.0 / 3.0
ONE_SIXTH = 1.0 / 6.0
TWO_THIRD = 2.0 / 3.0

def rgb_to_hls(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    sumc = (maxc + minc)
    rangec = (maxc - minc)
    l = sumc/2.0
    if minc == maxc:
        return 0.0, l, 0.0
    if l <= 0.5:
        s = rangec / sumc
    else:
        s = rangec / (2.0 - maxc - minc)  # Not always 2.0-sumc: gh-106498.
    rc = (maxc - r) / rangec
    gc = (maxc - g) / rangec
    bc = (maxc - b) / rangec
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2.0 + rc - bc
    else:
        h = 4.0 + gc - rc
    h = (h / 6.0) % 1.0
    return h, l, s

def hls_to_rgb(h, l, s):
    if s == 0.0:
        return l, l, l
    if l <= 0.5:
        m2 = l * (1.0 + s)
    else:
        m2 = l + s - (l * s)
    m1 = 2.0 * l - m2
    return (_v(m1, m2, h+ONE_THIRD), _v(m1, m2, h), _v(m1, m2, h - ONE_THIRD))

def _v(m1, m2, hue):
    hue = hue % 1.0
    if hue < ONE_SIXTH:
        return m1 + (m2 - m1) * hue * 6.0
    if hue < 0.5:
        return m2
    if hue < TWO_THIRD:
        return m1 + (m2 - m1) * (TWO_THIRD - hue) * 6.0
    return m1


class Color:

    BACKGROUND = -1
    TITLE = -1
    LABEL = -1
    GOOD_LABEL = -1
    WARNING_LABEL = -1
    ALERT_LABEL = -1
    BUTTON = -1
    LIST = -1
    SCROLL = -1

    def __init__(self, r, g, b):
        self.red = r
        self.green = g
        self.blue = b

    def __repr__(self):
        return 'Color({},{},{})'.format(self.red, self.green, self.blue)

    def r_g_b_float(self):
        return self.red / 255.0, self.green / 255.0, self.blue / 255.0

    def scale_lightness(self, scale_l):
        # convert rgb to hls
        r, g, b = self.r_g_b_float()
        h, l, s = rgb_to_hls(r, g, b)
        # manipulate h, l, s values and return as rgb
        r, g, b =  hls_to_rgb(h, min(1, l * scale_l), s)
        return Color(int(r * 255), int(g * 255), int(b * 255))

    # Return a triple that can be successively added to my r/g/b values
    # to fade from my color to the given color over count cycles
    def fade_values_to(self, color, count):
        red_offset = color.red - self.red
        green_offset = color.green - self.green
        blue_offset = color.blue - self.blue
        return (red_offset / count, green_offset / count, blue_offset / count)

    def fade_by(self, triple):
        return Color(self.red + triple[0], self.green + triple[1], self.blue + triple[2])

    def as565(self):
        return gc9a01.color565(int(self.red), int(self.green), int(self.blue))


M_RED = Color(0xF4, 0x43, 0x36)
M_PINK = Color(0xE9, 0x1E, 0x63)
M_PURPLE = Color(0x9C, 0x27, 0xB0)
M_DEEP_PURPLE = Color(0x67, 0x3A, 0xB7)
M_INDIGO = Color(0x3F, 0x51, 0xB5)
M_BLUE = Color(0x21, 0x96, 0xF3)
M_LIGHT_BLUE = Color(0x03, 0xA9, 0xF4)
M_CYAN = Color(0x00, 0xBC, 0xD4)
M_TEAL = Color(0x00, 0x96, 0x88)
M_GREEN = Color(0x4C, 0xAF, 0x50)
M_LIGHT_GREEN = Color(0x8B, 0xC3, 0x4A)
M_LIME = Color(0xCD, 0xDC, 0x39)
M_YELLOW = Color(0xFF, 0xEB, 0x3B)
M_AMBER = Color(0xFF, 0xC1, 0x07)
M_ORANGE = Color(0xFF, 0x98, 0x00)
M_DEEP_ORANGE = Color(0xFF, 0x57, 0x22)
M_BROWN = Color(0x79, 0x55, 0x48)
M_BLUE_GREY = Color(0x60, 0x7D, 0x8B)
M_GREY = Color(0x9E, 0x9E, 0x9E)
M_BLACK = Color(0x00, 0x00, 0x00)
M_WHITE = Color(0xFF, 0xFF, 0xFF)


class Theme:

    def __init__(self, name):
        self.name = name
        self.colors = {
            'background': M_BLACK,
            'title': M_YELLOW,
            'label': M_CYAN,
            'good_label': M_GREEN,
            'warning_label': M_AMBER,
            'alert_label': M_RED,
            'button': M_BLUE_GREY,
            'list': M_BLUE_GREY,
            'scroll': M_TEAL
        }

    def color_named(self, color_name):
        return self.colors[color_name]

    def set_color_named(self, color_name, color):
        self.colors[color_name] = color

    def apply(self):
        print('Applying theme {}'.format(self.name))
        Color.BACKGROUND = self.color_named('background')
        Color.TITLE = self.color_named('title')
        Color.LABEL = self.color_named('label')
        Color.GOOD_LABEL = self.color_named('good_label')
        Color.WARNING_LABEL = self.color_named('warning_label')
        Color.ALERT_LABEL = self.color_named('alert_label')
        Color.BUTTON = self.color_named('button')
        Color.LIST = self.color_named('list')
        Color.SCROLL = self.color_named('scroll')

    def dump_to_file(self):
        map = {}
        map['name'] = self.name
        map['colors'] = {}
        for color_name, color in self.colors.items():
            map['colors'][color_name] = (color.red, color.green, color.blue)
        file = io.open('theme-{}.json'.format(self.name), mode='w')
        json.dump(map, file)
        file.close()

    # Class method
    def read_from_file(theme_name):
        return Theme.read_from_file_named('theme-{}.json'.format(theme_name))

    # Class method
    def read_from_file_named(filename):
        print('Loading theme {}'.format(filename))
        file = io.open(filename, mode='r')
        map = json.load(file)
        file.close()
        color_map = {}
        for color_name, triple in map['colors'].items():
            color_map[color_name] = Color(triple[0], triple[1], triple[2])
        theme = Theme(map['name'])
        theme.colors = color_map
        return theme

    # Class method
    def available_themes():
        json_files = [filename for filename in os.listdir('.')
                      if filename.endswith('.json') and filename.startswith('theme-')]
        themes = []
        for name in json_files:
            themes.append(Theme.read_from_file_named(name))
        return themes


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    # class method
    def r_degrees(rho, degrees):
        radians = math.radians(degrees)
        return Point(rho * math.cos(radians), rho * math.sin(radians))

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __repr__(self):
        return '({} @ {})'.format(self.x, self.y)

    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def compass_heading_to(self, other):
        return (360.0 - (math.degrees(math.atan2(other.y - self.y, other.x - self.x)) - 90.0)) % 360


class Rectangle:
    def __init__(self, origin, extent):
        self.origin = origin
        self.extent = extent

    # class method - return a new rectangle centered at the given point with the given extent
    def center_extent(center, extent):
        return Rectangle(Point(center.x - (extent.x // 2), center.y - (extent.y // 2)), extent)

    # class method - return a new rectangle with all the points inside it
    def encompassing(points):
        left = points[0].x
        top = points[0].y
        bottom = top
        right = left
        for point in points:
            left = min(left, point.x)
            right = max(right, point.x)
            top = min(top, point.y)
            bottom = max(bottom, point.y)
        return Rectangle(Point(left, top), Point(right - left, bottom - top))

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

    def scale_by(self, value):
        return Rectangle(Point(self.origin.x * value, self.origin.y * value), Point(self.extent.x * value, self.extent.y * value))

    def center_in(self, other):
        x = (other.extent.x // 2) - (self.extent.x // 2)
        y = (other.extent.y // 2) - (self.extent.y // 2)
        return Rectangle(Point(other.origin.x + x, other.origin.y + y), self.extent)

    def contains_point(self, point):
        return self.origin.x <= point.x and self.corner().x >= point.x and self.origin.y <= point.y and self.corner().y >= point.y


class GpsCoordinate:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return '(GpsCoordinate lat: {} long: {})'.format(self.latitude, self.longitude)

    # In this context, the gps coordinates are close (within a few hundred meters),
    # so we don't really concern ourselves with the bearing changing over the distance.
    # Implementation dervied from https://www.movable-type.co.uk/scripts/latlong.html
    def bearing_to(self, coordinate):
        delta_long_rads = math.radians(coordinate.longitude - self.longitude)
        my_lat_rads = math.radians(self.latitude)
        c_lat_rads = math.radians(coordinate.latitude)
        first_part = -math.sin(delta_long_rads) * math.cos(c_lat_rads)
        second_part = (math.cos(my_lat_rads) * math.sin(c_lat_rads)) \
            - (math.sin(my_lat_rads) * math.cos(c_lat_rads) * math.cos(delta_long_rads))
        return math.degrees(math.atan2(first_part, second_part))

    # This implements the haversine formula to find the great-circle distance
    # Implementation dervied from https://www.movable-type.co.uk/scripts/latlong.html
    def distance_to(self, coordinate):
        radius = 6371
        deltaLatitude = coordinate.latitude - self.latitude
        deltaLongitude = coordinate.longitude - self.longitude
        alpha = math.sin(math.radians(deltaLatitude / 2)) ** 2 \
            + (math.cos(math.radians(self.latitude)) \
                * math.cos(math.radians(coordinate.latitude)) \
                * (math.sin(math.radians(deltaLongitude / 2)) ** 2))
        km = 2 * radius * math.atan2(math.sqrt(alpha), math.sqrt(1 - alpha))
        return km * 1000

    # class method - return a new GpsCoordinate from the given lat/long strings, in GPS sentence format
    # strings should be of the form: 'hhmm.mmmmD' or 'Dhhmm.mmmm', where D can be one of N/S/E/W
    def from_gps_coordinates(latitude_string, longitude_string):
        lat = GpsCoordinate.convert_coordinate(latitude_string)
        long = GpsCoordinate.convert_coordinate(longitude_string)
        return GpsCoordinate(lat, long)

    # class method - convert a GPS coordinate string 'hhmm.mmmm' to a decimal. Handle N/S/E/W (regardless of where it is).
    def convert_coordinate(coordinate_string):
        c = coordinate_string.upper()
        sign = 1
        if c.find('S') > 0 or c.find('W') > 0:
            sign = -1
        c = c.replace('N','').replace('E','').replace('S','').replace('W','').replace(',','.').replace(u'°',' ').replace('\'',' ').replace('"',' ')
        a = c.split()
        a.extend([0,0,0])
        try:
            return sign*(float(a[0])+float(a[1])/60.0+float(a[2])/3600.0) 
        except:
            return coordinate_string
