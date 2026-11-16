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
        from ui.theme import ThemeManager

        self._btn_focus = FluentButton(" Start Focus", primary=True)
        self._btn_focus.clicked.connect(self.action_focus.emit)

        self._btn_locker = FluentButton(" App Locker", primary=False)
        self._btn_locker.clicked.connect(self.action_locker.emit)

        self._btn_settings = FluentButton(" Settings", primary=False)
        self._btn_settings.clicked.connect(self.action_settings.emit)

        self._update_icons()
        ThemeManager.instance().theme_changed.connect(self._update_icons)

        layout.addWidget(self._btn_focus)
        layout.addWidget(self._btn_locker)
        layout.addWidget(self._btn_settings)
        layout.addStretch()

    def _update_icons(self, is_dark: bool = None) -> None:
        from ui.icons import get_icon
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self._btn_focus.setIcon(get_icon("focus", color="#FFFFFF"))
        self._btn_locker.setIcon(get_icon("lock", color=tm.color("text_main")))
        self._btn_settings.setIcon(get_icon("settings", color=tm.color("text_main")))
