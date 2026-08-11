from __future__ import annotations

import sys

from PySide6.QtCore import QObject


if sys.platform == "darwin":
    import Network
    import dispatch


class MacLocalNetworkPermission(QObject):
    """Trigger the native macOS local-network permission request through Bonjour."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._browser: object | None = None

    def request(self) -> None:
        if sys.platform != "darwin" or self._browser is not None:
            return

        descriptor = Network.nw_browse_descriptor_create_bonjour_service(
            b"_hcd._tcp", b"local."
        )
        parameters = Network.nw_parameters_create()
        self._browser = Network.nw_browser_create(descriptor, parameters)
        Network.nw_browser_set_queue(self._browser, dispatch.dispatch_get_main_queue())
        Network.nw_browser_start(self._browser)

    def stop(self) -> None:
        if self._browser is not None:
            Network.nw_browser_cancel(self._browser)
        self._browser = None
