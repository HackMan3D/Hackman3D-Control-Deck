from __future__ import annotations

from collections.abc import Callable
import re
import subprocess
import sys
import threading

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import COMPATIBLE_PRODUCT_NAMES
from .firmware_updater import (
    FIRMWARE_TARGETS,
    FirmwareUpdater,
    firmware_target,
)
from .protocol import DeviceInfo


class FirmwareDialog(QDialog):
    update_requested = Signal(str, str, str, str)
    install_requested = Signal(str, str, str, str)
    wifi_scan_finished = Signal(object, str)
    wifi_password_finished = Signal(str, str, str)
    _PRO_OTA_MINIMUM_VERSION = (1, 2, 2)

    def __init__(
        self,
        device_info: DeviceInfo | None,
        connected_port: str,
        text: Callable[..., str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._device_info = device_info
        self._connected_port = connected_port
        self._busy = False
        self._location_manager = None
        self.setWindowTitle(text("firmware_manager"))
        self.setMinimumWidth(560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel(text("firmware_manager"), objectName="title")
        layout.addWidget(title)
        self._summary = QLabel(text("firmware_manager_help"), objectName="subtitle")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        info_frame = QFrame(objectName="firmwareCard")
        info_frame.setMinimumHeight(142)
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 12)
        for row in range(4):
            info_layout.setRowMinimumHeight(row, 25)
        info_layout.addWidget(QLabel(text("detected_device")), 0, 0)
        self._detected_device_value = QLabel(
            device_info.product if device_info else text("no_hcd_detected")
        )
        info_layout.addWidget(self._detected_device_value, 0, 1)
        info_layout.addWidget(QLabel(text("hardware_model")), 1, 0)
        self._hardware_model_value = QLabel(
            device_info.model_identifier if device_info else "—"
        )
        info_layout.addWidget(self._hardware_model_value, 1, 1)
        info_layout.addWidget(QLabel(text("installed_firmware")), 2, 0)
        self._installed_firmware_value = QLabel(
            device_info.firmware_version if device_info else "—"
        )
        info_layout.addWidget(self._installed_firmware_value, 2, 1)
        detected_target = (
            firmware_target(device_info.model_identifier) if device_info else None
        )
        included_version = detected_target.version if detected_target else "—"
        info_layout.addWidget(QLabel(text("included_firmware")), 3, 0)
        self._included_firmware_value = QLabel(included_version)
        info_layout.addWidget(self._included_firmware_value, 3, 1)
        layout.addWidget(info_frame)

        update_row = QHBoxLayout()
        update_row.addStretch()
        update_label = (
            text("reinstall_connected_hcd")
            if device_info
            and detected_target
            and device_info.firmware_version == detected_target.version
            else text("update_connected_hcd")
        )
        self._update_button = QPushButton(update_label, objectName="accent")
        self._update_button.setEnabled(self._can_update_connected_device())
        self._update_button.clicked.connect(
            lambda: self.update_requested.emit(
                self._connected_update_port(),
                self._device_info.model_identifier if self._device_info else "",
                self._wifi_ssid.currentText().strip()
                if self._device_info and self._device_info.model_identifier == "HCD-PRO"
                else "",
                self._wifi_password.text()
                if self._device_info and self._device_info.model_identifier == "HCD-PRO"
                else "",
            )
        )
        update_row.addWidget(self._update_button)
        layout.addLayout(update_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        install_title = QLabel(text("install_new_arduino"), objectName="sectionTitle")
        layout.addWidget(install_title)
        install_help = QLabel(text("install_new_arduino_help"), objectName="subtitle")
        install_help.setWordWrap(True)
        layout.addWidget(install_help)

        model_row = QHBoxLayout()
        self._model_label = QLabel(text("firmware_model_to_install"))
        model_row.addWidget(self._model_label)
        self._model_combo = QComboBox()
        for target in FIRMWARE_TARGETS.values():
            details = text(
                "firmware_model_details",
                keys=target.key_count,
                pots=target.potentiometer_count,
            )
            development = (
                f" · {text('in_development')}"
                if target.model_identifier in {"HCD-PLUS", "HCD-PRO"}
                else ""
            )
            self._model_combo.addItem(
                f"{target.display_name}{development} — {details}",
                target.model_identifier,
            )
        if device_info is not None:
            detected_model_index = self._model_combo.findData(device_info.model_identifier)
            if detected_model_index >= 0:
                self._model_combo.setCurrentIndex(detected_model_index)
        self._model_combo.currentIndexChanged.connect(self._model_changed)
        model_row.addWidget(self._model_combo, 1)
        layout.addLayout(model_row)

        self._wifi_frame = QFrame(objectName="firmwareCard")
        wifi_layout = QGridLayout(self._wifi_frame)
        wifi_layout.addWidget(QLabel(text("wifi_network")), 0, 0)
        self._wifi_ssid = QComboBox()
        self._wifi_ssid.setEditable(True)
        self._wifi_ssid.setInsertPolicy(QComboBox.NoInsert)
        self._wifi_ssid.lineEdit().setPlaceholderText(text("wifi_network_placeholder"))
        self._wifi_ssid.currentTextChanged.connect(self._update_install_enabled)
        self._wifi_ssid.currentTextChanged.connect(self._start_wifi_password_lookup)
        wifi_layout.addWidget(self._wifi_ssid, 0, 1)
        self._wifi_refresh_button = QPushButton(text("refresh_wifi_networks"))
        self._wifi_refresh_button.clicked.connect(self._start_wifi_scan)
        wifi_layout.addWidget(self._wifi_refresh_button, 0, 2)
        wifi_layout.addWidget(QLabel(text("wifi_password")), 1, 0)
        self._wifi_password = QLineEdit()
        self._wifi_password.setEchoMode(QLineEdit.Password)
        wifi_layout.addWidget(self._wifi_password, 1, 1)
        wifi_help = QLabel(text("wifi_provisioning_help"), objectName="subtitle")
        wifi_help.setWordWrap(True)
        wifi_layout.addWidget(wifi_help, 2, 0, 1, 3)
        self._wifi_scan_status = QLabel(objectName="subtitle")
        self._wifi_scan_status.setWordWrap(True)
        wifi_layout.addWidget(self._wifi_scan_status, 3, 0, 1, 3)
        layout.addWidget(self._wifi_frame)
        self.wifi_scan_finished.connect(self._wifi_networks_received)
        self.wifi_password_finished.connect(self._wifi_password_received)

        port_row = QHBoxLayout()
        self._port_combo = QComboBox()
        self._port_combo.currentIndexChanged.connect(self._port_changed)
        port_row.addWidget(self._port_combo, 1)
        self._refresh_button = QPushButton(text("refresh_ports"))
        self._refresh_button.clicked.connect(self.refresh_ports)
        port_row.addWidget(self._refresh_button)
        layout.addLayout(port_row)

        self._install_button = QPushButton(text("install_firmware"))
        self._install_button.clicked.connect(self._request_install)
        layout.addWidget(self._install_button)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._progress_label = QLabel("0%", objectName="subtitle")
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._progress_label.setFixedWidth(48)
        self._progress_label.setVisible(False)
        progress_row = QHBoxLayout()
        progress_row.addWidget(self._progress, 1)
        progress_row.addWidget(self._progress_label)
        layout.addLayout(progress_row)
        self._status = QLabel(objectName="subtitle")
        self._status.setWordWrap(True)
        self._status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status)

        self._details_button = QPushButton(text("show_firmware_details"))
        self._details_button.setVisible(False)
        self._details_button.clicked.connect(self._toggle_details)
        layout.addWidget(self._details_button)
        self._details = QPlainTextEdit()
        self._details.setReadOnly(True)
        self._details.setMaximumHeight(150)
        self._details.setVisible(False)
        layout.addWidget(self._details)

        close_row = QHBoxLayout()
        close_row.addStretch()
        self._close_button = QPushButton(text("close"))
        self._close_button.clicked.connect(self.accept)
        close_row.addWidget(self._close_button)
        layout.addLayout(close_row)
        self.refresh_ports()
        self._model_changed()
        self._start_wifi_scan()

    def update_detected_device(
        self,
        device_info: DeviceInfo | None,
        connected_port: str,
    ) -> None:
        """Refresh a dialog that was opened before the controller connected."""
        self._device_info = device_info
        self._connected_port = connected_port
        target = firmware_target(device_info.model_identifier) if device_info else None
        self._detected_device_value.setText(
            device_info.product if device_info else self._text("no_hcd_detected")
        )
        self._hardware_model_value.setText(
            device_info.model_identifier if device_info else "—"
        )
        self._installed_firmware_value.setText(
            device_info.firmware_version if device_info else "—"
        )
        self._included_firmware_value.setText(target.version if target else "—")
        if device_info is not None:
            model_index = self._model_combo.findData(device_info.model_identifier)
            if model_index >= 0:
                self._model_combo.setCurrentIndex(model_index)
        self.refresh_ports()
        self._update_button.setEnabled(not self._busy and self._can_update_connected_device())

    def _can_update_connected_device(self) -> bool:
        if self._device_info is None or not self._connected_port:
            return False
        target = firmware_target(self._device_info.model_identifier)
        compatible_product = self._device_info.product.startswith(COMPATIBLE_PRODUCT_NAMES)
        wifi_ready = bool(
            target is None
            or target.architecture != "esp32s3"
            or self._connected_pro_supports_ota()
            or (
                hasattr(self, "_wifi_ssid")
                and self._wifi_ssid.currentText().strip()
            )
        )
        return (
            target is not None
            and compatible_product
            and bool(self._connected_update_port())
            and wifi_ready
            and self._version_tuple(self._device_info.firmware_version)
            <= self._version_tuple(target.version)
        )

    def _connected_update_port(self) -> str:
        if self._device_info is None:
            return ""
        if not self._connected_port.startswith("Wi-Fi"):
            return self._connected_port
        if self._connected_pro_supports_ota():
            return self._connected_port
        if not hasattr(self, "_port_combo"):
            return ""
        for index in range(self._port_combo.count()):
            if self._port_combo.itemData(index, Qt.UserRole + 1) == "HCD-PRO":
                return str(self._port_combo.itemData(index) or "")
        return ""

    def _connected_pro_supports_ota(self) -> bool:
        return bool(
            self._device_info is not None
            and self._device_info.model_identifier == "HCD-PRO"
            and self._version_tuple(self._device_info.firmware_version)
            >= self._PRO_OTA_MINIMUM_VERSION
        )

    @staticmethod
    def _version_tuple(version: str) -> tuple[int, ...]:
        try:
            return tuple(int(part) for part in version.split("."))
        except ValueError:
            return (0,)

    def refresh_ports(self) -> None:
        selected = self._port_combo.currentData()
        self._port_combo.clear()
        for info in QSerialPortInfo.availablePorts():
            if not FirmwareUpdater.is_compatible_port(info):
                continue
            name = info.portName()
            description = info.description().strip()
            label = f"{description} — {name}" if description else name
            self._port_combo.addItem(label, name)
            self._port_combo.setItemData(
                self._port_combo.count() - 1,
                self._suggested_model_for_port(info),
                Qt.UserRole + 1,
            )
        matching_index = self._port_combo.findData(selected)
        if matching_index >= 0:
            self._port_combo.setCurrentIndex(matching_index)
        if hasattr(self, "_update_button"):
            self._update_button.setEnabled(not self._busy and self._can_update_connected_device())
        self._update_install_enabled()

    @staticmethod
    def _suggested_model_for_port(info: QSerialPortInfo) -> str:
        vendor = info.vendorIdentifier() if info.hasVendorIdentifier() else 0
        product = info.productIdentifier() if info.hasProductIdentifier() else 0
        identity = " ".join(
            (info.portName(), info.description(), info.manufacturer())
        ).casefold()
        if vendor == 0x303A or (vendor, product) == (0x1A86, 0x55D3):
            return "HCD-PRO"
        if "esp32" in identity or "espressif" in identity:
            return "HCD-PRO"
        return ""

    def _port_changed(self, index: int) -> None:
        if index < 0 or self._busy:
            return
        suggested_model = str(self._port_combo.itemData(index, Qt.UserRole + 1) or "")
        if suggested_model:
            model_index = self._model_combo.findData(suggested_model)
            if model_index >= 0:
                self._model_combo.setCurrentIndex(model_index)
        self._update_button.setEnabled(not self._busy and self._can_update_connected_device())
        self._update_install_enabled()

    def _request_install(self) -> None:
        port = str(self._port_combo.currentData() or "")
        model = str(self._model_combo.currentData() or "")
        if port and model:
            self.install_requested.emit(
                port,
                model,
                self._wifi_ssid.currentText().strip() if model == "HCD-PRO" else "",
                self._wifi_password.text() if model == "HCD-PRO" else "",
            )

    def _model_changed(self, index: int = -1) -> None:
        del index
        model = self._model_combo.currentData()
        is_pro = model == "HCD-PRO"
        is_development_model = model in {"HCD-PLUS", "HCD-PRO"}
        self._wifi_frame.setVisible(is_pro)
        self._status.setText(
            self._text("firmware_development_only") if is_development_model else ""
        )
        self._update_install_enabled()

    def _update_install_enabled(self, value: str = "") -> None:
        del value
        model = self._model_combo.currentData()
        is_pro = model == "HCD-PRO"
        has_wifi = bool(self._wifi_ssid.currentText().strip()) if is_pro else True
        self._install_button.setEnabled(
            self._port_combo.count() > 0
            and not self._busy
            and has_wifi
        )
        self._update_button.setEnabled(not self._busy and self._can_update_connected_device())

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_button.setEnabled(not busy and self._can_update_connected_device())
        self._update_install_enabled()
        self._refresh_button.setEnabled(not busy)
        self._port_combo.setEnabled(not busy)
        self._model_combo.setEnabled(not busy)
        self._wifi_ssid.setEnabled(not busy)
        self._wifi_refresh_button.setEnabled(not busy)
        self._wifi_password.setEnabled(not busy)
        self._close_button.setEnabled(not busy)
        self._progress.setVisible(busy)
        self._progress_label.setVisible(busy)
        if busy:
            self._progress.setValue(0)
            self._progress_label.setText("0%")
            self._details_button.setVisible(False)
            self._details.setVisible(False)

    def _start_wifi_scan(self) -> None:
        if self._busy or not self._wifi_frame.isVisible():
            return
        self._wifi_refresh_button.setEnabled(False)
        self._wifi_scan_status.setText(self._text("wifi_loading_saved"))
        threading.Thread(target=self._scan_wifi_worker, daemon=True).start()

    def _request_macos_location_access(self) -> bool:
        try:
            from CoreLocation import CLLocationManager
        except ImportError:
            return False
        if CLLocationManager.authorizationStatus() != 0:
            return False
        self._location_manager = CLLocationManager.alloc().init()
        self._location_manager.requestWhenInUseAuthorization()
        return True

    def _scan_wifi_worker(self) -> None:
        networks: list[str] = []
        error = ""
        try:
            if sys.platform == "darwin":
                from CoreWLAN import CWWiFiClient

                interface = CWWiFiClient.sharedWiFiClient().interface()
                if interface is not None:
                    current = interface.ssid()
                    configuration = interface.configuration()
                    profiles = configuration.networkProfiles() if configuration else None
                    if profiles is None:
                        profile_items = []
                    elif hasattr(profiles, "array"):
                        profile_items = list(profiles.array())
                    elif hasattr(profiles, "count") and hasattr(profiles, "objectAtIndex_"):
                        profile_items = [
                            profiles.objectAtIndex_(index)
                            for index in range(int(profiles.count()))
                        ]
                    else:
                        profile_items = list(profiles)
                    networks = sorted(
                        {profile.ssid() for profile in profile_items if profile.ssid()},
                        key=str.casefold,
                    )
                    if current and current not in networks:
                        networks.insert(0, current)
            elif sys.platform == "win32":
                result = subprocess.run(
                    ["netsh", "wlan", "show", "profiles"],
                    capture_output=True,
                    text=True,
                    timeout=12,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
                networks = sorted(
                    {
                        match.group(1).strip()
                        for match in re.finditer(
                            r"^\s*(?:All User Profile|Profil Tous les utilisateurs)\s*:\s*(.+)$",
                            result.stdout,
                            re.MULTILINE,
                        )
                        if match.group(1).strip()
                    },
                    key=str.casefold,
                )
                if result.returncode != 0:
                    error = result.stderr.strip()
        except Exception as exception:
            error = str(exception)
        self.wifi_scan_finished.emit(networks, error)

    @Slot(object, str)
    def _wifi_networks_received(self, networks: object, error: str) -> None:
        current = self._wifi_ssid.currentText().strip()
        names = [str(name) for name in networks]
        self._wifi_ssid.blockSignals(True)
        self._wifi_ssid.clear()
        self._wifi_ssid.addItems(names)
        if current:
            if self._wifi_ssid.findText(current) < 0:
                self._wifi_ssid.insertItem(0, current)
            self._wifi_ssid.setCurrentText(current)
        elif names:
            self._wifi_ssid.setCurrentIndex(0)
        self._wifi_ssid.blockSignals(False)
        if names:
            self._wifi_scan_status.setText(
                self._text("wifi_networks_found", count=len(names))
            )
        else:
            self._wifi_scan_status.setText(
                self._text("wifi_scan_unavailable") if not error else error
            )
        self._wifi_refresh_button.setEnabled(not self._busy)
        self._update_install_enabled()
        self._start_wifi_password_lookup(self._wifi_ssid.currentText())

    def _start_wifi_password_lookup(self, ssid: str) -> None:
        network = ssid.strip()
        if self._busy or not network:
            return
        self._wifi_password.clear()
        threading.Thread(
            target=self._wifi_password_worker,
            args=(network,),
            daemon=True,
        ).start()

    def _wifi_password_worker(self, ssid: str) -> None:
        password = ""
        error = ""
        try:
            if sys.platform == "darwin":
                result = subprocess.run(
                    [
                        "security",
                        "find-generic-password",
                        "-D",
                        "AirPort network password",
                        "-a",
                        ssid,
                        "-w",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if result.returncode == 0:
                    password = result.stdout.rstrip("\r\n")
                else:
                    error = result.stderr.strip()
            elif sys.platform == "win32":
                result = subprocess.run(
                    ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
                    capture_output=True,
                    text=True,
                    timeout=12,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
                match = re.search(
                    r"^\s*(?:Key Content|Contenu de la cl(?:é|e))\s*:\s*(.+)$",
                    result.stdout,
                    re.MULTILINE | re.IGNORECASE,
                )
                if match:
                    password = match.group(1).strip()
                elif result.returncode != 0:
                    error = result.stderr.strip()
        except Exception as exception:
            error = str(exception)
        self.wifi_password_finished.emit(ssid, password, error)

    @Slot(str, str, str)
    def _wifi_password_received(self, ssid: str, password: str, error: str) -> None:
        if ssid != self._wifi_ssid.currentText().strip():
            return
        if password:
            self._wifi_password.setText(password)
            self._wifi_scan_status.setText(self._text("wifi_password_loaded"))
        elif error:
            self._wifi_scan_status.setText(self._text("wifi_password_manual"))

    def set_progress(self, value: int) -> None:
        self._progress.setValue(value)
        self._progress_label.setText(f"{value}%")

    def set_status(self, message: str) -> None:
        self._status.setText(message)

    def set_log(self, log: str) -> None:
        self._details.setPlainText(log)

    def _toggle_details(self) -> None:
        visible = not self._details.isVisible()
        self._details.setVisible(visible)
        self._details_button.setText(
            self._text("hide_firmware_details") if visible else self._text("show_firmware_details")
        )

    def finish(self, successful: bool, message: str) -> None:
        self.set_busy(False)
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        final_progress = 100 if successful else 0
        self._progress.setValue(final_progress)
        self._progress_label.setText(f"{final_progress}%")
        self._status.setText(message)
        self._details_button.setVisible(not successful and bool(self._details.toPlainText()))
        if successful:
            self._update_button.setEnabled(False)
            self._install_button.setEnabled(False)
            self._refresh_button.setEnabled(False)
            self._port_combo.setEnabled(False)
            self._model_combo.setEnabled(False)

    def reject(self) -> None:
        if not self._busy:
            super().reject()
