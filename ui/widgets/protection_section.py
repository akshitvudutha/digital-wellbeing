from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QMessageBox
)
from protection.core import ProtectionManager

class ProtectionSection(QWidget):
    def __init__(self, protection: ProtectionManager, parent=None) -> None:
        super().__init__(parent)
        self._protection = protection
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("setting_desc")
        layout.addWidget(self.status_lbl)
        
        row = QHBoxLayout()
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter 4-8 digit PIN")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setFixedWidth(200)
        row.addWidget(self.pin_input)
        
        self.btn_action = QPushButton("Enable PIN")
        self.btn_action.setFixedWidth(120)
        self.btn_action.clicked.connect(self._on_action)
        row.addWidget(self.btn_action)
        row.addStretch()
        
        layout.addLayout(row)
        self._refresh()
        
    def _refresh(self) -> None:
        if self._protection.pin.is_enabled():
            self.status_lbl.setText("PIN is currently ENABLED. Enter a new PIN to change it, or leave blank and click Disable.")
            self.btn_action.setText("Update / Disable")
        else:
            self.status_lbl.setText("PIN is currently DISABLED. Set a PIN to protect limits.")
            self.btn_action.setText("Enable PIN")
            
    def _on_action(self) -> None:
        pin = self.pin_input.text().strip()
        if not pin:
            if self._protection.pin.is_enabled():
                self._protection.pin.disable_pin()
                QMessageBox.information(self, "PIN Disabled", "PIN protection has been disabled.")
            else:
                QMessageBox.warning(self, "Error", "Please enter a PIN.")
        else:
            if self._protection.pin.set_pin(pin):
                QMessageBox.information(self, "PIN Set", "PIN has been successfully saved.")
                self.pin_input.clear()
            else:
                QMessageBox.warning(self, "Error", "PIN must be 4 to 8 digits.")
                
        self._refresh()
