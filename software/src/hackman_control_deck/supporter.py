from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

import certifi
from PySide6.QtCore import QObject, QThread, Signal


@dataclass(frozen=True)
class SupporterStatus:
    active: bool
    tier: str = "HCD Supporter"
    active_until: str = ""
    token: str = ""


def normalized_supporter_endpoint(value: object) -> str:
    endpoint = str(value or "").strip().rstrip("/")
    return endpoint if endpoint.startswith("https://") else ""


class SupporterClient(QObject):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._endpoint = ""
        self._worker: _SupporterWorker | None = None

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    def set_endpoint(self, endpoint: object) -> None:
        self._endpoint = normalized_supporter_endpoint(endpoint)

    def check(self, token: str) -> None:
        self._start("status", token=token)

    def claim(self, transaction_id: str) -> None:
        self._start("claim", transaction_id=transaction_id)

    def _start(self, operation: str, **values: str) -> None:
        if self._worker is not None or not self._endpoint:
            return
        worker = _SupporterWorker(self._endpoint, operation, values, self)
        worker.loaded.connect(self.loaded)
        worker.failed.connect(self.failed)
        worker.finished.connect(self._finished)
        self._worker = worker
        worker.start()

    def _finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()


class _SupporterWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        endpoint: str,
        operation: str,
        values: dict[str, str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._endpoint = endpoint
        self._operation = operation
        self._values = values

    def run(self) -> None:
        headers = {"User-Agent": "HackMan3D-Control-Deck", "Accept": "application/json"}
        data = None
        url = f"{self._endpoint}/status"
        method = "GET"
        if self._operation == "claim":
            url = f"{self._endpoint}/claim"
            method = "POST"
            data = json.dumps({"transaction_id": self._values["transaction_id"]}).encode()
            headers["Content-Type"] = "application/json"
        else:
            headers["Authorization"] = f"Bearer {self._values.get('token', '')}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(request, timeout=10, context=context) as result:
                document = json.loads(result.read(64 * 1024).decode("utf-8"))
            self.loaded.emit(
                SupporterStatus(
                    active=bool(document.get("active")),
                    tier=str(document.get("tier") or "HCD Supporter"),
                    active_until=str(document.get("active_until") or ""),
                    token=str(document.get("token") or ""),
                )
            )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                self.failed.emit("membership_not_found")
            elif error.code == 401:
                self.loaded.emit(SupporterStatus(active=False))
            else:
                self.failed.emit(f"http_{error.code}")
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
            self.failed.emit("service_unavailable")
