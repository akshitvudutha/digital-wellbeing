"""
shutdown.py — Windows Power Action Executor for Digital Wellbeing Platform v2.4.

Provides a safe interface for triggering automated PC power actions
(shutdown, sleep, hibernate, lock) with pre-action hook execution
and structured logging.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import subprocess
import sys
from datetime import datetime
from typing import Optional

logger = logging.getLogger("digital_wellbeing.shutdown")

# Valid power actions
VALID_ACTIONS = {"shutdown", "sleep", "hibernate", "lock", "cancel"}

# Minimum countdown floor to prevent accidental immediate execution
MIN_COUNTDOWN_SECONDS = 10

def _enable_shutdown_privilege() -> bool:
    if sys.platform != "win32":
        return False
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY = 0x0008
    SE_PRIVILEGE_ENABLED = 0x00000002
    
    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]
        
    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]
        
    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
        
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
        logger.warning(f"Failed to open process token. Error: {ctypes.get_last_error()}")
        return False
        
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, "SeShutdownPrivilege", ctypes.byref(luid)):
        logger.warning(f"Failed to lookup SeShutdownPrivilege. Error: {ctypes.get_last_error()}")
        kernel32.CloseHandle(token)
        return False
        
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    
    res = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
    if not res:
        logger.warning(f"AdjustTokenPrivileges failed. Error: {ctypes.get_last_error()}")
    
    kernel32.CloseHandle(token)
    return bool(res)



class ShutdownManager:
    def __init__(self) -> None:
        self._hooks: list[callable] = []

    def register_pre_shutdown_hook(self, callback: callable) -> None:
        self._hooks.append(callback)
        logger.debug("Pre-shutdown hook registered: %s", callback)

    def _run_hooks(self) -> None:
        for hook in self._hooks:
            try:
                hook()
            except Exception as exc:
                logger.error("Pre-shutdown hook error (%r): %s", hook, exc)

    @staticmethod
    def validate_action(action: str) -> bool:
        """Validate that the action is a known, safe power action."""
        return isinstance(action, str) and action.lower() in VALID_ACTIONS

    def execute_action(self, action: str) -> bool:
        """Execute a power action by name. Returns True on success, False on failure.
        
        Supported actions: shutdown, sleep, hibernate, lock, cancel.
        """
        ts = datetime.now().isoformat()
        action = (action or "").lower().strip()

        logger.info("[SLEEPGUARD_ACTION] execute_action() entered at %s with action='%s'", ts, action)

        if not self.validate_action(action):
            logger.error(
                "[SLEEPGUARD_ACTION] SAFETY GUARD: Refused to execute invalid/unknown action '%s'. "
                "No destructive power action will be taken.", action
            )
            return False

        if action == "cancel":
            logger.info("[SLEEPGUARD_ACTION] Action is 'cancel' — no power action will be taken.")
            return True

        # Run pre-action hooks (e.g., save state, close sessions)
        logger.info("[SLEEPGUARD_ACTION] Running %d pre-shutdown hooks...", len(self._hooks))
        self._run_hooks()
        logger.info("[SLEEPGUARD_ACTION] Pre-shutdown hooks completed.")

        if action == "shutdown":
            return self._execute_shutdown()
        elif action == "sleep":
            return self._execute_sleep()
        elif action == "hibernate":
            return self._execute_hibernate()
        elif action == "lock":
            return self._execute_lock()

        # Should be unreachable due to validation above, but defend anyway
        logger.error("[SLEEPGUARD_ACTION] SAFETY GUARD: Action '%s' passed validation but has no handler.", action)
        return False

    def shutdown_now(self) -> bool:
        """Legacy method — calls execute_action('shutdown') for backward compatibility."""
        logger.warning("ShutdownManager.shutdown_now() called — delegating to execute_action('shutdown')")
        return self.execute_action("shutdown")

    def cancel_shutdown(self) -> None:
        """Cancel any pending scheduled shutdown command."""
        if sys.platform != "win32":
            logger.info("No scheduled NYW shutdown command exists on this platform.")
            return
        logger.info("Cancelling any pending scheduled shutdown...")
        try:
            subprocess.run(
                ["shutdown", "/a"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            logger.error("Failed to cancel shutdown: %s", exc)

    @staticmethod
    def _execute_shutdown() -> bool:
        ts = datetime.now().isoformat()
        logger.warning("[SLEEPGUARD_ACTION] Executing SHUTDOWN at %s", ts)
        
        if sys.platform == "darwin":
            command = ["osascript", "-e", 'tell application "System Events" to shut down']
        elif sys.platform.startswith("linux"):
            command = ["systemctl", "poweroff"]
        else:
            command = [r"C:\Windows\System32\shutdown.exe", "/s", "/f", "/t", "0"]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("shutdown command failed (exit %d): %s", exc.returncode, exc.stderr)
            return False
        except OSError as exc:
            logger.error("Failed to invoke shutdown command: %s", exc)
            return False

        logger.info("[SLEEPGUARD_ACTION] Shutdown command accepted by the operating system.")
        return True

    @staticmethod
    def _execute_sleep() -> bool:
        ts = datetime.now().isoformat()
        logger.info("[SLEEPGUARD_ACTION] Executing SLEEP (suspend) at %s", ts)
        
        if sys.platform == "darwin":
            return ShutdownManager._run_power_command(["pmset", "sleepnow"], "sleep")
        if sys.platform.startswith("linux"):
            return ShutdownManager._run_power_command(["systemctl", "suspend"], "sleep")

        # Required for both Sleep and Hibernate via SetSuspendState
        _enable_shutdown_privilege()
        
        try:
            powrprof = ctypes.WinDLL('powrprof', use_last_error=True)
            result = powrprof.SetSuspendState(
                ctypes.c_bool(False),  # bHibernate = False → sleep
                ctypes.c_bool(True),   # bForce = True
                ctypes.c_bool(False),  # bWakeupEventsDisabled = False
            )
            if result:
                logger.info("[SLEEPGUARD_ACTION] Sleep command accepted by Windows.")
                return True
            else:
                err = ctypes.get_last_error()
                logger.error("[SLEEPGUARD_ACTION] SetSuspendState returned False for sleep. Win32 Error: %s", err)
                return False
        except Exception as exc:
            logger.error("[SLEEPGUARD_ACTION] Failed to execute sleep: %s", exc)
            return False

    @staticmethod
    def _execute_hibernate() -> bool:
        ts = datetime.now().isoformat()
        logger.info("[SLEEPGUARD_ACTION] Executing HIBERNATE at %s", ts)
        if sys.platform == "darwin":
            logger.error("Hibernate is not exposed as a supported macOS user action.")
            return False
        if sys.platform.startswith("linux"):
            return ShutdownManager._run_power_command(["systemctl", "hibernate"], "hibernate")

        _enable_shutdown_privilege()
        try:
            powrprof = ctypes.WinDLL('powrprof', use_last_error=True)
            result = powrprof.SetSuspendState(
                ctypes.c_bool(True),   # bHibernate = True → hibernate
                ctypes.c_bool(True),   # bForce = True
                ctypes.c_bool(False),  # bWakeupEventsDisabled = False
            )
            if result:
                logger.info("[SLEEPGUARD_ACTION] Hibernate command accepted by Windows.")
                return True
            else:
                err = ctypes.get_last_error()
                logger.error("[SLEEPGUARD_ACTION] SetSuspendState returned False for hibernate. Win32 Error: %s", err)
                return False
        except Exception as exc:
            logger.error("[SLEEPGUARD_ACTION] Failed to execute hibernate: %s", exc)
            return False

    @staticmethod
    def _execute_lock() -> bool:
        ts = datetime.now().isoformat()
        logger.info("[SLEEPGUARD_ACTION] Executing LOCK at %s", ts)
        if sys.platform == "darwin":
            return ShutdownManager._run_power_command(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"],
                "lock",
            )
        if sys.platform.startswith("linux"):
            if ShutdownManager._run_power_command(["loginctl", "lock-session"], "lock"):
                return True
            return ShutdownManager._run_power_command(["xdg-screensaver", "lock"], "lock")

        try:
            result = ctypes.windll.user32.LockWorkStation()
            if result:
                logger.info("[SLEEPGUARD_ACTION] LockWorkStation succeeded.")
                return True
            else:
                logger.error("[SLEEPGUARD_ACTION] LockWorkStation returned False.")
                return False
        except Exception as exc:
            logger.error("[SLEEPGUARD_ACTION] Failed to execute lock: %s", exc)
            return False

    @staticmethod
    def _run_power_command(command: list[str], action: str) -> bool:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info("[SLEEPGUARD_ACTION] %s command accepted.", action.capitalize())
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("%s command failed (exit %d): %s", action, exc.returncode, exc.stderr)
            return False
        except OSError as exc:
            logger.error("Failed to invoke %s command: %s", action, exc)
            return False
