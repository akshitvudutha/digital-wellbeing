from __future__ import annotations

import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import Optional


def get_app_user_data_dir() -> Path:
    path = Path.home() / "AppData" / "Local" / "DigitalWellbeing"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_windows_version() -> tuple[int, int, int]:
    try:
        ver = ctypes.windll.ntdll.RtlGetVersion
        class RTL_OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", ctypes.c_ulong),
                ("dwMajorVersion", ctypes.c_ulong),
                ("dwMinorVersion", ctypes.c_ulong),
                ("dwBuildNumber", ctypes.c_ulong),
                ("dwPlatformId", ctypes.c_ulong),
                ("szCSDVersion", ctypes.c_wchar * 128),
                ("wServicePackMajor", ctypes.c_ushort),
                ("wServicePackMinor", ctypes.c_ushort),
                ("wSuiteMask", ctypes.c_ushort),
                ("wProductType", ctypes.c_byte),
                ("wReserved", ctypes.c_byte),
            ]
        osvi = RTL_OSVERSIONINFOEXW()
        osvi.dwOSVersionInfoSize = ctypes.sizeof(osvi)
        ctypes.windll.ntdll.RtlGetVersion(ctypes.byref(osvi))
        return (osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber)
    except Exception:
        return (10, 0, 0)
