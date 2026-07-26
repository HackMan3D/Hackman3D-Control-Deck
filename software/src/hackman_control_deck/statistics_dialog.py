from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .statistics import StatisticsStore


class StatisticsDialog(QDialog):
    def __init__(
        self,
        store: StatisticsStore,
        profile_name: str,
        text: Callable[..., str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._profile_name = profile_name
        self._text = text
        self.setWindowTitle(text("statistics"))
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        title = QLabel(text("statistics_for", name=profile_name), objectName="title")
        layout.addWidget(title)
        self._summary = QLabel(objectName="subtitle")
        layout.addWidget(self._summary)
        self._grid = QGridLayout()
        layout.addLayout(self._grid)

        buttons = QHBoxLayout()
        self._reset_button = QPushButton(text("reset_statistics"))
        self._reset_button.clicked.connect(self._reset)
        buttons.addWidget(self._reset_button)
        buttons.addStretch()
        close_button = QPushButton(text("close"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for column, heading in enumerate(
            (self._text("key_heading"), self._text("short_press"), self._text("long_press"))
        ):
            label = QLabel(heading)
            label.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(label, 0, column)

        counts = self._store.counts(self._profile_name)
        total = 0
        for key_id in map(str, range(1, 10)):
            values = counts.get(key_id, {"short": 0, "long": 0})
            total += values["short"] + values["long"]
            self._grid.addWidget(QLabel(self._text("key", number=key_id)), int(key_id), 0)
            self._grid.addWidget(QLabel(str(values["short"])), int(key_id), 1)
            self._grid.addWidget(QLabel(str(values["long"])), int(key_id), 2)
        self._summary.setText(self._text("total_key_uses", count=total))

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            self._text("statistics"),
            self._text("reset_statistics_confirm"),
        )
        if answer != QMessageBox.Yes:
            return
        self._store.reset(self._profile_name)
        self._refresh()
