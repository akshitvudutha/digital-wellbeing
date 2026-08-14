from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QDialog, QLineEdit, QComboBox, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from ui.widgets.fluent import FluentLabel
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager

class WebsiteTimerItem(QFrame):
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, domain: str, limit_s: int, used_s: float, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.limit_s = limit_s
        self.used_s = used_s
        self.setObjectName("website_item")
        # Removing absolute height, let it size automatically
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setup_ui()
        self._apply_theme()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        tm = ThemeManager.instance()
        
        self.domain_lbl = QLabel(self.domain)
        self.domain_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {tm.color('text_main')};")
        
        limit_str = AnalyticsEngine.format_duration_short(self.limit_s)
        used_str = AnalyticsEngine.format_duration_short(self.used_s)
        self.stats_lbl = QLabel(f"Used {used_str} of {limit_str}")
        self.stats_lbl.setStyleSheet(f"font-size: 13px; color: {tm.color('text_sub')};")
        
        info_layout.addWidget(self.domain_lbl)
        info_layout.addWidget(self.stats_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("btn_delete")
        self.btn_delete.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.domain))
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.domain))
        
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#website_item {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#website_item:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QPushButton {{
                background-color: {tm.color('window_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 6px;
                color: {tm.color('text_main')};
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QPushButton:pressed {{
                background-color: {tm.color('card_pressed')};
            }}
            QPushButton#btn_delete {{
                color: {tm.color('danger_text')};
            }}
            QPushButton#btn_delete:hover {{
                background-color: {tm.color('danger_bg')};
                border: 1px solid {tm.color('danger_border')};
            }}
        """)

class WebsiteTimerConfigDialog(QDialog):
    def __init__(self, parent=None, domain: str = "", rule: dict = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.domain = domain
        self.rule = rule or {}
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Space for drop shadow
        
        self.container = QFrame()
        self.container.setObjectName("dialogContainer")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {tm.color('window_bg')};
                border-radius: 16px;
                border: 1px solid {tm.color('border')};
            }}
            QLabel {{
                color: {tm.color('text_main')};
                font-family: "Segoe UI", sans-serif;
            }}
            QLabel#titleLbl {{
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#subLbl {{
                font-size: 14px;
                font-weight: 600;
                color: {tm.color('text_sub')};
                margin-bottom: 4px;
            }}
            QLineEdit, QComboBox {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                color: {tm.color('text_main')};
                padding: 12px;
                font-size: 14px;
                selection-background-color: {tm.color('accent')};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {tm.color('accent')};
                background-color: {tm.color('card_hover')};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QPushButton {{
                background-color: {tm.color('accent')};
                color: white;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 700;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {tm.color('accent')};
            }}
            QPushButton#cancelBtn {{
                background-color: {tm.color('card_bg')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#cancelBtn:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QPushButton#cancelBtn:pressed {{
                background-color: {tm.color('card_pressed')};
            }}
        """)
        
        title = QLabel("Configure Website Timer" if self.domain else "Add Website Timer")
        title.setObjectName("titleLbl")
        layout.addWidget(title)
        
        # Domain Section
        domain_layout = QVBoxLayout()
        domain_layout.setSpacing(4)
        lbl_domain = QLabel("Website Domain")
        lbl_domain.setObjectName("subLbl")
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("e.g. instagram.com")
        if self.domain:
            self.domain_input.setText(self.domain)
            self.domain_input.setEnabled(False)
            
        domain_layout.addWidget(lbl_domain)
        domain_layout.addWidget(self.domain_input)
        layout.addLayout(domain_layout)
        
        # Time Section
        time_section_layout = QVBoxLayout()
        time_section_layout.setSpacing(4)
        lbl_limit = QLabel("Daily Limit")
        lbl_limit.setObjectName("subLbl")
        time_section_layout.addWidget(lbl_limit)
        
        time_h_layout = QHBoxLayout()
        time_h_layout.setSpacing(12)
        
        self.hours_combo = QComboBox()
        self.hours_combo.addItems([str(i) for i in range(24)])
        self.mins_combo = QComboBox()
        self.mins_combo.addItems([str(i) for i in range(0, 60, 5)])
        
        limit_s = self.rule.get("limit_seconds", 1800)
        h = limit_s // 3600
        m = (limit_s % 3600) // 60
        self.hours_combo.setCurrentText(str(h))
        m_snap = (m // 5) * 5
        self.mins_combo.setCurrentText(str(m_snap))
        
        # Hours Wrapper
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.hours_combo, 1)
        h_layout.addWidget(QLabel("hrs"))
        
        # Mins Wrapper
        m_layout = QHBoxLayout()
        m_layout.addWidget(self.mins_combo, 1)
        m_layout.addWidget(QLabel("mins"))
        
        time_h_layout.addLayout(h_layout)
        time_h_layout.addLayout(m_layout)
        
        time_section_layout.addLayout(time_h_layout)
        layout.addLayout(time_section_layout)
        
        layout.addSpacing(16)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_save = QPushButton("Save")
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)

    def get_data(self):
        h = int(self.hours_combo.currentText())
        m = int(self.mins_combo.currentText())
        limit_s = h * 3600 + m * 60
        domain = self.domain_input.text().strip().lower()
        if domain.startswith("http"):
            domain = domain.split("//")[-1].split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain, {
            "limit_seconds": limit_s,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock"
        }

class WebsiteTimersSection(QWidget):
    def __init__(self, protection_manager, process_name: str, parent=None):
        super().__init__(parent)
        self.pm = protection_manager
        self.process_name = process_name
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        title = FluentLabel("Website Timers", FluentLabel.Style.HEADING)
        self.btn_add = QPushButton("+ Add Website")
        self.btn_add.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        tm = ThemeManager.instance()
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {tm.color('accent')};
                color: white;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {tm.color('accent_hover')}; }}
            QPushButton:pressed {{ background-color: {tm.color('accent')}; }}
        """)
        self.btn_add.clicked.connect(self._on_add)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_add)
        
        self.layout.addLayout(header_layout)
        
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(12)
        self.layout.addLayout(self.list_layout)
        
        self.refresh()

    def refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.pm:
            return
            
        limits = self.pm.website_limits.get_all_limits(self.process_name)
        if not limits:
            lbl = QLabel("No website timers configured.\nClick '+ Add Website' to create one.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tm = ThemeManager.instance()
            lbl.setStyleSheet(f"color: {tm.color('text_sub')}; font-size: 14px; padding: 40px; background: {tm.color('card_bg')}; border-radius: 12px; border: 1px dashed {tm.color('border')};")
            self.list_layout.addWidget(lbl)
            return
            
        for domain, rule in limits.items():
            limit_s = rule.get("limit_seconds", 0)
            used_s = self.pm.website_timer.get_time(domain)
            item = WebsiteTimerItem(domain, limit_s, used_s)
            item.edit_requested.connect(self._on_edit)
            item.delete_requested.connect(self._on_delete)
            self.list_layout.addWidget(item)

    def _on_add(self):
        dialog = WebsiteTimerConfigDialog(self.window())
        if dialog.exec():
            domain, rule = dialog.get_data()
            if domain and rule["limit_seconds"] > 0:
                self.pm.website_limits.set_limit_rule(self.process_name, domain, rule)
                self.refresh()

    def _on_edit(self, domain: str):
        rule = self.pm.website_limits.get_all_limits(self.process_name).get(domain, {})
        dialog = WebsiteTimerConfigDialog(self.window(), domain=domain, rule=rule)
        if dialog.exec():
            _, rule = dialog.get_data()
            if rule["limit_seconds"] > 0:
                self.pm.website_limits.set_limit_rule(self.process_name, domain, rule)
                self.refresh()

    def _on_delete(self, domain: str):
        self.pm.website_limits.set_limit_rule(self.process_name, domain, None)
        self.refresh()
