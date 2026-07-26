from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from typing import Callable

LAUNCH_AGENT_ID = "com.hackman3d.control-deck"


class MacMenuBarIcon:
    """Native menu-bar button used instead of Qt's unstable macOS tray menu."""

    def __init__(self, icon_path: Path, open_callback: Callable[[], None]) -> None:
        if sys.platform != "darwin":
            raise RuntimeError("MacMenuBarIcon is only available on macOS")

        import objc
        from AppKit import NSImage, NSStatusBar, NSSquareStatusItemLength
        from Foundation import NSObject, NSMakeSize

        class StatusItemTarget(NSObject):
            def initWithCallback_(target_self, callback):
                target_self = objc.super(StatusItemTarget, target_self).init()
                if target_self is not None:
                    target_self.callback = callback
                return target_self

            @objc.IBAction
            def statusItemClicked_(target_self, sender) -> None:
                del sender
                target_self.callback()

        self._status_bar = NSStatusBar.systemStatusBar()
        self._status_item = self._status_bar.statusItemWithLength_(NSSquareStatusItemLength)
        self._target = StatusItemTarget.alloc().initWithCallback_(open_callback)

        image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
        if image is not None:
            image.setSize_(NSMakeSize(18.0, 18.0))
            image.setTemplate_(True)

        button = self._status_item.button()
        button.setImage_(image)
        button.setToolTip_("HackMan3D Control Deck — click to open")
        button.setTarget_(self._target)
        button.setAction_("statusItemClicked:")

    def show(self) -> None:
        self._status_item.setVisible_(True)

    def hide(self) -> None:
        if self._status_item is not None:
            self._status_item.setVisible_(False)

    def dispose(self) -> None:
        if self._status_item is not None:
            self._status_bar.removeStatusItem_(self._status_item)
            self._status_item = None


class MacWindowMinimizeHandler:
    """Redirect the native yellow button before AppKit miniaturizes the window."""

    def __init__(self, window_title: str, callback: Callable[[], None]) -> None:
        if sys.platform != "darwin":
            raise RuntimeError("MacWindowMinimizeHandler is only available on macOS")

        import objc
        from Foundation import NSObject

        class MinimizeTarget(NSObject):
            def initWithCallback_(target_self, target_callback):
                target_self = objc.super(MinimizeTarget, target_self).init()
                if target_self is not None:
                    target_self.callback = target_callback
                return target_self

            @objc.IBAction
            def minimizeClicked_(target_self, sender) -> None:
                del sender
                target_self.callback()

        self._window_title = window_title
        self._target = MinimizeTarget.alloc().initWithCallback_(callback)
        self._button = None

    def install(self) -> bool:
        from AppKit import NSApplication, NSWindowMiniaturizeButton

        for window in NSApplication.sharedApplication().windows():
            if str(window.title()) != self._window_title:
                continue
            button = window.standardWindowButton_(NSWindowMiniaturizeButton)
            if button is None:
                continue
            button.setTarget_(self._target)
            button.setAction_("minimizeClicked:")
            self._button = button
            return True
        return False


def set_dock_icon_visible(visible: bool) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        from AppKit import (
            NSApplication,
            NSApplicationActivationPolicyAccessory,
            NSApplicationActivationPolicyRegular,
        )

        policy = (
            NSApplicationActivationPolicyRegular
            if visible
            else NSApplicationActivationPolicyAccessory
        )
        application = NSApplication.sharedApplication()
        if application.activationPolicy() != policy:
            application.setActivationPolicy_(policy)
        return True
    except ImportError:
        return False


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_ID}.plist"


def is_start_at_login_enabled() -> bool:
    return sys.platform == "darwin" and launch_agent_path().exists()


def set_start_at_login(enabled: bool) -> None:
    if sys.platform != "darwin":
        return

    path = launch_agent_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "Label": LAUNCH_AGENT_ID,
        "ProgramArguments": _launch_arguments(),
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_XML, sort_keys=True))
    temporary.replace(path)


def _launch_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        app_bundle = Path(sys.executable).resolve().parents[2]
        return ["/usr/bin/open", str(app_bundle)]
    return [sys.executable, "-m", "hackman_control_deck.main"]
