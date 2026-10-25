from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo


class SerialTransport(QObject):
  data_received = Signal(bytes)

  connection_changed = Signal(bool)

  error_occurred = Signal(str)

  bytes_written = Signal(int)

  MAX_TX_BUFFER = 64 * 1024

  def __init__(self, parent=None):
    super().__init__(parent)

    self._port = QSerialPort(self)

    self._port.readyRead.connect(self._on_ready_read)
    self._port.bytesWritten.connect(self._on_bytes_written)
    self._port.errorOccurred.connect(self._on_error)

  @staticmethod
  def available_ports() -> list[dict[str, str]]:
    result = []

    for info in QSerialPortInfo.availablePorts():
      result.append({
        "name": info.portName(),
        "description": info.description(),
      })

    return result

  @property
  def is_connected(self) -> bool:
    return self._port.isOpen()

  @property
  def port_name(self) -> str:
    return self._port.portName()

  def connect_port(
    self,
    port_name: str,
    baudrate: int = 115200,
  ) -> bool:
    if self._port.isOpen():
      self.disconnect_port()

    self._port.setPortName(port_name)
    self._port.setBaudRate(baudrate)
    self._port.setDataBits(QSerialPort.DataBits.Data8)
    self._port.setParity(QSerialPort.Parity.NoParity)
    self._port.setStopBits(QSerialPort.StopBits.OneStop)
    self._port.setFlowControl(
      QSerialPort.FlowControl.NoFlowControl
    )

    if not self._port.open(QSerialPort.OpenModeFlag.ReadWrite):
      self.error_occurred.emit(
        f"Cannot open {port_name}: "
        f"{self._port.errorString()}"
      )
      return False

    self._port.setReadBufferSize(64 * 1024)

    self._port.clear(
      QSerialPort.Direction.AllDirections
    )

    self.connection_changed.emit(True)
    return True

  @Slot()
  def disconnect_port(self) -> None:
    if not self._port.isOpen():
      return

    self._port.close()
    self.connection_changed.emit(False)

  @Slot(bytes)
  def send(self, data: bytes) -> bool:
    if not self._port.isOpen():
      self.error_occurred.emit(
        "Cannot send: serial port is not open"
      )
      return False

    if not data:
      return True

    if (
      self._port.bytesToWrite() + len(data)
      > self.MAX_TX_BUFFER
    ):
      self.error_occurred.emit(
        "TX buffer limit exceeded"
      )
      return False

    written = self._port.write(data)

    if written < 0:
      self.error_occurred.emit(
        f"Serial write failed: "
        f"{self._port.errorString()}"
      )
      return False

    if written != len(data):
      self.error_occurred.emit(
        f"Incomplete TX enqueue: "
        f"{written}/{len(data)} bytes"
      )
      return False

    return True

  @Slot()
  def _on_ready_read(self) -> None:
    data = bytes(self._port.readAll())

    if data:
      self.data_received.emit(bytes(data))

  @Slot(int)
  def _on_bytes_written(self, count: int) -> None:
    self.bytes_written.emit(count)

  @Slot(QSerialPort.SerialPortError)
  def _on_error(
    self,
    error: QSerialPort.SerialPortError,
  ) -> None:
    if error == QSerialPort.SerialPortError.NoError:
      return

    message = (
      f"Serial error on {self._port.portName()}: "
      f"{self._port.errorString()}"
    )
    self.error_occurred.emit(message)

    critical_errors = {
      QSerialPort.SerialPortError.ResourceError,
      QSerialPort.SerialPortError.DeviceNotFoundError,
      QSerialPort.SerialPortError.PermissionError,
      QSerialPort.SerialPortError.OpenError,
      QSerialPort.SerialPortError.NotOpenError,
    }

    if error in critical_errors and self._port.isOpen():
      self._port.close()
      self.connection_changed.emit(False)

  def close(self) -> None:
    self.disconnect_port()