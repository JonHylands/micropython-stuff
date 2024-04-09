
from telemetry import Telemetry
from machine import UART
import time


class RobotComms:
    def __init__(self):
        self.comms = Telemetry()
        self.comms.register_telemetry_callback(self.command_callback)
        self.robot = UART(1, baudrate=1000000, tx=43, rx=44, rxbuf=1000, timeout=10)

    def command_callback(self, packet_bytes):
        self.robot.write(packet_bytes)

    def update(self):
        if self.robot.any():
            time.sleep_ms(10)
            bytes = self.robot.read()
            self.comms.send_packet(bytes)

rc = RobotComms()
while True:
    rc.update()
    time.sleep_ms(1)
