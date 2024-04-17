
from telemetry import Telemetry
from machine import UART
import time
import json


class RobotComms:
    def __init__(self):
        self.comms = Telemetry()
        self.comms.register_telemetry_callback(self.command_callback)
        self.robot = UART(1, baudrate=1000000, tx=43, rx=44, rxbuf=1000, timeout=10)

    def command_callback(self, packet):
        print('Got command from URC: {}'.format(packet))
        self.robot.write(json.dumps(packet))

    def update(self):
        if self.robot.any():
            time.sleep_ms(10)
            bytes = self.robot.read()
            print('Got command from robot: {}'.format(bytes))
            self.comms.send_packet(bytes)

print('Roz Telemetry on Robot (ESP32)')
rc = RobotComms()
while True:
    rc.update()
    time.sleep_ms(1)
