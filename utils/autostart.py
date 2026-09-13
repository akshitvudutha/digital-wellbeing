from __future__ import annotations

import os
import plistlib
import shlex
import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg
else:
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DigitalWellbeing"


def _executable_path() -> str:
    return subprocess_arguments_as_string()


def _subprocess_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    return [sys.executable, str(Path(__file__).parent.parent / "main.py"), "--background"]


def subprocess_arguments_as_string() -> str:
    if sys.platform == "win32":
        return " ".join(f'"{part}"' if " " in part else part for part in _subprocess_arguments())
    return shlex.join(_subprocess_arguments())


def _autostart_file() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / "io.github.nyw.autostart.plist"
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "autostart" / "digital-wellbeing.desktop"


def enable_autostart() -> None:
    if sys.platform == "darwin":
        path = _autostart_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            plistlib.dump(
                {
                    "Label": "io.github.nyw.autostart",
                    "ProgramArguments": _subprocess_arguments(),
                    "RunAtLoad": True,
                },
                stream,
            )
        return
    if sys.platform.startswith("linux"):
        path = _autostart_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Not Your Wellbeing\n"
            f"Exec={subprocess_arguments_as_string()}\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
        return
    if winreg is None:
        raise RuntimeError(f"Autostart is unsupported on {sys.platform}")
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _executable_path())
    except OSError as exc:
        raise RuntimeError(f"Failed to enable autostart: {exc}") from exc


def disable_autostart() -> None:
    if sys.platform != "win32":
        _autostart_file().unlink(missing_ok=True)
        return
    if winreg is None:
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise RuntimeError(f"Failed to disable autostart: {exc}") from exc


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return _autostart_file().is_file()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
