from transport.serial_transport import SerialTransport
from protocol.frame_parser import FrameParser, Frame
from protocol.tlv_parser import parse_tlv
from enum import Enum

class CommandId(Enum):
  CMD_PING        = 0x01
  CMD_MODULE_INFO = 0x10
  CMD_GNSS_POWER  = 0x11
  CMD_GET_FIX     = 0x12

class DeviceClient:
  def __init__(self, transport: SerialTransport, parser: FrameParser):
    self.transport = transport
    self.parser = parser

  def ping(self):
    frame = Frame(0, CommandId.CMD_PING.value, 1)
    self.transport.send(self.parser.encode_frame(frame))

  def get_module_info(self):
    frame = Frame(0, CommandId.CMD_MODULE_INFO.value, 2)
    self.transport.send(self.parser.encode_frame(frame))

  def set_gnss_power(self, enabled: bool):
    data = b'\x02' if enabled else b'\x01'
    frame = Frame(0, CommandId.CMD_GNSS_POWER.value, 3, data)
    self.transport.send(self.parser.encode_frame(frame))

  def get_fix(self):
    frame = Frame(0, CommandId.CMD_GET_FIX.value, 4)
    self.transport.send(self.parser.encode_frame(frame))
