from protocol.tlv_parser import parse_tlv

def test_tlv_parse():
  data = b'\x01\x00\x01\x02AT\x02\x04test'
  
  status, error, fields = parse_tlv(data)
  
  assert status == 1
  assert error == 0
  assert fields.model_imei == "AT"
  assert fields.model_firmware == "test"
