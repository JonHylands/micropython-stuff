
import network


class URCAccessPoint:

    AP = "URC_WLAN"
    PWD = "roundURC_128"

    def __init__(self):
        self.wlan = network.WLAN(network.AP_IF)
        self.wlan.active(True)
        self.wlan.config(essid=URCAccessPoint.AP, password=URCAccessPoint.PWD)

        while self.wlan.active() == False:
            pass

        print(self.wlan.ifconfig())

