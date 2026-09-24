from __future__ import annotations

import json
import secrets
import ssl
import threading
import urllib.request
from urllib.parse import urlparse

import certifi
from PySide6.QtCore import QCoreApplication, QObject, QSettings, QTimer, Signal


def normalized_usage_endpoint(value: object) -> str:
    endpoint = str(value or "").strip()
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return endpoint


def usage_payload(session: str, event: str, actions: int, installation: str = "") -> dict[str, object]:
    if event not in {"start", "heartbeat", "stop"}:
        raise ValueError("Unsupported anonymous usage event")
    payload = {
        "schema": 1,
        "session": session,
        "event": event,
        "actions": max(0, int(actions)),
    }
    if installation:
        payload["installation"] = installation
    return payload


def installation_identifier(settings: QSettings) -> str:
    """Random local identifier; never derived from hardware or a user account."""
    value = settings.value("privacy/installationId", "", type=str)
    if not value:
        value = secrets.token_urlsafe(24)
        settings.setValue("privacy/installationId", value)
        settings.sync()
    return value


class AnonymousUsageReporter(QObject):
    """Sends grouped counters and a random installation identifier when enabled."""

    _request_finished = Signal(bool, str, int)

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
        self._installation = ""
        self._pending_actions = 0
        self._started = False
        self._request_in_flight = False
        self._request_finished.connect(self._on_request_finished)
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.flush)
        application = QCoreApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.stop)
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

    def stop(self) -> None:
        """Remove this session immediately when the application exits cleanly."""
        if not self._enabled or not self._endpoint:
            return
        self._timer.stop()
        payload = usage_payload(self._session, "stop", self._pending_actions, self._installation)
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        try:
            self._send(self._endpoint, body, timeout=2)
        except Exception:
            # A stale session expires server-side if the computer is offline.
            pass

    def flush(self) -> None:
        if not self._enabled or not self._endpoint or self._request_in_flight:
            return
        event = "heartbeat" if self._started else "start"
        actions = self._pending_actions
        self._pending_actions = 0
        if not self._installation:
            self._installation = installation_identifier(QSettings())
        payload = usage_payload(self._session, event, actions, self._installation)
        self._request_in_flight = True
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        endpoint = self._endpoint
        threading.Thread(
            target=self._post,
            args=(endpoint, body, event, actions),
            daemon=True,
            name="hcd-anonymous-usage",
        ).start()

    def _post(self, endpoint: str, body: bytes, event: str, actions: int) -> None:
        successful = False
        try:
            successful = self._send(endpoint, body, timeout=8)
        except Exception:
            # Usage sharing must never interrupt or slow down the application.
            successful = False
        self._request_finished.emit(successful, event, actions)

    @staticmethod
    def _send(endpoint: str, body: bytes, *, timeout: int) -> bool:
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "HackMan3D-Control-Deck",
            },
        )
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return 200 <= response.status < 300

    def _on_request_finished(self, successful: bool, event: str, actions: int) -> None:
        self._request_in_flight = False
        if successful:
            self._started = True
        else:
            self._pending_actions += actions

    def _update_state(self) -> None:
        if self._enabled and self._endpoint:
            self._timer.start()
            QTimer.singleShot(1_000, self.flush)
        else:
            self._timer.stop()
