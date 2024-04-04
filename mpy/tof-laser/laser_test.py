
from laser import LaserRangeSensor as Laser
from machine import Pin, I2C
import time


shutdown = Pin(Pin.cpu.B2, Pin.OUT)
i2c = I2C(2)

sensor = Laser('Test', i2c, 0x29, shutdown, Laser.LASER_SENSOR_VL53L1X)

time.sleep_ms(50)
sensor.setup_sensor()
time.sleep_ms(50)

while True:
    sensor.update()
    print('Range: {}'.format(sensor.distance))
    time.sleep_ms(50)
