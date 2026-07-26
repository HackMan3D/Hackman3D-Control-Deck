from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath

ICON_CHUNKS = (
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
)
WINDOWS_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def rounded_icon(source_path: Path) -> QImage:
    source = QImage(str(source_path))
    if source.isNull():
        raise OSError(f"Could not load {source_path}")

    canvas = QImage(1024, 1024, QImage.Format_RGBA8888)
    canvas.fill(QColor(0, 0, 0, 0))
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(12, 12, 1000, 1000), 220, 220)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setClipPath(clip)
    painter.fillPath(clip, QColor(5, 5, 5))
    painter.drawImage(QRectF(42, 290, 940, 444), source)
    painter.end()
    return canvas


def png_data(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise OSError("Could not encode icon image")
    buffer.close()
    return bytes(data)


def windows_icon_data(master: QImage) -> bytes:
    images = [
        png_data(master.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        for size in WINDOWS_ICON_SIZES
    ]
    offset = 6 + 16 * len(images)
    entries = []
    for size, payload in zip(WINDOWS_ICON_SIZES, images, strict=True):
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        offset += len(payload)
    return struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(images)


def build(
    source_path: Path,
    output_path: Path,
    preview_path: Path,
    windows_output_path: Path,
) -> None:
    master = rounded_icon(source_path)
    if not master.save(str(preview_path), "PNG"):
        raise OSError(f"Could not save {preview_path}")

    chunks = []
    for chunk_type, size in ICON_CHUNKS:
        scaled = master.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        payload = png_data(scaled)
        chunks.append(chunk_type.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload)
    body = b"".join(chunks)
    output_path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)
    windows_output_path.write_bytes(windows_icon_data(master))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    assets = root / "src" / "hackman_control_deck" / "assets"
    build(
        assets / "hcd_logo.png",
        assets / "hcd_app_icon.icns",
        assets / "hcd_app_icon_rounded.png",
        assets / "hcd_app_icon.ico",
    )
