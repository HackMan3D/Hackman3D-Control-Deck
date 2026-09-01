from __future__ import annotations

import os
import ctypes
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

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

    def set_continuous_value(self, mode: str, value: int) -> None:
        level = max(0, min(100, int(value)))
        try:
            if mode == "volume":
                self._set_absolute_volume(level)
            elif mode == "brightness":
                self._set_absolute_brightness(level)
            elif mode == "microphone":
                self._set_absolute_microphone(level)
        except Exception as error:
            self.action_failed.emit(str(error))

    def continuous_value(self, mode: str) -> int | None:
        try:
            if mode == "volume":
                return self._absolute_volume()
            if mode == "brightness":
                return self._absolute_brightness()
            if mode == "microphone":
                return self._absolute_microphone()
        except Exception:
            return None
        return None

    def adjust_continuous_value(self, mode: str, delta: int) -> None:
        current = self.continuous_value(mode)
        if current is None:
            return
        self.set_continuous_value(mode, current + int(delta))

    @staticmethod
    def _set_absolute_volume(level: int) -> None:
        if sys.platform == "darwin":
            result = subprocess.run(  # noqa: S603
                ["osascript", "-e", f"set volume output volume {level}"],
                check=False,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Could not set the volume")
            return
        if sys.platform == "win32":
            ActionRunner._windows_endpoint_volume().SetMasterVolumeLevelScalar(
                level / 100.0,
                None,
            )
            return
        if sys.platform.startswith("linux"):
            ActionRunner._linux_set_audio_level("sink", level)
            return
        raise OSError("Absolute volume control is not available on this platform yet")

    @staticmethod
    def _absolute_volume() -> int:
        if sys.platform == "darwin":
            result = subprocess.run(  # noqa: S603
                ["osascript", "-e", "output volume of (get volume settings)"],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            return max(0, min(100, round(float(result.stdout.strip()))))
        if sys.platform == "win32":
            scalar = ActionRunner._windows_endpoint_volume().GetMasterVolumeLevelScalar()
            return max(0, min(100, round(float(scalar) * 100)))
        if sys.platform.startswith("linux"):
            return ActionRunner._linux_audio_level("sink")
        raise OSError("Volume level is unavailable on this platform")

    @staticmethod
    def _set_absolute_microphone(level: int) -> None:
        if sys.platform == "darwin":
            result = subprocess.run(  # noqa: S603
                ["osascript", "-e", f"set volume input volume {level}"],
                check=False,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Could not set microphone volume")
            return
        if sys.platform == "win32":
            ActionRunner._windows_microphone_endpoint().SetMasterVolumeLevelScalar(
                level / 100.0,
                None,
            )
            return
        if sys.platform.startswith("linux"):
            ActionRunner._linux_set_audio_level("source", level)
            return
        raise OSError("Microphone level is unavailable on this platform")

    @staticmethod
    def _absolute_microphone() -> int:
        if sys.platform == "darwin":
            result = subprocess.run(  # noqa: S603
                ["osascript", "-e", "input volume of (get volume settings)"],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            return max(0, min(100, round(float(result.stdout.strip()))))
        if sys.platform == "win32":
            scalar = ActionRunner._windows_microphone_endpoint().GetMasterVolumeLevelScalar()
            return max(0, min(100, round(float(scalar) * 100)))
        if sys.platform.startswith("linux"):
            return ActionRunner._linux_audio_level("source")
        raise OSError("Microphone level is unavailable on this platform")

    @staticmethod
    def _windows_endpoint_volume():
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint

        from comtypes import CLSCTX_ALL
        from ctypes import POINTER, cast
        from pycaw.pycaw import IAudioEndpointVolume

        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    @staticmethod
    def _set_absolute_brightness(level: int) -> None:
        if sys.platform == "darwin":
            from Quartz import CGMainDisplayID

            framework = ctypes.cdll.LoadLibrary(
                "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
            )
            setter = framework.DisplayServicesSetBrightness
            setter.argtypes = [ctypes.c_uint32, ctypes.c_float]
            setter.restype = ctypes.c_int
            if setter(CGMainDisplayID(), ctypes.c_float(level / 100.0)) != 0:
                raise RuntimeError("macOS could not set the display brightness")
            return
        if sys.platform == "win32":
            script = (
                "$m=Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightnessMethods;"
                f"$m|Invoke-CimMethod -MethodName WmiSetBrightness -Arguments "
                f"@{{Timeout=1;Brightness=[byte]{level}}}|Out-Null"
            )
            subprocess.run(  # noqa: S603
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
                close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return
        if sys.platform.startswith("linux"):
            result = subprocess.run(
                ["brightnessctl", "set", f"{level}%"],
                check=False,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Could not set display brightness")
            return
        raise OSError("Brightness control is unavailable on this platform")

    @staticmethod
    def _absolute_brightness() -> int:
        if sys.platform == "darwin":
            from Quartz import CGMainDisplayID

            framework = ctypes.cdll.LoadLibrary(
                "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
            )
            getter = framework.DisplayServicesGetBrightness
            getter.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
            getter.restype = ctypes.c_int
            value = ctypes.c_float()
            if getter(CGMainDisplayID(), ctypes.byref(value)) != 0:
                raise RuntimeError("macOS could not read the display brightness")
            return max(0, min(100, round(value.value * 100)))
        if sys.platform == "win32":
            script = (
                "(Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightness | "
                "Select-Object -First 1 -ExpandProperty CurrentBrightness)"
            )
            result = subprocess.run(  # noqa: S603
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return max(0, min(100, round(float(result.stdout.strip()))))
        if sys.platform.startswith("linux"):
            result = subprocess.run(
                ["brightnessctl", "-m"],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            matches = re.findall(r"(\d+)%", result.stdout)
            if not matches:
                raise RuntimeError("Could not read display brightness")
            return max(0, min(100, int(matches[-1])))
        raise OSError("Brightness level is unavailable on this platform")

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
        if value in {"microphone_up", "microphone_down"}:
            current = self._absolute_microphone()
            step = 5 if value == "microphone_up" else -5
            self._set_absolute_microphone(max(0, min(100, current + step)))
            return
        if sys.platform == "darwin":
            if value in {"shutdown", "restart", "lock", "sleep"}:
                self._macos_power(value)
                return
            if value == "microphone_mute":
                self._macos_microphone_mute()
                return
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

        if sys.platform.startswith("linux"):
            self._linux_system(value)
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
        if sys.platform == "win32" and value in {"shutdown", "restart", "lock", "sleep"}:
            self._windows_power(value)
            return
        if sys.platform == "win32" and value == "microphone_mute":
            endpoint = self._windows_microphone_endpoint()
            endpoint.SetMute(not bool(endpoint.GetMute()), None)
            return
        raise ValueError(f"Unknown system command: {value}")

    @staticmethod
    def _macos_microphone_mute() -> None:
        script = """
            set currentInput to input volume of (get volume settings)
            if currentInput is 0 then
                set volume input volume 50
            else
                set volume input volume 0
            end if
        """
        result = subprocess.run(  # noqa: S603
            ["osascript", "-e", script],
            check=False,
            close_fds=True,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "macOS could not mute the microphone")

    @staticmethod
    def _windows_microphone_endpoint():
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetMicrophone()
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint

        from comtypes import CLSCTX_ALL
        from ctypes import POINTER, cast
        from pycaw.pycaw import IAudioEndpointVolume

        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    @staticmethod
    def _linux_audio_target(kind: str) -> tuple[str, str]:
        if kind == "source":
            return "@DEFAULT_AUDIO_SOURCE@", "@DEFAULT_SOURCE@"
        return "@DEFAULT_AUDIO_SINK@", "@DEFAULT_SINK@"

    @staticmethod
    def _linux_audio_level(kind: str) -> int:
        wpctl_target, pactl_target = ActionRunner._linux_audio_target(kind)
        if shutil.which("wpctl"):
            result = subprocess.run(
                ["wpctl", "get-volume", wpctl_target],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)", result.stdout)
            if match:
                return max(0, min(100, round(float(match.group(1)) * 100)))
        if shutil.which("pactl"):
            command = "get-source-volume" if kind == "source" else "get-sink-volume"
            result = subprocess.run(
                ["pactl", command, pactl_target],
                check=True,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            match = re.search(r"(\d+)%", result.stdout)
            if match:
                return max(0, min(100, int(match.group(1))))
        raise OSError("Install wpctl or pactl to control audio on Linux")

    @staticmethod
    def _linux_set_audio_level(kind: str, level: int) -> None:
        wpctl_target, pactl_target = ActionRunner._linux_audio_target(kind)
        if shutil.which("wpctl"):
            arguments = ["wpctl", "set-volume", wpctl_target, f"{level}%"]
        elif shutil.which("pactl"):
            action = "set-source-volume" if kind == "source" else "set-sink-volume"
            arguments = ["pactl", action, pactl_target, f"{level}%"]
        else:
            raise OSError("Install wpctl or pactl to control audio on Linux")
        subprocess.run(arguments, check=True, close_fds=True)

    @staticmethod
    def _linux_system(command: str) -> None:
        audio = {
            "volume_up": ("sink", 5),
            "volume_down": ("sink", -5),
            "microphone_up": ("source", 5),
            "microphone_down": ("source", -5),
        }
        if command in audio:
            kind, delta = audio[command]
            current = ActionRunner._linux_audio_level(kind)
            ActionRunner._linux_set_audio_level(kind, max(0, min(100, current + delta)))
            return
        if command in {"volume_mute", "microphone_mute"}:
            kind = "source" if command == "microphone_mute" else "sink"
            wpctl_target, pactl_target = ActionRunner._linux_audio_target(kind)
            if shutil.which("wpctl"):
                arguments = ["wpctl", "set-mute", wpctl_target, "toggle"]
            elif shutil.which("pactl"):
                action = "set-source-mute" if kind == "source" else "set-sink-mute"
                arguments = ["pactl", action, pactl_target, "toggle"]
            else:
                raise OSError("Install wpctl or pactl to control audio on Linux")
            subprocess.run(arguments, check=True, close_fds=True)
            return
        media = {
            "media_play_pause": "play-pause",
            "media_next": "next",
            "media_previous": "previous",
        }
        if command in media:
            if not shutil.which("playerctl"):
                raise OSError("Install playerctl to control media playback on Linux")
            subprocess.run(["playerctl", media[command]], check=True, close_fds=True)
            return
        if command in {"brightness_up", "brightness_down"}:
            ActionRunner._change_brightness(command == "brightness_up")
            return
        power = {
            "lock": ["loginctl", "lock-session"],
            "sleep": ["systemctl", "suspend"],
            "restart": ["systemctl", "reboot"],
            "shutdown": ["systemctl", "poweroff"],
        }
        if command in power:
            subprocess.run(power[command], check=True, close_fds=True)
            return
        raise ValueError(f"Unknown system command: {command}")

    @staticmethod
    def _macos_power(command: str) -> None:
        if command == "lock":
            result = subprocess.run(  # noqa: S603
                ["/usr/bin/pmset", "displaysleepnow"],
                check=False,
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "macOS could not lock the session")
            return
        scripts = {
            "shutdown": 'tell application "System Events" to shut down',
            "restart": 'tell application "System Events" to restart',
            "sleep": 'tell application "System Events" to sleep',
        }
        script = scripts.get(command)
        if script is None:
            raise ValueError(f"Unknown macOS power command: {command}")
        result = subprocess.run(  # noqa: S603
            ["osascript", "-e", script],
            check=False,
            close_fds=True,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "macOS could not run the power command")

    @staticmethod
    def _windows_power(command: str) -> None:
        commands = {
            "shutdown": ["shutdown.exe", "/s", "/t", "0"],
            "restart": ["shutdown.exe", "/r", "/t", "0"],
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        }
        arguments = commands.get(command)
        if arguments is None:
            raise ValueError(f"Unknown Windows power command: {command}")
        subprocess.run(  # noqa: S603
            arguments,
            check=True,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

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
        if sys.platform.startswith("linux"):
            direction = "+5%" if increase else "5%-"
            subprocess.run(
                ["brightnessctl", "set", direction],
                check=True,
                close_fds=True,
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
        if sys.platform.startswith("linux") and value.casefold().endswith(".desktop"):
            if shutil.which("gio"):
                subprocess.Popen(["gio", "launch", value], close_fds=True)  # noqa: S603
            else:
                subprocess.Popen(  # noqa: S603
                    ["gtk-launch", Path(value).stem], close_fds=True
                )
            return
        subprocess.Popen([value], close_fds=True)  # noqa: S603
