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
                "card_bg": "rgba(255, 255, 255, 0.04)",
                "card_hover": "rgba(255, 255, 255, 0.08)",
                "card_pressed": "rgba(255, 255, 255, 0.02)",
                "border": "rgba(255, 255, 255, 0.12)",
                "border_hover": "rgba(56, 189, 248, 0.4)",
                "text_main": "#F8FAFC",
                "text_sub": "#94A3B8",
                "text_muted": "#64748b",
                "accent": "#38BDF8",
                "accent_hover": "#7dd3fc",
                "track": "rgba(255, 255, 255, 0.05)",
                "center_circle": "rgba(20, 24, 38, 0.85)",
                "grid": "rgba(255, 255, 255, 0.05)",
                
                # Semantic
                "success_bg": "rgba(16, 185, 129, 0.15)",
                "success_border": "rgba(16, 185, 129, 0.3)",
                "success_text": "#34d399",
                
                "warning_bg": "rgba(250, 204, 21, 0.15)",
                "warning_border": "rgba(250, 204, 21, 0.3)",
                "warning_text": "#facc15",
                
                "danger_bg": "rgba(244, 63, 94, 0.15)",
                "danger_border": "rgba(244, 63, 94, 0.25)",
                "danger_text": "#fb7185",
                
                "info_bg": "rgba(56, 189, 248, 0.15)",
                "info_border": "rgba(56, 189, 248, 0.25)",
                "info_text": "#38bdf8",
                
                "indigo_bg": "rgba(99, 102, 241, 0.1)",
                "indigo_border": "rgba(99, 102, 241, 0.2)",
                "indigo_text": "#818cf8",
                
                # Gradients
                "window_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B0F19, stop:0.4 #1A1C2C, stop:1 #2D2A4A)",
                "primary_btn_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(47, 129, 247, 0.8), stop:1 rgba(99, 102, 241, 0.8))",
                "primary_btn_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(59, 140, 248, 0.9), stop:1 rgba(129, 140, 248, 0.9))",
            }
        else:
            return {
                "bg": "transparent",
                "card_bg": "rgba(255, 255, 255, 0.6)",
                "card_hover": "rgba(255, 255, 255, 0.8)",
                "card_pressed": "rgba(255, 255, 255, 0.4)",
                "border": "rgba(255, 255, 255, 0.8)",
                "border_hover": "rgba(2, 132, 199, 0.4)",
                "text_main": "#0F172A",
                "text_sub": "#64748B",
                "text_muted": "#94a3b8",
                "accent": "#0284C7",
                "accent_hover": "#0ea5e9",
                "track": "rgba(0, 0, 0, 0.05)",
                "center_circle": "rgba(255, 255, 255, 0.95)",
                "grid": "rgba(0, 0, 0, 0.05)",
                
                # Semantic
                "success_bg": "rgba(16, 185, 129, 0.2)",
                "success_border": "rgba(16, 185, 129, 0.4)",
                "success_text": "#059669",
                
                "warning_bg": "rgba(250, 204, 21, 0.2)",
                "warning_border": "rgba(250, 204, 21, 0.4)",
                "warning_text": "#d97706",
                
                "danger_bg": "rgba(244, 63, 94, 0.2)",
                "danger_border": "rgba(244, 63, 94, 0.35)",
                "danger_text": "#e11d48",
                
                "info_bg": "rgba(56, 189, 248, 0.2)",
                "info_border": "rgba(56, 189, 248, 0.4)",
                "info_text": "#0284c7",
                
                "indigo_bg": "rgba(99, 102, 241, 0.15)",
                "indigo_border": "rgba(99, 102, 241, 0.3)",
                "indigo_text": "#4f46e5",
                
                # Gradients
                "window_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F1F5F9, stop:0.5 #E2E8F0, stop:1 #CBD5E1)",
                "primary_btn_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(14, 165, 233, 0.8), stop:1 rgba(99, 102, 241, 0.8))",
                "primary_btn_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(2, 132, 199, 0.9), stop:1 rgba(79, 70, 229, 0.9))",
            }

    def _apply_palette(self, app: QApplication, dark_mode: bool) -> None:
        palette = QPalette()
        if dark_mode:
            palette.setColor(QPalette.ColorRole.Window, QColor("#0B0F19"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255, 10))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(255, 255, 255, 5))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(20, 25, 35, 240))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255, 20))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#38BDF8"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#38BDF8"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(255, 255, 255, 100))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(255, 255, 255, 100))
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255, 180))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(255, 255, 255, 120))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255, 240))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255, 180))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#0284C7"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#0284C7"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(0, 0, 0, 100))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(0, 0, 0, 100))
        app.setPalette(palette)

    def _apply_global_stylesheet(self, app: QApplication, dark_mode: bool) -> None:
        scroll_handle = "rgba(255, 255, 255, 0.15)" if dark_mode else "rgba(0, 0, 0, 0.15)"
        scroll_hover = "rgba(255, 255, 255, 0.3)" if dark_mode else "rgba(0, 0, 0, 0.3)"
        
        glass_styles = f"""
        * {{ font-family: 'Segoe UI Variable', 'Segoe UI', 'San Francisco', -apple-system, sans-serif; }}
        QMainWindow {{
            background: {self.color("window_gradient")};
        }}
        QScrollArea {{ border: none; background: transparent; }}
        QWidget#content_area {{ background: transparent; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 8px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {scroll_handle}; min-height: 30px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """

        # Also load the base static stylesheet from assets
        base_dir = Path(__file__).parent.parent
        qss_path = base_dir / "assets" / "styles" / ("dark_theme.qss" if dark_mode else "light_theme.qss")
        static_qss = qss_path.read_text(encoding="utf-8") if qss_path.exists() else ""
        
        app.setStyleSheet(glass_styles + "\n" + static_qss)


# Legacy bindings mapped to ThemeManager for compatibility
def apply_theme(app: Optional[QApplication] = None, theme_arg: Union[str, bool, None] = None) -> None:
    ThemeManager.instance().set_theme(theme_arg, app)

def get_theme_tokens(dark_mode: Optional[bool] = None) -> dict[str, str]:
    # Used strictly by old code, redirect to ThemeManager tokens
    is_dark = dark_mode if dark_mode is not None else ThemeManager.instance().is_dark
    return ThemeManager.instance()._get_tokens(is_dark)

