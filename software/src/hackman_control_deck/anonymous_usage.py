from __future__ import annotations

import json
import secrets
from urllib.parse import urlparse

from PySide6.QtCore import QByteArray, QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest


def normalized_usage_endpoint(value: object) -> str:
    endpoint = str(value or "").strip()
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return endpoint


def usage_payload(session: str, event: str, actions: int) -> dict[str, object]:
    if event not in {"start", "heartbeat"}:
        raise ValueError("Unsupported anonymous usage event")
    return {
        "schema": 1,
        "session": session,
        "event": event,
        "actions": max(0, int(actions)),
    }


class AnonymousUsageReporter(QObject):
    """Sends anonymous, grouped counters without persisting a device identifier."""

    def __init__(
        self,
        *,
        enabled: bool,
        endpoint: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self._endpoint = normalized_usage_endpoint(endpoint)
        self._session = secrets.token_urlsafe(24)
        self._pending_actions = 0
        self._started = False
        self._request_in_flight = False
        self._network = QNetworkAccessManager(self)
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.flush)
        self._update_state()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if not self._enabled:
            self._pending_actions = 0
            self._started = False
        self._update_state()

    def set_endpoint(self, endpoint: str) -> None:
        normalized = normalized_usage_endpoint(endpoint)
        if normalized == self._endpoint:
            return
        self._endpoint = normalized
        self._started = False
        self._update_state()

    def record_action(self) -> None:
        if self._enabled and self._endpoint:
            self._pending_actions += 1

    def flush(self) -> None:
        if not self._enabled or not self._endpoint or self._request_in_flight:
            return
        event = "heartbeat" if self._started else "start"
        actions = self._pending_actions
        self._pending_actions = 0
        self._started = True
        payload = usage_payload(self._session, event, actions)
        request = QNetworkRequest(QUrl(self._endpoint))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"User-Agent", b"HackMan3D-Control-Deck")
        self._request_in_flight = True
        reply = self._network.post(
            request,
            QByteArray(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        )

        def finished() -> None:
            self._request_in_flight = False
            reply.deleteLater()

        reply.finished.connect(finished)

    def _update_state(self) -> None:
        if self._enabled and self._endpoint:
            self._timer.start()
            QTimer.singleShot(1_000, self.flush)
        else:
            self._timer.stop()
