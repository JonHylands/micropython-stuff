
import network
import espnow
import json


class Telemetry:
    def __init__(self):
        # A WLAN interface must be active to send()/recv()
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.disconnect()   # Because ESP8266 auto-connects to last Access Point

        self.esp_now = espnow.ESPNow()
        self.esp_now.active(True)
        self.esp_now.irq(self.receive_callback)

        self.telemetry_callback = None
        self.return_mac = None

    def register_telemetry_callback(self, callback):
        self.telemetry_callback = callback

    # Packets are JSON strings
    def process_packet(self, packet_bytes):
        packet = json.loads(packet_bytes)
        if self.telemetry_callback is not None:
            self.telemetry_callback(packet)

    def send_packet(self, packet_bytes):
        if self.return_mac is not None:
            self.esp_now.send(self.return_mac, packet_bytes, True)

    def receive_callback(self, interface):
        while True:
            mac, msg = interface.recv(0)  # 0 timeout == no waiting
            if mac is None:
                return
            self.process_packet(msg)
            if self.return_mac is None:
                self.return_mac = mac
                self.esp_now.add_peer(self.return_mac)

    def shutdown(self):
        self.esp_now.active(False)
        self.wlan.active(False)
