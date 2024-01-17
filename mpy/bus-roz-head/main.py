
import pyb
from stm_uart_port import UART_Port
from Packet import Packet
from machine import I2C
from vl53l1x import VL53L1X
from em7180 import EM7180_Master
from pmw3901 import *
import sys
import math
import gc


#================================================
#
#     Class Metro
#

class Metro:

  def __init__(self, interval_millis):
    self.interval = interval_millis
    self.previous = pyb.millis()

  def setInterval(self, interval_millis):
    self.interval = interval_millis

  def check(self):
    now = pyb.millis()
    if self.interval == 0:
      self.previous = now
      return True
    if (now - self.previous) >= self.interval:
      self.previous = now
      return True
    return False

  def reset(self):
    self.previous = pyb.millis()


#================================================
#
#       Class HeartbeatLED
#

class HeartbeatLED:

    def __init__(self, ledPin):
        self.led = ledPin
        self.led.value(0)
        self.timer = Metro(0)
        self.set(100, 900)

    def set(self, newOnInterval, newOffInterval):
        self.onInterval = newOnInterval
        self.offInterval = newOffInterval
        self.timer.setInterval(self.offInterval)
        self.ledState = 0
        self.led.value(0)

    def update(self):
        if self.timer.check():
            if self.ledState:
                self.ledState = 0
                self.led.value(0)
                if self.onInterval != self.offInterval:
                    self.timer.setInterval(self.offInterval)
            else:
                self.ledState = 1
                self.led.value(1)
                if self.onInterval != self.offInterval:
                    self.timer.setInterval(self.onInterval)

    def shutdown(self):
        self.led.value(0)


class State:

  def __init__(self, enterFunction, updateFunction, exitFunction):
    self.userEnter = enterFunction
    self.userUpdate = updateFunction
    self.userExit = exitFunction
    self.startTimeOnUpdate = self.userEnter is None

  def enter(self):
    self.startTimeMillis = pyb.millis()
    if self.userEnter is not None:
      self.userEnter()

  def update(self):
    if self.startTimeOnUpdate:
      self.startTimeMillis = pyb.millis()
      self.startTimeOnUpdate = False
    if self.userUpdate is not None:
      self.userUpdate()

  def exit(self):
    if self.userExit is not None:
      self.userExit()

  def elapsedTimeMillis(self):
    return pyb.elapsed_millis(self.startTimeMillis)


class FiniteStateMachine:

  def __init__(self, startState):
    self.currentState = startState
    self.nextState = startState
    self.needToTriggerEnter = True
    self.cycleCount = 0

  def transitionTo(self, newState):
    self.nextState = newState

  def getCycleCount(self):
    return self.cycleCount

  def getCurrentStateMillis(self):
    return self.currentState.elapsedTimeMillis()

  def update(self):
    if self.needToTriggerEnter:
      self.currentState.enter()
      self.needToTriggerEnter = False
    if self.currentState != self.nextState:
      self.currentState.exit()
      self.currentState = self.nextState
      self.currentState.enter()
      self.cycleCount = True
    self.currentState.update()


#=============================================


BIOLOID_CMD_PING = 1
BIOLOID_CMD_READ = 2
BIOLOID_CMD_WRITE = 3
BIOLOID_CMD_RESET = 6

CONTROL_MODEL_NUMBER_LOW = 0
CONTROL_MODEL_NUMBER_HIGH = 1
CONTROL_FIRMWARE_VERSION = 2
CONTROL_ID = 3
CONTROL_BAUD_RATE = 4
CONTROL_RETURN_DELAY_TIME = 5
CONTROL_STATUS_RETURN_LEVEL = 16

CONTROL_LED = 25
CONTROL_FRONT_RANGE_LOW = 26
CONTROL_FRONT_RANGE_HIGH = 27
CONTROL_FRONT_LEFT_RANGE_LOW = 28
CONTROL_FRONT_LEFT_RANGE_HIGH = 29
CONTROL_FRONT_RIGHT_RANGE_LOW = 30
CONTROL_FRONT_RIGHT_RANGE_HIGH = 31
CONTROL_LEFT_RANGE_LOW = 32
CONTROL_LEFT_RANGE_HIGH = 33
CONTROL_RIGHT_RANGE_LOW = 34
CONTROL_RIGHT_RANGE_HIGH = 35
CONTROL_IMU_PITCH_LOW = 36
CONTROL_IMU_PITCH_HIGH = 37
CONTROL_IMU_ROLL_LOW = 38
CONTROL_IMU_ROLL_HIGH = 39
CONTROL_IMU_YAW_LOW = 40
CONTROL_IMU_YAW_HIGH = 41
CONTROL_FLOW_X_LOW = 42
CONTROL_FLOW_X_HIGH = 43
CONTROL_FLOW_Y_LOW = 44
CONTROL_FLOW_Y_HIGH = 45

CONTROL_TABLE_SIZE = 46

PACKET_ERROR_RESERVED = 0x80         # Reserved - set to zero
PACKET_ERROR_INSTRUCTION = 0x40      # Undefined instruction
PACKET_ERROR_OVERLOAD = 0x20         # Max torque can't control applied load
PACKET_ERROR_CHECKSUM = 0x10         # Checksum of instruction packet incorrect
PACKET_ERROR_RANGE = 0x08            # Instruction is out of range
PACKET_ERROR_OVERHEATING = 0x04      # Internal temperature is too high
PACKET_ERROR_ANGLE_LIMIT = 0x02      # Goal position is outside of limit range
PACKET_ERROR_INPUT_VOLTAGE = 0x01    # Input voltage out of range
PACKET_ERROR_NONE = 0x00             # No Error

HEAD_BOARD_ID = 131

HEAD_BOARD_UART = 3


class BioloidDevice:
  def __init__(self, head_board):
    self.port = UART_Port(HEAD_BOARD_UART, 1000000, 256)
    self.uart = self.port.uart
    self.uart_first_buffer = bytearray(4)
    self.uart_last_buffer = bytearray(251)
    self.initControlTable()
    self.packet = Packet()
    self.packet.register_callback(self.packetReceived)
    self.head_board = head_board
    self.gc_timer = Metro(1000)
    # flush the UART
    while self.port.any():
      self.port.read_byte()
    #self.trigger_1 = pyb.Pin('C2', pyb.Pin.OUT_PP)
    #self.trigger_2 = pyb.Pin('A6', pyb.Pin.OUT_PP)
    #self.trigger_3 = pyb.Pin('A7', pyb.Pin.OUT_PP)
    #self.trigger_1.value(0)
    #self.trigger_2.value(0)
    #self.trigger_3.value(0)

  def initControlTable(self):
    self.controlTable = [0] * CONTROL_TABLE_SIZE
    self.controlTable[CONTROL_MODEL_NUMBER_LOW] = 13
    self.controlTable[CONTROL_MODEL_NUMBER_HIGH] = 67
    self.controlTable[CONTROL_FIRMWARE_VERSION] = 1
    self.controlTable[CONTROL_ID] = HEAD_BOARD_ID
    self.controlTable[CONTROL_BAUD_RATE] = 1
    self.controlTable[CONTROL_RETURN_DELAY_TIME] = 0
    self.controlTable[CONTROL_STATUS_RETURN_LEVEL] = 2

  def packetReceived(self, receivedPacket):
    # print('got packet for {}'.format(receivedPacket.id))
    if receivedPacket.id == HEAD_BOARD_ID:
      if receivedPacket.command == BIOLOID_CMD_PING:
        self.handlePing(receivedPacket)
      elif receivedPacket.command == BIOLOID_CMD_READ:
        self.handleRead(receivedPacket)
      elif receivedPacket.command == BIOLOID_CMD_WRITE:
        self.handleWrite(receivedPacket)
      elif receivedPacket.command == BIOLOID_CMD_RESET:
        self.doReset(receivedPacket)

  def handlePing(self, packet):
    # print('Got ping')
    # pyb.udelay(self.controlTable[CONTROL_RETURN_DELAY_TIME] * 2)
    response_buffer = bytearray([0xFF, 0xFF, HEAD_BOARD_ID, 0x02, 0, ((HEAD_BOARD_ID + 2) ^ 255)])
    self.port.write_packet(response_buffer)

  def handleRead(self, packet):
    # print('Got read')
    start = packet.parameters[0]
    length = packet.parameters[1]
    if start < 0 or start + length > CONTROL_TABLE_SIZE:
      print('handleRead out of range: {}: {}'.format(start, length))
      return self.sendErrorResponse(packet, PACKET_ERROR_RANGE)
    # pyb.udelay(self.controlTable[CONTROL_RETURN_DELAY_TIME] * 2)
    response_buffer = bytearray([0xFF, 0xFF, HEAD_BOARD_ID, length + 2, 0])
    crc = HEAD_BOARD_ID + length + 2
    for index in range(start, start + length):
      byte = self.controlTable[index]
      response_buffer.append(byte)
      crc += byte
    response_buffer.append((crc & 255) ^ 255)
    self.port.write_packet(response_buffer)
    # print('{} handleRead {} bytes at {}'.format(HEAD_BOARD_ID, length, start))

  def sendErrorResponse(self, packet, error):
    response_buffer = bytearray([0xFF, 0xFF, HEAD_BOARD_ID, 2, error])
    crc = HEAD_BOARD_ID + 2
    response_buffer.append((crc & 255) ^ 255)
    self.port.write_packet(response_buffer)

  def handleWrite(self, packet):
    # print('Got write')
    pass

  def update(self):
    while self.port.any():
      response = self.uart.readinto(self.uart_first_buffer, 4)
      if response is not None:
        self.packet.process_bytes(self.uart_first_buffer)
        if self.packet.length is None:
          while self.port.any():
            self.port.read_byte()
        else:
          response = self.uart.readinto(self.uart_last_buffer, self.packet.length)
          # sometimes the whole packet isn't there yet, so we need to read it in pieces
          if response < self.packet.length:
            mv = memoryview(self.uart_last_buffer)
            while response < self.packet.length:
              count = self.uart.readinto(mv[response:self.packet.length], self.packet.length - response)
              if count is not None:
                response += count
          if self.packet.id == HEAD_BOARD_ID:
            self.packet.process_bytes(self.uart_last_buffer, response)
          else:
            # if it isn't our packet, we don't care about it, so just reset the packet parser
            self.packet.reset_state()
            # We're going to do a gc here as well, if its been long enough
            if self.gc_timer.check():
              gc.collect()


HEAD_SHUTDOWN_LEFT = pyb.Pin.cpu.C3
HEAD_SHUTDOWN_FRONT_LEFT = pyb.Pin.cpu.B9
HEAD_SHUTDOWN_FRONT = pyb.Pin.cpu.B8
HEAD_SHUTDOWN_FRONT_RIGHT = pyb.Pin.cpu.C6
HEAD_SHUTDOWN_RIGHT = pyb.Pin.cpu.C7

HEAD_IMU_INT = pyb.Pin.cpu.C4
HEAD_SPI_CS = pyb.Pin('C5', pyb.Pin.OUT_PP)
HEAD_SPI_BUS = 2
HEAD_I2C_BUS = 1

HEAD_RANGE_DEFAULT_ADDRESS = 0x29
HEAD_RANGE_FRONT_ADDRESS = 0x30
HEAD_RANGE_FRONT_LEFT_ADDRESS = 0x31
HEAD_RANGE_FRONT_RIGHT_ADDRESS = 0x32
HEAD_RANGE_LEFT_ADDRESS = 0x33
HEAD_RANGE_RIGHT_ADDRESS = 0x34

HEAD_IMU_MAG_RATE = 100  # Hz
HEAD_IMU_ACCEL_RATE = 200  # Hz
HEAD_IMU_GYRO_RATE = 200  # Hz
HEAD_IMU_BARO_RATE = 50  # Hz
HEAD_IMU_Q_RATE_DIVISOR = 3  # 1/3 gyro rate


class HeadBoard:
  def __init__(self):
    self.pitch = 0
    self.roll = 0
    self.yaw = 0
    self.flow_x = 0
    self.flow_y = 0
    self.device = BioloidDevice(self)
    self.range_timer = Metro(20)
    self.mem_timer = Metro(100)
    self.i2c = I2C(HEAD_I2C_BUS)
    self.initializeRangeSensors()
    self.initializeImuSensor()
    self.initializeFlowSensor()
    print('Sensors Initialized')
    redPin = pyb.Pin(pyb.Pin.cpu.C1, pyb.Pin.OUT_PP)
    self.heartbeat = HeartbeatLED(redPin)
    self.word_buffer = bytearray(2)
    self.updateSensors()  # call it once

  def update(self):
    self.heartbeat.update()
    if self.range_timer.check():
      self.updateSensors()
      self.updateControlTable()
      # self.print_sensors()
    #if self.mem_timer.check():
      #print('Free memory: {}'.format(gc.mem_free()))

  def run(self):
    while True:
      self.device.update()
      self.update()

  def print_sensors(self):
    print('PITCH: {} ROLL: {} YAW: {} L: {} FL: {} F: {} FR: {} R: {} X,Y: {},{}'.format(round(self.pitch), round(self.roll),
                                                                              round(self.yaw), self.leftRange,
                                                                              self.frontLeftRange, self.frontRange,
                                                                              self.frontRightRange, self.rightRange,
                                                                              self.flow_x, self.flow_y))

  def updateControlTable(self):
    self.device.controlTable[CONTROL_FRONT_RANGE_LOW] = self.frontRange & 255
    self.device.controlTable[CONTROL_FRONT_RANGE_HIGH] = self.frontRange >> 8
    self.device.controlTable[CONTROL_FRONT_LEFT_RANGE_LOW] = self.frontLeftRange & 255
    self.device.controlTable[CONTROL_FRONT_LEFT_RANGE_HIGH] = self.frontLeftRange >> 8
    self.device.controlTable[CONTROL_FRONT_RIGHT_RANGE_LOW] = self.frontRightRange & 255
    self.device.controlTable[CONTROL_FRONT_RIGHT_RANGE_HIGH] = self.frontRightRange >> 8
    self.device.controlTable[CONTROL_LEFT_RANGE_LOW] = self.leftRange & 255
    self.device.controlTable[CONTROL_LEFT_RANGE_HIGH] = self.leftRange >> 8
    self.device.controlTable[CONTROL_RIGHT_RANGE_LOW] = self.rightRange & 255
    self.device.controlTable[CONTROL_RIGHT_RANGE_HIGH] = self.rightRange >> 8
    # Because all the following values can be negative, we'll use struct to pack them
    struct.pack_into('h', self.word_buffer, 0, int(round(self.pitch)))
    self.device.controlTable[CONTROL_IMU_PITCH_LOW] = self.word_buffer[0]
    self.device.controlTable[CONTROL_IMU_PITCH_HIGH] = self.word_buffer[1]
    struct.pack_into('h', self.word_buffer, 0, int(round(self.roll)))
    self.device.controlTable[CONTROL_IMU_ROLL_LOW] = self.word_buffer[0]
    self.device.controlTable[CONTROL_IMU_ROLL_HIGH] = self.word_buffer[1]
    struct.pack_into('h', self.word_buffer, 0, int(round(self.yaw)))
    self.device.controlTable[CONTROL_IMU_YAW_LOW] = self.word_buffer[0]
    self.device.controlTable[CONTROL_IMU_YAW_HIGH] = self.word_buffer[1]
    struct.pack_into('h', self.word_buffer, 0, int(self.flow_x))
    self.device.controlTable[CONTROL_FLOW_X_LOW] = self.word_buffer[0]
    self.device.controlTable[CONTROL_FLOW_X_HIGH] = self.word_buffer[1]
    struct.pack_into('h', self.word_buffer, 0, int(self.flow_y))
    self.device.controlTable[CONTROL_FLOW_Y_LOW] = self.word_buffer[0]
    self.device.controlTable[CONTROL_FLOW_Y_HIGH] = self.word_buffer[1]

  def initializeRangeSensors(self):
    shutdown_left_pin = pyb.Pin(HEAD_SHUTDOWN_LEFT, pyb.Pin.OUT_PP)
    shutdown_front_left_pin = pyb.Pin(HEAD_SHUTDOWN_FRONT_LEFT, pyb.Pin.OUT_PP)
    shutdown_front_pin = pyb.Pin(HEAD_SHUTDOWN_FRONT, pyb.Pin.OUT_PP)
    shutdown_front_right_pin = pyb.Pin(HEAD_SHUTDOWN_FRONT_RIGHT, pyb.Pin.OUT_PP)
    shutdown_right_pin = pyb.Pin(HEAD_SHUTDOWN_RIGHT, pyb.Pin.OUT_PP)
    # Shut down all the sensors
    shutdown_left_pin.value(0)
    shutdown_front_left_pin.value(0)
    shutdown_front_right_pin.value(0)
    shutdown_right_pin.value(0)
    shutdown_front_pin.value(0)
    pyb.delay(100)

    shutdown_front_pin.value(1)
    pyb.delay(50)
    self.front_lidar = VL53L1X(address=HEAD_RANGE_DEFAULT_ADDRESS, i2c_driver=self.i2c)
    self.front_lidar.sensor_init()
    pyb.delay(10)
    self.front_lidar.set_i2c_address(HEAD_RANGE_FRONT_ADDRESS)
    pyb.delay(10)
    shutdown_front_left_pin.value(1)
    pyb.delay(10)
    self.front_left_lidar = VL53L1X(address=HEAD_RANGE_DEFAULT_ADDRESS, i2c_driver=self.i2c)
    self.front_left_lidar.sensor_init()
    pyb.delay(10)
    self.front_left_lidar.set_i2c_address(HEAD_RANGE_FRONT_LEFT_ADDRESS)
    pyb.delay(10)
    shutdown_front_right_pin.value(1)
    pyb.delay(10)
    self.front_right_lidar = VL53L1X(address=HEAD_RANGE_DEFAULT_ADDRESS, i2c_driver=self.i2c)
    self.front_right_lidar.sensor_init()
    pyb.delay(10)
    self.front_right_lidar.set_i2c_address(HEAD_RANGE_FRONT_RIGHT_ADDRESS)
    pyb.delay(10)
    shutdown_left_pin.value(1)
    pyb.delay(10)
    self.left_lidar = VL53L1X(address=HEAD_RANGE_DEFAULT_ADDRESS, i2c_driver=self.i2c)
    self.left_lidar.sensor_init()
    pyb.delay(10)
    self.left_lidar.set_i2c_address(HEAD_RANGE_LEFT_ADDRESS)
    pyb.delay(10)
    shutdown_right_pin.value(1)
    pyb.delay(10)
    self.right_lidar = VL53L1X(address=HEAD_RANGE_DEFAULT_ADDRESS, i2c_driver=self.i2c)
    self.right_lidar.sensor_init()
    pyb.delay(10)
    self.right_lidar.set_i2c_address(HEAD_RANGE_RIGHT_ADDRESS)
    pyb.delay(10)
    for lidar in [self.front_lidar, self.front_left_lidar, self.front_right_lidar, self.left_lidar, self.right_lidar]:
      lidar.set_distance_mode(1)
      lidar.set_inter_measurement_in_ms(20)
      lidar.set_timing_budget_in_ms(15)
      lidar.start_ranging()

  def initializeImuSensor(self):
    self.em7180 = EM7180_Master(HEAD_IMU_MAG_RATE, HEAD_IMU_ACCEL_RATE, HEAD_IMU_GYRO_RATE, 
                                HEAD_IMU_BARO_RATE, HEAD_IMU_Q_RATE_DIVISOR)
    if not self.em7180.begin(HEAD_I2C_BUS):
        print('IMU initialization failed {}'.format(self.em7180.getErrorString()))
        self.em7180 = None

  def initializeFlowSensor(self):
    self.flow = PMW3901(spi_port=HEAD_SPI_BUS, spi_cs_gpio=HEAD_SPI_CS)

  def updateSensors(self):
    self.frontRange = self.front_lidar.get_distance()
    self.frontLeftRange = self.front_left_lidar.get_distance()
    self.frontRightRange = self.front_right_lidar.get_distance()
    self.leftRange = self.left_lidar.get_distance()
    self.rightRange = self.right_lidar.get_distance()
    x, y = self.flow.get_motion()
    self.flow_x += x
    self.flow_y += y
    if self.em7180 is not None:
      self.em7180.checkEventStatus()
      if self.em7180.gotError():
        print('IMU ERROR: {}'.format(self.em7180.getErrorString()))
      else:
        if (self.em7180.gotQuaternion()):
          qw, qx, qy, qz = self.em7180.readQuaternion()
          self.roll = math.atan2(2.0 * (qw * qx + qy * qz), qw * qw - qx * qx - qy * qy + qz * qz)
          self.pitch = -math.asin(2.0 * (qx * qz - qw * qy))
          self.yaw = math.atan2(2.0 * (qx * qy + qw * qz), qw * qw + qx * qx - qy * qy - qz * qz)   
          self.pitch *= 180.0 / math.pi
          self.roll *= 180.0 / math.pi
          self.yaw *= 180.0 / math.pi 
          self.yaw -= 9.65 # Declination at Kitchener, Ontario is -9.65 degrees on 2019-02-21
          if self.yaw < 0:
            self.yaw += 360.0  # Ensure yaw stays between 0 and 360
        else:
          print('IMU - no quaternion')
    else:
      pass
      # print('IMU not initialized')


#=============================================


print("BIOLOID_HEAD")
head = HeadBoard()
try:
  head.run()
except Exception as e:
  sys.print_exception(e)
