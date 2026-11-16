"""
ui/widgets/status_badge.py — Reusable semantic status badge component.
Supports 'active', 'warning', 'exceeded', 'locked', and 'neutral' variants with
WCAG AA compliant contrast in both dark and light themes.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QColor

from ui.theme import ThemeManager


class StatusBadge(QFrame):
    """A semantic pill badge displaying status information with theme-aware styling."""

    VARIANTS = {"active", "warning", "exceeded", "locked", "neutral"}

    def __init__(
        self,
        text: str,
        variant: str = "neutral",
        show_dot: bool = False,
        icon_name: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("status_badge")
        self._text = text
        self._variant = variant.lower() if variant.lower() in self.VARIANTS else "neutral"
        self._show_dot = show_dot
        self._icon_name = icon_name

        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Optional Dot indicator
        self._dot_lbl = QLabel()
        self._dot_lbl.setObjectName("badge_dot")
        self._dot_lbl.setFixedSize(6, 6)
        self._dot_lbl.setVisible(self._show_dot)
        layout.addWidget(self._dot_lbl)

        # Optional Icon
        self._icon_lbl = QLabel()
        self._icon_lbl.setObjectName("badge_icon")
        self._icon_lbl.setFixedSize(12, 12)
        self._icon_lbl.setVisible(bool(self._icon_name))
        layout.addWidget(self._icon_lbl)

        # Text Label
        self._text_lbl = QLabel(self._text)
        self._text_lbl.setObjectName("badge_text")
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text_lbl)

    @property
    def variant(self) -> str:
        return self._variant

    def set_variant(self, variant: str) -> None:
        val = variant.lower()
        if val in self.VARIANTS:
            self._variant = val
            self._apply_theme(ThemeManager.instance().is_dark)

    def set_text(self, text: str) -> None:
        self._text = text
        self._text_lbl.setText(text)

    def text(self) -> str:
        return self._text

    def set_dot_visible(self, visible: bool) -> None:
        self._show_dot = visible
        self._dot_lbl.setVisible(visible)

    def set_icon(self, icon_name: Optional[str]) -> None:
        self._icon_name = icon_name
        self._icon_lbl.setVisible(bool(icon_name))
        self._apply_theme(ThemeManager.instance().is_dark)

    def _get_colors(self, is_dark: bool) -> tuple[str, str, str]:
        """Returns (text_color, bg_color, border_color) for the current variant and theme."""
        if self._variant == "active":
            if is_dark:
                return "#34D399", "rgba(16, 185, 129, 0.16)", "rgba(16, 185, 129, 0.35)"
            return "#047857", "rgba(4, 120, 87, 0.12)", "rgba(4, 120, 87, 0.30)"
        elif self._variant == "warning":
            if is_dark:
                return "#FBBF24", "rgba(245, 158, 11, 0.16)", "rgba(245, 158, 11, 0.35)"
            return "#B45309", "rgba(180, 83, 9, 0.12)", "rgba(180, 83, 9, 0.30)"
        elif self._variant == "exceeded":
            if is_dark:
                return "#F87171", "rgba(239, 68, 68, 0.16)", "rgba(239, 68, 68, 0.35)"
            return "#B91C1C", "rgba(185, 28, 28, 0.12)", "rgba(185, 28, 28, 0.30)"
        elif self._variant == "locked":
            if is_dark:
                return "#A78BFA", "rgba(139, 92, 246, 0.16)", "rgba(139, 92, 246, 0.35)"
            return "#6D28D9", "rgba(109, 40, 217, 0.12)", "rgba(109, 40, 217, 0.30)"
        else:  # neutral
            if is_dark:
                return "#94A3B8", "rgba(148, 163, 184, 0.12)", "rgba(148, 163, 184, 0.25)"
            return "#475569", "rgba(71, 85, 105, 0.10)", "rgba(71, 85, 105, 0.22)"

    def _apply_theme(self, is_dark: bool) -> None:
        text_col, bg_col, border_col = self._get_colors(is_dark)

        self.setStyleSheet(f"""
            QFrame#status_badge {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 6px;
            }}
            QLabel#badge_text {{
                color: {text_col};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
                background: transparent;
                border: none;
            }}
            QLabel#badge_dot {{
                background-color: {text_col};
                border-radius: 3px;
                border: none;
            }}
        """)

        if self._icon_name:
            from ui.icons import get_pixmap
            pm = get_pixmap(self._icon_name, color=text_col, size=12)
            self._icon_lbl.setPixmap(pm)
