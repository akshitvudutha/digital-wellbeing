"""
fluent.py — Reusable Fluent Design UI Components.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
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
        self._anim.setStartValue(4.0)
        self._anim.setEndValue(24.0)
        
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


class IconButton(QAbstractButton):
    """A minimal icon-only button with Fluent hover/press animations, scaling, and rotation."""
    def __init__(self, icon_text: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon_text = icon_text
        
        self._hover_progress = 0.0
        self._scale = 1.0
        self._rotation = 0.0
        self._is_spinning = False
        
        self._hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)

        self._scale_anim = QPropertyAnimation(self, b"scale", self)
        self._scale_anim.setDuration(150)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._scale_anim.setStartValue(1.0)
        self._scale_anim.setEndValue(1.0)

        self._spin_anim = QPropertyAnimation(self, b"rotation", self)
        self._spin_anim.setDuration(700)
        self._spin_anim.setStartValue(0.0)
        self._spin_anim.setEndValue(360.0)
        self._spin_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._spin_anim.finished.connect(self._on_spin_finished)
        
    @Property(float)
    def hover_progress(self):
        return self._hover_progress
        
    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()

    @Property(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    @Property(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def set_spinning(self, spinning: bool):
        self._is_spinning = spinning
        if spinning:
            self.setCursor(Qt.CursorShape.BusyCursor)
            if self._spin_anim.state() != QPropertyAnimation.State.Running:
                self._spin_anim.start()
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_spin_finished(self):
        if self._is_spinning:
            self._spin_anim.start()
        else:
            self._rotation = 0.0
            self.update()
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        if not self.isDown():
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.03)
            self._scale_anim.start()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        if not self.isDown():
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.start()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(0.96)
            self._scale_anim.start()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.03 if self.underMouse() else 1.0)
            self._scale_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        # Dimensions
        w = self.width()
        h = self.height()
        
        # Leave some padding for shadow/glow
        rect_w = w - 8
        rect_h = h - 8
        
        center = QRectF(0, 0, w, h).center()
        painter.translate(center)
        painter.scale(self._scale, self._scale)
        
        # Fluent Translucent Colors
        if is_dark:
            base_color = QColor(255, 255, 255)
            normal_alpha = 25  # ~10%
            hover_alpha = 42   # ~16%
            press_alpha = 58   # ~22%
        else:
            base_color = QColor(0, 0, 0)
            normal_alpha = 15  # ~6%
            hover_alpha = 25   # ~10%
            press_alpha = 38   # ~15%
            
        # Interpolate between normal and hover alpha based on progress
        current_alpha = normal_alpha + (hover_alpha - normal_alpha) * self._hover_progress
        if self.isDown():
            current_alpha = press_alpha
            
        base_color.setAlpha(int(current_alpha))
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base_color))
        
        # Optional subtle glow/shadow at higher hover progress
        if self._hover_progress > 0.05 and not self.isDown():
            glow_color = QColor(255, 255, 255, int(15 * self._hover_progress)) if is_dark else QColor(0, 0, 0, int(10 * self._hover_progress))
            painter.setBrush(glow_color)
            # Draw slightly larger soft rect behind
            painter.drawRoundedRect(QRectF(-rect_w/2 - 1, -rect_h/2 - 1, rect_w + 2, rect_h + 2), 7, 7)
            
        # Main background
        painter.setBrush(QBrush(base_color))
        painter.drawRoundedRect(QRectF(-rect_w/2, -rect_h/2, rect_w, rect_h), 6, 6)
        
        painter.rotate(self._rotation)
        
        # Icon styling - thinner and modern
        icon_color = QColor(tm.color('text_main'))
        painter.setPen(icon_color)
        font = self.font()
        font.setPixelSize(19)  # 18-20px
        font.setWeight(QFont.Weight.Light)  # Thinner icon look
        painter.setFont(font)
        
        # Adjust Y slightly so icon looks perfectly centered visually
        painter.drawText(QRectF(-rect_w/2, -rect_h/2 - 2, rect_w, rect_h), Qt.AlignmentFlag.AlignCenter, self._icon_text)
        painter.end()
