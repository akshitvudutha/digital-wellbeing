"""
ui/widgets/segmented_control.py — Reusable, accessible segmented control component.
Supports keyboard navigation (Arrow keys, Space, Enter, Home, End), accessible focus states,
and theme-aware styling.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple, Union
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QPushButton, QSizePolicy, QWidget
)

from ui.theme import ThemeManager


class SegmentButton(QPushButton):
    """Internal button used inside SegmentedControl with keyboard forwarding."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


class SegmentedControl(QFrame):
    """
    A segmented pill control allowing selection among multiple mutually exclusive options.
    Full keyboard navigation: Left/Right/Up/Down arrow keys, Home, End, Space, Enter.
    """

    selection_changed = Signal(object)  # Emits value
    index_changed = Signal(int)         # Emits index

    def __init__(
        self,
        segments: List[Union[str, Tuple[str, Any], Tuple[str, Any, str]]],
        default_index: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmented_control")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setProperty("mouse_focus_clears", True)

        self._segments_data: List[Tuple[str, Any, Optional[str]]] = []
        self._buttons: List[SegmentButton] = []
        self._current_index = 0

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.idClicked.connect(self._on_button_id_clicked)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._layout.setSpacing(2)

        self.set_segments(segments, default_index=default_index)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def set_segments(
        self,
        segments: List[Union[str, Tuple[str, Any], Tuple[str, Any, str]]],
        default_index: int = 0,
    ) -> None:
        """Populate the segmented control with new items."""
        # Clean existing buttons
        for btn in self._buttons:
            self._button_group.removeButton(btn)
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()
        self._segments_data.clear()

        for idx, item in enumerate(segments):
            if isinstance(item, tuple):
                if len(item) == 2:
                    label, val = item
                    icon = None
                else:
                    label, val, icon = item[0], item[1], item[2]
            else:
                label = str(item)
                val = item
                icon = None

            self._segments_data.append((label, val, icon))

            btn = SegmentButton(label, self)
            btn.setObjectName("segment_btn")
            if icon:
                from ui.icons import get_icon
                btn.setIcon(get_icon(icon, size=16))

            self._buttons.append(btn)
            self._button_group.addButton(btn, idx)
            self._layout.addWidget(btn)

        if self._buttons:
            target_idx = max(0, min(default_index, len(self._buttons) - 1))
            self.set_current_index(target_idx, emit_signal=False)

        self._apply_theme(ThemeManager.instance().is_dark)

    def _on_button_id_clicked(self, idx: int) -> None:
        if idx != self._current_index:
            self._current_index = idx
            val = self._segments_data[idx][1]
            self.selection_changed.emit(val)
            self.index_changed.emit(idx)

    def current_index(self) -> int:
        return self._current_index

    def current_value(self) -> Any:
        if 0 <= self._current_index < len(self._segments_data):
            return self._segments_data[self._current_index][1]
        return None

    def current_text(self) -> str:
        if 0 <= self._current_index < len(self._segments_data):
            return self._segments_data[self._current_index][0]
        return ""

    def count(self) -> int:
        return len(self._buttons)

    def set_current_index(self, index: int, emit_signal: bool = True) -> None:
        if 0 <= index < len(self._buttons):
            self._current_index = index
            self._buttons[index].setChecked(True)
            if emit_signal:
                val = self._segments_data[index][1]
                self.selection_changed.emit(val)
                self.index_changed.emit(index)

    def set_current_value(self, value: Any, emit_signal: bool = True) -> bool:
        for idx, (_, val, _) in enumerate(self._segments_data):
            if val == value:
                self.set_current_index(idx, emit_signal=emit_signal)
                return True
        return False

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()

        bg_frame = tm.color("surface_secondary")
        border_frame = tm.color("border")
        active_bg = tm.color("card_bg") if is_dark else "#FFFFFF"
        active_border = tm.color("border_strong") if is_dark else "rgba(0, 0, 0, 0.12)"
        active_text = tm.color("accent")
        inactive_text = tm.color("text_sub")
        hover_bg = tm.color("surface_hover")
        focus_ring = tm.color("focus_ring")

        self.setStyleSheet(f"""
            QFrame#segmented_control {{
                background-color: {bg_frame};
                border: 1px solid {border_frame};
                border-radius: 8px;
            }}
            QFrame#segmented_control:focus {{
                border: 2px solid {focus_ring};
            }}
            QPushButton#segment_btn {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {inactive_text};
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#segment_btn:hover {{
                background-color: {hover_bg};
                color: {tm.color('text_main')};
            }}
            QPushButton#segment_btn:checked {{
                background-color: {active_bg};
                border: 1px solid {active_border};
                color: {active_text};
                font-weight: 700;
            }}
            QPushButton#segment_btn:focus {{
                border: 2px solid {focus_ring};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        count = len(self._buttons)
        if count == 0:
            super().keyPressEvent(event)
            return

        if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            new_idx = (self._current_index - 1) % count
            self.set_current_index(new_idx)
            event.accept()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            new_idx = (self._current_index + 1) % count
            self.set_current_index(new_idx)
            event.accept()
        elif key == Qt.Key.Key_Home:
            self.set_current_index(0)
            event.accept()
        elif key == Qt.Key.Key_End:
            self.set_current_index(count - 1)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            # Re-emit current selection
            val = self.current_value()
            self.selection_changed.emit(val)
            self.index_changed.emit(self._current_index)
            event.accept()
        else:
            super().keyPressEvent(event)
