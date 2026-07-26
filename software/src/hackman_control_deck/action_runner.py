from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from .models import Action


class ActionRunner(QObject):
    action_failed = Signal(str)

    def run(self, action: Action) -> None:
        handlers: dict[str, Callable[[str], None]] = {
            "shortcut": self._shortcut,
            "system": self._system,
            "text": self._text,
            "open_url": self._open_url,
            "launch": self._launch,
        }
        handler = handlers.get(action.type)
        if handler is None or not action.value.strip():
            return
        try:
            handler(action.value.strip())
        except Exception as error:  # OS input and process errors need a UI-safe boundary.
            self.action_failed.emit(str(error))

    @staticmethod
    def _keyboard_controller():
        from pynput.keyboard import Controller

        return Controller()

    def _shortcut(self, value: str) -> None:
        from pynput.keyboard import Key

        aliases = {
            "CTRL": Key.ctrl,
            "CONTROL": Key.ctrl,
            "ALT": Key.alt,
            "SHIFT": Key.shift,
            "WIN": Key.cmd,
            "CMD": Key.cmd,
            "ENTER": Key.enter,
            "RETURN": Key.enter,
            "ESC": Key.esc,
            "ESCAPE": Key.esc,
            "SPACE": Key.space,
            "TAB": Key.tab,
            "BACKSPACE": Key.backspace,
            "DELETE": Key.delete,
            "UP": Key.up,
            "DOWN": Key.down,
            "LEFT": Key.left,
            "RIGHT": Key.right,
        }
        for number in range(1, 13):
            aliases[f"F{number}"] = getattr(Key, f"f{number}")

        keys = []
        for token in (part.strip() for part in value.split("+")):
            if not token:
                continue
            keys.append(aliases.get(token.upper(), token.lower()))
        if not keys:
            return

        controller = self._keyboard_controller()
        for key in keys:
            controller.press(key)
        for key in reversed(keys):
            controller.release(key)

    def _text(self, value: str) -> None:
        self._keyboard_controller().type(value)

    def _system(self, value: str) -> None:
        if sys.platform == "darwin":
            if value in {"volume_up", "volume_down", "volume_mute"}:
                self._macos_audio(value)
                return
            macos_keys = {
                "brightness_up": 2,
                "brightness_down": 3,
                "media_play_pause": 16,
                "media_next": 17,
                "media_previous": 18,
            }
            key_type = macos_keys.get(value)
            if key_type is None:
                raise ValueError(f"Unknown system command: {value}")
            self._macos_system_key(key_type)
            return

        from pynput.keyboard import Key

        media_keys = {
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "volume_mute": Key.media_volume_mute,
            "media_play_pause": Key.media_play_pause,
            "media_next": Key.media_next,
            "media_previous": Key.media_previous,
        }
        if value in media_keys:
            controller = self._keyboard_controller()
            controller.press(media_keys[value])
            controller.release(media_keys[value])
            return
        if value in {"brightness_up", "brightness_down"}:
            self._change_brightness(value == "brightness_up")
            return
        raise ValueError(f"Unknown system command: {value}")

    @staticmethod
    def _macos_audio(command: str) -> None:
        scripts = {
            "volume_up": """
                set currentVolume to output volume of (get volume settings)
                set newVolume to currentVolume + 6
                if newVolume > 100 then set newVolume to 100
                set volume output volume newVolume
            """,
            "volume_down": """
                set currentVolume to output volume of (get volume settings)
                set newVolume to currentVolume - 6
                if newVolume < 0 then set newVolume to 0
                set volume output volume newVolume
            """,
            "volume_mute": """
                set isMuted to output muted of (get volume settings)
                if isMuted then
                    set volume without output muted
                else
                    set volume with output muted
                end if
            """,
        }
        script = scripts.get(command)
        if script is None:
            raise ValueError(f"Unknown macOS audio command: {command}")
        result = subprocess.run(  # noqa: S603
            ["osascript", "-e", script],
            check=False,
            close_fds=True,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            error = result.stderr.strip() or "macOS could not change the audio setting"
            raise RuntimeError(error)

    @staticmethod
    def _macos_system_key(key_type: int) -> None:
        from AppKit import NSEvent, NSSystemDefined
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        from Quartz import CGEventPost, kCGHIDEventTap

        trusted = AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        if not trusted:
            raise PermissionError(
                "Allow HackMan3D Control Deck in System Settings > Privacy & Security > "
                "Accessibility, then restart the application."
            )

        for phase in (0xA, 0xB):
            flags = phase << 8
            event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                NSSystemDefined,
                (0, 0),
                flags,
                0,
                0,
                None,
                8,
                (key_type << 16) | flags,
                -1,
            )
            if event is None:
                raise RuntimeError("macOS could not create the system key event")
            CGEventPost(kCGHIDEventTap, event.CGEvent())

    @staticmethod
    def _change_brightness(increase: bool) -> None:
        if sys.platform == "win32":
            delta = 10 if increase else -10
            script = (
                "$b=Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightness;"
                "$m=Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightnessMethods;"
                f"$v=[Math]::Max(0,[Math]::Min(100,$b.CurrentBrightness+({delta})));"
                "$m|Invoke-CimMethod -MethodName WmiSetBrightness "
                "-Arguments @{Timeout=1;Brightness=[byte]$v}|Out-Null"
            )
            subprocess.run(  # noqa: S603
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
                close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return
        raise OSError("Brightness control is unavailable on this platform")

    def _open_url(self, value: str) -> None:
        url = QUrl.fromUserInput(value)
        if not QDesktopServices.openUrl(url):
            raise RuntimeError(f"Could not open {value}")

    @staticmethod
    def _launch(value: str) -> None:
        if sys.platform == "darwin":
            subprocess.Popen(["open", value], close_fds=True)  # noqa: S603
            return
        if sys.platform == "win32":
            os.startfile(value)  # type: ignore[attr-defined]  # noqa: S606
            return
        subprocess.Popen([value], close_fds=True)  # noqa: S603
