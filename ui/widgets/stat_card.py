from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap


class StatCard(QFrame):
    """
    Reusable statistical metric card.
    Displays title, primary metric, optional supporting text, icon, and trend indicator.
    Fully backwards compatible with existing StatCard instances.
    """

    card_clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()
            event.accept()
        super().mousePressEvent(event)

    def __init__(
        self,
        label: str,
        value: str,
        icon: str = "",
        accent_color_key: str = "accent",
        subtext: str = "",
        trend: Optional[str] = None,
        trend_direction: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self._accent_key = accent_color_key
        self._icon_str = icon
        self._trend = trend
        self._trend_direction = trend_direction
        self._setup_ui(label, value, icon, subtext, trend)

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, label: str, value: str, icon: str, subtext: str, trend: Optional[str]) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # Icon pill with soft translucent glow
        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("stat_card_icon")
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_icon_display(icon)

        self._label_label = QLabel(label.upper(), self)
        self._label_label.setObjectName("stat_card_label")

        if icon:
            top_row.addWidget(self._icon_label)
            top_row.addSpacing(12)
        else:
            self._icon_label.hide()

        top_row.addWidget(self._label_label, 1)

        # Optional top-right trend badge
        self._trend_label = QLabel(self)
        self._trend_label.setObjectName("stat_card_trend")
        self._trend_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self._trend_label)
        if trend:
            self._trend_label.setText(trend)
            self._trend_label.show()
        else:
            self._trend_label.hide()

        self._value_label = QLabel(value, self)
        self._value_label.setObjectName("stat_card_value")

        self._layout.addLayout(top_row)
        self._layout.addWidget(self._value_label)

        # Bottom row for supporting subtext
        if subtext:
            self._subtext_label = QLabel(subtext, self)
            self._subtext_label.setObjectName("stat_card_subtext")
            self._layout.addWidget(self._subtext_label)
        else:
            self._subtext_label = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def _update_icon_display(self, icon: str) -> None:
        if not icon:
            self._icon_label.hide()
            return

        self._icon_label.show()
        from ui.icons import ICONS, get_pixmap
        from ui.theme import ThemeManager

        tm = ThemeManager.instance()
        accent = tm.color(self._accent_key)

        if icon in ICONS:
            pm = get_pixmap(icon, color=accent, size=20)
            self._icon_label.setPixmap(pm)
            self._icon_label.setText("")
        else:
            # Fallback for emoji or text character
            self._icon_label.setPixmap(QPixmap())
            self._icon_label.setText(icon)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        accent = tm.color(self._accent_key)

        # Determine trend color
        trend_col = tm.color("accent")
        if self._trend:
            direction = self._trend_direction
            if not direction:
                if any(c in self._trend for c in ["+", "↑"]):
                    direction = "up"
                elif any(c in self._trend for c in ["-", "↓"]):
                    direction = "down"
                else:
                    direction = "neutral"

            if direction == "up":
                trend_col = tm.color("accent")
            elif direction == "down":
                trend_col = tm.color("danger_text") if not is_dark else "#F87171"
            else:
                trend_col = tm.color("text_sub")

        from PySide6.QtGui import QColor
        qc_trend = QColor(trend_col)
        bg_trend = f"rgba({qc_trend.red()}, {qc_trend.green()}, {qc_trend.blue()}, 0.12)" if qc_trend.isValid() else "transparent"
        border_trend = f"rgba({qc_trend.red()}, {qc_trend.green()}, {qc_trend.blue()}, 0.25)" if qc_trend.isValid() else "transparent"

        qc_accent = QColor(accent)
        bg_icon = f"rgba({qc_accent.red()}, {qc_accent.green()}, {qc_accent.blue()}, 0.12)" if qc_accent.isValid() else "transparent"
        border_icon = f"rgba({qc_accent.red()}, {qc_accent.green()}, {qc_accent.blue()}, 0.25)" if qc_accent.isValid() else "transparent"

        self.setStyleSheet(f"""
            QLabel#stat_card_label {{ color: {tm.color('text_sub')}; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; }}
            QLabel#stat_card_value {{ font-size: 32px; font-weight: 900; color: {tm.color('text_main')}; letter-spacing: -0.8px; }}
            QLabel#stat_card_subtext {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
            QLabel#stat_card_trend {{
                color: {trend_col};
                font-size: 11px;
                font-weight: 700;
                padding: 3px 8px;
                border-radius: 6px;
                background-color: {bg_trend};
                border: 1px solid {border_trend};
            }}
        """)

        self._icon_label.setStyleSheet(
            f"color: {accent}; "
            f"background-color: {bg_icon}; "
            f"border: 1px solid {border_icon}; "
            f"border-radius: 12px; "
            f"font-size: 18px;"
        )
        self._update_icon_display(self._icon_str)

    def set_title(self, title: str) -> None:
        self._label_label.setText(title.upper())

    def set_metric(self, value: str) -> None:
        self._value_label.setText(value)

    def set_subtext(self, subtext: str) -> None:
        if self._subtext_label is None:
            self._subtext_label = QLabel(subtext, self)
            self._subtext_label.setObjectName("stat_card_subtext")
            self._layout.addWidget(self._subtext_label)
            self._subtext_label.show()
            from ui.theme import ThemeManager
            self._apply_theme(ThemeManager.instance().is_dark)
        else:
            self._subtext_label.setText(subtext)
            self._subtext_label.setVisible(bool(subtext))

    def set_trend(self, trend: Optional[str], direction: Optional[str] = None) -> None:
        self._trend = trend
        self._trend_direction = direction
        if trend:
            self._trend_label.setText(trend)
            self._trend_label.show()
        else:
            self._trend_label.hide()
        from ui.theme import ThemeManager
        self._apply_theme(ThemeManager.instance().is_dark)

    def set_icon(self, icon: str) -> None:
        self._icon_str = icon
        self._update_icon_display(icon)

    def update_value(self, value: str, subtext: str = "", trend: Optional[str] = None) -> None:
        """Backwards compatible update method."""
        self._value_label.setText(value)
        if subtext:
            self.set_subtext(subtext)
        if trend is not None:
            self.set_trend(trend)

    @property
    def value(self) -> str:
        return self._value_label.text()

    @property
    def title(self) -> str:
        return self._label_label.text()

    @property
    def trend_text(self) -> str:
        return self._trend or ""
