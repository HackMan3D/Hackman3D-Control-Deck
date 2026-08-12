from __future__ import annotations

import base64
from collections import deque
import time
import zlib

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtNetwork import (
    QAbstractSocket,
    QHostAddress,
    QHostInfo,
    QNetworkInterface,
    QTcpSocket,
    QUdpSocket,
)
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

from .constants import (
    BAUD_RATE,
    CONNECTION_TIMEOUT_MS,
    HCD_DISCOVERY_PORT,
    HCD_TCP_PORT,
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

        self._tcp = QTcpSocket(self)
        self._tcp.connected.connect(self._network_connected)
        self._tcp.readyRead.connect(self._read_network_available)
        self._tcp.disconnected.connect(self._network_disconnected)
        self._tcp.errorOccurred.connect(self._network_error)

        self._udp = QUdpSocket(self)
        self._udp.readyRead.connect(self._read_discovery_datagrams)
        self._udp.bind(
            QHostAddress.AnyIPv4,
            0,
            QUdpSocket.ShareAddress | QUdpSocket.ReuseAddressHint,
        )

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
        self._network_buffer = bytearray()
        self._candidate_ports: list[str] = []
        self._candidate_index = 0
        self._connected = False
        self._last_pong = 0.0
        self._heartbeat_active = False
        self._device_info_received = False
        self._transport = ""
        self._network_endpoint = ""
        self._network_candidate = ""
        self._running = False
        self._mdns_lookup_active = False
        self._last_mdns_lookup = 0.0
        self._pro_icon_signatures: dict[str, int | None] = {}
        self._pro_label_values: dict[str, str] = {}
        self._pro_display_state: tuple[int, bool, int, bool, int] | None = None
        self._pro_color_state: tuple[str, str, str, str, str] | None = None
        self._pro_upload_queue: deque[str] = deque()
        self._pro_upload_timer = QTimer(self)
        # Keep enough space between packets for the ESP32 display task. Large
        # theme changes can otherwise starve the RGB panel while it redraws.
        self._pro_upload_timer.setInterval(20)
        self._pro_upload_timer.timeout.connect(self._send_next_pro_upload)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def pro_sync_busy(self) -> bool:
        return self._pro_upload_timer.isActive() or bool(self._pro_upload_queue)

    @property
    def port_name(self) -> str:
        if self._transport == "wifi":
            return self._network_endpoint
        return self._serial.portName() if self._serial.isOpen() else ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._scan_timer.start()
        self._heartbeat_timer.start()
        self._scan()

    def stop(self) -> None:
        self._running = False
        self._scan_timer.stop()
        self._heartbeat_timer.stop()
        self._probe_timer.stop()
        self._close_connection()

    def set_feedback_hold_ms(self, duration_ms: int) -> None:
        duration = max(0, min(2000, int(duration_ms)))
        self._write_line(f"HCD_SET_LED_HOLD|{duration}")

    def set_pro_slider_value(self, value: int, slider_id: int = 1) -> None:
        if not self._connected or self._transport != "wifi":
            return
        normalized = max(0, min(100, int(value)))
        self._write_line(
            f"HCD_PRO_SLIDER_STATE|{max(1, min(2, int(slider_id)))}|"
            f"{round(normalized * 1023 / 100)}"
        )

    def arm_pro_ota(self, token: str) -> None:
        if not self._connected or self._transport != "wifi":
            return
        self._write_line(f"HCD_OTA_ARM|{token}")

    def set_pro_layout(
        self,
        labels: dict[str, str],
        icons: dict[str, bytes],
        icon_size: int = 1,
        show_labels: bool = False,
        theme: int = 1,
        second_fader: bool = False,
        slider_mode: str = "volume",
        colors: dict[str, str] | None = None,
    ) -> bool:
        if not self._connected or self._transport != "wifi":
            return False
        # A cache commit restarts the ESP32. Do not append or interleave a
        # second snapshot behind one already being transferred: the newest
        # state is sent after reconnect and the fresh HCD_INFO response.
        if self._pro_upload_timer.isActive() or self._pro_upload_queue:
            return False
        commands: deque[str] = deque()
        slider_mode_id = {"off": 0, "volume": 1, "brightness": 2}.get(slider_mode, 0)
        display_state = (
            max(0, min(3, icon_size)),
            False,
            max(0, min(2, theme)),
            bool(second_fader),
            slider_mode_id,
        )
        if display_state != self._pro_display_state:
            commands.append(
                f"HCD_PRO_DISPLAY|{display_state[0]}|{int(display_state[1])}|"
                f"{display_state[2]}|{int(display_state[3])}|{display_state[4]}"
            )
            self._pro_display_state = display_state
        if colors:
            values = [
                str(colors.get(name, fallback)).lstrip("#").upper()
                for name, fallback in (
                    ("screen", "080808"),
                    ("key", "171717"),
                    ("border", "404040"),
                    ("header", "FFFFFF"),
                    ("led", "F02020"),
                )
            ]
            color_state = tuple(values)
            if getattr(self, "_pro_color_state", None) != color_state:
                commands.append("HCD_PRO_COLORS|" + "|".join(values))
                self._pro_color_state = color_state
        for identifier in labels:
            if not identifier.isdigit():
                continue
            icon = icons.get(identifier, b"")
            signature = zlib.crc32(icon) if icon else None
            if (
                identifier in self._pro_icon_signatures
                and self._pro_icon_signatures[identifier] == signature
            ):
                continue
            if not icon:
                commands.append(f"HCD_PRO_ICON_CLEAR|{identifier}")
            else:
                commands.append(
                    f"HCD_PRO_ICON_BEGIN|{identifier}|{len(icon)}|{signature:08x}"
                )
                for offset in range(0, len(icon), 336):
                    chunk = base64.b64encode(icon[offset : offset + 336]).decode("ascii")
                    commands.append(f"HCD_PRO_ICON_CHUNK|{chunk}")
                commands.append(f"HCD_PRO_ICON_END|{identifier}")
            self._pro_icon_signatures[identifier] = signature
        if commands:
            commands.append("HCD_PRO_SYNC_END")
        if commands:
            commands.appendleft("HCD_PRO_SYNC_BEGIN")
            self._pro_upload_queue.extend(commands)
        if self._pro_upload_queue and not self._pro_upload_timer.isActive():
            self._pro_upload_timer.start()
        return True

    @Slot()
    def _send_next_pro_upload(self) -> None:
        if not self._connected or self._transport != "wifi":
            self._pro_upload_queue.clear()
            self._pro_upload_timer.stop()
            return
        if not self._pro_upload_queue:
            self._pro_upload_timer.stop()
            return
        # Do not let a slow ESP32 or Windows network stack accumulate an
        # unbounded write backlog. Heartbeats and the final SYNC_END command
        # must remain responsive during large icon transfers.
        if self._tcp.bytesToWrite() > 16_384:
            return
        self._write_line(self._pro_upload_queue.popleft())

    @Slot()
    def _scan(self) -> None:
        if not self._running:
            return
        self._send_discovery()
        self._start_mdns_lookup()
        if self._connected or self._serial.isOpen() or self._tcp.state() != QTcpSocket.UnconnectedState:
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
        self._transport = "serial"
        self._serial.setPortName(name)
        if not self._serial.open(QSerialPort.ReadWrite):
            return
        self._serial.clear()
        self._buffer.clear()
        self._last_pong = time.monotonic()
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
        if not self._running:
            return
        if self._connected:
            return
        self._close_connection()
        QTimer.singleShot(20, self._scan)

    @Slot()
    def _heartbeat(self) -> None:
        if not self._running:
            return
        if not self._transport_open():
            return

        now = time.monotonic()
        if (now - self._last_pong) * 1_000 > CONNECTION_TIMEOUT_MS:
            self._close_connection()
            self.status_changed.emit("Device disconnected")
            QTimer.singleShot(100, self._scan)
            return
        self._write_line("HCD_PING")
        # A lit connection LED proves PING/PONG works, but the first INFO reply
        # can still be lost while Windows finishes enumerating the CDC device.
        # Keep requesting identity until it has actually been parsed.
        if self._connected and not self._device_info_received:
            self._write_line("HCD_GET_INFO")

    @Slot()
    def _read_available(self) -> None:
        self._consume_data(bytes(self._serial.readAll()), self._buffer, "serial")

    @Slot()
    def _read_network_available(self) -> None:
        self._consume_data(bytes(self._tcp.readAll()), self._network_buffer, "wifi")

    def _consume_data(self, data: bytes, buffer: bytearray, transport: str) -> None:
        buffer.extend(data)
        while b"\n" in buffer:
            raw_line, _, remainder = buffer.partition(b"\n")
            buffer[:] = remainder
            line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
            message = parse_line(line)
            if message == "HCD_PONG":
                if transport != self._transport:
                    continue
                self._probe_timer.stop()
                self._last_pong = time.monotonic()
                if not self._heartbeat_active:
                    self._heartbeat_active = True
                    self.heartbeat_changed.emit(True)
                if not self._connected:
                    self._connected = True
                    endpoint = self.port_name
                    self.connection_changed.emit(True, endpoint)
                    self.status_changed.emit(f"Connected on {endpoint}")
                    # Recover a Pro whose previous Windows synchronization was
                    # interrupted after showing the display-update overlay.
                    # Other HCD models safely ignore this command.
                    self._write_line("HCD_PRO_SYNC_END")
                    self._write_line("HCD_GET_INFO")
            elif message == "HCD_READY":
                self._write_line("HCD_PING")
            elif isinstance(message, DeviceEvent):
                self.event_received.emit(message)
            elif isinstance(message, DeviceInfo):
                self._device_info_received = True
                if message.model_identifier == "HCD-PRO" and message.icon_signatures:
                    self._pro_icon_signatures = {
                        str(index): signature or None
                        for index, signature in enumerate(message.icon_signatures, start=1)
                    }
                self.info_received.emit(message)

    def _write_line(self, text: str) -> None:
        if self._transport == "wifi" and self._tcp.state() == QTcpSocket.ConnectedState:
            self._tcp.write((text + "\n").encode("ascii"))
        elif self._serial.isOpen():
            self._serial.write((text + "\n").encode("ascii"))

    def _transport_open(self) -> bool:
        if self._transport == "wifi":
            return self._tcp.state() == QTcpSocket.ConnectedState
        return self._serial.isOpen()

    def _send_discovery(self) -> None:
        if self._connected:
            return
        destinations: set[str] = set()
        required_flags = (
            QNetworkInterface.InterfaceFlag.IsUp
            | QNetworkInterface.InterfaceFlag.IsRunning
        )
        for interface in QNetworkInterface.allInterfaces():
            flags = interface.flags()
            if flags & required_flags != required_flags:
                continue
            if flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            for entry in interface.addressEntries():
                if (
                    entry.ip().protocol()
                    != QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
                ):
                    continue
                broadcast = entry.broadcast()
                address = broadcast.toString()
                if not broadcast.isNull() and address:
                    destinations.add(address)
        if not destinations:
            destinations.add(QHostAddress.Broadcast.toString())
        for address in destinations:
            self._udp.writeDatagram(
                b"HCD_DISCOVER\n",
                QHostAddress(address),
                HCD_DISCOVERY_PORT,
            )

    def _start_mdns_lookup(self) -> None:
        if self._connected or self._mdns_lookup_active:
            return
        now = time.monotonic()
        if now - self._last_mdns_lookup < 3.0:
            return
        self._last_mdns_lookup = now
        self._mdns_lookup_active = True
        QHostInfo.lookupHost("hcd-pro.local", self._mdns_resolved)

    @Slot(QHostInfo)
    def _mdns_resolved(self, host: QHostInfo) -> None:
        self._mdns_lookup_active = False
        if (
            not self._running
            or self._connected
            or self._tcp.state() != QTcpSocket.UnconnectedState
        ):
            return
        for address in host.addresses():
            if (
                address.protocol()
                == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
            ):
                self._try_network(address.toString(), HCD_TCP_PORT)
                return

    @Slot()
    def _read_discovery_datagrams(self) -> None:
        while self._udp.hasPendingDatagrams():
            datagram = self._udp.receiveDatagram()
            if not self._running:
                continue
            line = bytes(datagram.data()).decode("utf-8", errors="replace").strip()
            parts = line.split("|")
            if len(parts) != 7 or parts[0] != "HCD_HERE" or parts[2] != "HCD-PRO":
                continue
            try:
                tcp_port = int(parts[6])
            except ValueError:
                continue
            address = datagram.senderAddress().toString()
            if self._connected and self._transport == "wifi":
                continue
            self._try_network(address, tcp_port)

    def _try_network(self, address: str, port: int) -> None:
        if not self._running or self._tcp.state() != QTcpSocket.UnconnectedState:
            return
        if self._serial.isOpen() and not self._connected:
            self._serial.close()
            self._buffer.clear()
        self._transport = "wifi"
        self._network_candidate = address
        self._network_endpoint = f"Wi-Fi · {address}"
        self._last_pong = time.monotonic()
        self._tcp.connectToHost(address, port)

    @Slot()
    def _network_connected(self) -> None:
        if not self._running:
            self._tcp.abort()
            return
        self._network_buffer.clear()
        self._write_line("HCD_PING")
        self._probe_timer.start()

    @Slot()
    def _network_disconnected(self) -> None:
        if self._transport == "wifi":
            self._close_connection()
            if self._running:
                QTimer.singleShot(100, self._scan)

    @Slot(QAbstractSocket.SocketError)
    def _network_error(self, error: QAbstractSocket.SocketError) -> None:
        if error != QAbstractSocket.UnknownSocketError and self._transport == "wifi":
            self._close_connection()

    @Slot(QSerialPort.SerialPortError)
    def _handle_error(self, error: QSerialPort.SerialPortError) -> None:
        if self._transport == "serial" and error in {
            QSerialPort.ResourceError,
            QSerialPort.DeviceNotFoundError,
        }:
            self._close_connection()

    def _close_connection(self) -> None:
        self._probe_timer.stop()
        was_connected = self._connected
        self._connected = False
        self._device_info_received = False
        self._transport = ""
        if self._heartbeat_active:
            self._heartbeat_active = False
            self.heartbeat_changed.emit(False)
        self._buffer.clear()
        self._network_buffer.clear()
        if self._serial.isOpen():
            self._serial.close()
        if self._tcp.state() != QTcpSocket.UnconnectedState:
            self._tcp.abort()
        self._network_endpoint = ""
        self._network_candidate = ""
        self._pro_upload_timer.stop()
        self._pro_upload_queue.clear()
        self._pro_icon_signatures.clear()
        self._pro_label_values.clear()
        self._pro_display_state = None
        self._pro_color_state = None
        if was_connected:
            self.connection_changed.emit(False, "")
