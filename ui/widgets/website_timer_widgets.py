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
    def __init__(self, parent=None, domain: str = "", rule: dict = None, browser_name: str = "", browser_process: str = ""):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.domain = domain
        self.rule = rule or {}
        self.browser_name = browser_name
        self.browser_process = browser_process
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()

    def _set_preset(self, h: int, m: int):
        self.hours_combo.setCurrentText(str(h))
        self.mins_combo.setCurrentText(str(m))

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)  # Space for drop shadow
        
        self.container = QFrame()
        self.container.setObjectName("dialogContainer")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        if self.browser_name:
            title_text = f"Add Website Timer — {self.browser_name}"
        elif self.domain:
            title_text = "Configure Website Timer"
        else:
            title_text = "Add Website Timer"
        title = QLabel(title_text)
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
        
        # Presets Row
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)
        lbl_preset = QLabel("Presets:")
        lbl_preset.setObjectName("subLbl")
        preset_layout.addWidget(lbl_preset)
        
        presets = [("15m", 0, 15), ("30m", 0, 30), ("1h", 1, 0), ("2h", 2, 0), ("Unlimited", 0, 0)]
        for plabel, ph, pm_val in presets:
            pbtn = QPushButton(plabel)
            pbtn.setObjectName("presetBtn")
            pbtn.setCursor(Qt.CursorShape.PointingHandCursor)
            pbtn.setFixedHeight(28)
            pbtn.clicked.connect(lambda _, h_val=ph, m_val=pm_val: self._set_preset(h_val, m_val))
            preset_layout.addWidget(pbtn)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        layout.addSpacing(8)
        
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

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark=None):
        if is_dark is None:
            from ui.theme import ThemeManager
            is_dark = ThemeManager.instance().is_dark
        
        bg_col = "#0B0E14" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        title_col = "#F8FAFC" if is_dark else "#0F172A"
        sub_col = "#94A3B8" if is_dark else "#475569"
        input_bg = "#121721" if is_dark else "#F8FAFC"
        input_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.14)"
        input_col = "#F8FAFC" if is_dark else "#0F172A"
        cancel_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "#F1F5F9"
        cancel_col = "#94A3B8" if is_dark else "#475569"
        cancel_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.1)"

        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {bg_col};
                border-radius: 16px;
                border: 1px solid {border_col};
            }}
            QLabel {{
                color: {title_col};
                font-family: "Segoe UI", sans-serif;
            }}
            QLabel#titleLbl {{
                font-size: 20px;
                font-weight: 800;
                letter-spacing: -0.3px;
                color: {title_col};
            }}
            QLabel#subLbl {{
                font-size: 13px;
                font-weight: 700;
                color: {sub_col};
                margin-bottom: 2px;
            }}
            QLineEdit, QComboBox {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 8px;
                color: {input_col};
                padding: 10px;
                font-size: 14px;
                selection-background-color: #10B981;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #10B981;
                background-color: {input_bg};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                border-radius: 8px;
                padding: 10px 22px;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid rgba(16, 185, 129, 0.4);
            }}
            QPushButton:hover {{
                background: #059669;
                border-color: #10B981;
            }}
            QPushButton#cancelBtn {{
                background-color: {cancel_bg};
                color: {cancel_col};
                border: 1px solid {cancel_border};
            }}
            QPushButton#cancelBtn:hover {{
                background-color: rgba(255, 255, 255, 0.09);
                color: {title_col};
            }}
            QPushButton#presetBtn {{
                background-color: {cancel_bg};
                color: {sub_col};
                border: 1px solid {cancel_border};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#presetBtn:hover {{
                background-color: rgba(16, 185, 129, 0.15);
                color: #10B981;
                border: 1px solid #10B981;
            }}
        """)

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
