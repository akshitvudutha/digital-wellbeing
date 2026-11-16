"""
deep_work_cockpit.py — Visual cockpit widget for managing and monitoring Deep Work Sessions in Notch v3.6.3.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QGridLayout
)
from database.repository import Repository
from protection.deep_work import DeepWorkController, DeepWorkPhase
from ui.widgets.deep_work_dialog import DeepWorkConfigDialog
from ui.theme import ThemeManager


def _format_time(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class DeepWorkCockpitWidget(QWidget):
    def __init__(self, controller: Optional[DeepWorkController] = None, parent=None):
        super().__init__(parent)
        self._controller = controller or DeepWorkController.instance()
        self._repo = Repository()

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

        # Wire controller signals
        self._controller.tick.connect(self._on_tick)
        self._controller.phase_changed.connect(self._on_phase_changed)
        self._controller.session_started.connect(lambda _: self._refresh_view())
        self._controller.session_completed.connect(lambda _: self._refresh_view())
        self._controller.session_aborted.connect(self._refresh_view)

        self._refresh_view()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # 1. Cockpit Frame
        self._frame = QFrame()
        self._frame.setObjectName("cockpit_frame")
        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(28, 28, 28, 28)
        self._frame_layout.setSpacing(16)
        layout.addWidget(self._frame)

        # --- Active Session Elements ---
        self._active_box = QWidget()
        active_layout = QVBoxLayout(self._active_box)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(14)
        active_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Phase Badge
        self._lbl_phase_badge = QLabel("WORKING")
        self._lbl_phase_badge.setObjectName("phase_badge_work")
        self._lbl_phase_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_layout.addWidget(self._lbl_phase_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        # Goal Label
        self._lbl_goal = QLabel("Refactor API Controllers")
        self._lbl_goal.setObjectName("active_goal")
        self._lbl_goal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_layout.addWidget(self._lbl_goal)

        # Interval details
        self._lbl_interval_info = QLabel("Interval 1 of 4 • 25m Work / 5m Break")
        self._lbl_interval_info.setObjectName("active_interval_sub")
        self._lbl_interval_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_layout.addWidget(self._lbl_interval_info)

        # Big Countdown
        self._lbl_countdown = QLabel("25:00")
        self._lbl_countdown.setObjectName("countdown_display")
        self._lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_layout.addWidget(self._lbl_countdown)

        # Progress Bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setObjectName("phase_progress")
        active_layout.addWidget(self._progress)

        # Active Control Buttons
        active_btn_row = QHBoxLayout()
        active_btn_row.setSpacing(12)
        active_btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_pause_resume = QPushButton("Pause")
        self._btn_pause_resume.setObjectName("btn_secondary")
        self._btn_pause_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pause_resume.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_pause_resume.clicked.connect(self._toggle_pause)
        active_btn_row.addWidget(self._btn_pause_resume)

        self._btn_finish_early = QPushButton("Finish Early")
        self._btn_finish_early.setObjectName("btn_secondary")
        self._btn_finish_early.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_finish_early.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_finish_early.clicked.connect(self._on_finish_early)
        active_btn_row.addWidget(self._btn_finish_early)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("btn_danger")
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_cancel.clicked.connect(self._on_cancel)
        active_btn_row.addWidget(self._btn_cancel)

        active_layout.addLayout(active_btn_row)
        self._frame_layout.addWidget(self._active_box)

        # --- Idle Session Elements ---
        self._idle_box = QWidget()
        idle_layout = QVBoxLayout(self._idle_box)
        idle_layout.setContentsMargins(0, 0, 0, 0)
        idle_layout.setSpacing(16)
        idle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_idle_title = QLabel("Structured Deep Work")
        lbl_idle_title.setObjectName("idle_title")
        lbl_idle_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        idle_layout.addWidget(lbl_idle_title)

        lbl_idle_sub = QLabel("Eliminate interruptions and organize your highest-priority tasks into focused intervals.")
        lbl_idle_sub.setObjectName("idle_sub")
        lbl_idle_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_idle_sub.setWordWrap(True)
        idle_layout.addWidget(lbl_idle_sub)

        btn_launch = QPushButton("Start Deep Work Session")
        btn_launch.setObjectName("btn_primary_large")
        btn_launch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_launch.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        btn_launch.clicked.connect(self._open_start_dialog)
        idle_layout.addWidget(btn_launch, alignment=Qt.AlignmentFlag.AlignCenter)

        self._frame_layout.addWidget(self._idle_box)

        # 2. Historical Stats Summary Row
        self._stats_frame = QFrame()
        self._stats_frame.setObjectName("stats_row_frame")
        self._stats_layout = QHBoxLayout(self._stats_frame)
        self._stats_layout.setContentsMargins(18, 14, 18, 14)
        self._stats_layout.setSpacing(20)

        self._lbl_stat_hours = self._create_stat_cell("TOTAL FOCUSED", "0.0h")
        self._lbl_stat_sessions = self._create_stat_cell("SESSIONS COMPLETED", "0")
        self._lbl_stat_rate = self._create_stat_cell("GOAL COMPLETION", "0%")

        layout.addWidget(self._stats_frame)

    def _create_stat_cell(self, title: str, value: str) -> QLabel:
        cell = QVBoxLayout()
        cell.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setObjectName("stat_cell_title")
        lbl_v = QLabel(value)
        lbl_v.setObjectName("stat_cell_value")
        cell.addWidget(lbl_t)
        cell.addWidget(lbl_v)
        self._stats_layout.addLayout(cell)
        return lbl_v

    def _refresh_view(self):
        is_active = self._controller.is_active
        self._active_box.setVisible(is_active)
        self._idle_box.setVisible(not is_active)

        if is_active:
            self._lbl_goal.setText(self._controller.goal)
            iv = self._controller.current_interval
            tot = self._controller.total_intervals
            wm = self._controller.total_phase_seconds // 60
            self._lbl_interval_info.setText(f"Interval {iv} of {tot} • {self._controller.preset} Preset")
            self._btn_pause_resume.setText("Resume" if self._controller.is_paused else "Pause")
            self._lbl_countdown.setText(_format_time(self._controller.remaining_seconds))
            if self._controller.total_phase_seconds > 0:
                pct = int((self._controller.remaining_seconds / self._controller.total_phase_seconds) * 100)
                self._progress.setValue(pct)
            self._on_phase_changed(self._controller.phase.value)
        else:
            self._update_stats()

    def _update_stats(self):
        stats = self._repo.get_deep_work_stats()
        hours = stats["total_work_s"] / 3600.0
        self._lbl_stat_hours.setText(f"{hours:.1f}h")
        self._lbl_stat_sessions.setText(str(stats["completed_sessions"]))
        self._lbl_stat_rate.setText(f"{stats['completion_rate']:.0f}%")

    def _on_tick(self, rem_s: int, tot_s: int):
        self._lbl_countdown.setText(_format_time(rem_s))
        if tot_s > 0:
            pct = int((rem_s / tot_s) * 100)
            self._progress.setValue(pct)

    def _on_phase_changed(self, phase_val: str):
        if phase_val == DeepWorkPhase.WORK.value:
            self._lbl_phase_badge.setText(f"WORKING — INTERVAL {self._controller.current_interval} OF {self._controller.total_intervals}")
            self._lbl_phase_badge.setObjectName("phase_badge_work")
            self._btn_pause_resume.setText("Pause")
        elif phase_val in (DeepWorkPhase.SHORT_BREAK.value, DeepWorkPhase.LONG_BREAK.value):
            self._lbl_phase_badge.setText("RECHARGE BREAK")
            self._lbl_phase_badge.setObjectName("phase_badge_break")
            self._btn_pause_resume.setText("Pause")
        elif phase_val in (DeepWorkPhase.PAUSED_WORK.value, DeepWorkPhase.PAUSED_BREAK.value):
            self._lbl_phase_badge.setText("PAUSED")
            self._lbl_phase_badge.setObjectName("phase_badge_paused")
            self._btn_pause_resume.setText("Resume")
        self._apply_theme()

    def _toggle_pause(self):
        if self._controller.is_paused:
            self._controller.resume_session()
        else:
            self._controller.pause_session()

    def _on_finish_early(self):
        res = QMessageBox.question(
            self,
            "Finish Session Early",
            "Are you ready to conclude this session? Your focused work time will be saved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if res == QMessageBox.StandardButton.Yes:
            self._controller.finish_early()

    def _on_cancel(self):
        res = QMessageBox.question(
            self,
            "Cancel Session",
            "Are you sure you want to cancel this Deep Work session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self._controller.cancel_session()

    def _open_start_dialog(self):
        dlg = DeepWorkConfigDialog(parent=self)
        if dlg.exec():
            cfg = dlg.get_config()
            self._controller.start_session(
                goal=cfg.get("goal", "Focused Work"),
                work_minutes=cfg.get("work_minutes", 25),
                break_minutes=cfg.get("break_minutes", 5),
                total_intervals=cfg.get("total_intervals", 4),
                preset=cfg.get("preset", "25/5"),
                mode=cfg.get("mode", "deep"),
                strict_mode=cfg.get("strict_mode", False),
            )
            self._refresh_view()

    def _apply_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg = "#11151C" if is_dark else "#FFFFFF"
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        accent_bg = tm.color("accent_emerald_bg")

        self.setStyleSheet(f"""
            QFrame#cockpit_frame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#stats_row_frame {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#phase_badge_work {{
                background-color: {accent_bg};
                color: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#phase_badge_break {{
                background-color: rgba(56, 189, 248, 0.15);
                color: #38BDF8;
                border: 1px solid #38BDF8;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#phase_badge_paused {{
                background-color: {tm.color('accent_amber_bg')};
                color: {tm.color('accent_amber')};
                border: 1px solid {tm.color('accent_amber')};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#active_goal {{
                font-size: 22px;
                font-weight: 800;
                color: {text_main};
            }}
            QLabel#active_interval_sub {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QLabel#countdown_display {{
                font-size: 64px;
                font-weight: 800;
                color: {text_main};
                letter-spacing: -2px;
            }}
            QProgressBar#phase_progress {{
                background-color: {tm.color('surface_secondary')};
                border-radius: 3px;
            }}
            QProgressBar#phase_progress::chunk {{
                background-color: {accent};
                border-radius: 3px;
            }}
            QLabel#idle_title {{
                font-size: 22px;
                font-weight: 800;
                color: {text_main};
            }}
            QLabel#idle_sub {{
                font-size: 13px;
                font-weight: 500;
                color: {text_sub};
                max-width: 500px;
            }}
            QPushButton#btn_primary_large {{
                background: {tm.color('primary_btn_gradient')};
                border: none;
                border-radius: 10px;
                padding: 12px 32px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton#btn_primary_large:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#btn_secondary {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 18px;
                color: {text_main};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_secondary:hover {{
                background-color: {tm.color('surface_hover')};
            }}
            QPushButton#btn_secondary:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#btn_danger {{
                background: transparent;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                padding: 8px 18px;
                color: #EF4444;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_danger:hover {{
                background-color: rgba(239, 68, 68, 0.12);
            }}
            QPushButton#btn_danger:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QLabel#stat_cell_title {{
                font-size: 10px;
                font-weight: 700;
                color: {text_sub};
                letter-spacing: 0.8px;
            }}
            QLabel#stat_cell_value {{
                font-size: 18px;
                font-weight: 800;
                color: {text_main};
            }}
        """)
