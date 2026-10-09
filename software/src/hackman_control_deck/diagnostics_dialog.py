from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import platform
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .protocol import DeviceInfo
from .constants import APP_NAME, APP_VERSION


class DiagnosticsDialog(QDialog):
    def __init__(self, text: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setWindowTitle(text("diagnostics"))
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout(self)
        title = QLabel(text("diagnostics"), objectName="title")
        layout.addWidget(title)

        card = QFrame(objectName="firmwareCard")
        info = QGridLayout(card)
        self._values: dict[str, QLabel] = {}
        for row, key in enumerate(("connection", "model", "firmware", "serial_port", "heartbeat")):
            info.addWidget(QLabel(text(key)), row, 0)
            value = QLabel("—")
            self._values[key] = value
            info.addWidget(value, row, 1)
        layout.addWidget(card)

        layout.addWidget(QLabel(text("live_buttons"), objectName="sectionTitle"))
        self._key_grid = QGridLayout()
        self._keys: dict[str, QLabel] = {}
        self._pot_values: dict[int, QLabel] = {}
        self._key_states: dict[str, bool] = {}
        self._feedback_active = False
        layout.addLayout(self._key_grid)
        self.set_controls(9, 0)

        leds = QHBoxLayout()
        self._connection_led = QLabel(text("connection_led"), objectName="diagnosticLed")
        self._feedback_led = QLabel(text("feedback_led"), objectName="diagnosticLed")
        leds.addWidget(self._connection_led)
        leds.addWidget(self._feedback_led)
        layout.addLayout(leds)
        layout.addStretch()
        actions = QHBoxLayout()
        export = QPushButton(text("export_diagnostic_report"))
        export.clicked.connect(self._export_report)
        actions.addWidget(export)
        actions.addStretch()
        close = QPushButton(text("close"))
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        layout.addLayout(actions)

    def set_controls(self, key_count: int, potentiometer_count: int) -> None:
        while self._key_grid.count():
            item = self._key_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._keys.clear()
        self._key_states.clear()
        self._pot_values.clear()
        for index in range(1, key_count + 1):
            indicator = QLabel(str(index), objectName="diagnosticKey")
            indicator.setAlignment(Qt.AlignCenter)
            indicator.setProperty("active", False)
            indicator.setMinimumSize(90, 55)
            self._key_grid.addWidget(indicator, (index - 1) // 4, (index - 1) % 4)
            self._keys[str(index)] = indicator
            self._key_states[str(index)] = False
        row = (key_count + 3) // 4
        for index in range(1, potentiometer_count + 1):
            indicator = QLabel(f"Encoder {index} click", objectName="diagnosticKey")
            indicator.setAlignment(Qt.AlignCenter)
            indicator.setProperty("active", False)
            indicator.setMinimumSize(90, 55)
            value = QLabel("LEFT · RIGHT", objectName="subtitle")
            value.setAlignment(Qt.AlignCenter)
            column = (index - 1) * 2
            self._key_grid.addWidget(indicator, row, column)
            self._key_grid.addWidget(value, row, column + 1)
            self._keys[f"P{index}"] = indicator
            self._key_states[f"P{index}"] = False
            self._pot_values[index] = value

    def update_device(
        self,
        connected: bool,
        port: str,
        device_info: DeviceInfo | None,
        heartbeat: bool,
    ) -> None:
        self._values["connection"].setText(
            self._text("connected_generic") if connected else self._text("disconnected")
        )
        self._values["serial_port"].setText(port or "—")
        self._values["heartbeat"].setText(
            self._text("heartbeat_ok") if heartbeat else self._text("heartbeat_missing")
        )
        self._values["model"].setText(device_info.model_identifier if device_info else "—")
        self._values["firmware"].setText(device_info.firmware_version if device_info else "—")
        self._set_indicator(self._connection_led, connected)

    def set_key_state(self, identifier: str, pressed: bool) -> None:
        indicator = self._keys.get(identifier)
        if indicator is not None:
            self._key_states[identifier] = pressed
            self._set_indicator(indicator, pressed)

    def set_feedback_led(self, active: bool) -> None:
        self._feedback_active = active
        self._set_indicator(self._feedback_led, active)

    def _report(self) -> str:
        lines = [
            f"{APP_NAME} — diagnostic report",
            f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            f"Desktop app: {APP_VERSION}",
            f"System: {platform.system()} {platform.release()}",
            "",
        ]
        for key in ("connection", "model", "firmware", "serial_port", "heartbeat"):
            lines.append(f"{self._text(key)}: {self._values[key].text()}")
        active = [key for key, pressed in self._key_states.items() if pressed]
        lines.extend(
            (
                f"Controls reported: {len(self._key_states)}",
                f"Controls currently pressed: {', '.join(active) if active else 'none'}",
                f"Feedback LED active: {'yes' if self._feedback_active else 'no'}",
                "",
                "This report contains technical status only and no profile actions or personal files.",
            )
        )
        return "\n".join(lines) + "\n"

    def _export_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._text("export_diagnostic_report"),
            str(Path.home() / "HackMan3D-diagnostic.txt"),
            "Text report (*.txt)",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != ".txt":
            destination = destination.with_suffix(".txt")
        destination.write_text(self._report(), encoding="utf-8")

    def set_potentiometer_value(self, identifier: int, value: int) -> None:
        label = self._pot_values.get(identifier)
        if label is not None:
            label.setText(f"{max(0, min(1023, value))} / 1023")

    @staticmethod
    def _set_indicator(widget: QWidget, active: bool) -> None:
        widget.setProperty("active", active)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
