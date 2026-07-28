from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
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
        info_layout.addWidget(
            QLabel(device_info.product if device_info else text("no_hcd_detected")), 0, 1
        )
        info_layout.addWidget(QLabel(text("hardware_model")), 1, 0)
        info_layout.addWidget(QLabel(device_info.model_identifier if device_info else "—"), 1, 1)
        info_layout.addWidget(QLabel(text("installed_firmware")), 2, 0)
        info_layout.addWidget(QLabel(device_info.firmware_version if device_info else "—"), 2, 1)
        detected_target = (
            firmware_target(device_info.model_identifier) if device_info else None
        )
        included_version = detected_target.version if detected_target else "—"
        info_layout.addWidget(QLabel(text("included_firmware")), 3, 0)
        info_layout.addWidget(QLabel(included_version), 3, 1)
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
                self._connected_port,
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
            self._model_combo.addItem(
                f"{target.display_name} — {details}",
                target.model_identifier,
            )
        model_row.addWidget(self._model_combo, 1)
        layout.addLayout(model_row)

        port_row = QHBoxLayout()
        self._port_combo = QComboBox()
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
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
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

    def _can_update_connected_device(self) -> bool:
        if self._device_info is None or not self._connected_port:
            return False
        target = firmware_target(self._device_info.model_identifier)
        compatible_product = self._device_info.product.startswith(COMPATIBLE_PRODUCT_NAMES)
        return (
            target is not None
            and compatible_product
            and self._version_tuple(self._device_info.firmware_version)
            <= self._version_tuple(target.version)
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
        matching_index = self._port_combo.findData(selected)
        if matching_index >= 0:
            self._port_combo.setCurrentIndex(matching_index)
        self._install_button.setEnabled(self._port_combo.count() > 0 and not self._busy)

    def _request_install(self) -> None:
        port = str(self._port_combo.currentData() or "")
        model = str(self._model_combo.currentData() or "")
        if port and model:
            self.install_requested.emit(port, model)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_button.setEnabled(not busy and self._can_update_connected_device())
        self._install_button.setEnabled(not busy and self._port_combo.count() > 0)
        self._refresh_button.setEnabled(not busy)
        self._port_combo.setEnabled(not busy)
        self._model_combo.setEnabled(not busy)
        self._close_button.setEnabled(not busy)
        self._progress.setVisible(busy)
        if busy:
            self._progress.setValue(0)
            self._details_button.setVisible(False)
            self._details.setVisible(False)

    def set_progress(self, value: int) -> None:
        self._progress.setValue(value)

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
        self._progress.setValue(100 if successful else 0)
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
