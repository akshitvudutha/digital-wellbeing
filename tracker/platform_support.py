from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Capability:
    name: str
    available: bool
    detail: str

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def _module_available(name: str, finder: Callable[[str], object | None]) -> bool:
    try:
        return finder(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def get_tracking_capabilities(
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> list[Capability]:
    """Describe tracking backends without collecting any activity data."""
    platform_id = (platform_name or sys.platform).lower()
    env = os.environ if environ is None else environ

    if platform_id.startswith("win"):
        foreground = _module_available("win32gui", finder) and _module_available("win32process", finder)
        return [
            Capability("foreground_tracking", foreground, "Win32 foreground-window API" if foreground else "Install the Windows requirements (pywin32)."),
            Capability("idle_detection", True, "Win32 last-input API"),
            Capability("session_events", foreground, "Win32 session notifications" if foreground else "Install the Windows requirements (pywin32)."),
            Capability("media_detection", _module_available("winrt", finder), "Windows media sessions"),
        ]

    if platform_id == "darwin":
        cocoa = _module_available("AppKit", finder)
        quartz = _module_available("Quartz", finder)
        return [
            Capability("foreground_tracking", cocoa and quartz, "AppKit and Quartz; Screen Recording permission may be required for window titles."),
            Capability("idle_detection", quartz, "Quartz input-event timer" if quartz else "Install the macOS requirements (PyObjC Quartz)."),
            Capability("session_events", False, "Native lock/sleep event monitoring is not available yet; polling remains active."),
            Capability("media_detection", False, "Native media-session detection is currently Windows-only."),
        ]

    if platform_id.startswith("linux"):
        has_x11 = bool(env.get("DISPLAY")) and _module_available("Xlib", finder)
        wayland_only = bool(env.get("WAYLAND_DISPLAY")) and not env.get("DISPLAY")
        if wayland_only:
            foreground_detail = "Wayland blocks global window inspection; use an X11 session until a desktop portal is available."
        elif not env.get("DISPLAY"):
            foreground_detail = "No X11 DISPLAY was detected."
        elif not _module_available("Xlib", finder):
            foreground_detail = "Install the Linux requirements (python-xlib)."
        else:
            foreground_detail = "X11 EWMH active-window API"
        return [
            Capability("foreground_tracking", has_x11, foreground_detail),
            Capability("idle_detection", has_x11, "XScreenSaver idle timer" if has_x11 else foreground_detail),
            Capability("session_events", False, "Native lock/sleep event monitoring is not available yet; polling remains active."),
            Capability("media_detection", False, "Native media-session detection is currently Windows-only."),
        ]

    return [
        Capability("foreground_tracking", False, f"Unsupported platform: {platform_id}"),
        Capability("idle_detection", False, f"Unsupported platform: {platform_id}"),
        Capability("session_events", False, f"Unsupported platform: {platform_id}"),
        Capability("media_detection", False, f"Unsupported platform: {platform_id}"),
    ]
