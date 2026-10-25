from dataclasses import dataclass

SOF = b'\xA5\x5A'

HEADER_SIZE = 6
CRC_SIZE = 2

MAX_PAYLOAD_SIZE = 256

@dataclass(frozen=True)
class Frame:
  flags: int
  cmd: int
  seq: int
  data: bytes = b''

class FrameParser:
  def __init__(self):
    self._buffer = bytearray()

  def reset(self):
    self._buffer.clear()

  def encode_frame(self, frame: Frame) -> bytes:
    frame_bytes = int(len(frame.data) + 3).to_bytes(1, 'little') \
            + frame.flags.to_bytes(1, 'little') \
            + frame.cmd.to_bytes(1, 'little') \
            + frame.seq.to_bytes(1, 'little') \
            + frame.data

    crc = crc16(frame_bytes).to_bytes(2, 'little')
    
    return SOF + frame_bytes + crc

  def feed(self, data: bytes) -> list[Frame]:
    self._buffer.extend(data)
    frames = []

    while True:
      # Find the beginning of a frame.
      sof_index = self._buffer.find(SOF)

      if sof_index == -1:
        # Keep a possible first byte of a split SOF.
        keep = 1 if self._buffer.endswith(SOF[:1]) else 0
        if keep:
            self._buffer[:] = self._buffer[-1:]
        else:
            self._buffer.clear()
        break

      # Discard garbage before SOF.
      if sof_index > 0:
        del self._buffer[:sof_index]

      # Wait until the complete header is available.
      if len(self._buffer) <= HEADER_SIZE:
        break

      frame_len = self._buffer[2]
      flags = self._buffer[3]
      cmd = self._buffer[4]
      seq = self._buffer[5]

      frame_size = 3 + frame_len + CRC_SIZE

      # The frame may arrive in several chunks.
      if len(self._buffer) < frame_size:
        break

      payload_end = 3 + frame_len
      payload = bytes(self._buffer[HEADER_SIZE:payload_end])

      received_crc = int.from_bytes(
        self._buffer[payload_end:frame_size], "little"
      )

      crc_data = bytes(self._buffer[2:payload_end])
      calculated_crc = crc16(crc_data)

      if received_crc != calculated_crc:
        del self._buffer[0]
        continue

      frames.append(
        Frame(
          cmd=cmd,
          flags=flags,
          seq=seq,
          data=payload
        )
      )

      del self._buffer[:frame_size]

    return frames

def crc16(data: bytes) -> int:
  crc = 0xFFFF

  for byte in data:
    crc ^= byte << 8

    for _ in range(8):
      if crc & 0x8000:
        crc = ((crc << 1) ^ 0x1021) & 0xFFFF
      else:
        crc = (crc << 1) & 0xFFFF

  return crc