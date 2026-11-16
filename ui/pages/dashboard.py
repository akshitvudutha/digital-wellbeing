"""
ui/pages/dashboard.py — Redesigned Modern Dashboard Page for Notch.
Features disciplined 8px spacing, cohesive hierarchy, and integration with the
Batch 2 Shared Component Library (StatCard, StatusBadge, EntityRow).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager
from ui.widgets.stat_card import StatCard
from ui.widgets.status_badge import StatusBadge
from ui.widgets.entity_row import EntityRow


class DashboardPage(QWidget):
    """Modern visual Dashboard for Digital Wellbeing."""

    request_screen_time_details = Signal()
    request_focus_session = Signal()
    request_category_details = Signal(str)
    request_app_details = Signal(str)

    def __init__(
        self,
        on_global_refresh: Optional[Callable[[], None]] = None,
        navigate_callback: Optional[Callable[[int], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_global_refresh = on_global_refresh
        self._navigate = navigate_callback
        self._engine = AnalyticsEngine()
        self._setup_ui()
        self._refresh()

        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(16)

        # ── 1. Header Row ─────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self._greeting_label = QLabel("Good morning")
        self._greeting_label.setObjectName("dashboard_greeting")
        self._context_label = QLabel("")
        self._context_label.setObjectName("dashboard_context")
        self._date_label = QLabel("")
        self._date_label.setObjectName("dashboard_date")

        title_box.addWidget(self._greeting_label)
        title_box.addWidget(self._context_label)
        title_box.addWidget(self._date_label)
        header.addLayout(title_box)

        header.addStretch()

        from ui.widgets.fluent import IconButton
        self._refresh_btn = IconButton("↻")
        self._refresh_btn.setToolTip("Refresh Data")
        self._is_refreshing = False
        self._refresh_btn.clicked.connect(self._trigger_refresh)
        header.addWidget(self._refresh_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header)

        # ── 2. Scrollable Body Area ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(16)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # ── 3. Overview Metrics Row (StatCards) ────────────────────────────────
        overview_row = QHBoxLayout()
        overview_row.setSpacing(16)

        self._screen_time_card = StatCard(
            label="Today's Screen Time",
            value="0h 0m",
            icon="clock",
            accent_color_key="accent",
            subtext="Click to view full breakdown",
        )
        self._screen_time_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self._screen_time_card.card_clicked.connect(self.request_screen_time_details.emit)

        self._active_time_card = StatCard(
            label="Active Time",
            value="0h 0m",
            icon="usage",
            accent_color_key="accent",
            subtext="Intentional computer activity",
        )

        self._idle_time_card = StatCard(
            label="Idle Time",
            value="0h 0m",
            icon="hourglass",
            accent_color_key="accent_amber",
            subtext="Inactivity detected",
        )

        overview_row.addWidget(self._screen_time_card)
        overview_row.addWidget(self._active_time_card)
        overview_row.addWidget(self._idle_time_card)
        self._inner_layout.addLayout(overview_row)

        # ── 4. Main Content Grid (Two Columns: 5 : 3) ─────────────────────────
        content_grid = QHBoxLayout()
        content_grid.setSpacing(16)

        # ── Left Column: Top Applications & Categories ─────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Top Applications Card
        self._apps_card = QFrame()
        self._apps_card.setObjectName("v2_card")
        apps_layout = QVBoxLayout(self._apps_card)
        apps_layout.setContentsMargins(20, 18, 20, 18)
        apps_layout.setSpacing(12)

        apps_hdr = QHBoxLayout()
        lbl_apps = QLabel("TOP APPLICATIONS")
        lbl_apps.setObjectName("card_section_title")
        apps_hdr.addWidget(lbl_apps)
        apps_hdr.addStretch()
        apps_layout.addLayout(apps_hdr)

        self._apps_container = QVBoxLayout()
        self._apps_container.setSpacing(6)
        apps_layout.addLayout(self._apps_container)
        left_col.addWidget(self._apps_card)

        # Most Used Categories Card
        self._cats_card = QFrame()
        self._cats_card.setObjectName("v2_card")
        cats_layout = QVBoxLayout(self._cats_card)
        cats_layout.setContentsMargins(20, 18, 20, 18)
        cats_layout.setSpacing(12)

        cats_hdr = QHBoxLayout()
        lbl_cats = QLabel("MOST USED CATEGORIES")
        lbl_cats.setObjectName("card_section_title")
        cats_hdr.addWidget(lbl_cats)
        cats_hdr.addStretch()
        cats_layout.addLayout(cats_hdr)

        self._cats_container = QVBoxLayout()
        self._cats_container.setSpacing(6)
        cats_layout.addLayout(self._cats_container)
        left_col.addWidget(self._cats_card)

        content_grid.addLayout(left_col, stretch=5)

        # ── Right Column: Focus Cockpit & Wellbeing Controls ───────
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Focus Session Cockpit Card
        self._focus_card = QFrame()
        self._focus_card.setObjectName("v2_card")
        focus_layout = QVBoxLayout(self._focus_card)
        focus_layout.setContentsMargins(20, 18, 20, 18)
        focus_layout.setSpacing(12)

        focus_hdr = QHBoxLayout()
        lbl_focus = QLabel("FOCUS SESSION")
        lbl_focus.setObjectName("card_section_title")
        self._focus_badge = StatusBadge("STANDBY", variant="neutral")
        focus_hdr.addWidget(lbl_focus)
        focus_hdr.addStretch()
        focus_hdr.addWidget(self._focus_badge)
        focus_layout.addLayout(focus_hdr)

        self._focus_status_lbl = QLabel("No session active. Ready to eliminate distractions.")
        self._focus_status_lbl.setObjectName("card_desc")
        self._focus_status_lbl.setWordWrap(True)
        focus_layout.addWidget(self._focus_status_lbl)

        focus_btn_row = QHBoxLayout()
        self._start_focus_btn = QPushButton("▶  Start Focus Session")
        self._start_focus_btn.setObjectName("btn_primary")
        self._start_focus_btn.setProperty("primary", True)
        self._start_focus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_focus_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._start_focus_btn.setMinimumHeight(40)
        self._start_focus_btn.clicked.connect(self.request_focus_session.emit)
        focus_btn_row.addWidget(self._start_focus_btn)
        focus_layout.addLayout(focus_btn_row)

        right_col.addWidget(self._focus_card)

        # Wellbeing Controls Card
        self._ctrl_card = QFrame()
        self._ctrl_card.setObjectName("v2_card")
        ctrl_layout = QVBoxLayout(self._ctrl_card)
        ctrl_layout.setContentsMargins(20, 18, 20, 18)
        ctrl_layout.setSpacing(12)

        ctrl_hdr = QHBoxLayout()
        lbl_ctrl = QLabel("WELLBEING CONTROLS")
        lbl_ctrl.setObjectName("card_section_title")
        ctrl_hdr.addWidget(lbl_ctrl)
        ctrl_hdr.addStretch()
        ctrl_layout.addLayout(ctrl_hdr)

        # Controls list
        ctrl_list = QVBoxLayout()
        ctrl_list.setSpacing(6)

        # 1. App Timers Row
        self._row_timers = EntityRow(
            primary_text="App Timers",
            secondary_text="Daily limits & cooldowns",
            icon="clock",
            entity_id="app_timers",
        )
        btn_view_timers = QPushButton("View")
        btn_view_timers.setObjectName("ctrl_action_btn")
        btn_view_timers.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_timers.clicked.connect(lambda: self._nav_to(4))
        self._row_timers.add_action(btn_view_timers)
        self._row_timers.clicked.connect(lambda _: self._nav_to(4))
        ctrl_list.addWidget(self._row_timers)

        # 2. App Locker Row
        self._row_locker = EntityRow(
            primary_text="App Locker",
            secondary_text="PIN protection & restrict apps",
            icon="lock",
            entity_id="app_locker",
        )
        btn_view_locker = QPushButton("Configure")
        btn_view_locker.setObjectName("ctrl_action_btn")
        btn_view_locker.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_locker.clicked.connect(lambda: self._nav_to(3))
        self._row_locker.add_action(btn_view_locker)
        self._row_locker.clicked.connect(lambda _: self._nav_to(3))
        ctrl_list.addWidget(self._row_locker)

        # 3. SleepGuard Row
        self._row_sleep = EntityRow(
            primary_text="SleepGuard",
            secondary_text="Inactivity power management",
            icon="sleepguard",
            entity_id="sleepguard",
        )
        btn_view_sleep = QPushButton("Status")
        btn_view_sleep.setObjectName("ctrl_action_btn")
        btn_view_sleep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_sleep.clicked.connect(lambda: self._nav_to(6))
        self._row_sleep.add_action(btn_view_sleep)
        self._row_sleep.clicked.connect(lambda _: self._nav_to(6))
        ctrl_list.addWidget(self._row_sleep)

        ctrl_layout.addLayout(ctrl_list)
        right_col.addWidget(self._ctrl_card)
        right_col.addStretch()

        content_grid.addLayout(right_col, stretch=3)
        self._inner_layout.addLayout(content_grid)
        self._inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()

        card_bg = tm.color("card_bg")
        border_col = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        text_muted = tm.color("text_muted")
        accent = tm.color("accent")
        accent_hover = tm.color("accent_hover")
        focus_ring = tm.color("focus_ring")

        self.setStyleSheet(f"""
            QLabel#dashboard_greeting {{
                font-size: 26px;
                font-weight: 800;
                color: {text_main};
                letter-spacing: -0.5px;
            }}
            QLabel#dashboard_context {{
                font-size: 13.5px;
                font-weight: 500;
                color: {text_sub};
                margin-top: 1px;
                margin-bottom: 2px;
            }}
            QLabel#dashboard_date {{
                font-size: 12px;
                font-weight: 500;
                color: {text_muted};
            }}
            QLabel#card_section_title {{
                color: {text_muted};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
                text-transform: uppercase;
            }}
            QLabel#card_desc {{
                color: {text_sub};
                font-size: 13px;
                line-height: 1.4;
            }}
            QFrame#v2_card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            QPushButton#ctrl_action_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {text_sub};
                border: 1px solid {border_col};
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                padding: 5px 14px;
            }}
            QPushButton#ctrl_action_btn:hover {{
                background-color: {tm.color('surface_hover')};
                color: {text_main};
                border-color: {tm.color('border_strong')};
            }}
            QPushButton#ctrl_action_btn:focus {{
                border: 2px solid {focus_ring};
            }}
        """)

        self._start_focus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 17px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:focus {{
                border: 2px solid {focus_ring};
            }}
        """)

    def _nav_to(self, index: int) -> None:
        if self._navigate:
            self._navigate(index)

    def _trigger_refresh(self) -> None:
        if getattr(self, "_is_refreshing", False):
            return
        self._is_refreshing = True
        self._refresh_btn.set_spinning(True)

        if self._on_global_refresh:
            self._on_global_refresh()
        else:
            self._refresh()

        QTimer.singleShot(600, self._finish_refresh)

    def _finish_refresh(self) -> None:
        self._refresh_btn.set_spinning(False)
        self._is_refreshing = False

    @staticmethod
    def get_greeting_and_context(
        now: datetime, name: str = "", screen_time_s: float = 0.0, formatted_time: str = ""
    ) -> tuple[str, str]:
        """
        Determines the time-aware greeting and contextual message based on local system time.
        Time periods:
          - Morning (05:00 - 11:59)
          - Afternoon (12:00 - 16:59)
          - Evening (17:00 - 21:59)
          - Late-Night (22:00 - 23:59)
          - Very Late Hours (00:00 - 04:59)
        """
        hour = now.hour
        day_seed = now.timetuple().tm_yday

        if 5 <= hour < 12:
            base_greeting = "Good morning"
        elif 12 <= hour < 17:
            base_greeting = "Good afternoon"
        elif 17 <= hour < 22:
            base_greeting = "Good evening"
        else:
            base_greeting = "Good night"

        greeting = f"{base_greeting}, {name}" if name else base_greeting

        if 0 <= hour < 5:
            very_late_with_name = (
                f"Still going, {name}? It's well past midnight. Give yourself a proper break."
                if name
                else "Still going? It's well past midnight. Give yourself a proper break."
            )
            messages = [
                very_late_with_name,
                "Late hours add up quietly. Rest when you're ready.",
                "Tomorrow is already here. A quiet night awaits.",
                "Past midnight. Consider saving your work and catching some rest.",
            ]
            context = messages[day_seed % len(messages)]
        elif 22 <= hour < 24:
            messages = [
                "The day's winding down. Maybe your screen time should too.",
                "It's getting late. Your screen can wait until tomorrow.",
                "Tomorrow will still be there. Give yourself a proper break.",
                "Still going? It might be a good time to call it a night.",
            ]
            context = messages[day_seed % len(messages)]
        elif 17 <= hour < 22:
            messages = [
                "A little more focus, or a little more rest?",
                "Wrapping up your priorities for today.",
                "Time to review the day and unwind.",
                "The evening is yours. Pace yourself.",
            ]
            context = messages[day_seed % len(messages)]
        elif 12 <= hour < 17:
            if screen_time_s >= 60 and formatted_time:
                context = f"You've spent {formatted_time} on your computer today."
            else:
                messages = [
                    "Steady progress makes the day.",
                    "Keep your momentum going into the afternoon.",
                    "Focus where it matters most this afternoon.",
                ]
                context = messages[day_seed % len(messages)]
        else:
            messages = [
                "Your day is yours. Make it count.",
                "Ready for a focused, intentional day?",
                "Start with what matters most today.",
                "A fresh start to work on what matters.",
            ]
            context = messages[day_seed % len(messages)]

        return greeting, context

    def _refresh(self) -> None:
        now = datetime.now()
        from settings.manager import SettingsManager
        user_name = SettingsManager().display_name

        summary = self._engine.get_today_summary()
        formatted_total = self._engine.format_duration(summary.total_screen_time_s)
        formatted_active = self._engine.format_duration(summary.active_time_s)
        formatted_idle = self._engine.format_duration(summary.idle_time_s)

        greeting, context_msg = self.get_greeting_and_context(
            now, user_name, summary.total_screen_time_s, formatted_total
        )
        self._greeting_label.setText(greeting)
        self._context_label.setText(context_msg)

        today = date.today()
        self._date_label.setText(today.strftime("%A, %B %d, %Y"))

        comp = self._engine.get_yesterday_comparison()
        pct = comp.get("pct_change")
        trend_text = None
        trend_dir = None

        if pct is not None and not comp.get("yesterday_was_zero", False):
            if pct > 0:
                trend_text = f"↑ {abs(pct):.1f}% vs yesterday"
                trend_dir = "up"
            elif pct < 0:
                trend_text = f"↓ {abs(pct):.1f}% vs yesterday"
                trend_dir = "down"
            else:
                trend_text = "Equal to yesterday"
                trend_dir = "neutral"

        # 1. Update Overview StatCards
        self._screen_time_card.set_metric(formatted_total)
        self._screen_time_card.set_subtext(f"Active: {formatted_active} • Idle: {formatted_idle}")
        self._screen_time_card.set_trend(trend_text, direction=trend_dir)

        total_s = max(summary.total_screen_time_s, 1.0)
        active_pct = int((summary.active_time_s / total_s) * 100)
        idle_pct = int((summary.idle_time_s / total_s) * 100)

        self._active_time_card.set_metric(formatted_active)
        self._active_time_card.set_subtext(f"{active_pct}% of total screen time")

        self._idle_time_card.set_metric(formatted_idle)
        self._idle_time_card.set_subtext(f"{idle_pct}% of total screen time")

        # 2. Update Focus Status
        from protection.focus_manager import FocusManager
        fm = FocusManager.instance()
        if fm.is_active:
            m, s = divmod(fm.remaining_seconds, 60)
            mode_name = fm.mode.title() if hasattr(fm, "mode") else "Focus"
            self._focus_badge.set_text("ACTIVE")
            self._focus_badge.set_variant("active")
            self._focus_badge.set_dot_visible(True)
            self._focus_status_lbl.setText(f"Active: {m:02d}:{s:02d} remaining in {mode_name} mode.")
            self._start_focus_btn.setText("Manage Active Focus")
        else:
            self._focus_badge.set_text("STANDBY")
            self._focus_badge.set_variant("neutral")
            self._focus_badge.set_dot_visible(False)
            self._focus_status_lbl.setText("No session active. Ready to eliminate distractions.")
            self._start_focus_btn.setText("▶  Start Focus Session")

        # 3. Update Top Applications
        while self._apps_container.count():
            item = self._apps_container.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        top_apps = [a for a in summary.top_apps if a.get("total_s", 0) > 0]
        if not top_apps:
            lbl_empty = QLabel("No application activity recorded today.")
            lbl_empty.setObjectName("card_desc")
            self._apps_container.addWidget(lbl_empty)
        else:
            top_duration = float(top_apps[0].get("total_s", 1.0))
            for app in top_apps[:5]:
                dur_s = float(app.get("total_s", 0))
                proc = app["process_name"]
                name = app.get("display_name", proc)
                formatted_dur = self._engine.format_duration(dur_s)
                progress_val = dur_s / max(top_duration, 1.0)

                row = EntityRow(
                    primary_text=name,
                    secondary_text=f"{int(dur_s / total_s * 100)}% of total screen time",
                    icon=proc,
                    progress=progress_val,
                    trailing_text=formatted_dur,
                    entity_id=proc,
                )
                row.clicked.connect(self.request_app_details.emit)
                self._apps_container.addWidget(row)

        # 4. Update Top Categories
        while self._cats_container.count():
            item = self._cats_container.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        category_breakdown = [c for c in summary.category_breakdown if float(c.get("total_s", 0.0)) > 0]
        if not category_breakdown:
            lbl_empty_cat = QLabel("No category data recorded today.")
            lbl_empty_cat.setObjectName("card_desc")
            self._cats_container.addWidget(lbl_empty_cat)
        else:
            sorted_cats = sorted(category_breakdown, key=lambda x: float(x.get("total_s", 0.0)), reverse=True)
            for item in sorted_cats[:4]:
                dur = float(item.get("total_s", 0.0))
                cat_name = item["category"]
                cat_str = cat_name.value if hasattr(cat_name, "value") else str(cat_name)
                formatted_dur = self._engine.format_duration(dur)
                cat_pct = int(dur / total_s * 100)

                row = EntityRow(
                    primary_text=cat_str,
                    secondary_text=f"{cat_pct}% of total screen time",
                    icon="apps",
                    progress=dur / total_s,
                    trailing_text=formatted_dur,
                    entity_id=cat_str,
                )
                row.clicked.connect(self.request_category_details.emit)
                self._cats_container.addWidget(row)

    def on_data_changed(self) -> None:
        self._refresh()
