from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import certifi
import ssl
from PySide6.QtCore import QObject, QStandardPaths, QThread, Signal


class AppUpdateDownloader(QObject):
    progress_changed = Signal(int)
    downloaded = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _DownloadWorker | None = None

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    def download(self, url: str, checksum: str = "") -> None:
        if self._worker is not None:
            return
        worker = _DownloadWorker(url, checksum, self)
        worker.progress_changed.connect(self.progress_changed)
        worker.downloaded.connect(self.downloaded)
        worker.failed.connect(self.failed)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        worker.start()

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()


class _DownloadWorker(QThread):
    progress_changed = Signal(int)
    downloaded = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, checksum: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self._checksum = checksum.strip().lower()

    def run(self) -> None:
        try:
            path = download_update(
                self._url,
                self._checksum,
                progress=self.progress_changed.emit,
            )
        except Exception as error:  # noqa: BLE001 - surfaced in the application UI
            self.failed.emit(str(error))
            return
        self.downloaded.emit(str(path))


def download_update(url: str, checksum: str = "", *, progress=None) -> Path:
    if not url.startswith("https://"):
        raise ValueError("The update download must use HTTPS.")
    filename = Path(urllib.parse.urlparse(url).path).name or "HackMan3D-update"
    target_root = Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation))
    if not target_root.is_dir():
        target_root = Path(tempfile.gettempdir())
    target = target_root / filename
    temporary = target.with_suffix(target.suffix + ".part")
    context = ssl.create_default_context(cafile=certifi.where())
    request = urllib.request.Request(url, headers={"User-Agent": "HackMan3D-Control-Deck"})
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=60, context=context) as response:
            total = int(response.headers.get("Content-Length", "0") or 0)
            received = 0
            with temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if progress is not None and total > 0:
                        progress(min(100, round(received * 100 / total)))
        if checksum and digest.hexdigest() != checksum:
            raise ValueError("The downloaded update failed its integrity check.")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if progress is not None:
        progress(100)
    return target


def start_installer(path: Path, current_pid: int | None = None) -> bool:
    path = path.resolve()
    if not path.is_file():
        return False
    if sys.platform == "win32":
        subprocess.Popen(
            [
                str(path),
                "/SP-",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
            ],
            close_fds=True,
        )
        return True
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)], close_fds=True)
        return True
    appimage = os.environ.get("APPIMAGE", "")
    if path.suffix.casefold() == ".appimage" and appimage:
        destination = Path(appimage).resolve()
        if os.access(destination.parent, os.W_OK):
            helper = Path(tempfile.mkstemp(prefix="hcd-update-", suffix=".sh")[1])
            helper.write_text(
                "#!/bin/sh\n"
                f"while kill -0 {current_pid or os.getpid()} 2>/dev/null; do sleep 1; done\n"
                f"cp {shlex_quote(str(path))} {shlex_quote(str(destination))}\n"
                f"chmod +x {shlex_quote(str(destination))}\n"
                f"exec {shlex_quote(str(destination))}\n",
                encoding="utf-8",
            )
            helper.chmod(0o700)
            subprocess.Popen([str(helper)], start_new_session=True, close_fds=True)
            return True
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(path)], close_fds=True)
        return True
    return False


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)
