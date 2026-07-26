from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPaintEvent,
    QPainter,
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
        self.setMinimumSize(430, 310)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._source = QPixmap(str(image_path))
        self._scaled = QPixmap()
        self._image_rect = QRect()
        self._connection_active = False
        self._feedback_active = False

        self.buttons: dict[str, QToolButton] = {}
        for index in range(1, 10):
            identifier = str(index)
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

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._scaled.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self._image_rect, self._scaled)

        scale = self._image_rect.width() / self._SOURCE_WIDTH
        if self._connection_active:
            self._paint_connection_led(painter, scale)
        if self._feedback_active:
            self._paint_feedback_led(painter, scale)

    def _map_point(self, point: QPointF, scale: float) -> QPointF:
        return QPointF(
            self._image_rect.left() + point.x() * scale,
            self._image_rect.top() + point.y() * scale,
        )

    def _paint_connection_led(self, painter: QPainter, scale: float) -> None:
        center = self._map_point(self._CONNECTION_LED_CENTER, scale)
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Screen)
        painter.setPen(Qt.NoPen)

        # Illuminate the plastic around the physical lens with a broad,
        # continuous falloff.
        glow_radius = max(14.0, 78.0 * scale)
        glow = QRadialGradient(center, glow_radius)
        glow.setColorAt(0.0, QColor(255, 20, 12, 200))
        glow.setColorAt(0.2, QColor(255, 18, 10, 120))
        glow.setColorAt(0.48, QColor(245, 10, 6, 55))
        glow.setColorAt(0.75, QColor(225, 5, 3, 16))
        glow.setColorAt(1.0, QColor(210, 0, 0, 0))
        painter.setBrush(glow)
        painter.drawEllipse(center, glow_radius, glow_radius)
        painter.restore()

        # Saturate the lens in normal source-over mode. Screen blending here
        # would wash it out to pink or white.
        painter.save()
        painter.setPen(Qt.NoPen)
        core_radius = max(3.0, 9.0 * scale)
        core = QRadialGradient(center, core_radius)
        core.setColorAt(0.0, QColor(255, 210, 190, 245))
        core.setColorAt(0.22, QColor(255, 45, 30, 245))
        core.setColorAt(0.68, QColor(225, 5, 5, 225))
        core.setColorAt(1.0, QColor(140, 0, 0, 80))
        painter.setBrush(core)
        painter.drawEllipse(center, core_radius, core_radius)
        painter.restore()

    def _paint_feedback_led(self, painter: QPainter, scale: float) -> None:
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

        scale = scaled.width() / self._SOURCE_WIDTH
        button_width = max(48, round(148 * scale))
        button_height = max(42, round(118 * scale))
        icon_size = max(20, round(62 * scale))
        for index, center in enumerate(self._KEY_CENTERS, start=1):
            center_x = offset_x + round(center[0] * scale)
            center_y = offset_y + round(center[1] * scale)
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
        self.update()
