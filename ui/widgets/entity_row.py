"""
ui/widgets/entity_row.py — Reusable EntityRow component.
Displays an entity (application, category, website, session) with icon,
primary/secondary text, optional badge, progress bar, and action buttons.
Accessible with keyboard focus (Space/Enter activation) and theme-aware styling.
"""

from __future__ import annotations

from typing import Optional, Union
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor, QIcon, QPixmap, QKeyEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget, QPushButton
)

from ui.theme import ThemeManager
from ui.widgets.status_badge import StatusBadge


class EntityRow(QFrame):
    """
    A unified, accessible entity row for applications, websites, categories, or schedules.
    """

    clicked = Signal(str)

    def __init__(
        self,
        primary_text: str,
        secondary_text: str = "",
        icon: Optional[Union[QIcon, QPixmap, str]] = None,
        badge: Optional[Union[StatusBadge, str]] = None,
        badge_variant: str = "neutral",
        progress: Optional[float] = None,
        trailing_text: str = "",
        entity_id: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("entity_row")
        self.entity_id = entity_id or primary_text
        self._primary_text = primary_text
        self._secondary_text = secondary_text
        self._trailing_text = trailing_text
        self._progress = progress
        self._icon = icon

        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setProperty("mouse_focus_clears", True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._setup_ui(badge, badge_variant)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, badge: Optional[Union[StatusBadge, str]], badge_variant: str) -> None:
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(12, 10, 12, 10)
        self._main_layout.setSpacing(12)

        # 1. Leading Icon
        self._icon_lbl = QLabel(self)
        self._icon_lbl.setObjectName("entity_icon")
        self._icon_lbl.setFixedSize(32, 32)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_icon(self._icon)
        self._main_layout.addWidget(self._icon_lbl)

        # 2. Center Content (Primary, Secondary, Progress)
        self._center_layout = QVBoxLayout()
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._center_layout.setSpacing(4)

        # Top row: Primary label + Badge + Stretch
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self._primary_lbl = QLabel(self._primary_text, self)
        self._primary_lbl.setObjectName("entity_primary_text")
        top_row.addWidget(self._primary_lbl)

        # Optional Badge
        self._badge_widget: Optional[QWidget] = None
        if isinstance(badge, StatusBadge):
            self._badge_widget = badge
        elif isinstance(badge, str) and badge:
            self._badge_widget = StatusBadge(badge, variant=badge_variant, parent=self)

        if self._badge_widget:
            top_row.addWidget(self._badge_widget)

        top_row.addStretch()
        self._center_layout.addLayout(top_row)

        # Subtitle / Secondary label
        self._secondary_lbl = QLabel(self._secondary_text, self)
        self._secondary_lbl.setObjectName("entity_secondary_text")
        if not self._secondary_text:
            self._secondary_lbl.hide()
        self._center_layout.addWidget(self._secondary_lbl)

        # Optional Progress Bar
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setObjectName("entity_progress_bar")
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setRange(0, 100)
        self._center_layout.addWidget(self._progress_bar)
        if self._progress is not None:
            self._progress_bar.setValue(int(min(max(self._progress, 0.0), 1.0) * 100))
        else:
            self._progress_bar.hide()

        self._main_layout.addLayout(self._center_layout, 1)

        # 3. Trailing text (duration, timestamp, etc.)
        self._trailing_lbl = QLabel(self._trailing_text)
        self._trailing_lbl.setObjectName("entity_trailing_text")
        self._trailing_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if not self._trailing_text:
            self._trailing_lbl.hide()
        self._main_layout.addWidget(self._trailing_lbl)

        # 4. Actions container
        self._actions_layout = QHBoxLayout()
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(6)
        self._main_layout.addLayout(self._actions_layout)

    def _update_icon(self, icon: Optional[Union[QIcon, QPixmap, str]]) -> None:
        if icon is None:
            self._icon_lbl.hide()
            return

        self._icon_lbl.show()
        if isinstance(icon, QPixmap):
            self._icon_lbl.setPixmap(icon.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        elif isinstance(icon, QIcon):
            self._icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))
        elif isinstance(icon, str):
            # Check if it is a registered SVG icon name
            from ui.icons import ICONS, get_pixmap
            if icon in ICONS:
                tm = ThemeManager.instance()
                pm = get_pixmap(icon, color=tm.color("text_main"), size=24)
                self._icon_lbl.setPixmap(pm)
            else:
                # Try app icon provider
                try:
                    from utils.icon_provider import AppIconProvider
                    app_ico = AppIconProvider().get_icon(icon)
                    if not app_ico.isNull():
                        self._icon_lbl.setPixmap(app_ico.pixmap(QSize(32, 32)))
                        return
                except Exception:
                    pass
                self._icon_lbl.setText(icon[:2].upper())

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()

        card_bg = "transparent"
        hover_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"
        border_col = tm.color("border")
        accent = tm.color("accent")
        focus_ring = tm.color("focus_ring")

        self.setStyleSheet(f"""
            QFrame#entity_row {{
                background-color: {card_bg};
                border: 1px solid transparent;
                border-radius: 8px;
            }}
            QFrame#entity_row:hover {{
                background-color: {hover_bg};
            }}
            QFrame#entity_row:focus {{
                border: 2px solid {focus_ring};
            }}
            QLabel#entity_primary_text {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#entity_secondary_text {{
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
            QLabel#entity_trailing_text {{
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                font-family: monospace;
                background: transparent;
            }}
            QProgressBar#entity_progress_bar {{
                background-color: {tm.color('surface_secondary')};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar#entity_progress_bar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
        """)

        # Re-render icon if string SVG icon name was passed
        if isinstance(self._icon, str):
            self._update_icon(self._icon)

    def set_primary_text(self, text: str) -> None:
        self._primary_text = text
        self._primary_lbl.setText(text)

    def set_secondary_text(self, text: str) -> None:
        self._secondary_text = text
        self._secondary_lbl.setText(text)
        self._secondary_lbl.setVisible(bool(text))

    def set_trailing_text(self, text: str) -> None:
        self._trailing_text = text
        self._trailing_lbl.setText(text)
        self._trailing_lbl.setVisible(bool(text))

    def set_progress(self, progress: Optional[float]) -> None:
        self._progress = progress
        if progress is not None:
            pct = int(min(max(progress, 0.0), 1.0) * 100)
            self._progress_bar.setValue(pct)
            self._progress_bar.show()
        else:
            self._progress_bar.hide()

    def set_badge(self, badge: Optional[Union[StatusBadge, str]], variant: str = "neutral") -> None:
        if self._badge_widget:
            self._badge_widget.setParent(None)
            self._badge_widget.deleteLater()
            self._badge_widget = None

        if isinstance(badge, StatusBadge):
            self._badge_widget = badge
        elif isinstance(badge, str) and badge:
            self._badge_widget = StatusBadge(badge, variant=variant)

        if self._badge_widget:
            # Insert after primary label
            top_layout = self._center_layout.itemAt(0).layout()
            top_layout.insertWidget(1, self._badge_widget)

    def set_icon(self, icon: Optional[Union[QIcon, QPixmap, str]]) -> None:
        self._icon = icon
        self._update_icon(icon)

    @property
    def primary_text(self) -> str:
        return self._primary_text

    @property
    def title(self) -> str:
        return self._primary_text

    def add_action(self, widget: QWidget) -> None:
        """Add an action button or control to the trailing edge of the row."""
        self._actions_layout.addWidget(widget)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entity_id)
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.entity_id)
            event.accept()
        else:
            super().keyPressEvent(event)
