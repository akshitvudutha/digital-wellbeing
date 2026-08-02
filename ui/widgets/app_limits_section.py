from __future__ import annotations

from typing import Dict, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QScrollArea, QFrame, QPushButton
)
from database.repository import Repository
from protection.core import ProtectionManager

class AppLimitsSection(QWidget):
    def __init__(self, protection: ProtectionManager, parent=None) -> None:
        super().__init__(parent)
        self._protection = protection
        self._repo = Repository()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setMinimumHeight(400)
        
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(10)
        self.scroll.setWidget(self.inner)
        
        layout.addWidget(self.scroll)

    def refresh(self) -> None:
        # Clear existing
        while self.inner_layout.count():
            item = self.inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Get all apps
        import datetime
        start = datetime.date.today() - datetime.timedelta(days=7)
        apps = self._repo.get_top_apps_for_range(start, datetime.date.today(), limit=50)
        
        for app in apps:
            pname = app["process_name"]
            if not pname: continue
            
            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(10, 10, 10, 10)
            
            # App Name
            lbl = QLabel(pname.replace(".exe", "").title())
            lbl.setObjectName("setting_label")
            row_l.addWidget(lbl, 1)
            
            # Today's Usage
            elapsed_s = self._protection.timer.get_time(pname)
            usage_lbl = QLabel(f"{int(elapsed_s // 60)}m today")
            usage_lbl.setStyleSheet("color: #AAAAAA;")
            row_l.addWidget(usage_lbl)
            
            # Limit Combo
            combo = QComboBox()
            combo.setFixedWidth(120)
            combo.addItem("Unlimited", 0)
            combo.addItem("15 min", 15)
            combo.addItem("30 min", 30)
            combo.addItem("45 min", 45)
            combo.addItem("1 hour", 60)
            combo.addItem("2 hours", 120)
            combo.addItem("3 hours", 180)
            
            current_limit = self._protection.limits.get_limit(pname)
            current_mins = (current_limit // 60) if current_limit else 0
            
            idx = combo.findData(current_mins)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentIndex(0)
                
            def on_combo_changed(index: int, process_name=pname):
                mins = combo.itemData(index)
                sec = (mins * 60) if mins > 0 else None
                self._protection.limits.set_limit(process_name, sec)
                
            combo.currentIndexChanged.connect(on_combo_changed)
            row_l.addWidget(combo)
            
            self.inner_layout.addWidget(row)
            
        self.inner_layout.addStretch()
