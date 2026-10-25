from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import struct
import time

class TlvType(Enum):
  TYPE_MODULE_IMEI 	    = 0x01
  TYPE_MODULE_FIRMWARE  = 0x02
  TYPE_MODULE_MODEL 	  = 0x03
  TYPE_GNSS_RUN_STATUS  = 0x10
  TYPE_GNSS_FIXSTATUS   = 0x11
  TYPE_GNSS_UTC 		    = 0x12
  TYPE_GNSS_LAT 		    = 0x13
  TYPE_GNSS_LON 		    = 0x14
  TYPE_GNSS_ALT 		    = 0x15
  TYPE_GNSS_SPEED 	    = 0x16
  TYPE_GNSS_COURSE   	  = 0x17
  TYPE_GNSS_SAT_VISIBLE = 0x18
  TYPE_GNSS_SAT_USED 	  = 0x19
  TYPE_GNSS_HDOP		    = 0x1a

@dataclass
class TlvFields:
  model_imei: str = None
  model_firmware: str = None
  model_model: str = None
  gnss_run_status: int = None
  gnss_fix_status: int = None
  gnss_utc: datetime = None
  gnss_lat: float = None
  gnss_lon: float = None
  gnss_alt: float = None
  gnss_speed: float = None
  gnss_course: float = None
  gnss_sat_visible: int = None
  gnss_sat_used: int = None
  gnss_hdop: float = None
  
  def __str__(self):
    fields_str = list(filter(lambda attr: not attr.startswith("__"), dir(self)))
    total_str = []
    for field_str in fields_str:
      field = getattr(self, field_str)
      if field is not None:
        total_str.append(f"{field_str}={field}")
    return ", ".join(total_str)


def parse_tlv(data: bytes):
  fields = TlvFields()
  
  if len(data) < 2:
    return None, None, None
  
  status = int(data[0])
  error = int(data[1])

  i = 2
  
  while i < len(data):
    if len(data[i:]) < 2:
      break

    val_type: TlvType = data[i]
    i += 1
    val_len = data[i]
    i += 1
    
    if len(data[i:]) < val_len:
      break
    
    val = data[i:i + val_len]
    i += val_len
    
    if val_type not in TlvType:
      break

    match val_type:
      case TlvType.TYPE_MODULE_IMEI.value:
        fields.model_imei = val.decode("utf-8")
      case TlvType.TYPE_MODULE_FIRMWARE.value:
        fields.model_firmware = val.decode("utf-8")
      case TlvType.TYPE_MODULE_MODEL.value:
        fields.model_model = val.decode("utf-8")
      case TlvType.TYPE_GNSS_RUN_STATUS.value:
        fields.gnss_run_status = int.from_bytes(val, byteorder='little')
      case TlvType.TYPE_GNSS_FIXSTATUS.value:
        fields.gnss_fix_status = int.from_bytes(val, byteorder='little')
      case TlvType.TYPE_GNSS_UTC.value:
        fields.gnss_utc = datetime.strptime(val.decode("utf-8"), "%Y%m%d%H%M%S.%f")
      case TlvType.TYPE_GNSS_LAT.value:
        fields.gnss_lat = struct.unpack('f', val)[0]
      case TlvType.TYPE_GNSS_LON.value:
        fields.gnss_lon = struct.unpack('f', val)[0]
      case TlvType.TYPE_GNSS_ALT.value:
        fields.gnss_alt = struct.unpack('f', val)[0]
      case TlvType.TYPE_GNSS_SPEED.value:
        fields.gnss_speed = struct.unpack('f', val)[0]
      case TlvType.TYPE_GNSS_COURSE.value:
        fields.gnss_course = struct.unpack('f', val)[0]
      case TlvType.TYPE_GNSS_SAT_VISIBLE.value:
        fields.gnss_sat_visible = int.from_bytes(val, byteorder='little')
      case TlvType.TYPE_GNSS_SAT_USED.value:
        fields.gnss_sat_used = int.from_bytes(val, byteorder='little')
      case TlvType.TYPE_GNSS_HDOP.value:
        fields.gnss_hdop = struct.unpack('f', val)[0]
      case _:
        break
      
      # struct.error
  
  return status, error, fields
