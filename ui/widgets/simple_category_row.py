"""
simple_category_row.py — Minimalist category row for the redesigned dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel
)

from core.constants import AppCategory, CATEGORY_ICONS
from analytics.engine import AnalyticsEngine

from ui.widgets.fluent import FluentCard

class ClickableCategoryCard(FluentCard):
    """A minimal card widget representing category usage with icon, name, and duration."""

    def __init__(
        self,
        category: AppCategory | str,
        duration_s: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("simple_category_row")
        
        self._category = category
        self._duration_s = duration_s
        
        self._setup_ui(duration_s)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, duration_s: float) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setFixedSize(140, 140)

        cat_enum = self._category if isinstance(self._category, AppCategory) else None
        if not cat_enum:
            try:
                cat_enum = AppCategory(str(self._category).title())
            except ValueError:
                pass
                
        icon_text = CATEGORY_ICONS.get(cat_enum, "📌") if cat_enum else "📌"
        cat_name = self._category.value.title() if isinstance(self._category, AppCategory) else str(self._category).title()

        # Category Icon
        self._icon_lbl = QLabel(icon_text)
        self._icon_lbl.setObjectName("cat_icon_lbl")
        self._icon_lbl.setFixedSize(36, 36)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_lbl)

        # Center Column (Name)
        self._name_lbl = QLabel(cat_name)
        self._name_lbl.setObjectName("cat_name_lbl")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_lbl)
        
        # Bottom Column (Duration)
        engine = AnalyticsEngine()
        self._dur_lbl = QLabel(engine.format_duration_short(duration_s))
        self._dur_lbl.setObjectName("cat_dur_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dur_lbl)

    def _apply_theme(self, is_dark: bool) -> None:
        if not hasattr(self, "_category"):
            return
            
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        from core.constants import CATEGORY_COLORS
        cat_enum = self._category if isinstance(self._category, AppCategory) else None
        if not cat_enum:
            try:
                cat_enum = AppCategory(str(self._category).title())
            except ValueError:
                pass
        cat_color = CATEGORY_COLORS.get(cat_enum, tm.color('accent')) if cat_enum else tm.color('accent')
        
        self.setStyleSheet(f"""
            ClickableCategoryCard:hover {{
                border-color: {cat_color};
            }}
            QLabel#cat_icon_lbl {{ 
                background-color: transparent;
                color: {cat_color};
                font-size: 28px;
            }}
            QLabel#cat_name_lbl {{ color: {tm.color('text_main')}; font-size: 15px; font-weight: 600; letter-spacing: 0.3px; }}
            QLabel#cat_dur_lbl {{ color: {tm.color('text_sub')}; font-size: 13px; font-weight: 500; }}
        """)
