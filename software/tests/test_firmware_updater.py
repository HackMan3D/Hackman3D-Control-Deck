from pathlib import Path

from hackman_control_deck.firmware_updater import (
    BUNDLED_FIRMWARE_VERSION,
    BUNDLED_MODEL_IDENTIFIER,
    FIRMWARE_TARGETS,
    FirmwareUpdater,
    firmware_update_available,
)
from hackman_control_deck.firmware_dialog import FirmwareDialog


class PortInfo:
    def __init__(
        self,
        name: str,
        description: str,
        manufacturer: str = "",
        vendor_identifier: int | None = None,
        product_identifier: int | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._manufacturer = manufacturer
        self._vendor_identifier = vendor_identifier
        self._product_identifier = product_identifier

    def portName(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def manufacturer(self) -> str:
        return self._manufacturer

    def hasVendorIdentifier(self) -> bool:
        return self._vendor_identifier is not None

    def vendorIdentifier(self) -> int:
        return self._vendor_identifier or 0

    def hasProductIdentifier(self) -> bool:
        return self._product_identifier is not None

    def productIdentifier(self) -> int:
        return self._product_identifier or 0

    def systemLocation(self) -> str:
        return f"/dev/{self._name}"


def test_bundled_hcd_base_firmware_is_valid_intel_hex() -> None:
    _, _, firmware = FirmwareUpdater.resource_paths()

    content = firmware.read_text(encoding="ascii")
    assert BUNDLED_MODEL_IDENTIFIER == "HCD-BASE"
    assert BUNDLED_FIRMWARE_VERSION == "1.7.0"
    assert content.startswith(":")
    assert ":00000001FF" in content


def test_bundled_hcd_plus_firmware_is_valid_intel_hex() -> None:
    _, _, firmware = FirmwareUpdater.resource_paths("HCD-PLUS")

    content = firmware.read_text(encoding="ascii")
    assert FIRMWARE_TARGETS["HCD-PLUS"].version == "1.1.1"
    assert content.startswith(":")
    assert ":00000001FF" in content


def test_bundled_hcd_pro_firmware_is_a_complete_8mb_esp32_image() -> None:
    executable, firmware = FirmwareUpdater.esp32_resource_paths("HCD-PRO")

    assert FIRMWARE_TARGETS["HCD-PRO"].version == "1.2.45"
    assert executable.is_file()
    assert firmware.read_bytes()[:1] == b"\xE9"
    assert firmware.stat().st_size == 8 * 1024 * 1024


def test_esptool_arguments_target_the_esp32s3_full_flash_image() -> None:
    arguments = FirmwareUpdater.esptool_arguments(
        "/dev/cu.usbmodem101", Path("firmware.bin")
    )

    assert arguments[:2] == ["--chip", "esp32s3"]
    assert "460800" in arguments
    assert arguments[arguments.index("--before") + 1] == "default-reset"
    assert arguments[arguments.index("--flash-mode") + 1] == "dio"
    assert arguments[-2:] == ["0x0", "firmware.bin"]


def test_manual_esp32_flash_does_not_reset_the_bootloader() -> None:
    arguments = FirmwareUpdater.esptool_arguments(
        "/dev/cu.usbmodem101", Path("firmware.bin"), manual_bootloader=True
    )

    assert arguments[arguments.index("--before") + 1] == "no-reset"


def test_esp32_connection_failures_offer_manual_bootloader_retry() -> None:
    assert FirmwareUpdater._is_esp32_connection_failure(
        "A fatal error occurred: Failed to connect to ESP32-S3: No serial data received."
    )
    assert FirmwareUpdater._is_esp32_connection_failure(
        "Invalid head of packet (0x45): Possible serial noise or corruption"
    )
    assert not FirmwareUpdater._is_esp32_connection_failure("Hash of data verified.")


def test_esp32_usb_port_is_offered_for_firmware() -> None:
    assert FirmwareUpdater.is_compatible_port(
        PortInfo("cu.usbmodem1101", "ESP32-S3 USB JTAG", "Espressif", 0x303A)
    )


def test_waveshare_usb_bridge_suggests_hcd_pro() -> None:
    port = PortInfo(
        "cu.usbmodem5ABA0551801",
        "USB Single Serial",
        vendor_identifier=0x1A86,
        product_identifier=0x55D3,
    )

    assert FirmwareDialog._suggested_model_for_port(port) == "HCD-PRO"


def test_hcd_pro_ota_requires_transition_firmware() -> None:
    assert FirmwareDialog._PRO_OTA_MINIMUM_VERSION == (1, 2, 2)


def test_firmware_update_detection_compares_versions_numerically() -> None:
    assert firmware_update_available("1.3.9")
    assert not firmware_update_available(BUNDLED_FIRMWARE_VERSION)
    assert not firmware_update_available("1.10.0")
    assert firmware_update_available("0.9.0", "HCD-PLUS")
    assert not firmware_update_available("1.1.1", "HCD-PLUS")
    assert firmware_update_available("1.0.0", "HCD-PRO")
    assert firmware_update_available("1.0.1", "HCD-PRO")
    assert firmware_update_available("1.2.0", "HCD-PRO")
    assert firmware_update_available("1.2.1", "HCD-PRO")
    assert firmware_update_available("1.2.2", "HCD-PRO")
    assert firmware_update_available("1.2.3", "HCD-PRO")
    assert firmware_update_available("1.2.4", "HCD-PRO")
    assert firmware_update_available("1.2.5", "HCD-PRO")
    assert firmware_update_available("1.2.19", "HCD-PRO")
    assert firmware_update_available("1.2.33", "HCD-PRO")
    assert firmware_update_available("1.2.34", "HCD-PRO")
    assert firmware_update_available("1.2.35", "HCD-PRO")
    assert not firmware_update_available("1.2.45", "HCD-PRO")


def test_hcd_pro_ota_uses_application_image_and_wifi_address() -> None:
    firmware = FirmwareUpdater.esp32_ota_resource_path("HCD-PRO")

    assert firmware.name.endswith("-1.2.45-ota.bin")
    assert firmware.read_bytes()[:1] == b"\xE9"
    assert firmware.stat().st_size < 0x330000
    assert FirmwareUpdater._wifi_address("Wi-Fi · 192.168.1.42") == "192.168.1.42"
    assert FirmwareUpdater._wifi_address("cu.usbmodem101") == ""


def test_avrdude_arguments_target_caterina_atmega32u4() -> None:
    arguments = FirmwareUpdater.avrdude_arguments(
        "/dev/cu.usbmodem101", Path("avrdude.conf"), Path("firmware.hex")
    )

    assert "-patmega32u4" in arguments
    assert "-cavr109" in arguments
    assert "-b57600" in arguments
    assert "-P/dev/cu.usbmodem101" in arguments
    assert arguments[-1] == "-Uflash:w:firmware.hex:i"


def test_bootloader_selection_uses_new_compatible_usb_port() -> None:
    updater = FirmwareUpdater()
    updater._baseline_ports = {"cu.usbmodem101", "cu.Bluetooth-Incoming-Port"}
    updater._original_port = "cu.usbmodem101"
    ports = [
        PortInfo("cu.Bluetooth-Incoming-Port", "Bluetooth"),
        PortInfo("cu.usbmodem202", "Arduino Leonardo", "Arduino", 0x2341),
    ]

    assert updater._select_bootloader_port(ports) == "/dev/cu.usbmodem202"


def test_unknown_clone_bootloader_is_preferred_over_returned_application_port() -> None:
    updater = FirmwareUpdater()
    updater._baseline_ports = {"cu.usbmodem101"}
    updater._original_port = "cu.usbmodem101"
    ports = [
        PortInfo("cu.usbmodem101", "Arduino Leonardo", "Arduino", 0x2341, 0x8036),
        PortInfo("cu.usbserial-clone", "USB serial bootloader", "wch.cn", 0x1A86, 0x7523),
    ]

    assert updater._select_bootloader_port(ports) == "/dev/cu.usbserial-clone"


def test_existing_application_port_is_not_mistaken_for_bootloader() -> None:
    updater = FirmwareUpdater()
    updater._baseline_ports = {"COM8"}
    updater._original_port = "COM8"
    updater._saw_original_disappear = False
    ports = [
        PortInfo("COM8", "Arduino Leonardo", "Arduino", 0x2341, 0x8036),
    ]

    assert updater._select_bootloader_port(ports) == ""


def test_explicit_caterina_port_can_keep_same_name() -> None:
    updater = FirmwareUpdater()
    updater._baseline_ports = {"COM8"}
    updater._original_port = "COM8"
    updater._saw_original_disappear = False
    ports = [
        PortInfo("COM8", "Arduino Leonardo bootloader", "Arduino", 0x2341, 0x0036),
    ]

    assert updater._select_bootloader_port(ports).endswith("COM8")


def test_unrelated_serial_port_is_not_offered_for_firmware() -> None:
    assert not FirmwareUpdater.is_compatible_port(
        PortInfo("cu.Bluetooth-Incoming-Port", "Bluetooth")
    )


def test_windows_uses_bundled_executable(monkeypatch) -> None:
    monkeypatch.setattr("hackman_control_deck.firmware_updater.sys.platform", "win32")

    executable, configuration, firmware = FirmwareUpdater.resource_paths()

    assert executable.name == "avrdude.exe"
    assert executable.is_file()
    assert configuration.is_file()
    assert firmware.is_file()


def test_firmware_versions_are_compared_numerically() -> None:
    assert FirmwareDialog._version_tuple("1.10.0") > FirmwareDialog._version_tuple("1.9.9")


def test_verified_flash_is_successful_despite_bootloader_exit_error() -> None:
    output = """
    Reading | ################################################## | 100% 0.02 s
    5328 bytes of flash verified
    avrdude error: programmer did not respond to command: exit bootloader
    avrdude done.  Thank you.
    """

    assert FirmwareUpdater._flash_was_verified(output)


def test_verification_mismatch_is_never_successful() -> None:
    output = "5328 bytes of flash verified\navrdude error: verification mismatch"

    assert not FirmwareUpdater._flash_was_verified(output)


def test_failure_summary_ignores_generic_avrdude_goodbye() -> None:
    output = """
    avrdude error: programmer is not responding
    avrdude done.  Thank you.
    """

    assert FirmwareUpdater._failure_summary(output, 1) == (
        "avrdude error: programmer is not responding"
    )


def test_avr_retry_restarts_returned_application_port(monkeypatch) -> None:
    updater = FirmwareUpdater()
    updater._busy = True
    updater._original_port = "COM8"
    updater._bootloader_port = "COM9"
    updater._baseline_ports = {"COM8"}
    returned = PortInfo("COM8", "HackMan3D Control Deck", "HackMan3D", 0x2341)
    touched: list[str] = []

    monkeypatch.setattr(
        "hackman_control_deck.firmware_updater.QSerialPortInfo.availablePorts",
        lambda: [returned],
    )
    monkeypatch.setattr(
        FirmwareUpdater,
        "_touch_1200_baud",
        staticmethod(lambda port: touched.append(port) or True),
    )
    monkeypatch.setattr(updater._poll_timer, "start", lambda: touched.append("poll"))

    updater._prepare_avr_retry()

    assert touched == ["COM8", "poll"]
    assert updater._bootloader_port == ""


def test_1200_baud_touch_creates_dtr_falling_edge(monkeypatch) -> None:
    events: list[object] = []
    monkeypatch.setattr("hackman_control_deck.firmware_updater.sys.platform", "win32")

    class FakeSerial:
        ReadWrite = object()

        def setPortName(self, name: str) -> None:
            events.append(("port", name))

        def setBaudRate(self, baud_rate: int) -> None:
            events.append(("baud", baud_rate))

        def open(self, mode: object) -> bool:
            events.append(("open", mode))
            return True

        def setDataTerminalReady(self, enabled: bool) -> None:
            events.append(("dtr", enabled))

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("hackman_control_deck.firmware_updater.QSerialPort", FakeSerial)
    monkeypatch.setattr(
        "hackman_control_deck.firmware_updater.QThread.msleep",
        lambda delay: events.append(("wait", delay)),
    )

    assert FirmwareUpdater._touch_1200_baud("cu.usbmodem101")
    assert events[-5:] == [
        ("dtr", True),
        ("wait", 40),
        ("dtr", False),
        ("wait", 40),
        "close",
    ]


def test_macos_1200_baud_touch_uses_native_open_and_close(monkeypatch) -> None:
    import fcntl
    import os
    import termios

    events: list[object] = []
    attributes = [0, 0, 0, 0, 0, 0, []]
    monkeypatch.setattr(os, "open", lambda path, flags: events.append(("open", path)) or 42)
    monkeypatch.setattr(os, "close", lambda descriptor: events.append(("close", descriptor)))
    monkeypatch.setattr(termios, "tcgetattr", lambda descriptor: list(attributes))
    monkeypatch.setattr(
        termios,
        "tcsetattr",
        lambda descriptor, when, settings: events.append(("speed", settings[4], settings[5])),
    )
    monkeypatch.setattr(
        fcntl,
        "ioctl",
        lambda descriptor, operation, value, mutate: events.append(("dtr", descriptor)),
    )

    assert FirmwareUpdater._touch_macos_1200_baud("cu.usbmodem101")
    assert events == [
        ("open", "/dev/cu.usbmodem101"),
        ("speed", termios.B1200, termios.B1200),
        ("dtr", 42),
        ("close", 42),
    ]


def test_butterfly_receive_failure_can_be_retried() -> None:
    assert FirmwareUpdater._is_retryable_failure("avrdude error: butterfly_recv(pgm, &c, 1) failed")
    assert not FirmwareUpdater._is_retryable_failure("avrdude error: verification mismatch")
