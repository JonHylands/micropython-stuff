
from machine import Pin, SPI
import gc9a01
import time


class Display:

    SCREEN_WIDTH = 240
    SCREEN_HEIGHT = 240

    # Waveshare ESP32-S3 Touch Screen
    LCD_SPI_PORT = 2
    LCD_SCK_PIN = 10
    LCD_MOSI_PIN = 11
    LCD_CS_PIN = 9
    LCD_DC_PIN = 8
    LCD_RST_PIN = 14
    LCD_BL_PIN = 2


    def __init__(self):
        spi = SPI(Display.LCD_SPI_PORT)
        spi.deinit()
        time.sleep_ms(100)

        spi = SPI(Display.LCD_SPI_PORT, baudrate=40000000, sck=Pin(Display.LCD_SCK_PIN, Pin.OUT), mosi=Pin(Display.LCD_MOSI_PIN, Pin.OUT))
        self.backlight_pin = Pin(Display.LCD_BL_PIN, Pin.OUT)
        self.screen = gc9a01.GC9A01(spi, Display.SCREEN_WIDTH, Display.SCREEN_HEIGHT, reset=Pin(Display.LCD_RST_PIN, Pin.OUT), dc=Pin(Display.LCD_DC_PIN, Pin.OUT), cs=Pin(Display.LCD_CS_PIN, Pin.OUT), backlight=self.backlight_pin, rotation=0)

        self.screen.init()
        self.clear_screen()

    def turn_off_screen(self):
        self.backlight_pin.value(0)

    def turn_on_screen(self):
        self.backlight_pin.value(1)

    def jpg(self, filename, x, y):
        self.screen.jpg(filename, x, y) # , gc9a01.SLOW)

    def text_width(self, text, font):
        return self.screen.write_len(font, text)

    def clear_screen(self):
        self.screen.fill(gc9a01.BLACK)

    def center_text_x(self, text, font, y, color=gc9a01.WHITE):
        text_width = self.screen.write_len(font, text)
        x = (Display.SCREEN_WIDTH // 2) - (text_width // 2)
        self.screen.write(font, text, x, y, color)

    def draw_text(self, text, font, x, y, color=gc9a01.WHITE, back_color=gc9a01.BLACK):
        self.screen.write(font, text, x, y, color, back_color)

    def draw_circle(self, center_x, center_y, radius, color=gc9a01.WHITE):
        self.screen.circle(center_x, center_y, radius, color)

    def fill_circle(self, cx, cy, radius, color=gc9a01.WHITE):
        self.screen.fill_circle(cx, cy, radius, color)
