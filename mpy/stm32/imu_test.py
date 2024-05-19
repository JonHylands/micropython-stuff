
from imu import BNO085_IMU
import time


print('IMU BNO085 Test')

imu = BNO085_IMU(6)

while True:
    if imu.ready():
        imu.update()
        print('{} - IMU Pitch: {} Roll: {} Yaw: {}'.format(time.ticks_ms(), imu.pitch, imu.roll, imu.yaw))


