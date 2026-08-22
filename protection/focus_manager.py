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
        self._seconds_remaining = 0
        
        self._blocklist = ["youtube.com", "facebook.com", "twitter.com", "instagram.com", "reddit.com", "tiktok.com"]
        self._allowlist = ["code.exe", "cursor.exe", "msedge.exe", "chrome.exe"]
        self._app_block_response = "warn_close" # can be 'warn', 'close', 'warn_close'
        
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        
        # Ensure any lingering hosts blocks from a previous crash are cleared on startup
        self._remove_hosts_blocking()
        
        # Load settings from DB
        stored_block = self._repo.get_setting("focus_blocklist")
        if stored_block:
            self._blocklist = [d.strip() for d in stored_block.split(",") if d.strip()]
            
        stored_allow = self._repo.get_setting("focus_allowlist")
        if stored_allow:
            self._allowlist = [a.strip() for a in stored_allow.split(",") if a.strip()]
            
        stored_response = self._repo.get_setting("focus_app_block_response")
        if stored_response:
            self._app_block_response = stored_response

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
        self._blocklist = [d.strip().lower() for d in domains if d.strip()]
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
                
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0
        self._timer.stop()
        self._remove_hosts_blocking()
        
        self.focus_state_changed.emit(False)
        logger.info("Focus session stopped manually.")
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
                from tracker.browser import BrowserURLProvider
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
                        if domain and any(b in domain for b in self._blocklist):
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
        self._overlay = WebsiteLimitOverlayDialog(process_name, domain, self._seconds_remaining)
        
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
                self.stop_focus("verified")
                if hasattr(self, '_overlay') and self._overlay:
                    self._overlay.close()
        else:
            self.stop_focus()
            if hasattr(self, '_overlay') and self._overlay:
                self._overlay.close()

    def _has_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _apply_hosts_blocking(self) -> None:
        if not self._has_admin():
            logger.warning("No admin privileges to modify hosts file. Relying solely on browser title inspection overlay.")
            return
            
        try:
            with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Remove existing NYW block
            content = self._strip_nyw_block(content)
            
            # Add new block
            block_lines = [NYW_MARKER_START]
            for domain in self._blocklist:
                block_lines.append(f"127.0.0.1 {domain}")
                block_lines.append(f"127.0.0.1 www.{domain}")
            block_lines.append(NYW_MARKER_END)
            
            new_content = content.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"
            
            with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            # Flush DNS
            os.system("ipconfig /flushdns")
            logger.info("Hosts file updated and DNS flushed.")
        except Exception as e:
            logger.error(f"Failed to apply hosts blocking: {e}")

    def _remove_hosts_blocking(self) -> None:
        if not self._has_admin():
            return
            
        try:
            with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                
            new_content = self._strip_nyw_block(content)
            
            with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            os.system("ipconfig /flushdns")
            logger.info("Hosts file blocking removed.")
        except Exception as e:
            logger.error(f"Failed to remove hosts blocking: {e}")

    def _strip_nyw_block(self, content: str) -> str:
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

