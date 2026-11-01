from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import ASSET_DIR, HCD_BASE_SLIM_MODEL_LINKS


class SlimAnnouncementDialog(QDialog):
    """One-time HCD Base Slim announcement that requires opening one model page."""

    def __init__(
        self,
        text: Callable[[str], str],
        parent: QWidget | None = None,
        *,
        open_url: Callable[[QUrl], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._open_url = open_url or QDesktopServices.openUrl
        self._link_opened = False

        self.setWindowTitle(text("slim_announcement_window_title"))
        self.setModal(True)
        self.setMinimumWidth(680)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        title = QLabel(text("slim_announcement_title"), objectName="title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(text("slim_announcement_text"), objectName="subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(245)
        source = QPixmap(str(ASSET_DIR / "hcd_base_slim.png"))
        if not source.isNull():
            preview.setPixmap(
                source.scaled(
                    QSize(500, 280),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        layout.addWidget(preview)

        prompt = QLabel(text("slim_announcement_prompt"))
        prompt.setWordWrap(True)
        prompt.setAlignment(Qt.AlignCenter)
        layout.addWidget(prompt)

        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)
        for key, label, url, icon_name in HCD_BASE_SLIM_MODEL_LINKS:
            button = QPushButton(label, objectName="slimModelLink")
            button.setIcon(QIcon(str(ASSET_DIR / icon_name)))
            button.setIconSize(QSize(30, 30))
            button.setMinimumHeight(58)
            button.setToolTip(label)
            button.clicked.connect(
                lambda checked=False, destination=url: self._open_model_page(destination)
            )
            button_layout.addWidget(button, 1)
        layout.addWidget(button_frame)

        hint = QLabel(text("slim_announcement_close_help"), objectName="subtitle")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.setStyleSheet(
            "QPushButton#slimModelLink {"
            "  font-size: 15px; font-weight: 700; padding: 10px 14px;"
            "  border: 1px solid #505050; border-radius: 10px; background: #202020;"
            "}"
            "QPushButton#slimModelLink:hover {"
            "  border-color: #00c8f4; background: #272727;"
            "}"
        )

    @property
    def link_opened(self) -> bool:
        return self._link_opened

    def _open_model_page(self, url: str) -> None:
        self._link_opened = True
        self._open_url(QUrl(url))
        self.accept()

    def reject(self) -> None:
        if self._link_opened:
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._link_opened:
            super().closeEvent(event)
        else:
            event.ignore()
