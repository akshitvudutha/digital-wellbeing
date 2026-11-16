"""
theme.py — Commercial-Grade Windows 11 / One UI Theme Engine for Digital Wellbeing.
Supports Light, Dark, and System modes with instant palette and stylesheet updates.
"""

import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal, QEvent
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QAbstractButton, QProxyStyle, QStyle, QTabBar


class FocusIndicatorStyle(QProxyStyle):
    """Use the shared themed ring instead of Qt's extra inner focus rectangle."""

    @staticmethod
    def suppresses_native_focus_rect(widget) -> bool:
        return isinstance(widget, (QAbstractButton, QTabBar))

    def drawPrimitive(self, element, option, painter, widget=None):
        if (
            element == QStyle.PrimitiveElement.PE_FrameFocusRect
            and self.suppresses_native_focus_rect(widget)
        ):
            return
        super().drawPrimitive(element, option, painter, widget)


class ButtonFocusPolicyFilter(QObject):
    """
    Keeps pointer interaction from leaving keyboard focus rings on controls,
    while preserving visible focus for Tab and other keyboard navigation.
    """

    @staticmethod
    def _clears_on_mouse(widget) -> bool:
        return (
            isinstance(widget, (QAbstractButton, QTabBar))
            or widget.property("mouse_focus_clears") is True
        )

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Show, QEvent.Type.Polish):
            if isinstance(watched, (QAbstractButton, QTabBar)) and watched.focusPolicy() == Qt.FocusPolicy.StrongFocus:
                watched.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        elif event.type() == QEvent.Type.MouseButtonPress:
            app = QApplication.instance()
            focused = app.focusWidget() if app else None
            target = watched if hasattr(watched, "parentWidget") else None
            if focused is not None:
                same_control = target is focused or (
                    target is not None and focused.isAncestorOf(target)
                )
                if self._clears_on_mouse(focused) or not same_control:
                    focused.clearFocus()
        return super().eventFilter(watched, event)


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
        self._focus_filter: Optional[ButtonFocusPolicyFilter] = None
        self._focus_style: Optional[FocusIndicatorStyle] = None
        self._focus_app: Optional[QApplication] = None
    
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
            # QApplication.style() may return Qt's stylesheet wrapper around
            # this proxy, so comparing it to _focus_style would reinstall and
            # nest a proxy on every theme switch.
            if self._focus_app is not app:
                self._focus_style = FocusIndicatorStyle(app.style())
                app.setStyle(self._focus_style)
                self._focus_app = app
            if self._focus_filter is None:
                self._focus_filter = ButtonFocusPolicyFilter(app)
                app.installEventFilter(self._focus_filter)
            self._apply_palette(app, self._is_dark)
            self._apply_global_stylesheet(app, self._is_dark)

        # Notify all widgets to update dynamic styles
        self.theme_changed.emit(self._is_dark)

    def color(self, token: str, default: str = "transparent") -> str:
        """Get a specific theme color by token name."""
        return self._tokens.get(token, default)

    def _get_tokens(self, dark_mode: bool) -> Dict[str, str]:
        if dark_mode:
            return {
                "bg": "#080A0D",
                "window_bg": "transparent",      # Allows Mica to show through or dark obsidian fallback
                "sidebar_bg": "rgba(10, 13, 18, 0.75)",  # Deep frosted obsidian sidebar
                "surface": "rgba(18, 22, 29, 0.65)",     # Translucent dark obsidian surface
                "surface_elevated": "#11151C",           # Solid surface for dense data
                "surface_secondary": "rgba(255, 255, 255, 0.03)", # Ultra soft secondary surface
                "surface_hover": "rgba(255, 255, 255, 0.06)",
                "surface_pressed": "rgba(255, 255, 255, 0.09)",
                "card_bg": "rgba(18, 22, 29, 0.65)",
                "surface_card": "rgba(18, 22, 29, 0.65)",
                "card_hover": "rgba(24, 30, 40, 0.85)",
                "card_pressed": "rgba(14, 18, 24, 0.95)",
                "border": "rgba(255, 255, 255, 0.08)",   # Restrained hairline borders
                "border_strong": "rgba(255, 255, 255, 0.15)",
                "border_hover": "rgba(255, 255, 255, 0.22)",
                "input_bg": "rgba(15, 18, 24, 0.85)",    # Dark translucent inputs
                "input_border": "rgba(255, 255, 255, 0.10)",
                "input_hover": "rgba(255, 255, 255, 0.18)",
                "text_main": "#F8FAFC",                  # Crisp slate white
                "text_sub": "#94A3B8",                   # Calm slate text
                "text_muted": "#64748B",                 # Muted secondary
                "accent": "#10B981",                     # NYW Brand Emerald (from canonical logo)
                "accent_hover": "#059669",
                "accent_pressed": "#047857",
                "accent_amber": "#F59E0B",               # NYW Brand Amber (from canonical logo)
                "accent_amber_hover": "#D97706",
                "accent_amber_bg": "rgba(245, 158, 11, 0.12)",
                "accent_emerald_bg": "rgba(16, 185, 129, 0.12)",
                "accent_primary_bg": "rgba(16, 185, 129, 0.12)",
                "track": "rgba(255, 255, 255, 0.06)",
                "center_circle": "transparent",
                "grid": "rgba(255, 255, 255, 0.04)",
                
                # Semantic
                "success_bg": "rgba(16, 185, 129, 0.12)",
                "success_border": "rgba(16, 185, 129, 0.25)",
                "success_text": "#10B981",
                
                "warning_bg": "rgba(245, 158, 11, 0.12)",
                "warning_border": "rgba(245, 158, 11, 0.25)",
                "warning_text": "#F59E0B",
                
                "danger_bg": "rgba(239, 68, 68, 0.12)",
                "danger_border": "rgba(239, 68, 68, 0.25)",
                "danger_text": "#F87171",
                
                "info_bg": "rgba(56, 189, 248, 0.12)",
                "info_border": "rgba(56, 189, 248, 0.25)",
                "info_text": "#38BDF8",
                
                "indigo_bg": "rgba(99, 102, 241, 0.12)",
                "indigo_border": "rgba(99, 102, 241, 0.25)",
                "indigo_text": "#818CF8",
                
                "window_gradient": "transparent",
                "primary_btn_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669)",
                "primary_btn_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34D399, stop:1 #10B981)",
                "secondary_btn_bg": "rgba(255, 255, 255, 0.05)",
                "secondary_btn_hover": "rgba(255, 255, 255, 0.10)",
                "secondary_btn_pressed": "rgba(255, 255, 255, 0.03)",
                "secondary_btn_border": "rgba(255, 255, 255, 0.12)",
                "secondary_btn_text": "#F8FAFC",
                "focus_ring": "#10B981",
            }
        else:
            return {
                "bg": "#F8FAFC",
                "window_bg": "transparent",
                "sidebar_bg": "rgba(248, 250, 252, 0.90)",
                "surface": "rgba(255, 255, 255, 0.95)",
                "surface_elevated": "#FFFFFF",
                "surface_secondary": "rgba(0, 0, 0, 0.04)",
                "surface_hover": "rgba(0, 0, 0, 0.06)",
                "surface_pressed": "rgba(0, 0, 0, 0.09)",
                "card_bg": "#FFFFFF",
                "surface_card": "#FFFFFF",
                "card_hover": "#F8FAFC",
                "card_pressed": "#F1F5F9",
                "border": "rgba(0, 0, 0, 0.09)",
                "border_strong": "rgba(0, 0, 0, 0.16)",
                "border_hover": "rgba(0, 0, 0, 0.25)",
                "input_bg": "#FFFFFF",
                "input_border": "rgba(0, 0, 0, 0.14)",
                "input_hover": "rgba(0, 0, 0, 0.24)",
                "text_main": "#0F172A",                  # Deep slate, maximum contrast (16.9:1)
                "text_sub": "#475569",                   # Rich slate, WCAG AAA compliant (6.7:1)
                "text_muted": "#526071",                 # Refined slate, passes WCAG AA (5.5:1 on white, 5.0:1 on card)
                "accent": "#047857",                     # Emerald-700, WCAG AA compliant on light (5.4:1)
                "accent_hover": "#065F46",
                "accent_pressed": "#064E3B",
                "accent_amber": "#B45309",               # Amber-700, WCAG AA compliant on light (5.0:1)
                "accent_amber_hover": "#92400E",
                "accent_amber_bg": "rgba(180, 83, 9, 0.12)",
                "accent_emerald_bg": "rgba(4, 120, 87, 0.12)",
                "accent_primary_bg": "rgba(4, 120, 87, 0.12)",
                "track": "rgba(0, 0, 0, 0.07)",
                "center_circle": "transparent",
                "grid": "rgba(0, 0, 0, 0.05)",
                
                # Semantic (All text colors >= 4.5:1 against light canvas)
                "success_bg": "rgba(4, 120, 87, 0.12)",
                "success_border": "rgba(4, 120, 87, 0.28)",
                "success_text": "#047857",
                
                "warning_bg": "rgba(180, 83, 9, 0.12)",
                "warning_border": "rgba(180, 83, 9, 0.28)",
                "warning_text": "#B45309",
                
                "danger_bg": "rgba(220, 38, 38, 0.12)",
                "danger_border": "rgba(220, 38, 38, 0.28)",
                "danger_text": "#DC2626",
                
                "info_bg": "rgba(3, 105, 161, 0.12)",
                "info_border": "rgba(3, 105, 161, 0.28)",
                "info_text": "#0369A1",
                
                "indigo_bg": "rgba(79, 70, 229, 0.12)",
                "indigo_border": "rgba(79, 70, 229, 0.25)",
                "indigo_text": "#4F46E5",
                
                "window_gradient": "transparent",
                "primary_btn_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857)",
                "primary_btn_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #065F46)",
                "secondary_btn_bg": "#FFFFFF",
                "secondary_btn_hover": "#F1F5F9",
                "secondary_btn_pressed": "#E2E8F0",
                "secondary_btn_border": "rgba(0, 0, 0, 0.15)",
                "secondary_btn_text": "#0F172A",
                "focus_ring": "#047857",
            }

    def _apply_palette(self, app: QApplication, dark_mode: bool) -> None:
        palette = QPalette()
        # By setting Window to transparent, we let the native Mica shine through
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        if dark_mode:
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(255, 255, 255, 8))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(17, 21, 28, 240))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255, 12))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F8FAFC"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#10B981"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#10B981"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(255, 255, 255, 80))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(255, 255, 255, 80))
        else:
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255, 0))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 0, 0, 8))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255, 240))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.Button, QColor(0, 0, 0, 10))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0F172A"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#047857"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#047857"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(0, 0, 0, 80))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(0, 0, 0, 80))
        app.setPalette(palette)

    def _apply_global_stylesheet(self, app: QApplication, dark_mode: bool) -> None:
        scroll_handle = "rgba(255, 255, 255, 0.12)" if dark_mode else "rgba(0, 0, 0, 0.12)"
        scroll_hover = "rgba(255, 255, 255, 0.25)" if dark_mode else "rgba(0, 0, 0, 0.25)"
        
        glass_styles = f"""
        QWidget {{
            color: {self.color('text_main')};
            font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", -apple-system, sans-serif;
            font-size: 14px;
            border: none;
        }}
        QMainWindow, QWidget#content_area {{
            background: transparent;
        }}
        
        /* ─── Keyboard Focus Indicators ────────────────────────────────────────── */
        QAbstractButton:focus,
        QWidget[mouse_focus_clears="true"]:focus {{
            border: 2px solid {self.color('focus_ring')};
        }}
        QTabBar::tab:focus {{
            border-bottom: 2px solid {self.color('focus_ring')};
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 2px solid {self.color('focus_ring')};
        }}

        /* ─── Buttons ──────────────────────────────────────────────────────────── */
        QPushButton {{
            background-color: {self.color('secondary_btn_bg')};
            color: {self.color('secondary_btn_text')};
            border: 1px solid {self.color('secondary_btn_border')};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {self.color('secondary_btn_hover')};
            border-color: {self.color('border_strong')};
        }}
        QPushButton:pressed {{
            background-color: {self.color('secondary_btn_pressed')};
        }}
        QPushButton:disabled {{
            color: {self.color('text_muted')};
            opacity: 0.5;
        }}
        QPushButton#btn_primary, QPushButton[primary="true"] {{
            background: {self.color('primary_btn_gradient')};
            color: #FFFFFF;
            border: 1px solid {self.color('border')};
        }}
        QPushButton#btn_primary:hover, QPushButton[primary="true"]:hover {{
            background: {self.color('primary_btn_hover')};
        }}

        /* ─── Scrollbars ───────────────────────────────────────────────────────── */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {scroll_handle}; min-height: 36px; border-radius: 3px; }}
        QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ border: none; background: transparent; height: 6px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {scroll_handle}; min-width: 36px; border-radius: 3px; }}

        /* ─── Shared Components ────────────────────────────────────────────────── */
        QLabel#empty_title {{
            font-size: 16px;
            font-weight: 700;
            color: {self.color('text_main')};
        }}
        QLabel#empty_sub, QLabel#empty_subtitle {{
            font-size: 13px;
            font-weight: 500;
            color: {self.color('text_sub')};
        }}
        QLabel#empty_state_label, QLabel#empty_placeholder {{
            font-size: 13px;
            font-weight: 500;
            color: {self.color('text_muted')};
        }}
        QLabel#card_desc {{
            font-size: 13px;
            color: {self.color('text_sub')};
        }}

        QFrame#v2_card, QFrame#stat_card {{
            background-color: {self.color('card_bg')};
            border: 1px solid {self.color('border')};
            border-radius: 12px;
        }}
        QFrame#v2_card:hover, QFrame#stat_card:hover {{
            background-color: {self.color('card_hover')};
            border: 1px solid {self.color('border_hover')};
        }}
        
        QFrame#dense_card {{
            background-color: {self.color('surface_elevated')};
            border: 1px solid {self.color('border')};
            border-radius: 12px;
        }}
        QFrame#dense_card:hover {{
            border: 1px solid {self.color('border_hover')};
        }}
        
        QComboBox, QSpinBox, QLineEdit {{
            background-color: {self.color('input_bg')};
            border: 1px solid {self.color('input_border')};
            border-radius: 8px;
            padding: 8px 12px;
            color: {self.color('text_main')};
            font-size: 13px;
        }}
        QComboBox:hover, QSpinBox:hover, QLineEdit:hover, QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
            border-color: {self.color('accent')};
            background-color: {self.color('surface_elevated')};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {self.color('text_sub')}; width: 0; height: 0; margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.color('surface_elevated')};
            border: 1px solid {self.color('border_strong')};
            border-radius: 8px;
            selection-background-color: {self.color('accent_emerald_bg')};
            selection-color: {self.color('accent')};
            padding: 4px;
            color: {self.color('text_main')};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            border-radius: 6px;
            color: {self.color('text_main')};
            background-color: transparent;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {self.color('surface_hover')};
            color: {self.color('text_main')};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {self.color('accent_emerald_bg')};
            color: {self.color('accent')};
        }}
        QMenu {{
            background-color: {self.color('surface_elevated')};
            border: 1px solid {self.color('border_strong')};
            border-radius: 8px;
            padding: 4px;
            color: {self.color('text_main')};
        }}
        QMenu::item {{
            padding: 8px 20px;
            border-radius: 6px;
            color: {self.color('text_main')};
            background-color: transparent;
        }}
        QMenu::item:hover, QMenu::item:selected {{
            background-color: {self.color('surface_hover')};
            color: {self.color('text_main')};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {self.color('border')};
            margin: 4px 8px;
        }}
        QProgressBar {{
            background-color: {self.color('track')};
            border: 1px solid {self.color('border')};
            border-radius: 4px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background-color: {self.color('accent')};
            border-radius: 3px;
        }}
        QCheckBox {{
            color: {self.color('text_main')};
            spacing: 10px;
            font-size: 13px;
            font-weight: 500;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid {self.color('input_border')};
            background-color: {self.color('input_bg')};
        }}
        QCheckBox::indicator:hover {{
            border-color: {self.color('accent')};
        }}
        QCheckBox::indicator:checked {{
            background-color: {self.color('accent')};
            border-color: {self.color('accent')};
        }}
        QToolTip {{
            background-color: {self.color('surface_elevated')};
            color: {self.color('text_main')};
            border: 1px solid {self.color('border')};
            border-radius: 6px;
            padding: 6px 10px;
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
    
    # Restrict hue to avoid pure purple (260-310 roughly). 
    # Let's map 0-360, but if it falls in 260-310, shift it.
    hue = hash_val % 360
    if 260 <= hue <= 310:
        hue = (hue + 60) % 360
        
    sat = 60 + (hash_val % 20) # 60-80% saturation (vibrant but not oversaturated)
    light = 50 + (hash_val % 10) # 50-60% lightness
    
    # Convert HSL to HEX
    return QColor.fromHsl(hue, int(sat * 2.55), int(light * 2.55)).name()

