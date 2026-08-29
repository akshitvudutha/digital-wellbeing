"""
kpi_cards.py — Reusable Key Performance Indicator cards.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from ui.theme import ThemeManager

class KPICard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("kpi_title")
        
        self._value_lbl = QLabel("-")
        self._value_lbl.setObjectName("kpi_value")
        
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addStretch()

        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#kpi_card {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#kpi_title {{
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QLabel#kpi_value {{
                color: {tm.color('text_main')};
                font-size: 24px;
                font-weight: 700;
            }}
        """)

    def set_value(self, text: str):
        self._value_lbl.setText(text)
