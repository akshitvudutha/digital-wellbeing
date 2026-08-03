from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialog, QFrame, QScrollArea, QGraphicsOpacityEffect
)

from ui.theme import ThemeManager
from ui.widgets.fluent import FluentButton, FluentLabel, ToggleSwitch

class WheelPicker(QWidget):
    """A modern, animated scroll wheel picker."""
    value_changed = Signal(int)

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 160)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._items = items
        self._current_index = 0
        self._scroll_offset = 0.0  # in pixels
        self._item_height = 40
        self._is_dragging = False
        self._last_y = 0
        
        self._anim = QPropertyAnimation(self, b"scroll_offset", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(0.0)

    @Property(float)
    def scroll_offset(self):
        return self._scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, val):
        self._scroll_offset = val
        self.update()

    def set_index(self, index: int):
        self._current_index = max(0, min(len(self._items) - 1, index))
        self._scroll_offset = self._current_index * self._item_height
        self.update()

    def get_index(self) -> int:
        return self._current_index
        
    def _snap_to_index(self):
        idx = round(self._scroll_offset / self._item_height)
        idx = max(0, min(len(self._items) - 1, idx))
        self._current_index = idx
        self.value_changed.emit(idx)
        
        self._anim.stop()
        self._anim.setStartValue(self._scroll_offset)
        self._anim.setEndValue(idx * self._item_height)
        self._anim.start()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        self._scroll_offset -= delta * 0.2
        
        # Clamp bounds
        max_offset = (len(self._items) - 1) * self._item_height
        self._scroll_offset = max(0, min(max_offset, self._scroll_offset))
        self.update()
        
        if hasattr(self, "_snap_timer"):
            self._snap_timer.stop()
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self._snap_to_index)
        self._snap_timer.start(200)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._last_y = event.position().y()
            self._anim.stop()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            dy = event.position().y() - self._last_y
            self._scroll_offset -= dy
            self._last_y = event.position().y()
            
            max_offset = (len(self._items) - 1) * self._item_height
            self._scroll_offset = max(-self._item_height, min(max_offset + self._item_height, self._scroll_offset))
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._snap_to_index()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        h = self.height()
        w = self.width()
        center_y = h / 2.0
        
        font = self.font()
        font.setPixelSize(22)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        
        for i, item in enumerate(self._items):
            item_y_center = center_y + (i * self._item_height) - self._scroll_offset
            dist = abs(center_y - item_y_center)
            
            if dist > h / 2.0 + self._item_height:
                continue
                
            scale = max(0.6, 1.0 - (dist / (h / 1.2)))
            alpha = max(0, int(255 * (1.0 - (dist / (h / 2.0)))))
            
            painter.save()
            painter.translate(w/2, item_y_center)
            painter.scale(scale, scale)
            
            color = QColor(tm.color('text_main'))
            color.setAlpha(alpha)
            painter.setPen(color)
            
            rect = QRectF(-w/2, -self._item_height/2, w, self._item_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, item)
            painter.restore()


class CircularChip(QPushButton):
    """An animated circular chip for selecting repeat days."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(40, 40)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._bg_alpha = 0.0
        self._anim = QPropertyAnimation(self, b"bg_alpha", self)
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        
        self.toggled.connect(self._on_toggled)

    @Property(float)
    def bg_alpha(self):
        return self._bg_alpha

    @bg_alpha.setter
    def bg_alpha(self, val):
        self._bg_alpha = val
        self.update()

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._bg_alpha)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        # Draw background circle
        bg_color = QColor(tm.color('accent'))
        bg_color.setAlpha(int(255 * self._bg_alpha))
        
        painter.setPen(Qt.PenStyle.NoPen)
        if self._bg_alpha > 0:
            painter.setBrush(QBrush(bg_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
        painter.drawEllipse(2, 2, self.width()-4, self.height()-4)
        
        # Draw outline if not fully selected
        if self._bg_alpha < 1.0:
            border_color = QColor(tm.color('border'))
            painter.setPen(QPen(border_color, 1))
            painter.drawEllipse(2, 2, self.width()-4, self.height()-4)

        # Draw text
        text_color = QColor("#FFFFFF") if self._bg_alpha > 0.5 else QColor(tm.color('text_main'))
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(14)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class RepeatDaysPicker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self._days = ["M", "T", "W", "T", "F", "S", "S"]
        self._chips = []
        for d in self._days:
            chip = CircularChip(d)
            chip.setChecked(True)
            self._chips.append(chip)
            layout.addWidget(chip)
            
        layout.addStretch()

    def get_selected_days(self) -> list[int]:
        return [i for i, c in enumerate(self._chips) if c.isChecked()]

    def set_selected_days(self, days: list[int]):
        for i, c in enumerate(self._chips):
            c.setChecked(i in days)
            c._bg_alpha = 1.0 if c.isChecked() else 0.0


class RadioCard(QFrame):
    """A beautiful radio card for selections."""
    clicked = Signal(str)
    
    def __init__(self, title: str, desc: str, value: str, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self.value = value
        self._is_selected = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.desc_lbl = QLabel(desc)
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.desc_lbl)
        
        self._scale = 1.0
        self._anim = QPropertyAnimation(self, b"scale", self)
        self._anim.setDuration(150)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.97)
        
    @Property(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update()

    def mousePressEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(0.97)
        self._anim.start()

    def mouseReleaseEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.clicked.emit(self.value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        
        center = QRectF(self.rect()).center()
        painter.translate(center)
        painter.scale(self._scale, self._scale)
        
        rect = QRectF(-self.width()/2, -self.height()/2, self.width(), self.height())
        
        if self._is_selected:
            painter.setBrush(QBrush(QColor(tm.color('card_hover'))))
            painter.setPen(QPen(QColor(tm.color('accent')), 2))
            self.title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {tm.color('accent')};")
        else:
            painter.setBrush(QBrush(QColor(tm.color('card_bg'))))
            painter.setPen(QPen(QColor(tm.color('border')), 1))
            self.title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {tm.color('text_main')};")
            
        self.desc_lbl.setStyleSheet(f"font-size: 12px; color: {tm.color('text_sub')};")
            
        painter.drawRoundedRect(rect, 8, 8)


class RadioCardGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        self._cards = []

    def add_card(self, title: str, desc: str, value: str):
        card = RadioCard(title, desc, value)
        card.clicked.connect(self.set_selected)
        self._cards.append(card)
        self.layout.addWidget(card)

    def set_selected(self, value: str):
        for card in self._cards:
            card.set_selected(card.value == value)

    def get_selected(self) -> str:
        for card in self._cards:
            if card._is_selected:
                return card.value
        return ""


class PresetChipRow(QWidget):
    preset_selected = Signal(int) # minutes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        presets = [("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120), ("Unlimited", 0)]
        for label, val in presets:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked=False, v=val: self.preset_selected.emit(v))
            layout.addWidget(btn)
            
        layout.addStretch()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QPushButton {{
                background: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
                padding: 0 16px;
                color: {tm.color('text_main')};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {tm.color('card_hover')};
            }}
        """)


class MultiSelectChipRow(QWidget):
    def __init__(self, items: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self._chips = []
        for label, val in items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setProperty("val", val)
            self._chips.append(btn)
            layout.addWidget(btn)
            
        layout.addStretch()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QPushButton {{
                background: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
                padding: 0 16px;
                color: {tm.color('text_main')};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {tm.color('card_hover')};
            }}
            QPushButton:checked {{
                background: {tm.color('accent')};
                color: white;
                border: none;
            }}
        """)
        
    def get_selected(self) -> list[int]:
        return [btn.property("val") for btn in self._chips if btn.isChecked()]
        
    def set_selected(self, values: list[int]):
        for btn in self._chips:
            btn.setChecked(btn.property("val") in values)


class TimerConfigDialog(QDialog):
    """The main massive modal for configuring an app timer (Samsung inspired)."""
    def __init__(self, parent=None, current_rule: dict=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(540, 780)
        
        self.current_rule = current_rule or {}
        
        self._setup_ui()
        self._populate_data()
        
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("dialog_bg")
        
        # We need a scroll area because it's tall
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        scroll_content = QWidget()
        bg_layout = QVBoxLayout(scroll_content)
        bg_layout.setContentsMargins(32, 32, 32, 32)
        bg_layout.setSpacing(28)
        
        # Header
        header_layout = QHBoxLayout()
        title = FluentLabel("Configure App Timer", FluentLabel.Style.TITLE)
        header_layout.addWidget(title)
        header_layout.addStretch()
        bg_layout.addLayout(header_layout)
        
        # Timer Name
        from PySide6.QtWidgets import QLineEdit
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)
        name_layout.addWidget(FluentLabel("Timer Name (Optional)", FluentLabel.Style.HEADING))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Social Media Limit")
        self.name_input.setFixedHeight(40)
        self.name_input.setObjectName("timer_name_input")
        name_layout.addWidget(self.name_input)
        bg_layout.addLayout(name_layout)
        
        # Time Picker Row
        picker_layout = QHBoxLayout()
        picker_layout.addStretch()
        self.hr_picker = WheelPicker([str(i) for i in range(24)])
        self.min_picker = WheelPicker([str(i) for i in range(60)])
        hr_lbl = FluentLabel("hr", FluentLabel.Style.HEADING)
        min_lbl = FluentLabel("min", FluentLabel.Style.HEADING)
        picker_layout.addWidget(self.hr_picker)
        picker_layout.addWidget(hr_lbl)
        picker_layout.addSpacing(16)
        picker_layout.addWidget(self.min_picker)
        picker_layout.addWidget(min_lbl)
        picker_layout.addStretch()
        bg_layout.addLayout(picker_layout)
        
        # Presets
        self.preset_row = PresetChipRow()
        self.preset_row.preset_selected.connect(self._on_preset)
        bg_layout.addWidget(self.preset_row)
        
        # Repeat Days with Toggle
        days_header = QHBoxLayout()
        days_header.addWidget(FluentLabel("Repeat Days", FluentLabel.Style.HEADING))
        days_header.addStretch()
        days_header.addWidget(FluentLabel("Every Day", FluentLabel.Style.MUTED))
        self.every_day_toggle = ToggleSwitch()
        self.every_day_toggle.toggled.connect(self._on_every_day_toggled)
        days_header.addWidget(self.every_day_toggle)
        
        bg_layout.addLayout(days_header)
        self.days_picker = RepeatDaysPicker()
        bg_layout.addWidget(self.days_picker)
        
        # Notifications
        bg_layout.addWidget(FluentLabel("Notification Alerts", FluentLabel.Style.HEADING))
        self.alerts_row = MultiSelectChipRow([("15m before", 15), ("10m before", 10), ("5m before", 5), ("1m before", 1)])
        bg_layout.addWidget(self.alerts_row)
        
        # Action
        bg_layout.addWidget(FluentLabel("When Timer Expires", FluentLabel.Style.HEADING))
        self.action_group = RadioCardGroup()
        self.action_group.add_card("Close App", "Forcibly terminates the application", "close")
        self.action_group.add_card("Lock Screen", "Shows an overlay until tomorrow", "lock")
        self.action_group.add_card("Ask for PIN Override", "Allow override if PIN is entered", "pin")
        bg_layout.addWidget(self.action_group)
        
        # Reset note
        reset_lbl = FluentLabel("Timer resets every midnight.", FluentLabel.Style.MUTED)
        bg_layout.addWidget(reset_lbl)
        
        bg_layout.addStretch()
        scroll.setWidget(scroll_content)
        
        container_layout = QVBoxLayout(self.bg_frame)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)
        
        # Buttons fixed at bottom
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(32, 16, 32, 32)
        btn_layout.addStretch()
        cancel_btn = FluentButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = FluentButton("Save", primary=True)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.bg_frame)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#dialog_bg {{
                background-color: {tm.color('window_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
            }}
            QLineEdit#timer_name_input {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 0 12px;
                color: {tm.color('text_main')};
                font-size: 14px;
            }}
            QLineEdit#timer_name_input:focus {{
                border: 1px solid {tm.color('accent')};
            }}
        """)

    def _on_every_day_toggled(self, checked: bool):
        if checked:
            self.days_picker.set_selected_days([0,1,2,3,4,5,6])

    def _on_preset(self, mins: int):
        hr = mins // 60
        mn = mins % 60
        self.hr_picker.set_index(hr)
        self.min_picker.set_index(mn)

    def _populate_data(self):
        secs = self.current_rule.get("limit_seconds", 0)
        mins = secs // 60
        self.hr_picker.set_index(mins // 60)
        self.min_picker.set_index(mins % 60)
        
        self.name_input.setText(self.current_rule.get("name", ""))
        
        days = self.current_rule.get("repeat_days", [0,1,2,3,4,5,6])
        self.days_picker.set_selected_days(days)
        self.every_day_toggle.setChecked(len(days) == 7)
        
        notifs = self.current_rule.get("notifications", [15, 5, 1])
        self.alerts_row.set_selected(notifs)
        
        action = self.current_rule.get("on_expire", "lock")
        self.action_group.set_selected(action)

    def get_rule(self) -> dict:
        total_secs = (self.hr_picker.get_index() * 3600) + (self.min_picker.get_index() * 60)
        if total_secs == 0:
            return None # Unlimited
            
        return {
            "name": self.name_input.text().strip(),
            "limit_seconds": total_secs,
            "repeat_days": self.days_picker.get_selected_days(),
            "notifications": sorted(self.alerts_row.get_selected(), reverse=True),
            "on_expire": self.action_group.get_selected()
        }


class TimerDisplayCard(QFrame):
    """The summary card shown on App Details page displaying current timer (Samsung style)."""
    change_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timer_summary_card")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header area
        header_frame = QFrame()
        header_frame.setObjectName("timer_header")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        self.title_lbl = FluentLabel("App Timer", FluentLabel.Style.HEADING)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        self.status_lbl = FluentLabel("Disabled", FluentLabel.Style.MUTED)
        self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('text_sub')};")
        header_layout.addWidget(self.status_lbl)
        
        # Body area
        body_frame = QFrame()
        body_layout = QVBoxLayout(body_frame)
        body_layout.setContentsMargins(24, 20, 24, 24)
        body_layout.setSpacing(12)
        
        # Grid for stats
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(16)
        
        def add_stat(row, title, val_widget):
            lbl = FluentLabel(title, FluentLabel.Style.SUBHEADING)
            lbl.setFixedWidth(120)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val_widget, row, 1)
            
        self.val_limit = FluentLabel("Unlimited", FluentLabel.Style.BODY)
        self.val_repeats = FluentLabel("-", FluentLabel.Style.BODY)
        self.val_alerts = FluentLabel("-", FluentLabel.Style.BODY)
        self.val_action = FluentLabel("-", FluentLabel.Style.BODY)
        
        # Style values slightly bolder
        for w in [self.val_limit, self.val_repeats, self.val_alerts, self.val_action]:
            w.setStyleSheet("font-weight: 500;")
            
        add_stat(0, "Daily Limit", self.val_limit)
        add_stat(1, "Repeats", self.val_repeats)
        add_stat(2, "Alerts", self.val_alerts)
        add_stat(3, "Action", self.val_action)
        
        body_layout.addLayout(grid)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setObjectName("divider")
        body_layout.addSpacing(12)
        body_layout.addWidget(div)
        body_layout.addSpacing(12)
        
        # Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.change_btn = FluentButton("Edit Timer")
        self.change_btn.clicked.connect(self.change_requested.emit)
        btn_layout.addWidget(self.change_btn)
        body_layout.addLayout(btn_layout)
        
        main_layout.addWidget(header_frame)
        main_layout.addWidget(body_frame)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#timer_summary_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#timer_header {{
                background-color: {tm.color('card_hover')};
                border-bottom: 1px solid {tm.color('border')};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            QFrame#divider {{
                background-color: {tm.color('border')};
            }}
        """)

    def set_limit(self, rule: dict):
        if not rule or not rule.get("limit_seconds"):
            self.title_lbl.setText("App Timer")
            self.status_lbl.setText("Disabled")
            self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('text_muted')};")
            self.val_limit.setText("Unlimited")
            self.val_repeats.setText("-")
            self.val_alerts.setText("-")
            self.val_action.setText("-")
            self.change_btn.setText("Configure App Timer")
            return
            
        name = rule.get("name", "").strip()
        self.title_lbl.setText(name if name else "App Timer")
            
        self.status_lbl.setText("Enabled")
        self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('accent')};")
        
        secs = rule.get("limit_seconds", 0)
        hrs = secs // 3600
        mns = (secs % 3600) // 60
        if hrs > 0 and mns > 0:
            self.val_limit.setText(f"{hrs}h {mns}m")
        elif hrs > 0:
            self.val_limit.setText(f"{hrs}h")
        else:
            self.val_limit.setText(f"{mns}m")
            
        days = rule.get("repeat_days", [0,1,2,3,4,5,6])
        days_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        days_str = " ".join(days_map[d] for d in sorted(days)) if len(days) < 7 else "Every day"
        self.val_repeats.setText(days_str)
        
        action = rule.get("on_expire", "lock")
        action_str = "Close App" if action == "close" else "Ask for PIN" if action == "pin" else "Lock Screen"
        self.val_action.setText(action_str)
        
        notifs = rule.get("notifications", [])
        notifs_str = " • ".join(str(n)+'m' for n in sorted(notifs, reverse=True)) if notifs else "None"
        self.val_alerts.setText(notifs_str)
        
        self.change_btn.setText("Edit Timer")


class AnimatedProgressBar(QWidget):
    """Smooth animated progress bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._progress = 0.0
        
        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

    @Property(float)
    def progress(self):
        return self._progress
        
    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    def set_value(self, val: float):
        # val should be 0.0 to 1.0
        val = max(0.0, min(1.0, val))
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(val)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        
        bg_color = QColor(tm.color('border'))
        fill_color = QColor(tm.color('accent'))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height()/2, self.height()/2)
        
        if self._progress > 0:
            fill_w = self.width() * self._progress
            painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(0, 0, fill_w, self.height(), self.height()/2, self.height()/2)

