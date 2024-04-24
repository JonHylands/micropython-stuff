
from telemetry import Telemetry
from machine import UART
import time
import json


class RobotComms:
    def __init__(self):
        self.comms = Telemetry()
        self.comms.register_telemetry_callback(self.command_callback)
        self.robot_port = UART(1, baudrate=1000000, tx=43, rx=44, rxbuf=1000, timeout=1000)

    def command_callback(self, packet):
        print('Got command from URC: {}'.format(packet))
        packet_bytes = json.dumps(packet)
        print('Length: {}'.format(len(packet_bytes)))
        self.robot_port.write(packet_bytes)
        self.robot_port.write('\n')

    def update(self):
        if self.robot_port.any():
            time.sleep_ms(10)
            bytes = self.robot_port.readline()
            print('Got command from robot: {}'.format(bytes))
            self.comms.send_packet(bytes)

print('URC Telemetry on Robot (ESP32)')
rc = RobotComms()
while True:
    rc.update()
    time.sleep_ms(1)
