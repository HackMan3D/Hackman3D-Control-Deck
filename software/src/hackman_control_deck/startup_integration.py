from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

from .macos_integration import (
    is_start_at_login_enabled as macos_start_enabled,
)
from .macos_integration import set_start_at_login as set_macos_start


WINDOWS_VALUE_NAME = "HackMan3D Control Deck"
LINUX_DESKTOP_NAME = "hackman3d-control-deck.desktop"


def is_start_at_login_enabled() -> bool:
    if sys.platform == "darwin":
        return macos_start_enabled()
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
            ) as key:
                winreg.QueryValueEx(key, WINDOWS_VALUE_NAME)
            return True
        except (FileNotFoundError, OSError):
            return False
    if sys.platform.startswith("linux"):
        return linux_autostart_path().exists()
    return False


def set_start_at_login(enabled: bool) -> None:
    if sys.platform == "darwin":
        set_macos_start(enabled)
        return
    if sys.platform == "win32":
        _set_windows_start(enabled)
        return
    if sys.platform.startswith("linux"):
        _set_linux_start(enabled)


def linux_autostart_path() -> Path:
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_root / "autostart" / LINUX_DESKTOP_NAME


def _launch_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    return [sys.executable, "-m", "hackman_control_deck.main", "--background"]


def _set_windows_start(enabled: bool) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        if enabled:
            winreg.SetValueEx(
                key,
                WINDOWS_VALUE_NAME,
                0,
                winreg.REG_SZ,
                subprocess.list2cmdline(_launch_arguments()),
            )
        else:
            try:
                winreg.DeleteValue(key, WINDOWS_VALUE_NAME)
            except FileNotFoundError:
                pass


def _set_linux_start(enabled: bool) -> None:
    path = linux_autostart_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "[Desktop Entry]",
                "Type=Application",
                "Name=HackMan3D Control Deck",
                f"Exec={shlex.join(_launch_arguments())}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            )
        ),
        encoding="utf-8",
    )
