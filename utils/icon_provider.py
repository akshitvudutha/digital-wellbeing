"""
icon_provider.py — Utility to extract and cache application icons from executables.
"""

import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo
from database.repository import Repository

class AppIconProvider:
    _instance = None
    _cache: dict[str, QIcon] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._provider = QFileIconProvider()
            cls._instance._repo = Repository()
        return cls._instance

    def get_icon(self, process_name: str) -> QIcon:
        """Get the cached icon for the given process name, or extract it."""
        if process_name in self._cache:
            return self._cache[process_name]
            
        icon = self._extract_icon(process_name)
        self._cache[process_name] = icon
        return icon
        
    def _extract_icon(self, process_name: str) -> QIcon:
        # First, see if we have the full path in app_info
        app_info = self._repo.get_app_info(process_name)
        exe_path = app_info.exe_path if app_info else ""
        
        # If no path from DB, try searching common locations (heuristic)
        if not exe_path or not os.path.exists(exe_path):
            import shutil
            found = shutil.which(process_name)
            if found:
                exe_path = found
            else:
                # Common hardcoded fallbacks
                common_paths = [
                    os.path.expandvars(f"%ProgramFiles%\\Google\\Chrome\\Application\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles(x86)%\\Google\\Chrome\\Application\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles%\\Mozilla Firefox\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles%\\Microsoft VS Code\\{process_name}"),
                    os.path.expandvars(f"%LocalAppData%\\Programs\\Microsoft VS Code\\{process_name}"),
                    os.path.expandvars(f"%LocalAppData%\\Discord\\app-*\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles(x86)%\\Steam\\{process_name}"),
                ]
                import glob
                for cp in common_paths:
                    matches = glob.glob(cp)
                    if matches and os.path.exists(matches[0]):
                        exe_path = matches[0]
                        break

        # If we finally have a valid path, extract
        if exe_path and os.path.exists(exe_path):
            info = QFileInfo(exe_path)
            return self._provider.icon(info)
            
        # Fallback to default generic executable icon
        # In Windows, we can use the provider to get a default file icon
        # but creating a dummy file isn't ideal. We'll use the QIcon fallback.
        return QIcon.fromTheme("application-x-executable")
