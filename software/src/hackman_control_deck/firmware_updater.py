from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QThread, QTimer, Signal, Slot
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

from .constants import ASSET_DIR


@dataclass(frozen=True, slots=True)
class FirmwareTarget:
    model_identifier: str
    display_name: str
    version: str
    key_count: int
    potentiometer_count: int
    architecture: str = "avr"

    @property
    def filename(self) -> str:
        extension = "bin" if self.architecture == "esp32s3" else "hex"
        return f"HackMan3DControlDeck-{self.model_identifier}-{self.version}.{extension}"

FIRMWARE_TARGETS = {
    "HCD-BASE": FirmwareTarget("HCD-BASE", "HCD-BASE", "1.7.1", 9, 0),
    "HCD-PLUS": FirmwareTarget("HCD-PLUS", "HCD Plus", "1.1.2", 12, 2),
    "HCD-PRO": FirmwareTarget(
        "HCD-PRO",
        "HCD Pro",
        "1.3.6",
        28,
        0,
        "esp32s3",
    ),
}
BUNDLED_MODEL_IDENTIFIER = "HCD-BASE"
BUNDLED_FIRMWARE_VERSION = FIRMWARE_TARGETS[BUNDLED_MODEL_IDENTIFIER].version


def firmware_target(model_identifier: str) -> FirmwareTarget | None:
    if model_identifier == "HCD-LEGACY":
        return FIRMWARE_TARGETS[BUNDLED_MODEL_IDENTIFIER]
    return FIRMWARE_TARGETS.get(model_identifier)


def firmware_version_tuple(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


def firmware_update_available(
    installed_version: str,
    model_identifier: str = BUNDLED_MODEL_IDENTIFIER,
) -> bool:
    target = firmware_target(model_identifier)
    return bool(
        target
        and firmware_version_tuple(installed_version)
        < firmware_version_tuple(target.version)
    )


class FirmwareUpdater(QObject):
    status_changed = Signal(str)
    progress_changed = Signal(int)
    log_changed = Signal(str)
    finished = Signal(bool, str)
    esp32_bootloader_required = Signal()

    _POLL_INTERVAL_MS = 80
    _BOOTLOADER_TIMEOUT_TICKS = 150

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self._POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_bootloader)

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._read_process_output)
        self._process.finished.connect(self._process_finished)
        self._process.errorOccurred.connect(self._process_error)

        self._busy = False
        self._original_port = ""
        self._baseline_ports: set[str] = set()
        self._saw_original_disappear = False
        self._poll_ticks = 0
        self._output = ""
        self._attempt_output = ""
        self._attempt_count = 0
        self._bootloader_port = ""
        self._allow_existing_bootloader = False
        self._target = FIRMWARE_TARGETS[BUNDLED_MODEL_IDENTIFIER]
        self._esp32_manual_retry_pending = False
        self._displayed_progress = 0

    @property
    def is_busy(self) -> bool:
        return self._busy

    def start(
        self,
        port_name: str,
        model_identifier: str = BUNDLED_MODEL_IDENTIFIER,
        allow_existing_bootloader: bool = False,
    ) -> None:
        if self._busy:
            return
        if sys.platform not in {"darwin", "win32"}:
            self.finished.emit(False, "Firmware installation is not available here yet.")
            return
        if not port_name:
            self.finished.emit(False, "No serial port was selected.")
            return
        target = firmware_target(model_identifier)
        if target is None:
            self.finished.emit(False, f"Unsupported hardware model: {model_identifier}")
            return
        self._target = target

        self._displayed_progress = 0

        if target.architecture == "esp32s3":
            self._start_esp32_install(port_name)
            return

        executable, configuration, firmware = self.resource_paths(model_identifier)
        missing = [
            path.name for path in (executable, configuration, firmware) if not path.is_file()
        ]
        if missing:
            self.finished.emit(False, f"Missing firmware resource: {', '.join(missing)}")
            return

        self._busy = True
        self._original_port = port_name
        self._baseline_ports = {info.portName() for info in QSerialPortInfo.availablePorts()}
        self._saw_original_disappear = False
        self._poll_ticks = 0
        self._output = ""
        self._attempt_output = ""
        self._attempt_count = 0
        self._bootloader_port = ""
        self._allow_existing_bootloader = allow_existing_bootloader
        self.log_changed.emit("")
        self.progress_changed.emit(5)
        self.status_changed.emit("Restarting the controller in bootloader mode…")

        if not self._touch_1200_baud(port_name):
            self._fail(f"Could not open {port_name} at 1200 baud.")
            return
        self.progress_changed.emit(15)
        self._poll_timer.start()

    @staticmethod
    def resource_paths(
        model_identifier: str = BUNDLED_MODEL_IDENTIFIER,
    ) -> tuple[Path, Path, Path]:
        target = firmware_target(model_identifier)
        if target is None:
            raise ValueError(f"Unsupported hardware model: {model_identifier}")
        platform_directory = "windows" if sys.platform == "win32" else "macos"
        executable_name = "avrdude.exe" if sys.platform == "win32" else "avrdude"
        tool_directory = ASSET_DIR / "tools" / platform_directory
        return (
            tool_directory / executable_name,
            tool_directory / "avrdude.conf",
            ASSET_DIR / "firmware" / target.filename,
        )

    @staticmethod
    def esp32_resource_paths(model_identifier: str = "HCD-PRO") -> tuple[Path, Path]:
        target = firmware_target(model_identifier)
        if target is None or target.architecture != "esp32s3":
            raise ValueError(f"Unsupported ESP32 model: {model_identifier}")
        platform_directory = "windows" if sys.platform == "win32" else "macos"
        executable_name = "esptool.exe" if sys.platform == "win32" else "esptool"
        return (
            ASSET_DIR / "tools" / platform_directory / executable_name,
            ASSET_DIR / "firmware" / target.filename,
        )

    @staticmethod
    def esptool_arguments(
        port: str,
        firmware: Path,
        manual_bootloader: bool = False,
    ) -> list[str]:
        return [
            "--chip",
            "esp32s3",
            "--port",
            port,
            "--baud",
            "460800",
            "--before",
            "no-reset" if manual_bootloader else "default-reset",
            "--after",
            "hard-reset",
            "write-flash",
            "--flash-mode",
            "dio",
            "--flash-freq",
            "80m",
            "--flash-size",
            "8MB",
            "0x0",
            str(firmware),
        ]

    def _start_esp32_install(self, port_name: str) -> None:
        executable, firmware = self.esp32_resource_paths(self._target.model_identifier)
        missing = [path.name for path in (executable, firmware) if not path.is_file()]
        if missing:
            self.finished.emit(False, f"Missing firmware resource: {', '.join(missing)}")
            return
        self._busy = True
        self._original_port = self._serial_location(port_name)
        self._output = ""
        self._attempt_output = ""
        self._attempt_count = 1
        self._esp32_manual_retry_pending = False
        self.log_changed.emit("")
        self.progress_changed.emit(10)
        self._displayed_progress = 10
        self.status_changed.emit("Uploading the HCD Pro firmware to the ESP32-S3…")
        self._process.setProgram(str(executable))
        self._process.setArguments(
            self.esptool_arguments(self._original_port, firmware)
        )
        self._process.start()

    @Slot()
    def resume_esp32_install(self) -> None:
        """Continue after the user has placed the ESP32-S3 in download mode."""
        if not self._busy or not self._esp32_manual_retry_pending:
            return
        executable, firmware = self.esp32_resource_paths(self._target.model_identifier)
        port = self._current_esp32_port() or self._original_port
        self._esp32_manual_retry_pending = False
        self._attempt_count += 1
        self._attempt_output = ""
        self.progress_changed.emit(10)
        self._displayed_progress = max(self._displayed_progress, 10)
        self.status_changed.emit("Bootloader ready. Installing HCD Pro firmware…")
        self._process.setProgram(str(executable))
        self._process.setArguments(
            self.esptool_arguments(port, firmware, manual_bootloader=True)
        )
        self._process.start()

    @Slot()
    def cancel(self) -> None:
        if self._busy:
            self._fail("Firmware installation cancelled.")

    def _current_esp32_port(self) -> str:
        preferred_name = Path(self._original_port).name
        candidates: list[tuple[int, str]] = []
        for info in QSerialPortInfo.availablePorts():
            vendor = info.vendorIdentifier() if info.hasVendorIdentifier() else 0
            product = info.productIdentifier() if info.hasProductIdentifier() else 0
            identity = " ".join(
                (info.portName(), info.description(), info.manufacturer())
            ).casefold()
            is_esp32 = (
                vendor == 0x303A
                or (vendor, product) == (0x1A86, 0x55D3)
                or "esp32" in identity
                or "espressif" in identity
                or "usb single serial" in identity
            )
            if not is_esp32:
                continue
            location = info.systemLocation() or info.portName()
            rank = 0 if info.portName() == preferred_name else 1
            candidates.append((rank, location))
        return min(candidates, default=(99, ""))[1]

    @staticmethod
    def _serial_location(port_name: str) -> str:
        if sys.platform == "darwin" and not port_name.startswith("/dev/"):
            return f"/dev/{port_name}"
        return port_name

    @staticmethod
    def avrdude_arguments(port: str, configuration: Path, firmware: Path) -> list[str]:
        return [
            f"-C{configuration}",
            "-v",
            "-patmega32u4",
            "-cavr109",
            f"-P{port}",
            "-b57600",
            "-D",
            f"-Uflash:w:{firmware}:i",
        ]

    @staticmethod
    def _touch_1200_baud(port_name: str) -> bool:
        if sys.platform == "darwin":
            return FirmwareUpdater._touch_macos_1200_baud(port_name)
        if sys.platform == "win32":
            return FirmwareUpdater._touch_windows_1200_baud(port_name)

        serial = QSerialPort()
        serial.setPortName(port_name)
        serial.setBaudRate(1200)
        if not serial.open(QSerialPort.ReadWrite):
            return False
        serial.setDataTerminalReady(True)
        QThread.msleep(40)
        serial.setDataTerminalReady(False)
        QThread.msleep(40)
        serial.close()
        return True

    @staticmethod
    def _touch_windows_1200_baud(port_name: str) -> bool:
        # QtSerialPort can open the Leonardo CDC port on Windows without
        # causing the 1200-baud touch reset. pySerial performs the same native
        # DTR/close sequence as Arduino's uploader and reliably exposes the
        # Caterina bootloader on a new COM port.
        try:
            import serial

            port = serial.Serial(port_name, 1200, timeout=0)
            port.dtr = False
            QThread.msleep(100)
            port.close()
            return True
        except (OSError, serial.SerialException):
            return False

    @staticmethod
    def _touch_macos_1200_baud(port_name: str) -> bool:
        # The Arduino USB core enters Caterina when a CDC port opened at 1200
        # baud is closed. Use the native serial API so macOS performs the same
        # open/configure/close sequence as Arduino's uploader.
        import array
        import fcntl
        import os
        import termios

        location = port_name if port_name.startswith("/dev/") else f"/dev/{port_name}"
        descriptor = -1
        try:
            descriptor = os.open(location, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            attributes = termios.tcgetattr(descriptor)
            attributes[4] = termios.B1200
            attributes[5] = termios.B1200
            termios.tcsetattr(descriptor, termios.TCSANOW, attributes)
            dtr = array.array("i", [termios.TIOCM_DTR])
            fcntl.ioctl(descriptor, termios.TIOCMBIS, dtr, True)
            return True
        except OSError:
            return False
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @Slot()
    def _poll_bootloader(self) -> None:
        self._poll_ticks += 1
        infos = list(QSerialPortInfo.availablePorts())
        names = {info.portName() for info in infos}
        if self._original_port not in names:
            self._saw_original_disappear = True

        if self._saw_original_disappear or (
            self._allow_existing_bootloader and self._poll_ticks >= 4
        ):
            candidate = self._select_bootloader_port(infos)
            if candidate:
                self._poll_timer.stop()
                self._bootloader_port = candidate
                self.status_changed.emit(
                    f"Bootloader detected on {candidate}. Preparing the upload…"
                )
                QTimer.singleShot(300, lambda: self._start_avrdude(candidate))
                return

        if self._poll_ticks >= self._BOOTLOADER_TIMEOUT_TICKS:
            self._fail(
                "The automatic USB restart did not expose a bootloader port. Close Arduino IDE "
                "and other serial applications, reconnect the controller, then try again."
            )

    def _select_bootloader_port(self, infos: list[QSerialPortInfo]) -> str:
        ranked: list[tuple[int, str]] = []
        for info in infos:
            name = info.portName()
            is_new = name not in self._baseline_ports
            is_returned_original = name == self._original_port
            if not (is_new or is_returned_original):
                continue

            identity = " ".join((name, info.description(), info.manufacturer())).casefold()
            if "bluetooth" in identity:
                continue
            location = info.systemLocation() or name
            # Clone bootloaders often expose an unknown VID/PID and a different
            # serial name. Any newly appeared non-Bluetooth port is therefore a
            # stronger candidate than the original application port returning.
            known_bootloader_pid = info.hasProductIdentifier() and info.productIdentifier() in {
                0x0036,  # Arduino Leonardo Caterina
                0x0037,  # Arduino Micro Caterina
                0x9205,  # SparkFun Pro Micro bootloader
                0x9206,  # SparkFun Pro Micro bootloader
            }
            looks_like_bootloader = known_bootloader_pid or any(
                marker in identity
                for marker in ("caterina", "bootloader")
            )
            # For "install on a new Arduino", the selected application port
            # already existed in the baseline. It is not a bootloader merely
            # because four poll ticks elapsed. Accept that same name only after
            # it disappeared/reappeared, or when USB explicitly identifies it
            # as a bootloader.
            if (
                is_returned_original
                and not self._saw_original_disappear
                and not looks_like_bootloader
            ):
                continue
            rank = 0 if is_new and known_bootloader_pid else 1 if is_new else 2
            ranked.append((rank, location))
        return min(ranked, default=(99, ""))[1]

    @staticmethod
    def is_compatible_port(info: QSerialPortInfo) -> bool:
        identity = " ".join((info.portName(), info.description(), info.manufacturer())).casefold()
        known_usb_id = info.hasVendorIdentifier() and info.vendorIdentifier() in {
            0x2341,
            0x2A03,
            0x1B4F,
        }
        looks_compatible = any(
            marker in identity
            for marker in (
                "usbmodem",
                "leonardo",
                "caterina",
                "32u4",
                "pro micro",
                "hackman control deck",
                "esp32",
                "espressif",
                "usb jtag",
            )
        )
        esp_usb_id = info.hasVendorIdentifier() and info.vendorIdentifier() == 0x303A
        return known_usb_id or esp_usb_id or looks_compatible

    def _start_avrdude(self, port: str) -> None:
        if not self._busy:
            return
        executable, configuration, firmware = self.resource_paths(
            self._target.model_identifier
        )
        self._attempt_count += 1
        self._attempt_output = ""
        self.progress_changed.emit(30)
        retry = " (retry)" if self._attempt_count > 1 else ""
        self.status_changed.emit(
            f"Uploading and verifying the {self._target.display_name} firmware "
            f"on {port}…{retry}"
        )
        self._process.setProgram(str(executable))
        self._process.setArguments(self.avrdude_arguments(port, configuration, firmware))
        self._process.start()

    @Slot()
    def _read_process_output(self) -> None:
        output = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._output += output
        self._attempt_output += output
        self.log_changed.emit(self._output)
        percentages = re.findall(r"(\d{1,3})\s*%", output)
        if percentages:
            percentage = min(100, int(percentages[-1]))
            mapped_progress = 30 + round(percentage * 0.65)
            self._displayed_progress = max(self._displayed_progress, mapped_progress)
            self.progress_changed.emit(self._displayed_progress)

    @Slot(int, QProcess.ExitStatus)
    def _process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if not self._busy:
            return
        # Drain output that may have arrived immediately before QProcess.finished.
        self._read_process_output()
        if self._target.architecture == "esp32s3":
            if exit_status == QProcess.NormalExit and exit_code == 0:
                self._finish_success()
                return
            if self._attempt_count == 1 and self._is_esp32_connection_failure(
                self._attempt_output
            ):
                self._esp32_manual_retry_pending = True
                self.progress_changed.emit(0)
                self.status_changed.emit(
                    "The automatic restart was not accepted. Follow the BOOT/RESET "
                    "instructions shown by the application."
                )
                self.esp32_bootloader_required.emit()
                return
            suffix = self._failure_summary(self._attempt_output, exit_code)
            self._fail(f"Firmware installation failed: {suffix}")
            return
        flash_verified = self._flash_was_verified(self._attempt_output)
        if exit_status == QProcess.NormalExit and (exit_code == 0 or flash_verified):
            self._finish_success()
            return
        if self._attempt_count < 2 and self._is_retryable_failure(self._attempt_output):
            self.progress_changed.emit(25)
            self.status_changed.emit(
                "The bootloader did not answer. Restarting it before retrying…"
            )
            QTimer.singleShot(350, self._prepare_avr_retry)
            return
        suffix = self._failure_summary(self._attempt_output, exit_code)
        self._fail(f"Firmware installation failed: {suffix}")

    @Slot()
    def _prepare_avr_retry(self) -> None:
        """Retry against a live Caterina port, never a stale COM name."""
        if not self._busy:
            return
        infos = list(QSerialPortInfo.availablePorts())
        locations = {
            (info.systemLocation() or info.portName()): info.portName()
            for info in infos
        }
        if self._bootloader_port in locations:
            self._start_avrdude(self._bootloader_port)
            return

        original = next(
            (
                info
                for info in infos
                if info.portName() == self._original_port
                or (info.systemLocation() or info.portName()) == self._original_port
            ),
            None,
        )
        if original is None:
            self._fail(
                "The controller disappeared before the retry. Reconnect it, close other "
                "serial applications, then try again."
            )
            return

        self._baseline_ports = {info.portName() for info in infos}
        self._original_port = original.portName()
        self._saw_original_disappear = False
        self._poll_ticks = 0
        self._bootloader_port = ""
        if not self._touch_1200_baud(self._original_port):
            self._fail(
                f"Could not reopen {self._original_port} to restart the bootloader."
            )
            return
        self._poll_timer.start()

    @staticmethod
    def _flash_was_verified(output: str) -> bool:
        normalized = output.casefold()
        verified = bool(re.search(r"\d+\s+bytes?\s+of\s+flash\s+verified", normalized))
        verification_failed = any(
            marker in normalized
            for marker in (
                "verification mismatch",
                "failed verification",
                "verification error",
            )
        )
        return verified and not verification_failed

    @staticmethod
    def _failure_summary(output: str, exit_code: int) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        useful_markers = (
            "error:",
            "fatal:",
            "failed",
            "can't open",
            "cannot open",
            "unable to open",
            "not responding",
            "not in sync",
            "timed out",
            "permission denied",
            "verification mismatch",
        )
        useful = [
            line
            for line in lines
            if any(marker in line.casefold() for marker in useful_markers)
            and "done.  thank you." not in line.casefold()
        ]
        if useful:
            return useful[-1]
        return f"avrdude exited with code {exit_code}"

    @staticmethod
    def _is_retryable_failure(output: str) -> bool:
        normalized = output.casefold()
        return any(
            marker in normalized
            for marker in (
                "butterfly_recv",
                "programmer is not responding",
                "programmer did not respond",
                "not in sync",
            )
        )

    @staticmethod
    def _is_esp32_connection_failure(output: str) -> bool:
        normalized = output.casefold()
        return any(
            marker in normalized
            for marker in (
                "failed to connect",
                "no serial data received",
                "invalid head of packet",
                "wrong boot mode",
                "could not open",
                "port is busy",
            )
        )

    @Slot(QProcess.ProcessError)
    def _process_error(self, error: QProcess.ProcessError) -> None:
        if self._busy and error == QProcess.FailedToStart:
            self._fail("The bundled firmware installer could not be started.")

    def _fail(self, message: str) -> None:
        self._poll_timer.stop()
        if self._process.state() != QProcess.NotRunning:
            self._process.kill()
        self._busy = False
        self.status_changed.emit(message)
        self.finished.emit(False, message)

    def _finish_success(self) -> None:
        self._busy = False
        self.progress_changed.emit(100)
        self.status_changed.emit("Firmware installed. Waiting for the Control Deck…")
        self.finished.emit(
            True,
            f"{self._target.display_name} firmware "
            f"{self._target.version} was installed successfully.",
        )
