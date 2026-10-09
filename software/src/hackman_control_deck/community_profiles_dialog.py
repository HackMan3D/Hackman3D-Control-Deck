from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CommunityProfilesDialog(QDialog):
    def __init__(
        self,
        text: Callable[..., str],
        catalog_path: Path,
        model: str,
        install: Callable[[dict[str, object]], None],
        repository_url: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._install = install
        self._entries: list[dict[str, object]] = []
        self.setWindowTitle(text("community_profiles"))
        self.setMinimumSize(660, 460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(text("community_profiles"), objectName="title"))
        help_label = QLabel(text("community_profiles_help"))
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._selection_changed)
        layout.addWidget(self._list, 1)
        self._details = QLabel(objectName="subtitle")
        self._details.setWordWrap(True)
        layout.addWidget(self._details)
        buttons = QHBoxLayout()
        contribute = QPushButton(text("contribute_profile"))
        contribute.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(repository_url)))
        buttons.addWidget(contribute)
        buttons.addStretch()
        close = QPushButton(text("close"))
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        self._install_button = QPushButton(text("install_profile"), objectName="accent")
        self._install_button.setEnabled(False)
        self._install_button.clicked.connect(self._install_current)
        buttons.addWidget(self._install_button)
        layout.addLayout(buttons)
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            entries = payload.get("profiles", []) if isinstance(payload, dict) else []
        except (OSError, json.JSONDecodeError):
            entries = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("model") not in {model, "*"}:
                continue
            self._entries.append(entry)
            item = QListWidgetItem(str(entry.get("name", "Profile")))
            item.setToolTip(str(entry.get("description", "")))
            self._list.addItem(item)
        if not self._entries:
            self._list.addItem(text("no_community_profiles"))
            self._list.item(0).setFlags(Qt.NoItemFlags)

    def _selection_changed(self, row: int) -> None:
        valid = 0 <= row < len(self._entries)
        self._install_button.setEnabled(valid)
        if not valid:
            self._details.clear()
            return
        entry = self._entries[row]
        self._details.setText(
            f"{entry.get('description', '')}\n\n{self._text('profile_author')}: "
            f"{entry.get('author', 'HackMan3D Community')}"
        )

    def _install_current(self) -> None:
        row = self._list.currentRow()
        if not 0 <= row < len(self._entries):
            return
        try:
            self._install(self._entries[row])
        except ValueError as error:
            QMessageBox.warning(self, self.windowTitle(), str(error))
            return
        self.accept()
