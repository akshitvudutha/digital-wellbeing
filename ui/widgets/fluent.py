"""
fluent.py — Reusable Fluent Design UI Components.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QFrame, QPushButton, QLabel, QVBoxLayout, QWidget, QGraphicsOpacityEffect

class FluentCard(QFrame):
    """A glassmorphism-styled card widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fluent_card")
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_base_theme)
        self._apply_base_theme(ThemeManager.instance().is_dark)

    def _apply_base_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QFrame#fluent_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#fluent_card:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
        """)


class FluentButton(QPushButton):
    """A consistent, rounded button with smooth hover state."""
    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("fluent_btn_primary" if primary else "fluent_btn_secondary")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._primary = primary
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        if self._primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tm.color('accent')};
                    color: #FFFFFF; /* Primary button text is always white */
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {tm.color('accent_hover')};
                }}
                QPushButton:pressed {{
                    background-color: {tm.color('accent')};
                    opacity: 0.8;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tm.color('primary_btn_gradient')};
                    color: {tm.color('text_main')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {tm.color('primary_btn_hover')};
                    border: 1px solid {tm.color('border_hover')};
                }}
                QPushButton:pressed {{
                    background-color: {tm.color('primary_btn_gradient')};
                }}
            """)


class FluentLabel(QLabel):
    """A semantic label for consistent typography."""
    
    class Style:
        TITLE = "title"
        HEADING = "heading"
        SUBHEADING = "subheading"
        BODY = "body"
        MUTED = "muted"
    
    def __init__(self, text: str, style: str = Style.BODY, parent=None):
        super().__init__(text, parent)
        self._style = style
        self.setObjectName(f"fluent_label_{style}")
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        if self._style == self.Style.TITLE:
            self.setStyleSheet(f"""
                QLabel {{
                    font-size: 28px;
                    font-weight: 800;
                    color: {tm.color('text_main')};
                    letter-spacing: -0.5px;
                }}
            """)
        elif self._style == self.Style.HEADING:
            self.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    font-weight: 700;
                    color: {tm.color('text_main')};
                }}
            """)
        elif self._style == self.Style.SUBHEADING:
            self.setStyleSheet(f"""
                QLabel {{
                    font-size: 15px;
                    font-weight: 600;
                    color: {tm.color('text_sub')};
                    letter-spacing: 0.2px;
                }}
            """)
        elif self._style == self.Style.MUTED:
            self.setStyleSheet(f"""
                QLabel {{
                    font-size: 13px;
                    font-weight: 400;
                    color: {tm.color('text_muted')};
                }}
            """)
        else: # Body
            self.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    font-weight: 400;
                    color: {tm.color('text_main')};
                }}
            """)
