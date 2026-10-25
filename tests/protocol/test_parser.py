from protocol.frame_parser import Frame, FrameParser, crc16, SOF


def test_encode_no_data():
  parser = FrameParser()
  frame = Frame(1, 2, 3)

  expected_header = b'\x03\x01\x02\x03'
  expected_crc = crc16(expected_header).to_bytes(2, 'little')
  expected_result = SOF + expected_header + expected_crc

  result = parser.encode_frame(frame)
  
  assert len(result) == len(expected_result)
  assert result == expected_result


def test_encode_with_data():
  parser = FrameParser()
  frame = Frame(1, 2, 3, b'\x01\x02')
  
  expected_header = b'\x05\x01\x02\x03'
  expected_data = b'\x01\x02'
  expected_crc = crc16(expected_header + expected_data).to_bytes(2, 'little')
  expected_result = SOF + expected_header + expected_data + expected_crc

  result = parser.encode_frame(frame)
  
  assert len(result) == len(expected_result)
  assert result == expected_result


def test_parse_complete_frame_no_data():
  parser = FrameParser()
  line = SOF + b'\x03\x01\x02\x03' + crc16(b'\x03\x01\x02\x03').to_bytes(2, 'little')
  
  result = parser.feed(line)
  
  assert len(result) == 1
  assert result[0].flags == 1
  assert result[0].cmd == 2
  assert result[0].seq == 3
  assert result[0].data == b''


def test_parse_complete_frame_with_data():
  parser = FrameParser()
  line = SOF + b'\x05\x01\x02\x03\x01\x02' + crc16(b'\x05\x01\x02\x03\x01\x02').to_bytes(2, 'little')
  
  result = parser.feed(line)
  
  assert len(result) == 1
  assert result[0].flags == 1
  assert result[0].cmd == 2
  assert result[0].seq == 3
  assert result[0].data == b'\x01\x02'


def test_parse_complete_frame_invalid_crc():
  parser = FrameParser()
  line = SOF + b'\x05\x01\x02\x03\x01\x02' + b'\xff\xff'
  
  result = parser.feed(line)
  
  assert len(result) == 0


def test_parse_frame_in_parts():
  parser = FrameParser()
  line = SOF + b'\x05\x01\x02\x03\x01\x02' + crc16(b'\x05\x01\x02\x03\x01\x02').to_bytes(2, 'little')
  
  assert parser.feed(line[:2]) == []
  assert parser.feed(line[2:5]) == []
  
  result = parser.feed(line[5:])
  
  assert len(result) == 1
  assert result[0].flags == 1
  assert result[0].cmd == 2
  assert result[0].seq == 3
  assert result[0].data == b'\x01\x02'


def test_parse_frame_in_parts():
  parser = FrameParser()
  line1 = SOF + b'\x05\x01\x02\x03\x01\x02' + crc16(b'\x05\x01\x02\x03\x01\x02').to_bytes(2, 'little')
  line2 = SOF + b'\x03\x01\x02\x03' + crc16(b'\x03\x01\x02\x03').to_bytes(2, 'little')
  
  result = parser.feed(line1 + line2)
  
  assert len(result) == 2