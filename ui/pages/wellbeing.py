"""
wellbeing.py — Unified Focus Suite for Digital Wellbeing V2 / Notch v3.6.3.
Supports Focus Timer Cockpit and Smart Focus Scheduler.
"""

from __future__ import annotations
from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QStackedWidget, QMessageBox
)

from tracker.sleepguard import SleepGuardController
from ui.widgets.focus_timer import FocusTimerWidget
from ui.widgets.deep_work_cockpit import DeepWorkCockpitWidget
from ui.widgets.focus_schedule_card import FocusScheduleCard
from ui.widgets.focus_schedule_dialog import FocusScheduleDialog
from protection.focus_scheduler import FocusScheduler
from database.models import FocusSchedule
from ui.theme import ThemeManager


class WellbeingPage(QWidget):
    """Focus Session Suite: Timer Cockpit, Deep Work Sessions, & Smart Focus Scheduler."""

    focus_completed = Signal()

    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None) -> None:
        super().__init__(parent)
        self._sleepguard = sleepguard
        self._scheduler = FocusScheduler.instance()
        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

        # Connect scheduler updates
        self._scheduler.schedules_updated.connect(self._refresh_schedules)
        self._scheduler.schedule_started.connect(lambda _: self._refresh_schedules())
        self._scheduler.schedule_ended.connect(lambda _: self._refresh_schedules())

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(36, 28, 36, 32)
        inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Focus")
        title.setObjectName("page_title")
        subtitle = QLabel("Intentional distraction-free sessions engineered for deep concentration.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        inner_layout.addLayout(title_box)

        # Top Sub-tab Navigation Pills
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self._btn_tab_timer = QPushButton("Focus Timer")
        self._btn_tab_timer.setObjectName("subtab_active")
        self._btn_tab_timer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tab_timer.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_tab_timer.clicked.connect(lambda: self._switch_tab(0))

        self._btn_tab_deep_work = QPushButton("Deep Work Sessions")
        self._btn_tab_deep_work.setObjectName("subtab_inactive")
        self._btn_tab_deep_work.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tab_deep_work.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_tab_deep_work.clicked.connect(lambda: self._switch_tab(1))

        self._btn_tab_scheduler = QPushButton("Smart Scheduler")
        self._btn_tab_scheduler.setObjectName("subtab_inactive")
        self._btn_tab_scheduler.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tab_scheduler.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_tab_scheduler.clicked.connect(lambda: self._switch_tab(2))

        tab_row.addWidget(self._btn_tab_timer)
        tab_row.addWidget(self._btn_tab_deep_work)
        tab_row.addWidget(self._btn_tab_scheduler)
        tab_row.addStretch()
        inner_layout.addLayout(tab_row)

        # Stack for Tabs
        self._stack = QStackedWidget()
        self._stack.setObjectName("focus_stack")

        # Tab 0: Focus Timer Cockpit
        center_box = QWidget()
        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_box.setMaximumWidth(1060)

        self._focus_timer = FocusTimerWidget()
        self._focus_timer.focus_completed.connect(self.focus_completed.emit)
        center_layout.addWidget(self._focus_timer)
        self._stack.addWidget(center_box)

        # Tab 1: Deep Work Sessions Cockpit
        deep_box = QWidget()
        deep_layout = QVBoxLayout(deep_box)
        deep_layout.setContentsMargins(0, 0, 0, 0)
        deep_box.setMaximumWidth(1060)

        self._deep_work_cockpit = DeepWorkCockpitWidget()
        deep_layout.addWidget(self._deep_work_cockpit)
        self._stack.addWidget(deep_box)

        # Tab 2: Smart Scheduler View
        sched_box = QWidget()
        self._sched_layout = QVBoxLayout(sched_box)
        self._sched_layout.setContentsMargins(0, 8, 0, 0)
        self._sched_layout.setSpacing(14)
        sched_box.setMaximumWidth(1060)

        # Scheduler Header & Add button
        sched_hdr = QHBoxLayout()
        sched_hdr.setSpacing(12)
        sched_hdr_text = QVBoxLayout()
        sched_hdr_text.setSpacing(2)

        lbl_sched_title = QLabel("Recurring Focus Schedules")
        lbl_sched_title.setObjectName("section_title")
        lbl_sched_sub = QLabel("Automate Focus Mode during your daily work hours without manual activation.")
        lbl_sched_sub.setObjectName("section_sub")
        sched_hdr_text.addWidget(lbl_sched_title)
        sched_hdr_text.addWidget(lbl_sched_sub)
        sched_hdr.addLayout(sched_hdr_text)
        sched_hdr.addStretch()

        self._btn_add_schedule = QPushButton("+ Add Schedule")
        self._btn_add_schedule.setObjectName("btn_primary")
        self._btn_add_schedule.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add_schedule.clicked.connect(self._on_add_schedule)
        sched_hdr.addWidget(self._btn_add_schedule)
        self._sched_layout.addLayout(sched_hdr)

        # Container for cards
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._sched_layout.addWidget(self._cards_container)

        self._stack.addWidget(sched_box)
        inner_layout.addWidget(self._stack, 1)

        self._refresh_schedules()

    def _switch_tab(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        self._btn_tab_timer.setObjectName("subtab_active" if idx == 0 else "subtab_inactive")
        self._btn_tab_deep_work.setObjectName("subtab_active" if idx == 1 else "subtab_inactive")
        self._btn_tab_scheduler.setObjectName("subtab_active" if idx == 2 else "subtab_inactive")
        self._apply_theme(ThemeManager.instance().is_dark)
        if idx == 1:
            if hasattr(self, "_deep_work_cockpit"):
                self._deep_work_cockpit._refresh_view()
        elif idx == 2:
            self._refresh_schedules()

    def _refresh_schedules(self) -> None:
        # Clear existing card widgets
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        schedules = self._scheduler.get_schedules()
        active_sched = self._scheduler.active_schedule

        if not schedules:
            empty_frame = QFrame()
            empty_frame.setObjectName("empty_state_frame")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(24, 36, 24, 36)
            empty_layout.setSpacing(10)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_empty_title = QLabel("No Focus Schedules Configured")
            lbl_empty_title.setObjectName("empty_title")
            lbl_empty_sub = QLabel("Create a schedule to automate your study or deep work blocks every week.")
            lbl_empty_sub.setObjectName("empty_sub")
            btn_create = QPushButton("Create First Schedule")
            btn_create.setObjectName("btn_primary")
            btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_create.clicked.connect(self._on_add_schedule)

            empty_layout.addWidget(lbl_empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(lbl_empty_sub, alignment=Qt.AlignmentFlag.AlignCenter)
            empty_layout.addSpacing(6)
            empty_layout.addWidget(btn_create, alignment=Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.addWidget(empty_frame)
        else:
            for s in schedules:
                is_active = (active_sched is not None and active_sched.id == s.id)
                card = FocusScheduleCard(s, is_active_now=is_active)
                card.toggled.connect(self._on_schedule_toggled)
                card.edit_requested.connect(self._on_edit_schedule)
                card.delete_requested.connect(self._on_delete_schedule)
                self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()

    def _on_add_schedule(self) -> None:
        dlg = FocusScheduleDialog(parent=self)
        if dlg.exec():
            sched = dlg.get_schedule()
            self._scheduler.add_or_update_schedule(sched)
            self._refresh_schedules()

    def _on_edit_schedule(self, schedule_id: int) -> None:
        sched = self._scheduler.get_schedule(schedule_id)
        if not sched:
            return
        dlg = FocusScheduleDialog(schedule=sched, parent=self)
        if dlg.exec():
            updated = dlg.get_schedule()
            self._scheduler.add_or_update_schedule(updated)
            self._refresh_schedules()

    def _on_schedule_toggled(self, schedule_id: int, is_enabled: bool) -> None:
        self._scheduler.toggle_schedule(schedule_id, is_enabled)

    def _on_delete_schedule(self, schedule_id: int) -> None:
        res = QMessageBox.question(
            self,
            "Delete Schedule",
            "Are you sure you want to delete this focus schedule?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self._scheduler.delete_schedule(schedule_id)
            self._refresh_schedules()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        accent = tm.color("accent")
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")

        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 26px; font-weight: 800; color: {text_main}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle {{ font-size: 13px; font-weight: 500; color: {text_sub}; }}
            QLabel#section_title {{ font-size: 18px; font-weight: 700; color: {text_main}; }}
            QLabel#section_sub {{ font-size: 12px; font-weight: 500; color: {text_sub}; }}
            QLabel#empty_title {{ font-size: 16px; font-weight: 700; color: {text_main}; }}
            QLabel#empty_sub {{ font-size: 13px; font-weight: 500; color: {text_sub}; }}
            QFrame#empty_state_frame {{
                background-color: {tm.color('surface_secondary')};
                border: 1px dashed {border};
                border-radius: 12px;
            }}
            QPushButton#subtab_active {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {accent};
                border-radius: 8px;
                color: {text_main};
                font-weight: 700;
                font-size: 13px;
                padding: 6px 16px;
            }}
            QPushButton#subtab_active:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#subtab_inactive {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 8px;
                color: {text_sub};
                font-weight: 600;
                font-size: 13px;
                padding: 6px 16px;
            }}
            QPushButton#subtab_inactive:hover {{
                background-color: {tm.color('surface_hover')};
                color: {text_main};
            }}
            QPushButton#subtab_inactive:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#btn_primary {{
                background: {tm.color('primary_btn_gradient')};
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
            }}
        """)
        self.on_data_changed()

    def on_data_changed(self) -> None:
        if hasattr(self, "_scheduler"):
            self._refresh_schedules()
