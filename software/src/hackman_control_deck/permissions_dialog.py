from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def accessibility_is_authorized() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except ImportError:
        return False


class MacPermissionsDialog(QDialog):
    def __init__(self, text: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setWindowTitle(text("macos_permissions"))
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(text("macos_permissions"), objectName="title"))
        help_label = QLabel(text("macos_permissions_help"), objectName="subtitle")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self._status = QLabel()
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        open_button = QPushButton(text("open_system_settings"), objectName="accent")
        open_button.clicked.connect(self._open_settings)
        buttons.addWidget(open_button)
        refresh_button = QPushButton(text("refresh_permission"))
        refresh_button.clicked.connect(self._refresh)
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        close_button = QPushButton(text("close"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self) -> None:
        key = "permission_authorized" if accessibility_is_authorized() else "permission_required"
        self._status.setText(self._text(key))

    @staticmethod
    def _open_settings() -> None:
        QDesktopServices.openUrl(
            QUrl("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
        )
