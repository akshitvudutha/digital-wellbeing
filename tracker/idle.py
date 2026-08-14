from __future__ import annotations

import ctypes
import ctypes.wintypes
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.constants import AppCategory


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.wintypes.DWORD),
        ("Gamepad", _XINPUT_GAMEPAD),
    ]


class _JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("dwXpos", ctypes.wintypes.DWORD),
        ("dwYpos", ctypes.wintypes.DWORD),
        ("dwZpos", ctypes.wintypes.DWORD),
        ("dwRpos", ctypes.wintypes.DWORD),
        ("dwUpos", ctypes.wintypes.DWORD),
        ("dwVpos", ctypes.wintypes.DWORD),
        ("dwButtons", ctypes.wintypes.DWORD),
        ("dwButtonNumber", ctypes.wintypes.DWORD),
        ("dwPOV", ctypes.wintypes.DWORD),
        ("dwReserved1", ctypes.wintypes.DWORD),
        ("dwReserved2", ctypes.wintypes.DWORD),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetLastInputInfo.argtypes = [ctypes.c_void_p]
_user32.GetLastInputInfo.restype = ctypes.wintypes.BOOL
_kernel32.GetTickCount.argtypes = []
_kernel32.GetTickCount.restype = ctypes.wintypes.DWORD

_LASTINPUTINFO_SIZE = ctypes.sizeof(_LASTINPUTINFO)
_TICK_MAX = 0xFFFFFFFF

# Load XInput DLL (try 1.4 -> 9.1.0 -> 1.3)
_xinput = None
for _dll_name in ("xinput1_4.dll", "xinput9_1_0.dll", "xinput1_3.dll"):
    try:
        _xinput = ctypes.WinDLL(_dll_name)
        _xinput.XInputGetState.argtypes = [ctypes.wintypes.DWORD, ctypes.POINTER(_XINPUT_STATE)]
        _xinput.XInputGetState.restype = ctypes.wintypes.DWORD
        break
    except Exception:
        pass

# Load WinMM DLL for joystick fallback
_winmm = None
try:
    _winmm = ctypes.WinDLL("winmm.dll")
    _winmm.joyGetPosEx.argtypes = [ctypes.c_uint, ctypes.POINTER(_JOYINFOEX)]
    _winmm.joyGetPosEx.restype = ctypes.c_uint
except Exception:
    pass

JOY_RETURNALL = 0x000000FF

_last_xinput_packets: list[Optional[int]] = [None] * 4
_last_joy_states: list[Optional[tuple[int, int, int, int, int, int]]] = [None] * 2
_last_controller_activity_tick: int = 0


def _check_controller_activity(tick_now: int) -> None:
    global _last_controller_activity_tick

    # 1. Check XInput Gamepads (ports 0..3)
    if _xinput is not None:
        for i in range(4):
            state = _XINPUT_STATE()
            if _xinput.XInputGetState(i, ctypes.byref(state)) == 0:
                pkt = state.dwPacketNumber
                prev_pkt = _last_xinput_packets[i]
                _last_xinput_packets[i] = pkt
                if prev_pkt is not None and pkt != prev_pkt:
                    _last_controller_activity_tick = tick_now
            else:
                _last_xinput_packets[i] = None

    # 2. Check WinMM Joysticks (ports 0..1)
    if _winmm is not None:
        for j in range(2):
            ji = _JOYINFOEX()
            ji.dwSize = ctypes.sizeof(_JOYINFOEX)
            ji.dwFlags = JOY_RETURNALL
            if _winmm.joyGetPosEx(j, ctypes.byref(ji)) == 0:
                # Quantize axes to avoid analog drift noise triggering activity
                state_tuple = (
                    ji.dwXpos >> 10,
                    ji.dwYpos >> 10,
                    ji.dwZpos >> 10,
                    ji.dwRpos >> 10,
                    ji.dwButtons,
                    ji.dwPOV,
                )
                prev_state = _last_joy_states[j]
                _last_joy_states[j] = state_tuple
                if prev_state is not None and state_tuple != prev_state:
                    _last_controller_activity_tick = tick_now
            else:
                _last_joy_states[j] = None


def _elapsed_ms(tick_now: int, last_input: int) -> int:
    if tick_now >= last_input:
        return tick_now - last_input
    return (_TICK_MAX - last_input) + tick_now + 1


def get_idle_seconds() -> float:
    lii = _LASTINPUTINFO()
    lii.cbSize = _LASTINPUTINFO_SIZE
    has_lii = _user32.GetLastInputInfo(ctypes.byref(lii))

    tick_now: int = _kernel32.GetTickCount()
    _check_controller_activity(tick_now)

    last_win32: int = lii.dwTime if has_lii else tick_now
    elapsed_win32 = _elapsed_ms(tick_now, last_win32)

    elapsed_ctrl = (
        _elapsed_ms(tick_now, _last_controller_activity_tick)
        if _last_controller_activity_tick > 0
        else elapsed_win32
    )

    elapsed_ms = min(elapsed_win32, elapsed_ctrl)
    return max(0.0, elapsed_ms / 1000.0)


def is_idle(
    threshold_s: float,
    current_category: Optional[AppCategory] = None,
    is_media_playing: bool = False,
    mode: str = "smart",
    media_timeout_s: float = 900.0,
) -> bool:
    idle_s = get_idle_seconds()

    if is_media_playing:
        if mode == "media":
            return False
        elif mode == "strict":
            return idle_s >= threshold_s
        else:  # smart
            # Activity-aware multipliers when media is playing (entertainment vs gaming)
            # Cap the threshold at media_timeout_s (e.g. 120 minutes)
            try:
                from core.constants import AppCategory as _Cat
                multiplier = 1.0
                if current_category == _Cat.GAMING:
                    multiplier = 2.5
                elif current_category == _Cat.ENTERTAINMENT:
                    multiplier = 3.0
            except Exception:
                multiplier = 1.0
            
            # Allow media_timeout_s to override the multiplier if it's longer
            effective_threshold = max(threshold_s * multiplier, media_timeout_s)
            return idle_s >= effective_threshold

    if current_category is not None:
        from core.constants import AppCategory as _Cat
        if current_category == _Cat.GAMING:
            return idle_s >= threshold_s * 2.5

    return idle_s >= threshold_s
