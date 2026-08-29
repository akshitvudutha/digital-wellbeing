import os
import ctypes
import threading
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from core.logger import logger
from database.repository import Repository
from protection.pin import PINManager

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
NYW_MARKER_START = "# --- NYW FOCUS MODE START ---"
NYW_MARKER_END = "# --- NYW FOCUS MODE END ---"

class FocusManager(QObject):
    focus_state_changed = Signal(bool) # is_active
    tick = Signal(int) # seconds remaining
    focus_completed = Signal()

    _instance = None

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> 'FocusManager':
        if cls._instance is None:
            if repo is None:
                repo = Repository()
            cls._instance = FocusManager(repo)
        return cls._instance

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._pin_manager = PINManager(repo)
        self._is_active = False
        self._is_strict = False
        self._system_blocking_active = False
        self._seconds_remaining = 0
        
        self._blocklist = ["youtube.com", "facebook.com", "twitter.com", "instagram.com", "reddit.com", "tiktok.com"]
        self._allowlist = ["code.exe", "cursor.exe", "msedge.exe", "chrome.exe"]
        self._app_block_response = "warn_close" # can be 'warn', 'close', 'warn_close'
        
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        
        # Ensure any lingering hosts blocks from a previous crash are cleared on startup
        self._check_stale_markers()
        
        # Load settings from DB
        stored_block = self._repo.get_setting("focus_blocklist")
        if stored_block:
            self._blocklist = list(set([self._normalize_domain(d) for d in stored_block.split(",") if d.strip()]))
            
        stored_allow = self._repo.get_setting("focus_allowlist")
        if stored_allow:
            self._allowlist = [a.strip().lower() for a in stored_allow.split(",") if a.strip()]
            
        stored_response = self._repo.get_setting("focus_app_block_response")
        if stored_response:
            self._app_block_response = stored_response

    def _normalize_domain(self, domain_str: str) -> str:
        from urllib.parse import urlparse
        s = domain_str.strip().lower()
        if not s:
            return ""
        if not s.startswith("http://") and not s.startswith("https://"):
            s = "https://" + s
        parsed = urlparse(s)
        domain = parsed.netloc or parsed.path
        domain = domain.split('/')[0] # remove path
        domain = domain.split(':')[0] # remove port
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    @property
    def system_blocking_active(self) -> bool:
        return self._system_blocking_active
        
    @property
    def is_active(self) -> bool:
        return self._is_active
        
    @property
    def is_strict(self) -> bool:
        return self._is_strict
        
    @property
    def blocklist(self) -> List[str]:
        return self._blocklist
        
    @property
    def allowlist(self) -> List[str]:
        return self._allowlist
        
    @property
    def app_block_response(self) -> str:
        return self._app_block_response

    def save_blocklist(self, domains: List[str]) -> None:
        normalized = [self._normalize_domain(d) for d in domains if d.strip()]
        self._blocklist = list(set([d for d in normalized if d]))
        self._repo.set_setting("focus_blocklist", ",".join(self._blocklist))
        if self._is_active:
            self._apply_hosts_blocking()
            
    def save_allowlist(self, apps: List[str]) -> None:
        self._allowlist = [a.strip().lower() for a in apps if a.strip()]
        self._repo.set_setting("focus_allowlist", ",".join(self._allowlist))
        
    def save_app_block_response(self, response: str) -> None:
        self._app_block_response = response
        self._repo.set_setting("focus_app_block_response", response)

    def start_focus(self, minutes: int, strict_mode: bool = False) -> bool:
        if self._is_active:
            return False
            
        if strict_mode and not self._pin_manager.is_enabled():
            logger.warning("Cannot start strict mode: PIN is not configured.")
            return False
            
        self._is_active = True
        self._is_strict = strict_mode
        self._seconds_remaining = minutes * 60
        self._apply_hosts_blocking()
        
        self._timer.start()
        self.focus_state_changed.emit(True)
        logger.info(f"Focus session started. minutes={minutes}, strict={strict_mode}")
        return True

    def stop_focus(self, provided_pin: str = "") -> bool:
        if not self._is_active:
            return True
            
        if self._is_strict:
            if not self._pin_manager.verify_pin(provided_pin):
                logger.warning("Focus session stop denied: Invalid PIN.")
                return False
                
        return self._do_stop()

    def stop_focus_after_pin_dialog(self) -> bool:
        """Stop focus unconditionally after the PIN dialog has already verified the PIN.
        
        MUST only be called from code that has already run PinDialog.exec() and
        received QDialog.Accepted.  Never expose this path to un-validated input.
        """
        if not self._is_active:
            return True
        return self._do_stop()

    def _do_stop(self) -> bool:
        """Internal: perform the actual session teardown."""
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0
        self._timer.stop()
        self._remove_hosts_blocking()
        if hasattr(self, '_overlay') and self._overlay:
            try:
                self._overlay.close()
            except Exception:
                pass
        self.focus_state_changed.emit(False)
        logger.info("Focus session stopped.")
        return True

    def _on_tick(self) -> None:
        if self._seconds_remaining > 0:
            self._seconds_remaining -= 1
            self.tick.emit(self._seconds_remaining)
            
            # Browser and App inspection
            try:
                import win32gui
                import win32process
                import psutil
                from tracker.browser_url import BrowserURLProvider
                from tracker.foreground import _get_real_window_pid
                
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd:
                    return
                    
                pid = _get_real_window_pid(hwnd)
                if not pid:
                    return
                    
                p = psutil.Process(pid)
                p_name = p.name().lower()
                
                # Check SYSTEM_SAFE block overrides
                # Critical Windows processes that should NEVER be killed to prevent OS crash/instability.
                # NOTE: applicationframehost.exe, cmd.exe, and powershell.exe were removed to prevent Strict Focus bypass.
                # _get_real_window_pid automatically resolves ApplicationFrameHost.exe to the actual UWP child process.
                SYSTEM_SAFE = {"explorer.exe", "taskmgr.exe", "systemsettings.exe", "digitalwellbeing.exe", 
                               "searchapp.exe", "startmenuexperiencehost.exe", "dwm.exe"}
                
                if p_name in SYSTEM_SAFE:
                    return
                    
                # 1. Check Website Blocks (if browser)
                if p_name in ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"]:
                    domain = BrowserURLProvider.get_active_domain(hwnd, p_name)
                    if domain:
                        for b in self._blocklist:
                            if domain == b or domain.endswith("." + b):
                                self._show_overlay(p_name, domain)
                                return
                            
                    # 2. Check App Blocks
                    is_blocked = False
                    if self._is_strict:
                        # In strict mode, if it's not explicitly in allowlist (and not safe), block it.
                        if not any(a in p_name for a in self._allowlist):
                            is_blocked = True
                    else:
                        # In standard mode, block if explicitly in blocklist
                        if any(b in p_name for b in self._blocklist):
                            is_blocked = True
                            
                    if is_blocked:
                        self._handle_blocked_app(p, p_name)
                        
            except Exception as e:
                pass
                
        else:
            self._is_active = False
            self._is_strict = False
            self._timer.stop()
            self._remove_hosts_blocking()
            if hasattr(self, '_overlay') and self._overlay:
                self._overlay.close()
            self.focus_state_changed.emit(False)
            self.focus_completed.emit()
            logger.info("Focus session completed.")

    def _handle_blocked_app(self, proc, p_name: str) -> None:
        try:
            if self._app_block_response == "warn":
                self._show_overlay(p_name, f"App: {p_name}")
            elif self._app_block_response == "close":
                logger.info(f"Terminating blocked app {p_name} during Focus Mode.")
                proc.kill()
            elif self._app_block_response == "warn_close":
                self._show_overlay(p_name, f"App: {p_name}")
                # We could implement a countdown here, but for simplicity we kill it immediately if they stay on it
                proc.kill()
        except Exception as e:
            logger.warning(f"Failed to handle blocked app {p_name}: {e}")

    def _show_overlay(self, process_name: str, domain: str) -> None:
        if hasattr(self, '_overlay') and self._overlay and self._overlay.isVisible():
            return
            
        from ui.widgets.website_overlay import WebsiteLimitOverlayDialog
        self._overlay = WebsiteLimitOverlayDialog(process_name, domain, self._seconds_remaining, self._is_strict)
        
        # Override text for Focus Mode
        msg_lbl = self._overlay.findChild(QLabel, "") # The message label doesn't have an object name in the original
        # Let's just find the QLabel that contains "daily limit"
        for lbl in self._overlay.findChildren(QLabel):
            if "daily limit" in lbl.text():
                lbl.setText(f"This website is blocked during your focus session.\n\nTime remaining: {self._seconds_remaining // 60}m {self._seconds_remaining % 60}s")
        
        # In strict mode, hide the override button
        if self._is_strict:
            self._overlay.btn_override.hide()
            
        # If user closes tab, close overlay
        self._overlay.close_tab_requested.connect(self._overlay.close)
        
        # If user overrides (not strict mode), we can temporarily allow it by closing the overlay
        # Wait, if they override, it will just pop back up on the next tick!
        # For simplicity, if they override, we just stop the focus session early or prompt PIN.
        self._overlay.btn_override.clicked.connect(self._handle_overlay_override)
        
        self._overlay.show()

    def _handle_overlay_override(self) -> None:
        # Prompt PIN if strict, otherwise just stop focus
        if self._is_strict:
            from ui.widgets.pin_dialog import PinDialog
            dialog = PinDialog(self._pin_manager)
            if dialog.exec():
                self.stop_focus_after_pin_dialog()
                if hasattr(self, '_overlay') and self._overlay:
                    self._overlay.close()
        else:
            self.stop_focus()
            if hasattr(self, '_overlay') and self._overlay:
                self._overlay.close()




    def _check_stale_markers(self) -> None:
        try:
            with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            if NYW_MARKER_START in content:
                logger.info("Stale hosts marker found on startup. Prompting UAC for cleanup.")
                self._remove_hosts_blocking()
        except Exception:
            pass

    def _run_elevated_helper(self, action: str, domains: str = "") -> bool:
        import sys
        import ctypes
        from ctypes import wintypes
        import os
        
        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("fMask", ctypes.c_ulong),
                ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR),
                ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int),
                ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE),
            ]

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        INFINITE = 0xFFFFFFFF
        
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            args = f"--elevated-helper --action {action} --domains \"{domains}\""
        else:
            exe = sys.executable
            main_script = os.path.abspath(sys.argv[0])
            args = f"\"{main_script}\" --elevated-helper --action {action} --domains \"{domains}\""
            
        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.lpVerb = "runas"
        sei.lpFile = exe
        sei.lpParameters = args
        sei.nShow = 0  # SW_HIDE
        
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32
        
        if shell32.ShellExecuteExW(ctypes.byref(sei)):
            hProcess = sei.hProcess
            if hProcess:
                kernel32.WaitForSingleObject(hProcess, INFINITE)
                exit_code = wintypes.DWORD()
                kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
                kernel32.CloseHandle(hProcess)
                return exit_code.value == 0
            return True
        return False

    def _apply_hosts_blocking(self) -> None:
        if not self._blocklist:
            self._system_blocking_active = False
            return
            
        domains_str = ",".join(self._blocklist)
        success = self._run_elevated_helper("apply", domains_str)
        if success:
            self._system_blocking_active = True
            logger.info("Elevated hosts application succeeded.")
        else:
            self._system_blocking_active = False
            logger.warning("Elevated hosts application failed or denied.")

    def _remove_hosts_blocking(self) -> None:
        self._run_elevated_helper("remove")
        self._system_blocking_active = False

    @classmethod
    def run_elevated_action(cls, action: str, domains: str = "") -> bool:
        """This runs inside the elevated helper process."""
        try:
            if action == "apply":
                cls._do_apply_hosts(domains)
            elif action == "remove":
                cls._do_remove_hosts()
            return True
        except Exception as e:
            logger.error(f"Elevated helper failed: {e}")
            return False

    @staticmethod
    def _do_apply_hosts(domains_str: str) -> None:
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]
        with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        content = FocusManager._strip_nyw_block(content)
        block_lines = [NYW_MARKER_START]
        for domain in domains:
            block_lines.append(f"127.0.0.1 {domain}")
            block_lines.append(f"127.0.0.1 www.{domain}")
        block_lines.append(NYW_MARKER_END)
        new_content = content.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"
        with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        os.system("ipconfig /flushdns")
        logger.info("Hosts file updated by helper.")

    @staticmethod
    def _do_remove_hosts() -> None:
        with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = FocusManager._strip_nyw_block(content)
        with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        os.system("ipconfig /flushdns")
        logger.info("Hosts file blocking removed by helper.")

    @staticmethod
    def _strip_nyw_block(content: str) -> str:
        if NYW_MARKER_START not in content:
            return content
            
        lines = content.splitlines()
        new_lines = []
        in_block = False
        for line in lines:
            if line.strip() == NYW_MARKER_START:
                in_block = True
                continue
            if line.strip() == NYW_MARKER_END:
                in_block = False
                continue
            if not in_block:
                new_lines.append(line)
        return "\n".join(new_lines)

