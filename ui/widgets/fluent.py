"""
fluent.py — Reusable Fluent Design UI Components.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QFrame, QPushButton, QLabel, QVBoxLayout, QWidget, QGraphicsOpacityEffect, QAbstractButton

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

class ToggleSwitch(QAbstractButton):
    """A smooth, modern animated toggle switch (Windows 11 / Fluent style)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._thumb_position = 4.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.setDuration(200)
        
        self.toggled.connect(self._on_toggled)

    @Property(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()
        
    def _on_toggled(self, checked):
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(24.0 if checked else 4.0)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        # Track Colors
        if self.isChecked():
            track_color = QColor("#3B82F6") # Blue accent
        else:
            track_color = QColor(60, 60, 60) if is_dark else QColor(220, 220, 220)
            
        # Hover state
        if self.underMouse() and not self.isChecked():
            track_color = track_color.lighter(120) if is_dark else track_color.darker(110)
            
        # Draw track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2.0, self.height() / 2.0)
        
        # Thumb Colors
        if self.isChecked():
            thumb_color = QColor(255, 255, 255)
        else:
            thumb_color = QColor(200, 200, 200) if is_dark else QColor(120, 120, 120)
            if self.isDown(): # Press animation
                thumb_color = thumb_color.darker(110)
        
        # Draw thumb
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(QRectF(self._thumb_position, 4.0, 16.0, 16.0))
        painter.end()
