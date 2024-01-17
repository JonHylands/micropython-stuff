
import pyb

#
# Class Packet
#
# Represents a serial instruction packet between the host and 
# the ammeter, sent over the USB connection.
# Can also parse itself from a bytearray.
#

class Packet:

  def __init__(self, logger=None):
    self.id = None
    self.length = None
    self.command = None
    self.parameters = [0 for i in range(250)]
    self.parameter_index = 0
    self.crc = None
    self.parameter_count = None
    self.state = self.state_idle
    self.callback = None
    self.log = False

  def register_callback(self, callback_function):
    self.callback = callback_function

  def process_bytes(self, data_bytes, size=None):
    if size is None:
      for byte in data_bytes:
        self.state(byte)
    else:
      for index in range(size):
        self.state(data_bytes[index])

  def process_byte(self, data_byte):
    self.state(data_byte)

  def reset_state(self):
    self.state = self.state_idle

  def state_idle(self, next_byte):
    if next_byte == 255:
      if self.log:
        print('state_idle({}) -> state_second_header'.format(next_byte))
      self.state = self.state_second_header

  def state_second_header(self, next_byte):
    if next_byte == 255:
      if self.log:
        print('state_second_header({}) -> state_id'.format(next_byte))
      self.state = self.state_id
    else:
      self.state = self.state_idle

  def state_id(self, next_byte):
    self.id = next_byte
    if self.log:
      print('state_id({}) -> state_length'.format(next_byte))
    self.state = self.state_length

  def state_length(self, next_byte):
    self.length = next_byte
    if self.log:
      print('state_length({}) -> state_command'.format(next_byte))
    self.parameter_count = self.length - 2
    self.state = self.state_command

  def state_command(self, next_byte):
    self.command = next_byte
    if self.parameter_count > 0:
      self.parameter_index = 0
      if self.log:
        print('state_command({}) -> state_parameters'.format(next_byte))
      self.state = self.state_parameters
    else:
      if self.log:
        print('state_command({}) -> state_crc'.format(next_byte))
      self.state = self.state_crc

  def state_parameters(self, next_byte):
    self.parameters[self.parameter_index] = next_byte
    self.parameter_index += 1
    if self.log:
      print('state_parameters({})'.format(next_byte))
    if self.parameter_index >= self.parameter_count:
      if self.log:
        print('state_parameters -> state_crc')
      self.state = self.state_crc

  def state_crc(self, next_byte):
    self.crc = next_byte
    if self.log:
      print('packet received - performing callback')
    self.callback(self)
    if self.log:
      print('state_crc({}) -> state_idle\n'.format(next_byte))
    self.state = self.state_idle
