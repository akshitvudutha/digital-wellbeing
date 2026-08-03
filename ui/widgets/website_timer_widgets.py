from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QDialog, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal
from ui.widgets.fluent import FluentLabel
from analytics.engine import AnalyticsEngine

class WebsiteTimerItem(QFrame):
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, domain: str, limit_s: int, used_s: float, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.limit_s = limit_s
        self.used_s = used_s
        self.setObjectName("website_item")
        self.setFixedHeight(80)
        self.setup_ui()
        self._apply_theme()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.domain_lbl = QLabel(self.domain)
        self.domain_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        
        limit_str = AnalyticsEngine.format_duration_short(self.limit_s)
        used_str = AnalyticsEngine.format_duration_short(self.used_s)
        self.stats_lbl = QLabel(f"Used {used_str} of {limit_str}")
        self.stats_lbl.setStyleSheet("font-size: 12px; color: #888888;")
        
        info_layout.addWidget(self.domain_lbl)
        info_layout.addWidget(self.stats_lbl)
        
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setFixedSize(60, 32)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setFixedSize(60, 32)
        self.btn_delete.setObjectName("btn_delete")
        
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.domain))
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.domain))
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)

    def _apply_theme(self):
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#website_item {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
            }}
            QFrame#website_item:hover {{
                background-color: {tm.color('hover')};
            }}
            QPushButton {{
                background-color: {tm.color('button_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 4px;
                color: {tm.color('text_main')};
            }}
            QPushButton:hover {{
                background-color: {tm.color('button_hover')};
            }}
            QPushButton#btn_delete {{
                color: #EF4444;
            }}
            QPushButton#btn_delete:hover {{
                background-color: rgba(239, 68, 68, 0.1);
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 250);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QLabel { color: white; }
            QLineEdit, QComboBox {
                background-color: rgba(0, 0, 0, 100);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 6px;
                color: white;
                padding: 8px;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton#cancelBtn {
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        
        title = QLabel("Configure Website Timer" if self.domain else "Add Website Timer")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        
        layout.addWidget(title)
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("e.g. instagram.com")
        if self.domain:
            self.domain_input.setText(self.domain)
            self.domain_input.setEnabled(False)
            
        layout.addWidget(QLabel("Website Domain"))
        layout.addWidget(self.domain_input)
        
        layout.addSpacing(10)
        
        time_layout = QHBoxLayout()
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
        
        time_layout.addWidget(QLabel("Hours:"))
        time_layout.addWidget(self.hours_combo)
        time_layout.addWidget(QLabel("Minutes:"))
        time_layout.addWidget(self.mins_combo)
        
        layout.addWidget(QLabel("Daily Limit"))
        layout.addLayout(time_layout)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_save = QPushButton("Save")
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

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
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        title = FluentLabel("Website Timers", FluentLabel.Style.HEADING)
        self.btn_add = QPushButton("+ Add Website")
        self.btn_add.setFixedSize(120, 36)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; border-radius: 18px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        self.btn_add.clicked.connect(self._on_add)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_add)
        
        self.layout.addLayout(header_layout)
        self.layout.addSpacing(10)
        
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(8)
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
            lbl = QLabel("No website timers configured. Click '+ Add Website' to create one.")
            lbl.setStyleSheet("color: #888888; padding: 20px;")
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
