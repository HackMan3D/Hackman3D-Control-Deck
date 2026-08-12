from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
    update_requested = Signal(str, str)
    install_requested = Signal(str, str)

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
        return (
            target is not None
            and compatible_product
            and bool(self._connected_update_port())
            and self._version_tuple(self._device_info.firmware_version)
            <= self._version_tuple(target.version)
        )

    def _connected_update_port(self) -> str:
        if self._device_info is None:
            return ""
        return self._connected_port

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
            self.install_requested.emit(port, model)

    def _model_changed(self, index: int = -1) -> None:
        del index
        model = self._model_combo.currentData()
        is_development_model = model in {"HCD-PLUS", "HCD-PRO"}
        self._status.setText(
            self._text("firmware_development_only") if is_development_model else ""
        )
        self._update_install_enabled()

    def _update_install_enabled(self, value: str = "") -> None:
        del value
        model = self._model_combo.currentData()
        self._install_button.setEnabled(
            self._port_combo.count() > 0
            and not self._busy
        )
        self._update_button.setEnabled(not self._busy and self._can_update_connected_device())

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_button.setEnabled(not busy and self._can_update_connected_device())
        self._update_install_enabled()
        self._refresh_button.setEnabled(not busy)
        self._port_combo.setEnabled(not busy)
        self._model_combo.setEnabled(not busy)
        self._close_button.setEnabled(not busy)
        self._progress.setVisible(busy)
        self._progress_label.setVisible(busy)
        if busy:
            self._progress.setValue(0)
            self._progress_label.setText("0%")
            self._details_button.setVisible(False)
            self._details.setVisible(False)

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
