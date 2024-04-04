#
#   LaserRangeSensor
#
#   Time of Flight VL53L0X plus variants
#


from vl53l1x import VL53L1X
from vl53l0x import VL53L0X
from vl6180x import VL6180X
import time



class LaserRangeSensor:

    DEFAULT_ID = 0x29

    LASER_SENSOR_VL53L0X = 0
    LASER_SENSOR_VL53L1X = 1
    LASER_SENSOR_VL6180X = 2


    def __init__(self, name, i2c, my_id, shutdown_pin, sensor_type):
        self.shutdown_pin = shutdown_pin
        self.shutdown()
        self.name = name
        self.my_id = my_id
        self.i2c = i2c
        self.sensor_type = sensor_type
        self.distance = 0


    def shutdown(self):
        self.shutdown_pin.value(0)


    def startup(self):
        self.shutdown_pin.value(1)


    def setup_sensor(self):
        self.startup()
        time.sleep_ms(50)
        if self.sensor_type == self.LASER_SENSOR_VL53L0X:
            self.sensor = VL53L0X(self.i2c, self.DEFAULT_ID)
        elif self.sensor_type == self.LASER_SENSOR_VL53L1X:
            self.sensor = VL53L1X(address=self.DEFAULT_ID, i2c_driver=self.i2c)
            self.sensor.sensor_init()
            time.sleep_ms(10)
            self.sensor.set_roi(4, 4)
            self.sensor.set_distance_mode(1)
            self.sensor.set_inter_measurement_in_ms(20)
            self.sensor.set_timing_budget_in_ms(15)
            self.sensor.start_ranging()
            time.sleep_ms(10)
            if self.my_id == self.DEFAULT_ID:
                return
            time.sleep_ms(10)
            self.sensor.set_i2c_address(self.my_id)
            time.sleep_ms(10)
        elif self.sensor_type == self.LASER_SENSOR_VL6180X:
            self.sensor = VL6180X(self.i2c, self.DEFAULT_ID)
            if self.my_id == self.DEFAULT_ID:
                return
            time.sleep(10)
            self.sensor.address(self.my_id)
            time.sleep(10)


    def update(self):
        if self.sensor_type == self.LASER_SENSOR_VL53L0X:
            self.distance = self.sensor.ping()
        elif self.sensor_type == self.LASER_SENSOR_VL53L1X:
            self.distance = self.sensor.get_distance()
        elif self.sensor_type == self.LASER_SENSOR_VL6180X:
            self.distance = self.sensor.range()


    def __repr__(self):
        return 'LaserRangeSensor({}: {})'.format(self.name, self.distance)
