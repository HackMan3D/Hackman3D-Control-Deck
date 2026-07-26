from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QObject, QThread, Signal

from .constants import APP_VERSION, RELEASE_MANIFEST_URL

_VERSION_PART = re.compile(r"\d+")


@dataclass(frozen=True)
class ReleaseFeedData:
    latest_version: str
    download_url: str
    plus_progress: int
    pro_progress: int
    release_notes: str = ""

    @property
    def update_available(self) -> bool:
        return version_key(self.latest_version) > version_key(APP_VERSION)


def version_key(version: str) -> tuple[int, ...]:
    parts = tuple(int(part) for part in _VERSION_PART.findall(version))
    return parts or (0,)


def parse_release_feed(payload: bytes | bytearray | QByteArray) -> ReleaseFeedData:
    document = json.loads(bytes(payload).decode("utf-8"))
    if not isinstance(document, dict) or document.get("schema") != 1:
        raise ValueError("Unsupported release feed")

    latest_version = str(document.get("latest_version", "")).strip()
    if not latest_version or not _VERSION_PART.search(latest_version):
        raise ValueError("Missing latest version")

    downloads = document.get("downloads", {})
    if not isinstance(downloads, dict):
        downloads = {}
    platform_key = "macos" if sys.platform == "darwin" else "windows"
    download_url = str(downloads.get(platform_key, downloads.get("website", ""))).strip()

    roadmap = document.get("roadmap", {})
    if not isinstance(roadmap, dict):
        roadmap = {}

    def percentage(key: str) -> int:
        try:
            value = round(float(roadmap.get(key, 0)))
        except (TypeError, ValueError):
            value = 0
        return max(0, min(100, value))

    return ReleaseFeedData(
        latest_version=latest_version,
        download_url=download_url,
        plus_progress=percentage("plus"),
        pro_progress=percentage("pro"),
        release_notes=str(document.get("release_notes", "")).strip(),
    )


class ReleaseFeedClient(QObject):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _ReleaseFeedWorker | None = None

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    def check(self) -> None:
        if self._worker is not None or not RELEASE_MANIFEST_URL:
            return
        worker = _ReleaseFeedWorker(RELEASE_MANIFEST_URL, self)
        worker.received.connect(self._received)
        worker.request_failed.connect(self.failed)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        worker.start()

    def _received(self, payload: bytes) -> None:
        try:
            self.loaded.emit(parse_release_feed(payload))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.failed.emit(str(error))

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()


class _ReleaseFeedWorker(QThread):
    received = Signal(bytes)
    request_failed = Signal(str)

    def __init__(self, url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        request = urllib.request.Request(
            self._url,
            headers={"User-Agent": "HackMan3D-Control-Deck"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                self.received.emit(response.read(256 * 1024))
        except (OSError, urllib.error.URLError) as error:
            self.request_failed.emit(str(error))
