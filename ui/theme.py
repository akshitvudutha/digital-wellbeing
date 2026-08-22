"""
theme.py — Commercial-Grade Windows 11 / One UI Theme Engine for Digital Wellbeing.
Supports Light, Dark, and System modes with instant palette and stylesheet updates.
"""

import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def is_system_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return True


class ThemeManager(QObject):
    """Centralized Theme Manager for instant, app-wide UI updates."""
    _instance = None
    theme_changed = Signal(bool)  # Emits True if dark mode

    def __init__(self):
        super().__init__()
        self._is_dark = True
        self._tokens = {}
    
    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def resolve_dark_mode(self, theme_arg: Union[str, bool, None] = None) -> bool:
        if isinstance(theme_arg, bool):
            return theme_arg

        if theme_arg is None:
            try:
                from settings.manager import SettingsManager
                theme_arg = SettingsManager().theme
            except Exception:
                theme_arg = "dark"

        theme_str = str(theme_arg).lower()
        if theme_str == "system":
            return is_system_dark()
        if theme_str == "light":
            return False
        return True

    def set_theme(self, theme_arg: Union[str, bool, None] = None, app: Optional[QApplication] = None) -> None:
        if app is None:
            app = QApplication.instance()
            
        new_is_dark = self.resolve_dark_mode(theme_arg)
        self._is_dark = new_is_dark
        self._tokens = self._get_tokens(self._is_dark)
        
        if app:
            self._apply_palette(app, self._is_dark)
            self._apply_global_stylesheet(app, self._is_dark)

        # Notify all widgets to update dynamic styles
        self.theme_changed.emit(self._is_dark)

    def color(self, token: str, default: str = "#ff00ff") -> str:
        """Get a specific theme color by token name."""
        return self._tokens.get(token, default)

    def _get_tokens(self, dark_mode: bool) -> Dict[str, str]:
        if dark_mode:
            return {
                "bg": "transparent",
                "window_bg": "#0D1117",  # Deep Canvas
                "surface": "rgba(22, 27, 34, 0.75)", # Cards
                "surface_elevated": "rgba(28, 33, 40, 0.85)", # Hover Cards
                "surface_secondary": "rgba(33, 38, 45, 0.95)",
                "card_bg": "rgba(22, 27, 34, 0.75)",
                "card_hover": "rgba(28, 33, 40, 0.85)",
                "card_pressed": "rgba(22, 27, 34, 0.95)",
                "border": "rgba(255, 255, 255, 0.08)",
                "border_hover": "rgba(47, 129, 247, 0.35)",
                "input_bg": "#161B22",
                "input_border": "rgba(255, 255, 255, 0.12)",
                "input_hover": "rgba(47, 129, 247, 0.55)",
                "text_main": "#F0F6FC",
                "text_sub": "#8B949E",
                "text_muted": "rgba(240, 246, 252, 0.4)",
                "accent": "#2F81F7",
                "accent_hover": "#388BFD",
                "accent_pressed": "#1F6FEB",
                "track": "rgba(255, 255, 255, 0.05)",
                "center_circle": "transparent",
                "grid": "rgba(255, 255, 255, 0.05)",
                
                # Semantic
                "success_bg": "rgba(35, 134, 54, 0.15)",
                "success_border": "rgba(35, 134, 54, 0.3)",
                "success_text": "#3FB950",
                
                "warning_bg": "rgba(210, 153, 34, 0.15)",
                "warning_border": "rgba(210, 153, 34, 0.3)",
                "warning_text": "#D29922",
                
                "danger_bg": "rgba(248, 81, 73, 0.15)",
                "danger_border": "rgba(248, 81, 73, 0.25)",
                "danger_text": "#F85149",
                
                "info_bg": "rgba(47, 129, 247, 0.15)",
                "info_border": "rgba(47, 129, 247, 0.25)",
                "info_text": "#2F81F7",
                
                "indigo_bg": "rgba(99, 102, 241, 0.1)",
                "indigo_border": "rgba(99, 102, 241, 0.2)",
                "indigo_text": "#818cf8",
                
                "window_gradient": "transparent",
                "primary_btn_gradient": "rgba(255, 255, 255, 0.1)",
                "primary_btn_hover": "rgba(255, 255, 255, 0.15)",
            }
        else:
            return {
                "bg": "transparent",
                "window_bg": "#F3F5F9",
                "surface": "rgba(255, 255, 255, 0.75)",
                "surface_elevated": "rgba(255, 255, 255, 0.95)",
                "surface_secondary": "#FFFFFF",
                "card_bg": "rgba(255, 255, 255, 0.75)",
                "card_hover": "rgba(255, 255, 255, 0.95)",
                "card_pressed": "rgba(245, 245, 245, 0.95)",
                "border": "rgba(0, 0, 0, 0.05)",
                "border_hover": "rgba(0, 120, 212, 0.35)",
                "input_bg": "rgba(255, 255, 255, 0.9)",
                "input_border": "rgba(0, 0, 0, 0.08)",
                "input_hover": "#0078d4",
                "text_main": "#0F172A",
                "text_sub": "#64748B",
                "text_muted": "rgba(15, 23, 42, 0.4)",
                "accent": "#0078D4",
                "accent_hover": "#3B82F6",
                "accent_pressed": "#1D4ED8",
                "track": "rgba(0, 0, 0, 0.05)",
                "center_circle": "transparent",
                "grid": "rgba(0, 0, 0, 0.05)",
                
                # Semantic
                "success_bg": "rgba(16, 185, 129, 0.15)",
                "success_border": "rgba(16, 185, 129, 0.3)",
                "success_text": "#059669",
                
                "warning_bg": "rgba(250, 204, 21, 0.15)",
                "warning_border": "rgba(250, 204, 21, 0.3)",
                "warning_text": "#D97706",
                
                "danger_bg": "rgba(244, 63, 94, 0.15)",
                "danger_border": "rgba(244, 63, 94, 0.25)",
                "danger_text": "#E11D48",
                
                "info_bg": "rgba(56, 189, 248, 0.15)",
                "info_border": "rgba(56, 189, 248, 0.25)",
                "info_text": "#0284C7",
                
                "indigo_bg": "rgba(99, 102, 241, 0.1)",
                "indigo_border": "rgba(99, 102, 241, 0.2)",
                "indigo_text": "#4F46E5",
                
                "window_gradient": "transparent",
                "primary_btn_gradient": "rgba(0, 0, 0, 0.05)",
                "primary_btn_hover": "rgba(0, 0, 0, 0.08)",
            }

    def _apply_palette(self, app: QApplication, dark_mode: bool) -> None:
        palette = QPalette()
        # By setting Window to transparent, we let the native Mica shine through
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        if dark_mode:
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(255, 255, 255, 10))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(30, 30, 30, 230))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255, 15))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#60CDFF"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#60CDFF"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(255, 255, 255, 100))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(255, 255, 255, 100))
        else:
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#1C1C1C"))
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255, 0))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 0, 0, 10))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255, 230))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1C1C1C"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#1C1C1C"))
            palette.setColor(QPalette.ColorRole.Button, QColor(0, 0, 0, 15))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1C1C1C"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#005FB8"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#005FB8"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(0, 0, 0, 100))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(0, 0, 0, 100))
        app.setPalette(palette)

    def _apply_global_stylesheet(self, app: QApplication, dark_mode: bool) -> None:
        scroll_handle = "rgba(255, 255, 255, 0.15)" if dark_mode else "rgba(0, 0, 0, 0.15)"
        scroll_hover = "rgba(255, 255, 255, 0.3)" if dark_mode else "rgba(0, 0, 0, 0.3)"
        
        glass_styles = f"""
        QWidget {{
            color: {self.color('text_main')};
            font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", -apple-system, sans-serif;
            font-size: 13px;
            border: none;
            outline: none;
        }}
        QMainWindow, QWidget#content_area {{
            background: transparent;
        }}
        
        /* ─── Scrollbars ───────────────────────────────────────────────────────── */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {scroll_handle}; min-height: 30px; border-radius: 3px; }}
        QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ border: none; background: transparent; height: 6px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {scroll_handle}; min-width: 30px; border-radius: 3px; }}

        /* ─── Shared Components ────────────────────────────────────────────────── */
        QComboBox, QSpinBox, QLineEdit {{
            background-color: {self.color('input_bg')};
            border: 1px solid {self.color('input_border')};
            border-radius: 10px;
            padding: 8px 14px;
            color: {self.color('text_main')};
            font-size: 13px;
        }}
        QComboBox:hover, QSpinBox:hover, QLineEdit:hover, QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
            border-color: {self.color('input_hover')};
            background-color: {self.color('surface_secondary')};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid {self.color('text_sub')}; width: 0; height: 0; margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.color('surface_secondary')};
            border: 1px solid {self.color('border')};
            border-radius: 10px;
            selection-background-color: rgba(47, 129, 247, 0.15);
            selection-color: {self.color('accent')};
            padding: 4px;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 10px 14px;
            border-radius: 8px;
            color: {self.color('text_main')};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: rgba(47, 129, 247, 0.1);
        }}
        QProgressBar {{
            background-color: {self.color('border')};
            border-radius: 4px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background-color: {self.color('accent')};
            border-radius: 4px;
        }}
        QCheckBox {{
            color: {self.color('text_main')};
            spacing: 12px;
            font-size: 13px;
            font-weight: 600;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 2px solid {self.color('input_border')};
            background-color: transparent;
        }}
        QCheckBox::indicator:hover {{
            border-color: {self.color('accent')};
        }}
        QCheckBox::indicator:checked {{
            background-color: {self.color('accent')};
            border-color: {self.color('accent')};
        }}
        QToolTip {{
            background-color: {self.color('surface_secondary')};
            color: {self.color('text_main')};
            border: 1px solid {self.color('border')};
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        """

        app.setStyleSheet(glass_styles)

def apply_mica(hwnd: int, dark_mode: bool = True) -> None:
    """Applies Windows 11 Mica backdrop to the specified window handle."""
    try:
        import ctypes
        from ctypes.wintypes import DWORD, BOOL, HWND
        import sys
        
        if sys.platform != "win32":
            return
            
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2 # Mica
        
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        
        # Enable dark mode context
        value = ctypes.c_int(1 if dark_mode else 0)
        set_window_attribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(value), ctypes.sizeof(value))
        
        # Enable Mica
        backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)
        set_window_attribute(HWND(hwnd), DWORD(DWMWA_SYSTEMBACKDROP_TYPE), ctypes.byref(backdrop), ctypes.sizeof(backdrop))
    except Exception as e:
        from core.logger import logger
        logger.warning(f"Failed to apply Mica backdrop: {e}")


# Legacy bindings mapped to ThemeManager for compatibility
def apply_theme(app: Optional[QApplication] = None, theme_arg: Union[str, bool, None] = None) -> None:
    ThemeManager.instance().set_theme(theme_arg, app)

def get_theme_tokens(dark_mode: Optional[bool] = None) -> dict[str, str]:
    # Used strictly by old code, redirect to ThemeManager tokens
    is_dark = dark_mode if dark_mode is not None else ThemeManager.instance().is_dark
    return ThemeManager.instance()._get_tokens(is_dark)

def get_app_color(app_name: str) -> str:
    """Returns a deterministic accent color for a given application."""
    if not app_name:
        return "#7dd3fc"
        
    name = app_name.lower().replace(".exe", "")
    
    brand_colors = {
        "brave": "#FB542B",
        "chrome": "#4285F4",
        "spotify": "#1DB954",
        "code": "#007ACC",
        "github": "#777777",
        "discord": "#5865F2",
        "steam": "#171A21",
        "chatgpt": "#10A37F",
        "explorer": "#5C8BA6",
        "msedge": "#0078D7",
        "firefox": "#FF7139",
    }
    
    if name in brand_colors:
        return brand_colors[name]
        
    # Generate deterministic color from hash (avoid purple/oversaturated, use HSL)
    import hashlib
    hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
    
    # Restrict hue to avoid pure purple (260-290 roughly). 
    # Let's map 0-360, but if it falls in 260-290, shift it.
    hue = hash_val % 360
    if 260 <= hue <= 290:
        hue = (hue + 50) % 360
        
    sat = 60 + (hash_val % 20) # 60-80% saturation (vibrant but not oversaturated)
    light = 50 + (hash_val % 10) # 50-60% lightness
    
    # Convert HSL to HEX
    return QColor.fromHsl(hue, int(sat * 2.55), int(light * 2.55)).name()

