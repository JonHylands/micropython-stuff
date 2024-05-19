
#
#   Adafruit 9-DOF Orientation IMU Fusion Breakout - BNO085
#
#   Assumed to be in UART-RVC mode
#
#   UART - 115,200 bps
#   Transmits data at 100Hz with no prompting
#
#   19 byte binary record
#       - see https://www.ceva-ip.com/wp-content/uploads/2019/10/BNO080_085-Datasheet.pdf
#       - page 21 for details on record format
#

import struct
from machine import UART


class BNO085_IMU:

    def __init__(self, uart_number):
        self._uart = UART(uart_number)
        self._uart.init(baudrate=115200, rxbuf=100)
        self._read_buffer = bytearray(100)
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0

    def ready(self):
        return self._uart.any() >= 19

    def read_header(self):
        while True:
            self._uart.readinto(self._read_buffer, 1)  # read the first byte of the header
            if self._read_buffer[0] == 0xAA:
                self._uart.readinto(self._read_buffer, 1)  # read the second byte of the header
                if self._read_buffer[0] == 0xAA:
                    self._uart.readinto(self._read_buffer, 1)  # read the index byte of the header
                    return

    def update(self):
        done = False
        while not done:
            self.read_header()
            self._uart.readinto(self._read_buffer, 16)
            self.process_packet()
            done = self._uart.any() == 0

    def process_packet(self):
        items = struct.unpack('<hhh', self._read_buffer)
        self.yaw = items[0] * 0.01
        self.pitch = items[1] * 0.01
        self.roll = items[2] * 0.01

