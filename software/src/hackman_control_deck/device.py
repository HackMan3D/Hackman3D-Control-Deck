from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

from .constants import (
    BAUD_RATE,
    CONNECTION_TIMEOUT_MS,
    HEARTBEAT_INTERVAL_MS,
    PORT_PROBE_TIMEOUT_MS,
    PORT_SCAN_INTERVAL_MS,
)
from .protocol import DeviceEvent, DeviceInfo, parse_line


class HcdDeviceManager(QObject):
    connection_changed = Signal(bool, str)
    status_changed = Signal(str)
    event_received = Signal(object)
    info_received = Signal(object)
    heartbeat_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._serial = QSerialPort(self)
        self._serial.setBaudRate(BAUD_RATE)
        self._serial.readyRead.connect(self._read_available)
        self._serial.errorOccurred.connect(self._handle_error)

        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(PORT_SCAN_INTERVAL_MS)
        self._scan_timer.timeout.connect(self._scan)

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(HEARTBEAT_INTERVAL_MS)
        self._heartbeat_timer.timeout.connect(self._heartbeat)

        self._probe_timer = QTimer(self)
        self._probe_timer.setSingleShot(True)
        self._probe_timer.setInterval(PORT_PROBE_TIMEOUT_MS)
        self._probe_timer.timeout.connect(self._probe_timed_out)

        self._buffer = bytearray()
        self._candidate_ports: list[str] = []
        self._candidate_index = 0
        self._connected = False
        self._last_pong = 0.0
        self._heartbeat_active = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def port_name(self) -> str:
        return self._serial.portName() if self._serial.isOpen() else ""

    def start(self) -> None:
        self._scan_timer.start()
        self._heartbeat_timer.start()
        self._scan()

    def stop(self) -> None:
        self._scan_timer.stop()
        self._heartbeat_timer.stop()
        self._close_port()

    def set_feedback_hold_ms(self, duration_ms: int) -> None:
        duration = max(0, min(2000, int(duration_ms)))
        self._write_line(f"HCD_SET_LED_HOLD|{duration}")

    @Slot()
    def _scan(self) -> None:
        if self._connected or self._serial.isOpen():
            return

        port_infos = sorted(QSerialPortInfo.availablePorts(), key=self._port_priority)
        ports = [port.portName() for port in port_infos]
        if ports != self._candidate_ports:
            self._candidate_ports = ports
            self._candidate_index = 0

        if not self._candidate_ports:
            self.status_changed.emit("Waiting for HackMan3D Control Deck")
            return

        if self._candidate_index >= len(self._candidate_ports):
            self._candidate_index = 0

        name = self._candidate_ports[self._candidate_index]
        self._candidate_index += 1
        self._try_port(name)

    def _try_port(self, name: str) -> None:
        self._serial.setPortName(name)
        if not self._serial.open(QSerialPort.ReadWrite):
            return
        self._serial.clear()
        self._buffer.clear()
        self._last_pong = time.monotonic()
        self.status_changed.emit(f"Checking {name}")
        self._write_line("HCD_PING")
        self._probe_timer.start()

    @staticmethod
    def _port_priority(port: QSerialPortInfo) -> int:
        identity = " ".join((port.portName(), port.description(), port.manufacturer())).casefold()
        if any(
            marker in identity
            for marker in ("usbmodem", "arduino", "leonardo", "pro micro", "atmega32u4")
        ):
            return 0
        if any(marker in identity for marker in ("usbserial", "wchusbserial", "sparkfun")):
            return 1
        return 2

    @Slot()
    def _probe_timed_out(self) -> None:
        if self._connected:
            return
        self._close_port()
        QTimer.singleShot(20, self._scan)

    @Slot()
    def _heartbeat(self) -> None:
        if not self._serial.isOpen():
            return

        now = time.monotonic()
        if (now - self._last_pong) * 1_000 > CONNECTION_TIMEOUT_MS:
            self._close_port()
            self.status_changed.emit("Device disconnected")
            QTimer.singleShot(100, self._scan)
            return
        self._write_line("HCD_PING")

    @Slot()
    def _read_available(self) -> None:
        self._buffer.extend(bytes(self._serial.readAll()))
        while b"\n" in self._buffer:
            raw_line, _, remainder = self._buffer.partition(b"\n")
            self._buffer = bytearray(remainder)
            line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
            message = parse_line(line)
            if message == "HCD_PONG":
                self._probe_timer.stop()
                self._last_pong = time.monotonic()
                if not self._heartbeat_active:
                    self._heartbeat_active = True
                    self.heartbeat_changed.emit(True)
                if not self._connected:
                    self._connected = True
                    self.connection_changed.emit(True, self._serial.portName())
                    self.status_changed.emit(f"Connected on {self._serial.portName()}")
                    self._write_line("HCD_GET_INFO")
            elif message == "HCD_READY":
                self._write_line("HCD_PING")
            elif isinstance(message, DeviceEvent):
                self.event_received.emit(message)
            elif isinstance(message, DeviceInfo):
                self.info_received.emit(message)

    def _write_line(self, text: str) -> None:
        if self._serial.isOpen():
            self._serial.write((text + "\n").encode("ascii"))

    @Slot(QSerialPort.SerialPortError)
    def _handle_error(self, error: QSerialPort.SerialPortError) -> None:
        if error in {QSerialPort.ResourceError, QSerialPort.DeviceNotFoundError}:
            self._close_port()

    def _close_port(self) -> None:
        self._probe_timer.stop()
        was_connected = self._connected
        self._connected = False
        if self._heartbeat_active:
            self._heartbeat_active = False
            self.heartbeat_changed.emit(False)
        self._buffer.clear()
        if self._serial.isOpen():
            self._serial.close()
        if was_connected:
            self.connection_changed.emit(False, "")
