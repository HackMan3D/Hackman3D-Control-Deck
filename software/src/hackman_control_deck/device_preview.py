from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
    QResizeEvent,
    QDragEnterEvent,
    QDropEvent,
)
from PySide6.QtWidgets import QSizePolicy, QToolButton, QWidget


class DropKeyButton(QToolButton):
    application_dropped = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls or not urls[0].isLocalFile():
            return
        self.application_dropped.emit(urls[0].toLocalFile())
        event.acceptProposedAction()


class DevicePreview(QWidget):
    control_selected = Signal(str)
    application_dropped = Signal(str, str)

    _SOURCE_WIDTH = 1536
    _SOURCE_HEIGHT = 1024
    _KEY_CENTERS = (
        (620, 230),
        (794, 260),
        (966, 292),
        (555, 363),
        (726, 397),
        (892, 432),
        (489, 511),
        (658, 545),
        (821, 579),
    )
    _CONNECTION_LED_CENTER = QPointF(1161, 191)
    _FEEDBACK_LED_START = QPointF(438, 718)
    _FEEDBACK_LED_END = QPointF(870, 816)

    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._source = QPixmap(str(image_path))
        self._scaled = QPixmap()
        self._image_rect = QRect()
        self._connection_active = False
        self._feedback_active = False
        self._model_identifier = "HCD-BASE"
        self._key_count = 9
        self._potentiometer_count = 0
        self._pro_slider_value = 50
        self._pro_microphone_value = 50
        self._pro_second_fader = False
        self._pro_colors = {
            "screen": "#080808",
            "key": "#171717",
            "border": "#404040",
            "header": "#FFFFFF",
            "led": "#F02020",
        }

        self.buttons: dict[str, QToolButton] = {}
        self._configure_controls()

    def set_model(
        self,
        model_identifier: str,
        key_count: int,
        potentiometer_count: int = 0,
    ) -> None:
        normalized_model = (
            model_identifier
            if model_identifier in {"HCD-BASE", "HCD-PLUS", "HCD-PRO"}
            else "HCD-BASE"
        )
        if (
            normalized_model == self._model_identifier
            and key_count == self._key_count
            and potentiometer_count == self._potentiometer_count
        ):
            return
        self._model_identifier = normalized_model
        self._key_count = max(1, key_count)
        self._potentiometer_count = max(0, potentiometer_count)
        self._configure_controls()
        self._layout_controls()
        self.update()

    def _configure_controls(self) -> None:
        for button in self.buttons.values():
            button.deleteLater()
        self.buttons.clear()
        identifiers = [str(index) for index in range(1, self._key_count + 1)]
        identifiers.extend(
            f"P{index}" for index in range(1, self._potentiometer_count + 1)
        )
        for identifier in identifiers:
            button = DropKeyButton(self)
            button.setObjectName("deviceKey")
            button.setText(identifier)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(28, 28))
            button.setProperty("selected", False)
            button.setProperty("active", False)
            button.clicked.connect(
                lambda checked=False, item=identifier: self.control_selected.emit(item)
            )
            button.application_dropped.connect(
                lambda path, item=identifier: self.application_dropped.emit(item, path)
            )
            self.buttons[identifier] = button
            button.show()
        self._apply_pro_button_colors()

    def set_pro_colors(self, colors: dict[str, str]) -> None:
        for name in self._pro_colors:
            color = QColor(colors.get(name, self._pro_colors[name]))
            if color.isValid():
                self._pro_colors[name] = color.name(QColor.NameFormat.HexRgb).upper()
        self._apply_pro_button_colors()
        self.update()

    def _apply_pro_button_colors(self) -> None:
        if self._model_identifier != "HCD-PRO":
            for button in self.buttons.values():
                button.setStyleSheet("")
            return
        key = self._pro_colors["key"]
        border = self._pro_colors["border"]
        header = self._pro_colors["header"]
        style = f"""
            QToolButton#deviceKey {{
                background: {key}; color: {header};
                border: 2px solid {border}; border-radius: 10px; padding: 3px;
            }}
            QToolButton#deviceKey:hover,
            QToolButton#deviceKey[selected=\"true\"] {{ border-color: {header}; }}
            QToolButton#deviceKey[active=\"true\"] {{
                background: {border}; color: {header}; border-color: {header};
            }}
        """
        for button in self.buttons.values():
            button.setStyleSheet(style)

    def set_connection_active(self, active: bool) -> None:
        if self._connection_active == active:
            return
        self._connection_active = active
        self.update()

    def set_feedback_active(self, active: bool) -> None:
        if self._feedback_active == active:
            return
        self._feedback_active = active
        self.update()

    def set_pro_slider_value(self, value: int) -> None:
        normalized = max(0, min(100, int(value)))
        if normalized != self._pro_slider_value:
            self._pro_slider_value = normalized
            self.update()

    def set_pro_microphone_value(self, value: int) -> None:
        normalized = max(0, min(100, int(value)))
        if normalized != self._pro_microphone_value:
            self._pro_microphone_value = normalized
            self.update()

    def set_pro_second_fader(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self._pro_second_fader:
            return
        self._pro_second_fader = normalized
        self._layout_controls()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._model_identifier == "HCD-PLUS":
            self._paint_plus_device(painter)
        elif self._model_identifier == "HCD-PRO":
            self._paint_pro_device(painter)
        elif not self._scaled.isNull():
            painter.drawPixmap(self._image_rect, self._scaled)

        scale = (
            self._image_rect.width() / self._SOURCE_WIDTH
            if self._model_identifier == "HCD-BASE"
            else max(0.45, min(self.width() / 900, self.height() / 600))
        )
        if self._connection_active:
            self._paint_connection_led(painter, scale)
        if self._feedback_active:
            self._paint_feedback_led(painter, scale)

    def _paint_plus_device(self, painter: QPainter) -> None:
        panel = self.rect().adjusted(
            max(20, self.width() // 18),
            max(24, self.height() // 16),
            -max(20, self.width() // 18),
            -max(24, self.height() // 16),
        )
        painter.save()
        painter.setPen(QPen(QColor("#555555"), 2))
        painter.setBrush(QColor("#111111"))
        painter.drawRoundedRect(panel, 30, 30)
        painter.setPen(QColor("#f1f1f1"))
        painter.drawText(
            panel.adjusted(24, 14, -24, -14),
            Qt.AlignTop | Qt.AlignLeft,
            "HCD PLUS",
        )
        pot_area_x = panel.left() + round(panel.width() * 0.82)
        for row in range(self._potentiometer_count):
            center = QPointF(
                pot_area_x,
                panel.top() + round(panel.height() * (0.36 + row * 0.35)),
            )
            radius = max(28, round(min(panel.width(), panel.height()) * 0.075))
            painter.setPen(QPen(QColor("#7a7a7a"), 3))
            painter.setBrush(QColor("#252525"))
            painter.drawEllipse(center, radius, radius)
        painter.restore()

    def _paint_pro_device(self, painter: QPainter) -> None:
        panel = self._pro_panel()
        painter.save()
        painter.setPen(QPen(QColor("#555555"), 2))
        painter.setBrush(QColor(self._pro_colors["screen"]))
        painter.drawRoundedRect(panel, 24, 24)
        screen = panel.adjusted(18, 18, -18, -18)
        painter.setPen(QPen(QColor("#303030"), 2))
        painter.setBrush(QColor(self._pro_colors["screen"]).lighter(112))
        painter.drawRoundedRect(screen, 14, 14)
        painter.setPen(QColor(self._pro_colors["header"]))
        painter.drawText(
            screen.adjusted(18, 8, -18, -8),
            Qt.AlignTop | Qt.AlignLeft,
            "HCD PRO · WI-FI TOUCH DISPLAY",
        )
        slider_area = screen.adjusted(round(screen.width() * 0.92), 50, -14, -24)
        rail_x = slider_area.center().x()
        painter.setPen(QPen(QColor("#555555"), 3))
        painter.drawLine(rail_x, slider_area.top(), rail_x, slider_area.bottom())
        knob_y = round(
            slider_area.bottom()
            - slider_area.height() * (self._pro_slider_value / 100.0)
        )
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QColor("#e8e8e8"))
        painter.drawRoundedRect(rail_x - 12, knob_y - 7, 24, 14, 5, 5)
        if self._pro_second_fader:
            keys_area = screen.adjusted(20, 50, -round(screen.width() * 0.11), -24)
            microphone_x = round(keys_area.left() + keys_area.width() * 0.93)
            painter.setPen(QPen(QColor("#555555"), 3))
            painter.drawLine(
                microphone_x, slider_area.top(), microphone_x, slider_area.bottom()
            )
            microphone_y = round(
                slider_area.bottom()
                - slider_area.height() * (self._pro_microphone_value / 100.0)
            )
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QColor("#e8e8e8"))
            painter.drawRoundedRect(
                microphone_x - 12, microphone_y - 7, 24, 14, 5, 5
            )
        painter.restore()

    def _map_point(self, point: QPointF, scale: float) -> QPointF:
        return QPointF(
            self._image_rect.left() + point.x() * scale,
            self._image_rect.top() + point.y() * scale,
        )

    def _paint_connection_led(self, painter: QPainter, scale: float) -> None:
        if self._model_identifier == "HCD-PRO":
            panel = self._pro_panel().adjusted(18, 18, -18, -18)
            center = QPointF(panel.right() - 26, panel.top() + 22)
        elif self._model_identifier == "HCD-PLUS":
            panel = self._plus_panel()
            center = QPointF(panel.right() - 32, panel.top() + 32)
        else:
            center = self._map_point(self._CONNECTION_LED_CENTER, scale)
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Screen)
        painter.setPen(Qt.NoPen)

        # Illuminate the plastic around the physical lens with a broad,
        # continuous falloff.
        glow_radius = max(14.0, 78.0 * scale)
        led = QColor(
            self._pro_colors["led"]
            if self._model_identifier == "HCD-PRO"
            else "#F02020"
        )
        glow = QRadialGradient(center, glow_radius)
        glow.setColorAt(0.0, QColor(led.red(), led.green(), led.blue(), 200))
        glow.setColorAt(0.2, QColor(led.red(), led.green(), led.blue(), 120))
        glow.setColorAt(0.48, QColor(led.red(), led.green(), led.blue(), 55))
        glow.setColorAt(0.75, QColor(led.red(), led.green(), led.blue(), 16))
        glow.setColorAt(1.0, QColor(led.red(), led.green(), led.blue(), 0))
        painter.setBrush(glow)
        painter.drawEllipse(center, glow_radius, glow_radius)
        painter.restore()

        # Saturate the lens in normal source-over mode. Screen blending here
        # would wash it out to pink or white.
        painter.save()
        painter.setPen(Qt.NoPen)
        core_radius = max(3.0, 9.0 * scale)
        core = QRadialGradient(center, core_radius)
        dark = led.darker(140)
        core.setColorAt(0.0, QColor(255, 255, 255, 245))
        core.setColorAt(0.22, QColor(led.red(), led.green(), led.blue(), 245))
        core.setColorAt(0.68, QColor(dark.red(), dark.green(), dark.blue(), 225))
        core.setColorAt(1.0, QColor(dark.red(), dark.green(), dark.blue(), 80))
        painter.setBrush(core)
        painter.drawEllipse(center, core_radius, core_radius)
        painter.restore()

    def _paint_feedback_led(self, painter: QPainter, scale: float) -> None:
        if self._model_identifier == "HCD-PRO":
            panel = self._pro_panel().adjusted(18, 18, -18, -18)
            start = QPointF(panel.left() + panel.width() * 0.38, panel.bottom() - 10)
            end = QPointF(panel.left() + panel.width() * 0.62, panel.bottom() - 10)
        elif self._model_identifier == "HCD-PLUS":
            panel = self._plus_panel()
            start = QPointF(panel.left() + panel.width() * 0.28, panel.bottom() - 18)
            end = QPointF(panel.left() + panel.width() * 0.68, panel.bottom() - 18)
        else:
            start = self._map_point(self._FEEDBACK_LED_START, scale)
            end = self._map_point(self._FEEDBACK_LED_END, scale)
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Screen)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.NoBrush)

        # Do not redraw the diffuser as a line: it already exists in the
        # product render. Overlapping radial blooms create an area of light
        # that spills naturally onto the front panel above and below it.
        sample_count = 13
        for index in range(sample_count):
            amount = index / (sample_count - 1)
            point = QPointF(
                start.x() + (end.x() - start.x()) * amount,
                start.y() + (end.y() - start.y()) * amount,
            )
            for radius, center_alpha in ((100.0, 24), (66.0, 38), (40.0, 60)):
                scaled_radius = max(8.0, radius * scale)
                bloom = QRadialGradient(point, scaled_radius)
                bloom.setColorAt(0.0, QColor(248, 252, 255, center_alpha))
                bloom.setColorAt(0.32, QColor(238, 247, 255, center_alpha * 2 // 3))
                bloom.setColorAt(0.7, QColor(220, 235, 255, center_alpha // 5))
                bloom.setColorAt(1.0, QColor(210, 230, 255, 0))
                painter.setBrush(bloom)
                painter.drawEllipse(point, scaled_radius, scaled_radius)
        painter.restore()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._source.isNull():
            return

        scaled = self._source.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled.width()) // 2
        offset_y = (self.height() - scaled.height()) // 2
        self._scaled = scaled
        self._image_rect = QRect(offset_x, offset_y, scaled.width(), scaled.height())
        self._layout_controls()
        self.update()

    def _layout_controls(self) -> None:
        if not self.buttons:
            return
        if self._model_identifier == "HCD-PLUS":
            self._layout_plus_controls()
            return
        if self._model_identifier == "HCD-PRO":
            self._layout_pro_controls()
            return
        scale = self._scaled.width() / self._SOURCE_WIDTH
        button_width = max(48, round(148 * scale))
        button_height = max(42, round(118 * scale))
        icon_size = max(20, round(62 * scale))
        for index, center in enumerate(self._KEY_CENTERS, start=1):
            center_x = self._image_rect.left() + round(center[0] * scale)
            center_y = self._image_rect.top() + round(center[1] * scale)
            button = self.buttons[str(index)]
            button.setIconSize(QSize(icon_size, icon_size))
            button.setGeometry(
                QRect(
                    center_x - button_width // 2,
                    center_y - button_height // 2,
                    button_width,
                    button_height,
                )
            )
            button.raise_()

    def _layout_plus_controls(self) -> None:
        panel = self._plus_panel()
        keys_width = round(panel.width() * 0.72)
        columns = 5
        rows = max(1, (self._key_count + columns - 1) // columns)
        cell_width = keys_width / columns
        usable_height = panel.height() * 0.78
        cell_height = usable_height / rows
        button_width = max(54, round(cell_width * 0.72))
        button_height = max(48, round(cell_height * 0.68))
        icon_size = max(20, round(min(button_width, button_height) * 0.42))
        for index in range(1, self._key_count + 1):
            row = (index - 1) // columns
            column = (index - 1) % columns
            center_x = panel.left() + round((column + 0.5) * cell_width)
            center_y = panel.top() + round(
                panel.height() * 0.16 + (row + 0.5) * cell_height
            )
            button = self.buttons[str(index)]
            button.setVisible(not self._pro_second_fader or column != 6)
            button.setIconSize(QSize(icon_size, icon_size))
            button.setGeometry(
                center_x - button_width // 2,
                center_y - button_height // 2,
                button_width,
                button_height,
            )
            button.raise_()

        pot_x = panel.left() + round(panel.width() * 0.82)
        for index in range(1, self._potentiometer_count + 1):
            center_y = panel.top() + round(
                panel.height() * (0.36 + (index - 1) * 0.35)
            )
            button = self.buttons[f"P{index}"]
            button.setGeometry(pot_x - 44, center_y - 36, 88, 72)
            button.raise_()

    def _plus_panel(self) -> QRect:
        return self.rect().adjusted(
            max(20, self.width() // 18),
            max(24, self.height() // 16),
            -max(20, self.width() // 18),
            -max(24, self.height() // 16),
        )

    def _layout_pro_controls(self) -> None:
        panel = self._pro_panel()
        screen = panel.adjusted(26, 58, -round(panel.width() * 0.11), -34)
        columns = 7
        rows = max(1, (self._key_count + columns - 1) // columns)
        gap = max(6, round(min(screen.width(), screen.height()) * 0.018))
        cell_width = (screen.width() - gap * (columns - 1)) / columns
        cell_height = (screen.height() - gap * (rows - 1)) / rows
        for index in range(1, self._key_count + 1):
            row = (index - 1) // columns
            column = (index - 1) % columns
            button = self.buttons[str(index)]
            button.setVisible(not self._pro_second_fader or column != 6)
            button.setIconSize(
                QSize(
                    max(24, round(cell_height * 0.42)),
                    max(24, round(cell_height * 0.42)),
                )
            )
            button.setGeometry(
                round(screen.left() + column * (cell_width + gap)),
                round(screen.top() + row * (cell_height + gap)),
                round(cell_width),
                round(cell_height),
            )
            button.raise_()

    def _pro_panel(self) -> QRect:
        horizontal = max(18, self.width() // 20)
        vertical = max(24, self.height() // 14)
        return self.rect().adjusted(horizontal, vertical, -horizontal, -vertical)
