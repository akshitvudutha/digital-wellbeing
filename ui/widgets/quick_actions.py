"""
quick_actions.py — A row of quick action buttons for the dashboard.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout
from ui.widgets.fluent import FluentButton

class QuickActionsRow(QWidget):
    action_focus = Signal()
    action_locker = Signal()
    action_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        from ui.icons import get_icon
        
        btn_focus = FluentButton(" Start Focus", primary=True)
        btn_focus.setIcon(get_icon("focus"))
        btn_focus.clicked.connect(self.action_focus.emit)
        
        btn_locker = FluentButton(" App Locker", primary=False)
        btn_locker.setIcon(get_icon("lock"))
        btn_locker.clicked.connect(self.action_locker.emit)
        
        btn_settings = FluentButton(" Settings", primary=False)
        btn_settings.setIcon(get_icon("settings"))
        btn_settings.clicked.connect(self.action_settings.emit)
        
        layout.addWidget(btn_focus)
        layout.addWidget(btn_locker)
        layout.addWidget(btn_settings)
        layout.addStretch()
