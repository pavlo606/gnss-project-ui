from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QTimer, Slot

from design import Ui_MainWindow
from transport.serial_transport import SerialTransport
from protocol.frame_parser import FrameParser, Frame
from protocol.tlv_parser import TlvFields, parse_tlv
from services.device_client import DeviceClient, CommandId
from datetime import datetime

fix_status_msg = {
  0x00: "Disabled",
  0x01: "No Fix",
  0x02: "Valid Fix",
}

status_msg = {
  0x00: "ACCEPTED",
  0x01: "SUCCESS",
  0x02: "FAILED",
  0x03: "BUSY",
  0x04: "INVALID"  
}

error_msg = {
  0x00: "NONE",
  0x01: "AT",
  0x02: "INVALID_ARG",
  0x03: "TIMEOUT",
  0x04: "PARSE",
  0x05: "GNSS_OFF",
  0x06: "NO_FIX",
  0x07: "BUFFER_OVERFLOW",
  0x08: "INTERNAL"
}

class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)

    self.transport = SerialTransport(self)
    self.parser = FrameParser()
    self.device_client = DeviceClient(self.transport, self.parser)

    self.get_fix_timer = QTimer(self)
    self.get_fix_timer.setInterval(1000)

    self._setup_ui()
    self._connect_signals()

  def _setup_ui(self):
    self.setWindowTitle("STM32 Device Test Tool")

    self.ui.comboBaudrate.clear()
    self.ui.comboBaudrate.addItems([
      "9600",
      "19200",
      "38400",
      "57600",
      "115200",
    ])
    self.ui.comboBaudrate.setCurrentText("115200")

    self.ui.resultFixStatus.setText("-")
    self.ui.resultUtc.setText("-")
    self.ui.resultLat.setText("-")
    self.ui.resultLon.setText("-")
    self.ui.resultAlt.setText("-")
    self.ui.resultSpeedCourse.setText("- / -")
    self.ui.resultSat.setText("- / -")
    self.ui.resultHdop.setText("-")

    self.ui.resultImei.setText("-")
    self.ui.resultFirmware.setText("-")
    self.ui.resultModel.setText("-")

    self.ui.labelPingStatus.setText("None")
    self.ui.labelModuleInfoStatus.setText("None")
    self.ui.labelGnssPowerStatus.setText("None")
    self.ui.labelGnssFixStatus.setText("None")

    self.ui.btnPing.setEnabled(False)
    self.ui.btnModuleInfo.setEnabled(False)
    self.ui.btnGnssOn.setEnabled(False)
    self.ui.btnGnssOff.setEnabled(False)
    self.ui.btnGetFix.setEnabled(False)
    self.ui.checkBoxAutoRequest.setEnabled(False)

    self.ui.textLog.setReadOnly(True)

    self._refresh_ports()

  def _connect_signals(self):
    self.ui.btnScan.clicked.connect(self._refresh_ports)
    self.ui.btnOpen.clicked.connect(self._toggle_connection)

    self.ui.btnPing.clicked.connect(self._on_ping)
    self.ui.btnModuleInfo.clicked.connect(self._on_get_module_info)
    self.ui.btnGnssOff.clicked.connect(lambda: self._on_set_gnss_power(False))
    self.ui.btnGnssOn.clicked.connect(lambda: self._on_set_gnss_power(True))
    self.ui.btnGetFix.clicked.connect(self._on_get_fix)
    self.ui.checkBoxAutoRequest.toggled.connect(self._on_checkbox_auto_request_toggle)

    self.transport.connection_changed.connect(self._on_connection_changed)
    self.transport.data_received.connect(self._on_data_received)
    self.transport.error_occurred.connect(self._on_error)
    
    self.get_fix_timer.timeout.connect(self._on_get_fix)

  @Slot()
  def _refresh_ports(self):
    selected_port = self.ui.comboPort.currentData()

    self.ui.comboPort.clear()

    for port in SerialTransport.available_ports():
      name = port["name"]
      description = port["description"]

      self.ui.comboPort.addItem(
        f"{name} — {description}",
        name,
      )

    index = self.ui.comboPort.findData(selected_port)

    if index >= 0:
      self.ui.comboPort.setCurrentIndex(index)

  @Slot()
  def _toggle_connection(self):
    if self.transport.is_connected:
      self.transport.disconnect_port()
      self.parser.reset()
      return

    port_name = self.ui.comboPort.currentData()

    if not port_name:
      self._append_log("No COM port selected")
      return

    baudrate = int(
      self.ui.comboBaudrate.currentText()
    )

    self.transport.connect_port(
      port_name,
      baudrate,
    )

  @Slot()
  def _on_connection_changed(self, connected: bool):
    if not connected:
        self.get_fix_timer.stop()
        self.ui.checkBoxAutoRequest.setChecked(False)

    self.ui.btnOpen.setText(
      "Disconnect" if connected else "Connect"
    )

    self.ui.comboPort.setEnabled(not connected)
    self.ui.comboBaudrate.setEnabled(not connected)
    self.ui.btnScan.setEnabled(not connected)

    self.ui.btnPing.setEnabled(connected)
    self.ui.btnModuleInfo.setEnabled(connected)
    self.ui.btnGnssOn.setEnabled(connected)
    self.ui.btnGnssOff.setEnabled(connected)
    self.ui.btnGetFix.setEnabled(connected)
    self.ui.checkBoxAutoRequest.setEnabled(connected)

    self._append_log(
      "Serial connected" if connected
      else "Serial disconnected"
    )

  @Slot()
  def _on_ping(self):
    if not self.transport.is_connected:
        self.get_fix_timer.stop()
        self.ui.checkBoxAutoRequest.setChecked(False)
        return
    self._append_log("PING requested")
    self.device_client.ping()

  @Slot()
  def _on_get_module_info(self):
    if not self.transport.is_connected:
        self.get_fix_timer.stop()
        self.ui.checkBoxAutoRequest.setChecked(False)
        return
    self._append_log("Module Info requested")
    self.device_client.get_module_info()

  @Slot()
  def _on_set_gnss_power(self, enabled: bool):
    if not self.transport.is_connected:
        self.get_fix_timer.stop()
        self.ui.checkBoxAutoRequest.setChecked(False)
        return
    self._append_log("Set GNSS power requested")
    self.device_client.set_gnss_power(enabled)

  @Slot()
  def _on_get_fix(self):
    if not self.transport.is_connected:
        self.get_fix_timer.stop()
        self.ui.checkBoxAutoRequest.setChecked(False)
        return
    self._append_log("Get Fix requested")
    self.device_client.get_fix()

  @Slot(bytes)
  def _on_data_received(self, data: bytes):
    frames = self.parser.feed(data)

    for frame in frames:
      status, error, tlv = parse_tlv(frame.data)
      
      self._append_log(
        f"RX frame - Status: {status_msg.get(status) or "UNKNOWN STATUS"} - Error: {error_msg.get(error) or "UNKNOWN ERROR"}\n"
        f"cmd = {frame.cmd}, "
        f"flags={frame.flags}, "
        f"seq={frame.seq}, "
        f"tlv={tlv}"
      )
      
      if frame.cmd == CommandId.CMD_PING.value:
        if status == 1 and error == 0:
          self.ui.labelPingStatus.setText("Success")
          self.ui.labelPingStatus.setStyleSheet(f'color: green;')
        elif status != 0:
          self.ui.labelPingStatus.setText("Error")
          self.ui.labelPingStatus.setStyleSheet(f'color: red;')

      if frame.cmd == CommandId.CMD_MODULE_INFO.value:
        if status == 1 and error == 0:
          self.ui.labelModuleInfoStatus.setText("Success")
          self.ui.labelModuleInfoStatus.setStyleSheet(f'color: green;')
          self._update_module_info(tlv)
        elif status != 0:
          self.ui.labelModuleInfoStatus.setText("Error")
          self.ui.labelModuleInfoStatus.setStyleSheet(f'color: red;')

      if frame.cmd == CommandId.CMD_GNSS_POWER.value:
        if status == 1 and error == 0:
          self.ui.labelGnssPowerStatus.setText("On" if tlv.gnss_run_status == 2 else "Off")
          self.ui.labelGnssPowerStatus.setStyleSheet(f'color: white;')
        elif status != 0:
          self.ui.labelGnssPowerStatus.setText("Error")
          self.ui.labelGnssPowerStatus.setStyleSheet(f'color: red;')

      if frame.cmd == CommandId.CMD_GET_FIX.value:
        if status == 1 and error == 0:
          self.ui.labelGnssPowerStatus.setText("Off" if tlv.gnss_fix_status == 0 else "On")
          self.ui.labelGnssPowerStatus.setStyleSheet(f'color: white;')
          self.ui.labelGnssFixStatus.setText("Success")
          self.ui.labelGnssFixStatus.setStyleSheet(f'color: green;')
          self._update_gnss_info(tlv)
        elif status != 0:
          self.ui.labelGnssFixStatus.setText("Error")
          self.ui.labelGnssFixStatus.setStyleSheet(f'color: red;')

  def _on_error(self, message: str):
    self._append_log(f"ERROR: {message}")

  def _append_log(self, message: str):
    timstamp = datetime.strftime(datetime.now(), "%H:%M:%S.%f")[:-3]
    self.ui.textLog.appendPlainText(f"  [{timstamp}] -> {message}")

  def _update_gnss_info(self, fields: TlvFields):
    self.ui.resultFixStatus.setText(fix_status_msg.get(fields.gnss_fix_status) or "-")
    self.ui.resultUtc.setText(fields.gnss_utc.isoformat(" ") if fields.gnss_utc is not None else "-")
    self.ui.resultLat.setText(f"{fields.gnss_lat:.6f}°" if fields.gnss_lat is not None else "-")
    self.ui.resultLon.setText(f"{fields.gnss_lon:.6f}°" if fields.gnss_lon is not None else "-")
    self.ui.resultAlt.setText(f"{fields.gnss_alt:.6f} m" if fields.gnss_alt is not None else "-")
    self.ui.resultSpeedCourse.setText(
      (f"{fields.gnss_speed:.1f} km/s" if fields.gnss_speed is not None else "-") + " / " + \
      (f"{fields.gnss_course:.1f}°" if fields.gnss_course is not None else "-"))
    self.ui.resultSat.setText(
      (f"{fields.gnss_sat_visible} visible" if fields.gnss_sat_visible is not None else "-") + " / " + \
      (f"{fields.gnss_sat_used} used" if fields.gnss_sat_used is not None else "-"))
    self.ui.resultHdop.setText(f"{fields.gnss_hdop:.2f}" if fields.gnss_hdop is not None else "-")

  def _update_module_info(self, fields: TlvFields):
    self.ui.resultImei.setText(fields.model_imei or "-")
    self.ui.resultFirmware.setText(fields.model_firmware or "-")
    self.ui.resultModel.setText(fields.model_model or "-")

  @Slot(bool)
  def _on_checkbox_auto_request_toggle(self, checked: bool):
    if checked and self.transport.is_connected:
        self.get_fix_timer.start()
    else:
        self.get_fix_timer.stop()

  def closeEvent(self, event):
    self.transport.close()
    super().closeEvent(event)
