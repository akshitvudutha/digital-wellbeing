from __future__ import annotations
from typing import Optional
from urllib.parse import urlparse
import time

try:
    import uiautomation as auto
except ImportError:
    auto = None

from core.logger import logger

class BrowserURLProvider:
    """
    Extracts the active URL from browser windows using UIAutomation.
    """
    _last_query_time = 0.0
    _cached_url: Optional[str] = None
    _cached_hwnd: int = 0
    _cached_process: str = ""

    @classmethod
    def get_active_domain(cls, hwnd: int, process_name: str) -> Optional[str]:
        """
        Returns the domain (e.g. 'instagram.com') of the currently active browser tab.
        Uses aggressive caching to prevent UIA lag.
        """
        if not auto:
            return None
            
        now = time.time()
        if hwnd == cls._cached_hwnd and process_name == cls._cached_process:
            # Poll at most every 2 seconds for URL changes if window hasn't changed
            if now - cls._last_query_time < 2.0:
                return cls._cached_url
                
        cls._last_query_time = now
        cls._cached_hwnd = hwnd
        cls._cached_process = process_name

        try:
            # Set shorter timeout for UI queries to prevent freezing the main loop
            auto.SetGlobalSearchTimeout(0.2)
            window = auto.ControlFromHandle(hwnd)
            if not window:
                cls._cached_url = None
                return None

            url = None
            
            # Chrome, Brave, Edge
            if "chrome" in process_name.lower() or "brave" in process_name.lower() or "edge" in process_name.lower():
                # Fast path: Search only for EditControl
                edit = window.EditControl()
                if edit.Exists(0, 0):
                    val = edit.GetValuePattern().Value
                    url = val
            
            # Firefox
            elif "firefox" in process_name.lower():
                edit = window.EditControl()
                if edit.Exists(0, 0):
                    val = edit.GetValuePattern().Value
                    url = val

            if url:
                # Basic cleanup. If they typed 'instagram.com', it won't have http://
                if not url.startswith("http"):
                    url = "https://" + url
                    
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path
                
                # Exclude internal browser pages
                if domain and "." in domain and "chrome://" not in url and "edge://" not in url and "about:" not in url:
                    domain = domain.split('/')[0] # remove paths
                    if domain.startswith("www."):
                        domain = domain[4:]
                    cls._cached_url = domain
                    return domain
                    
            cls._cached_url = None
            return None
            
        except Exception as e:
            # logger.error(f"Failed to extract URL from {process_name}: {e}")
            cls._cached_url = None
            return None
        finally:
            if auto:
                auto.SetGlobalSearchTimeout(10.0) # restore default
