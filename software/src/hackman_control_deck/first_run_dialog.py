from __future__ import annotations

import sys
from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FirstRunDialog(QDialog):
    firmware_requested = Signal()
    permissions_requested = Signal()

    def __init__(
        self,
        text: Callable[..., str],
        *,
        connected: bool,
        start_at_login: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self.setWindowTitle(text("first_run_title"))
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(QLabel(text("first_run_title"), objectName="title"))
        welcome = QLabel(text("first_run_intro"))
        welcome.setWordWrap(True)
        layout.addWidget(welcome)

        status = QLabel(
            text("first_run_device_connected")
            if connected
            else text("first_run_device_missing"),
            objectName="sectionTitle",
        )
        status.setWordWrap(True)
        layout.addWidget(status)
        firmware = QPushButton(text("first_run_firmware"))
        firmware.clicked.connect(self.firmware_requested)
        layout.addWidget(firmware)

        if sys.platform == "darwin":
            permissions = QPushButton(text("macos_permissions"))
            permissions.clicked.connect(self.permissions_requested)
            layout.addWidget(permissions)

        self.start_at_login = QCheckBox(text("start_with_system"))
        self.start_at_login.setChecked(start_at_login)
        layout.addWidget(self.start_at_login)
        tip = QLabel(text("first_run_finish_help"), objectName="subtitle")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(text("first_run_finish"))
        buttons.button(QDialogButtonBox.Cancel).setText(text("skip"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
