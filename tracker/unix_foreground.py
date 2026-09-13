from __future__ import annotations

import os
import sys
from typing import Any

import psutil


def get_foreground_info() -> dict[str, Any] | None:
    if sys.platform == "darwin":
        return _get_macos_foreground_info()
    if sys.platform.startswith("linux"):
        return _get_x11_foreground_info()
    return None


def _get_macos_foreground_info() -> dict[str, Any] | None:
    try:
        import Quartz
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None

        pid = int(app.processIdentifier())
        executable_url = app.executableURL()
        exe_path = str(executable_url.path()) if executable_url else ""
        process_name = os.path.basename(exe_path) or str(app.localizedName() or "Unknown")
        title = ""
        fullscreen = False

        options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
        windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
        for window in windows:
            if int(window.get(Quartz.kCGWindowOwnerPID, -1)) != pid:
                continue
            if int(window.get(Quartz.kCGWindowLayer, 1)) != 0:
                continue
            title = str(window.get(Quartz.kCGWindowName, "") or "")
            bounds = window.get(Quartz.kCGWindowBounds, {}) or {}
            screen = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
            fullscreen = (
                float(bounds.get("Width", 0)) >= float(screen.size.width)
                and float(bounds.get("Height", 0)) >= float(screen.size.height)
            )
            break

        return {
            "process_name": process_name,
            "exe_path": exe_path,
            "pid": pid,
            "window_title": title or str(app.localizedName() or process_name),
            "hwnd": 0,
            "is_fullscreen": fullscreen,
        }
    except Exception:  # noqa: BLE001 - platform APIs fail for permissions and session state
        return None


def _get_x11_foreground_info() -> dict[str, Any] | None:
    if not os.environ.get("DISPLAY"):
        return None
    display = None
    try:
        from Xlib import X, Xatom
        from Xlib import display as xdisplay

        display = xdisplay.Display()
        root = display.screen().root
        active_atom = display.intern_atom("_NET_ACTIVE_WINDOW")
        active = root.get_full_property(active_atom, X.AnyPropertyType)
        if active is None or not active.value:
            return None
        window = display.create_resource_object("window", int(active.value[0]))

        pid_atom = display.intern_atom("_NET_WM_PID")
        pid_prop = window.get_full_property(pid_atom, Xatom.CARDINAL)
        if pid_prop is None or not pid_prop.value:
            return None
        pid = int(pid_prop.value[0])

        utf8 = display.intern_atom("UTF8_STRING")
        name_atom = display.intern_atom("_NET_WM_NAME")
        name_prop = window.get_full_property(name_atom, utf8)
        if name_prop is not None and name_prop.value:
            raw_title = name_prop.value
            title = raw_title.decode("utf-8", errors="replace") if isinstance(raw_title, bytes) else str(raw_title)
        else:
            title = str(window.get_wm_name() or "")

        proc = psutil.Process(pid)
        process_name = proc.name()
        try:
            exe_path = proc.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            exe_path = ""

        state_atom = display.intern_atom("_NET_WM_STATE")
        fullscreen_atom = display.intern_atom("_NET_WM_STATE_FULLSCREEN")
        state = window.get_full_property(state_atom, X.AnyPropertyType)
        fullscreen = bool(state is not None and fullscreen_atom in state.value)

        return {
            "process_name": process_name,
            "exe_path": exe_path,
            "pid": pid,
            "window_title": title or process_name,
            "hwnd": int(window.id),
            "is_fullscreen": fullscreen,
        }
    except Exception:  # noqa: BLE001 - X11 may disappear during logout/session changes
        return None
    finally:
        if display is not None:
            try:
                display.close()
            except Exception:  # noqa: S110, BLE001 - best-effort connection cleanup
                pass
