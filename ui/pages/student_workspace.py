"""Student study sessions with subject tagging and deadline-free daily review."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtCore import QDate, QDateTime, QTime, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDateTimeEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from database.models import StudyBlock, StudyExamTopic, StudyPlannerTask, StudySubject
from database.repository import Repository
from protection.deep_work import DeepWorkController, DeepWorkPhase
from ui.theme import ThemeManager
from utils.time_format import format_duration


STUDY_MODES = (
    ("study", "Study"),
    ("exam_prep", "Exam Preparation"),
    ("online_class", "Online Class"),
    ("revision", "Revision"),
    ("deep_work", "Deep Work"),
    ("reading", "Reading"),
)


class StudentWorkspacePage(QWidget):
    """Start focused study, plan recurring work, and review academic time."""

    def __init__(
        self,
        parent=None,
        repo: Optional[Repository] = None,
        controller: Optional[DeepWorkController] = None,
        navigate_to_focus=None,
        notifier=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("student_workspace_page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._repo = repo or Repository()
        self._controller = controller or DeepWorkController.instance(self._repo)
        self._navigate_to_focus = navigate_to_focus
        self._notifier = notifier
        self._last_session_message = ""
        self._pending_block_id: Optional[int] = None
        self._pending_block_date: Optional[date] = None
        self._build_ui()
        self._connect_controller()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        self.on_data_changed()
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(30_000)
        self._reminder_timer.timeout.connect(self._check_due_reminders)
        self._reminder_timer.start()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("student_workspace_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("student_workspace_content")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(36, 28, 36, 32)
        self._content_layout.setSpacing(18)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        header = QVBoxLayout()
        title = QLabel("Student Workspace")
        title.setObjectName("page_title")
        subtitle = QLabel("Plan a focused study session and keep academic time separate from general screen time.")
        subtitle.setObjectName("page_subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        self._content_layout.addLayout(header)

        self._today_summary = QLabel()
        self._today_summary.setObjectName("student_today_summary")
        self._content_layout.addWidget(self._today_summary)

        self._build_insights_section()
        self._build_session_card()
        self._build_subject_section()
        self._build_timetable_section()
        self._build_deadline_section()
        self._build_recent_section()
        self._apply_theme(ThemeManager.instance().is_dark)

    def _build_session_card(self) -> None:
        card = QFrame()
        card.setObjectName("student_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        heading_row = QHBoxLayout()
        heading = QLabel("Start a study session")
        heading.setObjectName("section_title")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        self._focus_settings_btn = QPushButton("Configure selected mode")
        self._focus_settings_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._focus_settings_btn.clicked.connect(self._open_focus_settings)
        heading_row.addWidget(self._focus_settings_btn)
        layout.addLayout(heading_row)

        hint = QLabel("Each session type keeps its own allowed apps and blocked websites.")
        hint.setObjectName("student_hint")
        layout.addWidget(hint)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self._mode_combo = QComboBox()
        for key, label in STUDY_MODES:
            self._mode_combo.addItem(label, key)
        self._mode_combo.currentIndexChanged.connect(self._update_next_profile_hint)
        form.addWidget(QLabel("Session type"), 0, 0)
        form.addWidget(self._mode_combo, 0, 1)

        subject_row = QHBoxLayout()
        self._subject_combo = QComboBox()
        self._subject_combo.setMinimumWidth(180)
        self._add_subject_btn = QPushButton("Add subject")
        self._add_subject_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._add_subject_btn.clicked.connect(self._add_subject)
        subject_row.addWidget(self._subject_combo, 1)
        subject_row.addWidget(self._add_subject_btn)
        form.addWidget(QLabel("Subject"), 0, 2)
        form.addLayout(subject_row, 0, 3)

        self._objective_edit = QLineEdit()
        self._objective_edit.setPlaceholderText("Optional objective, e.g. revise vectors chapter")
        form.addWidget(QLabel("Objective"), 1, 0)
        form.addWidget(self._objective_edit, 1, 1, 1, 3)

        self._work_minutes = self._spinbox(1, 180, 25, " min")
        self._break_minutes = self._spinbox(1, 30, 5, " min")
        self._intervals = self._spinbox(1, 8, 1, " intervals")
        form.addWidget(QLabel("Work interval"), 2, 0)
        form.addWidget(self._work_minutes, 2, 1)
        form.addWidget(QLabel("Break between intervals"), 2, 2)
        form.addWidget(self._break_minutes, 2, 3)
        form.addWidget(QLabel("Intervals"), 3, 0)
        form.addWidget(self._intervals, 3, 1)
        layout.addLayout(form)

        presets = QHBoxLayout()
        presets.addWidget(QLabel("Quick duration"))
        for minutes in (15, 25, 50, 90):
            button = QPushButton(f"{minutes} min")
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.clicked.connect(lambda _checked=False, value=minutes: self._work_minutes.setValue(value))
            presets.addWidget(button)
        presets.addStretch()
        layout.addLayout(presets)

        self._start_btn = QPushButton("Start Study Session")
        self._start_btn.setObjectName("primary_action")
        self._start_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._start_btn.clicked.connect(self._start_session)
        layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._active_frame = QFrame()
        self._active_frame.setObjectName("student_active_frame")
        active_layout = QVBoxLayout(self._active_frame)
        active_layout.setContentsMargins(14, 12, 14, 12)
        active_layout.setSpacing(8)
        self._active_title = QLabel("No study session active")
        self._active_title.setObjectName("student_active_title")
        self._active_status = QLabel("Your next session will use its matching focus profile.")
        self._active_status.setObjectName("student_hint")
        self._active_progress = QProgressBar()
        self._active_progress.setTextVisible(False)
        active_layout.addWidget(self._active_title)
        active_layout.addWidget(self._active_status)
        active_layout.addWidget(self._active_progress)
        active_buttons = QHBoxLayout()
        self._pause_btn = QPushButton("Pause")
        self._pause_btn.clicked.connect(self._toggle_pause)
        self._finish_btn = QPushButton("Finish early")
        self._finish_btn.clicked.connect(self._finish_early)
        self._cancel_btn = QPushButton("Cancel session")
        self._cancel_btn.clicked.connect(self._cancel_session)
        for button in (self._pause_btn, self._finish_btn, self._cancel_btn):
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            active_buttons.addWidget(button)
        active_buttons.addStretch()
        active_layout.addLayout(active_buttons)
        layout.addWidget(self._active_frame)

        self._content_layout.addWidget(card)

    def _build_insights_section(self) -> None:
        card = QFrame()
        card.setObjectName("student_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(10)
        heading = QLabel("This week")
        heading.setObjectName("section_title")
        self._weekly_summary = QLabel()
        self._weekly_summary.setObjectName("student_weekly_summary")
        self._weekly_summary.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(self._weekly_summary)
        self._weekly_trend_layout = QVBoxLayout()
        self._weekly_trend_layout.setSpacing(5)
        layout.addLayout(self._weekly_trend_layout)
        self._weekly_breakdown_layout = QVBoxLayout()
        self._weekly_breakdown_layout.setSpacing(4)
        layout.addLayout(self._weekly_breakdown_layout)
        self._content_layout.addWidget(card)

    @staticmethod
    def _spinbox(minimum: int, maximum: int, value: int, suffix: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    def _build_subject_section(self) -> None:
        self._subjects_card = QFrame()
        self._subjects_card.setObjectName("student_card")
        layout = QVBoxLayout(self._subjects_card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel("Subjects")
        heading.setObjectName("section_title")
        layout.addWidget(heading)
        self._subjects_layout = QVBoxLayout()
        self._subjects_layout.setSpacing(8)
        layout.addLayout(self._subjects_layout)
        self._content_layout.addWidget(self._subjects_card)

    def _build_recent_section(self) -> None:
        card = QFrame()
        card.setObjectName("student_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel("Today's study sessions")
        heading.setObjectName("section_title")
        layout.addWidget(heading)
        self._recent_layout = QVBoxLayout()
        self._recent_layout.setSpacing(8)
        layout.addLayout(self._recent_layout)
        self._content_layout.addWidget(card)

    def _build_timetable_section(self) -> None:
        card = QFrame()
        card.setObjectName("student_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading_row = QHBoxLayout()
        heading = QLabel("Weekly timetable")
        heading.setObjectName("section_title")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        add_button = QPushButton("Add study block")
        add_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        add_button.clicked.connect(self._add_study_block)
        heading_row.addWidget(add_button)
        layout.addLayout(heading_row)
        self._timetable_layout = QVBoxLayout()
        self._timetable_layout.setSpacing(7)
        layout.addLayout(self._timetable_layout)
        self._content_layout.addWidget(card)

    def _build_deadline_section(self) -> None:
        card = QFrame()
        card.setObjectName("student_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading_row = QHBoxLayout()
        heading = QLabel("Assignments, exams and revision")
        heading.setObjectName("section_title")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        add_button = QPushButton("Add deadline")
        add_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        add_button.clicked.connect(self._add_planner_task)
        heading_row.addWidget(add_button)
        layout.addLayout(heading_row)
        self._planner_tasks_layout = QVBoxLayout()
        self._planner_tasks_layout.setSpacing(7)
        layout.addLayout(self._planner_tasks_layout)
        self._content_layout.addWidget(card)

    @staticmethod
    def _subject_picker(subjects: list[StudySubject], selected_id: Optional[int] = None) -> QComboBox:
        combo = QComboBox()
        combo.addItem("No subject", None)
        for subject in subjects:
            combo.addItem(subject.name, subject.id)
        if selected_id is not None:
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        return combo

    @staticmethod
    def _to_qdatetime(value: datetime) -> QDateTime:
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return QDateTime(
            QDate(value.year, value.month, value.day),
            QTime(value.hour, value.minute, value.second, value.microsecond // 1000),
        )

    def _add_study_block(self, block_id: Optional[int] = None) -> None:
        block = next(
            (item for item in self._repo.get_study_blocks(enabled_only=False) if item.id == block_id),
            None,
        ) if block_id is not None else None
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Study Block" if block else "Add Study Block")
        form = QFormLayout(dialog)
        name_edit = QLineEdit(block.name if block else "")
        name_edit.setPlaceholderText("e.g. Physics problem practice")
        weekday = QComboBox()
        for day_number, day_name in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")):
            weekday.addItem(day_name, day_number)
        weekday.setCurrentIndex(weekday.findData(block.weekday if block else date.today().weekday()))
        start_time = QTimeEdit()
        start_time.setDisplayFormat("HH:mm")
        start_time.setTime(QTime.fromString(block.start_time, "HH:mm") if block else QTime.currentTime())
        subject = self._subject_picker(self._repo.get_study_subjects(), block.subject_id if block else None)
        work = self._spinbox(1, 180, block.work_minutes if block else 25, " min / interval")
        breaks = self._spinbox(1, 30, block.break_minutes if block else 5, " min")
        intervals = self._spinbox(1, 8, block.intervals if block else 1, " intervals")
        form.addRow("Block name", name_edit)
        form.addRow("Repeat every", weekday)
        form.addRow("Start time", start_time)
        form.addRow("Subject", subject)
        form.addRow("Work interval", work)
        form.addRow("Break between intervals", breaks)
        form.addRow("Intervals", intervals)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        subject_id = subject.currentData()
        updated = StudyBlock(
            id=block.id if block else None,
            name=name_edit.text().strip() or (subject.currentText() if subject_id else "Study"),
            weekday=int(weekday.currentData()),
            start_time=start_time.time().toString("HH:mm"),
            work_minutes=work.value(),
            break_minutes=breaks.value(),
            intervals=intervals.value(),
            subject_id=int(subject_id) if subject_id is not None else None,
        )
        try:
            self._repo.save_study_block(updated)
        except Exception as exc:
            QMessageBox.warning(self, "Study block not saved", str(exc))
            return
        self.on_data_changed()

    def _add_planner_task(self, task_id: Optional[int] = None) -> None:
        task = next(
            (item for item in self._repo.get_study_planner_tasks() if item.id == task_id),
            None,
        ) if task_id is not None else None
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Study Task" if task else "Add Assignment, Exam or Revision")
        form = QFormLayout(dialog)
        title = QLineEdit(task.title if task else "")
        title.setPlaceholderText("e.g. Complete lab report")
        task_type = QComboBox()
        for key, label in (("assignment", "Assignment"), ("exam", "Exam"), ("revision", "Revision task")):
            task_type.addItem(label, key)
        if task:
            task_type.setCurrentIndex(task_type.findData(task.task_type))
        subject = self._subject_picker(self._repo.get_study_subjects(), task.subject_id if task else None)
        due_at = QDateTimeEdit()
        due_at.setCalendarPopup(True)
        due_at.setDisplayFormat("ddd, d MMM yyyy, HH:mm")
        due_at.setDateTime(self._to_qdatetime(task.due_at) if task else QDateTime.currentDateTime().addDays(1))
        reminder_enabled = QCheckBox("Remind me")
        reminder_enabled.setChecked(bool(task and task.reminder_at))
        reminder_at = QDateTimeEdit()
        reminder_at.setCalendarPopup(True)
        reminder_at.setDisplayFormat("ddd, d MMM yyyy, HH:mm")
        reminder_at.setDateTime(
            self._to_qdatetime(task.reminder_at)
            if task and task.reminder_at
            else due_at.dateTime().addSecs(-3600)
        )
        reminder_at.setEnabled(reminder_enabled.isChecked())
        reminder_enabled.toggled.connect(reminder_at.setEnabled)
        notes = QLineEdit(task.notes if task else "")
        notes.setPlaceholderText("Optional notes")
        form.addRow("Title", title)
        form.addRow("Type", task_type)
        form.addRow("Subject", subject)
        form.addRow("Due", due_at)
        form.addRow(reminder_enabled, reminder_at)
        form.addRow("Notes", notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        subject_id = subject.currentData()
        updated = StudyPlannerTask(
            id=task.id if task else None,
            title=title.text(),
            task_type=str(task_type.currentData()),
            due_at=due_at.dateTime().toPython(),
            subject_id=int(subject_id) if subject_id is not None else None,
            reminder_at=reminder_at.dateTime().toPython() if reminder_enabled.isChecked() else None,
            notes=notes.text(),
        )
        try:
            self._repo.save_study_planner_task(updated)
        except Exception as exc:
            QMessageBox.warning(self, "Study task not saved", str(exc))
            return
        self.on_data_changed()

    def _start_study_block(self, block_id: int) -> None:
        today = date.today()
        block = next(
            (item for item in self._repo.get_study_blocks(on_date=today) if item.id == block_id),
            None,
        )
        if block is None or block.weekday != today.weekday():
            return
        if block.completed_for_date:
            self._active_status.setText("This study block is already marked complete for today.")
            return
        if self._controller.is_active:
            self._active_status.setText("Finish or cancel the active session before starting another.")
            return
        self._mode_combo.setCurrentIndex(self._mode_combo.findData("study"))
        self._subject_combo.setCurrentIndex(self._subject_combo.findData(block.subject_id) if block.subject_id else 0)
        self._work_minutes.setValue(block.work_minutes)
        self._break_minutes.setValue(block.break_minutes)
        self._intervals.setValue(block.intervals)
        self._objective_edit.setText(block.name or "Timetable study block")
        self._pending_block_id = block.id
        self._pending_block_date = today
        self._start_session()
        if not self._controller.is_active:
            self._pending_block_id = None
            self._pending_block_date = None

    def _toggle_block_completed(self, block_id: int, completed: bool) -> None:
        self._repo.set_study_block_completed(block_id, date.today(), completed)
        self.on_data_changed()

    def _delete_study_block(self, block_id: int) -> None:
        answer = QMessageBox.question(
            self, "Remove study block?", "This removes the recurring block from your timetable.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._repo.delete_study_block(block_id)
            self.on_data_changed()

    def _set_planner_task_completed(self, task_id: int, completed: bool) -> None:
        self._repo.set_study_planner_task_completed(task_id, completed)
        self.on_data_changed()

    def _delete_planner_task(self, task_id: int) -> None:
        answer = QMessageBox.question(
            self, "Remove study task?", "This removes the task and its reminder.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._repo.delete_study_planner_task(task_id)
            self.on_data_changed()

    def _check_due_reminders(self, now: Optional[datetime] = None) -> None:
        tasks = self._repo.claim_due_study_reminders(now)
        if not tasks:
            return
        if self._notifier is None:
            from notifications.notifier import Notifier
            self._notifier = Notifier()
        subjects = {item.id: item.name for item in self._repo.get_study_subjects(active_only=False)}
        for task in tasks:
            subject = subjects.get(task.subject_id)
            detail = f"{task.title} is due {task.due_at.strftime('%a, %d %b at %H:%M')}"
            if subject:
                detail += f" · {subject}"
            try:
                self._notifier.notify(f"{task.task_type.title()} reminder", detail, duration=7)
            except Exception:
                # The task remains claimed, preventing repeated toast attempts every 30 seconds.
                pass

    def _populate_timetable(self) -> None:
        self._clear_layout(self._timetable_layout)
        blocks = self._repo.get_study_blocks(on_date=date.today())
        if not blocks:
            empty = QLabel("Add recurring blocks to build a simple weekly study timetable.")
            empty.setObjectName("student_hint")
            self._timetable_layout.addWidget(empty)
            return

        subject_names = {
            subject.id: subject.name
            for subject in self._repo.get_study_subjects(active_only=False)
        }
        day_names = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        for weekday, day_name in enumerate(day_names):
            day_blocks = [block for block in blocks if block.weekday == weekday]
            if not day_blocks:
                continue
            header = QLabel(f"{day_name}{' · Today' if weekday == date.today().weekday() else ''}")
            header.setObjectName("student_subject_name")
            self._timetable_layout.addWidget(header)
            for block in day_blocks:
                row = QHBoxLayout()
                work_s = block.work_minutes * block.intervals * 60
                break_s = block.break_minutes * max(0, block.intervals - 1) * 60
                break_text = (
                    f"{format_duration(break_s, compact=True)} break time"
                    if break_s else "no break"
                )
                subject_name = subject_names.get(block.subject_id, "No subject")
                detail = QLabel(
                    f"{block.start_time} · {block.name or 'Study'} · {subject_name} · "
                    f"{format_duration(work_s, compact=True)} work + {break_text}"
                )
                detail.setObjectName("student_session_row")
                detail.setWordWrap(True)
                row.addWidget(detail, 1)

                if weekday == date.today().weekday():
                    start = QPushButton("Start")
                    start.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                    start.setEnabled(not block.completed_for_date)
                    start.clicked.connect(lambda _checked=False, bid=block.id: self._start_study_block(bid))
                    row.addWidget(start)
                    done = QCheckBox("Done")
                    done.setChecked(block.completed_for_date)
                    done.clicked.connect(lambda checked, bid=block.id: self._toggle_block_completed(bid, checked))
                    row.addWidget(done)

                edit = QPushButton("Edit")
                edit.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                edit.clicked.connect(lambda _checked=False, bid=block.id: self._add_study_block(bid))
                row.addWidget(edit)
                remove = QPushButton("Remove")
                remove.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                remove.clicked.connect(lambda _checked=False, bid=block.id: self._delete_study_block(bid))
                row.addWidget(remove)
                self._timetable_layout.addLayout(row)

    def _populate_planner_tasks(self) -> None:
        self._clear_layout(self._planner_tasks_layout)
        recent_cutoff = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())
        tasks = [
            task for task in self._repo.get_study_planner_tasks()
            if not task.is_completed or task.due_at >= recent_cutoff
        ][:12]
        if not tasks:
            empty = QLabel("Add an assignment, exam or revision task to track upcoming deadlines.")
            empty.setObjectName("student_hint")
            self._planner_tasks_layout.addWidget(empty)
            return

        subject_names = {
            subject.id: subject.name
            for subject in self._repo.get_study_subjects(active_only=False)
        }
        for task in tasks:
            row = QHBoxLayout()
            done = QCheckBox()
            done.setChecked(task.is_completed)
            done.setAccessibleName(f"Mark {task.title} complete")
            done.clicked.connect(
                lambda checked, tid=task.id: self._set_planner_task_completed(tid, checked)
            )
            row.addWidget(done)
            subject_name = subject_names.get(task.subject_id)
            due_label = task.due_at.strftime("%a, %d %b · %H:%M")
            if not task.is_completed and task.due_at < datetime.now():
                due_label = f"Overdue · {due_label}"
            text = QLabel(
                f"{task.task_type.title()} · {task.title} · {due_label}"
                + (f" · {subject_name}" if subject_name else "")
            )
            if task.task_type == "exam":
                topics = self._repo.get_study_exam_topics(task.id)
                revised = sum(topic.status == "revised" for topic in topics)
                text.setText(
                    f"{text.text()} · {self._exam_countdown(task.due_at)}"
                    f" · {revised}/{len(topics)} topics revised"
                )
            text.setObjectName("student_session_row")
            text.setWordWrap(True)
            row.addWidget(text, 1)
            if task.task_type == "exam":
                topics_button = QPushButton("Topics")
                topics_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                topics_button.setAccessibleName(f"Manage revision topics for {task.title}")
                topics_button.clicked.connect(
                    lambda _checked=False, tid=task.id: self._manage_exam_topics(tid)
                )
                row.addWidget(topics_button)
            edit = QPushButton("Edit")
            edit.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            edit.clicked.connect(lambda _checked=False, tid=task.id: self._add_planner_task(tid))
            row.addWidget(edit)
            remove = QPushButton("Remove")
            remove.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            remove.clicked.connect(lambda _checked=False, tid=task.id: self._delete_planner_task(tid))
            row.addWidget(remove)
            self._planner_tasks_layout.addLayout(row)

    @staticmethod
    def _exam_countdown(due_at: datetime, today: Optional[date] = None) -> str:
        days = (due_at.date() - (today or date.today())).days
        if days > 1:
            return f"Exam in {days} days"
        if days == 1:
            return "Exam tomorrow"
        if days == 0:
            return "Exam today"
        return f"Exam date passed by {abs(days)} {'day' if days == -1 else 'days'}"

    def _manage_exam_topics(self, exam_task_id: int) -> None:
        exam = next(
            (task for task in self._repo.get_study_planner_tasks() if task.id == exam_task_id),
            None,
        )
        if exam is None or exam.task_type != "exam":
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Revision Topics — {exam.title}")
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        summary = QLabel()
        summary.setObjectName("student_hint")
        layout.addWidget(summary)
        topics_layout = QVBoxLayout()
        topics_layout.setSpacing(8)
        layout.addLayout(topics_layout)

        def save_topic(topic: StudyExamTopic, status: str, target_minutes: int) -> None:
            updated = StudyExamTopic(
                id=topic.id,
                exam_task_id=exam_task_id,
                title=topic.title,
                status=status,
                revision_target_minutes=target_minutes,
            )
            try:
                self._repo.save_study_exam_topic(updated)
            except Exception as exc:
                QMessageBox.warning(dialog, "Topic not saved", str(exc))
                return
            self._populate_planner_tasks()
            refresh_topics()

        def refresh_topics() -> None:
            self._clear_layout(topics_layout)
            topics = self._repo.get_study_exam_topics(exam_task_id)
            revised = sum(topic.status == "revised" for topic in topics)
            target_total = sum(topic.revision_target_minutes for topic in topics)
            summary.setText(
                f"{self._exam_countdown(exam.due_at)} · {revised} of {len(topics)} topics revised · "
                f"{format_duration(target_total * 60, compact=True)} revision target"
            )
            if not topics:
                empty = QLabel("Add chapters or topics to plan exam revision.")
                empty.setObjectName("student_hint")
                topics_layout.addWidget(empty)

            for topic in topics:
                row = QHBoxLayout()
                title_label = QLabel(topic.title)
                title_label.setObjectName("student_session_row")
                title_label.setWordWrap(True)
                row.addWidget(title_label, 1)

                status = QComboBox()
                for value, label in (
                    ("not_started", "Not started"),
                    ("in_progress", "In progress"),
                    ("revised", "Revised"),
                ):
                    status.addItem(label, value)
                status.setCurrentIndex(status.findData(topic.status))
                status.setAccessibleName(f"Revision status for {topic.title}")
                row.addWidget(status)

                target = self._spinbox(0, 600, topic.revision_target_minutes, " min target")
                target.setAccessibleName(f"Revision target for {topic.title}")
                row.addWidget(target)

                status.currentIndexChanged.connect(
                    lambda _index, item=topic, state=status, minutes=target: save_topic(
                        item, str(state.currentData()), minutes.value()
                    )
                )
                target.valueChanged.connect(
                    lambda minutes, item=topic, state=status: save_topic(
                        item, str(state.currentData()), minutes
                    )
                )

                remove = QPushButton("Remove")
                remove.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                remove.clicked.connect(
                    lambda _checked=False, topic_id=topic.id: self._delete_exam_topic(
                        dialog, topic_id, refresh_topics
                    )
                )
                row.addWidget(remove)
                topics_layout.addLayout(row)

        def add_topic() -> None:
            add_dialog = QDialog(dialog)
            add_dialog.setWindowTitle("Add Revision Topic")
            form = QFormLayout(add_dialog)
            title = QLineEdit()
            title.setPlaceholderText("e.g. Newton's laws")
            status = QComboBox()
            for value, label in (
                ("not_started", "Not started"),
                ("in_progress", "In progress"),
                ("revised", "Revised"),
            ):
                status.addItem(label, value)
            target = self._spinbox(0, 600, 30, " min target")
            form.addRow("Topic or chapter", title)
            form.addRow("Status", status)
            form.addRow("Revision target", target)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(add_dialog.accept)
            buttons.rejected.connect(add_dialog.reject)
            form.addRow(buttons)
            if add_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._repo.save_study_exam_topic(
                    StudyExamTopic(
                        exam_task_id=exam_task_id,
                        title=title.text(),
                        status=str(status.currentData()),
                        revision_target_minutes=target.value(),
                    )
                )
            except Exception as exc:
                QMessageBox.warning(dialog, "Topic not saved", str(exc))
                return
            self._populate_planner_tasks()
            refresh_topics()

        refresh_topics()
        add_button = QPushButton("Add topic or chapter")
        add_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        add_button.clicked.connect(add_topic)
        layout.addWidget(add_button)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(dialog.reject)
        layout.addWidget(close_buttons)
        dialog.exec()

    def _delete_exam_topic(self, dialog: QDialog, topic_id: int, refresh) -> None:
        answer = QMessageBox.question(
            dialog,
            "Remove revision topic?",
            "This removes the topic from its exam plan.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._repo.delete_study_exam_topic(topic_id)
            self._populate_planner_tasks()
            refresh()

    def _connect_controller(self) -> None:
        self._controller.phase_changed.connect(self._update_active_session)
        self._controller.tick.connect(self._on_tick)
        self._controller.interval_changed.connect(self._on_interval_changed)
        self._controller.session_completed.connect(self._on_session_completed)
        self._controller.session_aborted.connect(self._on_session_aborted)

    def _add_subject(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Study Subject")
        form = QFormLayout(dialog)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. Mathematics")
        target = self._spinbox(0, 1440, 120, " min")
        weekly_target = self._spinbox(0, 10080, 600, " min")
        form.addRow("Subject name", name_edit)
        form.addRow("Daily study target", target)
        form.addRow("Weekly study target", weekly_target)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        subject = StudySubject(
            name=name_edit.text(),
            daily_target_minutes=target.value(),
            weekly_target_minutes=weekly_target.value(),
        )
        try:
            self._repo.save_study_subject(subject)
        except ValueError as exc:
            QMessageBox.warning(self, "Subject not saved", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "Subject not saved", f"A subject with that name may already exist.\n\n{exc}")
            return
        self.on_data_changed()
        self._subject_combo.setCurrentIndex(self._subject_combo.findData(subject.id))

    def _start_session(self) -> None:
        if self._controller.is_active:
            self._active_status.setText("Finish or cancel the active session before starting another.")
            return

        study_mode = str(self._mode_combo.currentData())
        focus_mode = study_mode
        self._controller.focus_manager.set_mode(focus_mode)
        if not self._controller.focus_manager.ensure_mode_app_suggestions(focus_mode):
            self._active_status.setText(
                f"Add at least one allowed app in {self._mode_combo.currentText()} focus settings before starting."
            )
            self._open_focus_settings()
            return
        subject_id = self._subject_combo.currentData()
        subject_id = int(subject_id) if subject_id is not None else None
        goal = self._objective_edit.text().strip()
        if not goal:
            goal = self._mode_combo.currentText()

        started = self._controller.start_session(
            goal=goal,
            work_minutes=self._work_minutes.value(),
            break_minutes=self._break_minutes.value(),
            total_intervals=self._intervals.value(),
            preset=f"{self._work_minutes.value()}/{self._break_minutes.value()}",
            mode=focus_mode,
            subject_id=subject_id,
            study_mode=study_mode,
        )
        if not started:
            self._active_status.setText("A session is already active or the selected subject is unavailable.")
            return
        self._last_session_message = ""
        self._update_active_session()
        self._update_form_enabled()

    def _toggle_pause(self) -> None:
        if self._controller.is_paused:
            self._controller.resume_session()
        else:
            self._controller.pause_session()
        self._update_active_session()

    def _finish_early(self) -> None:
        if self._controller.is_active:
            self._controller.finish_early()

    def _cancel_session(self) -> None:
        if not self._controller.is_active:
            return
        answer = QMessageBox.question(
            self,
            "Cancel study session?",
            "The time already focused will be kept in your study history.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._controller.cancel_session()

    def _on_tick(self, remaining: int, total: int) -> None:
        self._active_progress.setMaximum(max(1, total))
        self._active_progress.setValue(max(0, total - remaining))
        self._update_active_session()

    def _on_interval_changed(self, current: int, total: int) -> None:
        self._active_status.setText(f"Work interval {current} of {total}")

    def _on_session_completed(self, session) -> None:
        mode_name = dict(STUDY_MODES).get(session.study_mode or "", "Study")
        self._last_session_message = f"Last session {mode_name.lower()}: {session.status.replace('_', ' ')}."
        if (
            self._pending_block_id is not None
            and self._pending_block_date is not None
            and session.status == "completed"
        ):
            self._repo.set_study_block_completed(
                self._pending_block_id,
                self._pending_block_date,
                True,
                session.id,
            )
        self._pending_block_id = None
        self._pending_block_date = None
        self.on_data_changed()

    def _on_session_aborted(self) -> None:
        self._pending_block_id = None
        self._pending_block_date = None
        self.on_data_changed()

    def _update_active_session(self, _phase: str = "") -> None:
        active = self._controller.is_active
        paused = self._controller.is_paused
        if active:
            subject = self._repo.get_study_subject(self._controller.subject_id) if self._controller.subject_id else None
            parts = [self._controller.goal]
            if subject:
                parts.append(subject.name)
            self._active_title.setText(" · ".join(parts))
            self._active_status.setText(
                f"{self._controller.phase.value.replace('_', ' ').title()} · "
                f"{format_duration(self._controller.remaining_seconds, compact=True)} remaining · "
                f"interval {self._controller.current_interval}/{self._controller.total_intervals}"
            )
            self._pause_btn.setText("Resume" if paused else "Pause")
            self._active_progress.setVisible(True)
        else:
            self._active_title.setText("No study session active")
            self._active_status.setText(
                self._last_session_message or self._next_profile_hint()
            )
            self._pause_btn.setText("Pause")
            self._active_progress.setValue(0)
            self._active_progress.setVisible(False)
        self._pause_btn.setEnabled(active)
        self._finish_btn.setEnabled(active)
        self._cancel_btn.setEnabled(active)
        self._update_form_enabled()

    def _update_form_enabled(self) -> None:
        enabled = not self._controller.is_active
        for widget in (
            self._mode_combo,
            self._subject_combo,
            self._add_subject_btn,
            self._objective_edit,
            self._work_minutes,
            self._break_minutes,
            self._intervals,
            self._start_btn,
        ):
            widget.setEnabled(enabled)

    def _open_focus_settings(self) -> None:
        self._controller.focus_manager.set_mode(str(self._mode_combo.currentData()))
        if self._navigate_to_focus:
            self._navigate_to_focus()

    def _next_profile_hint(self) -> str:
        return f"Your next session will use the {self._mode_combo.currentText()} focus profile."

    def _update_next_profile_hint(self, _index: int = -1) -> None:
        if not self._controller.is_active and not self._last_session_message:
            self._active_status.setText(self._next_profile_hint())

    def on_data_changed(self) -> None:
        today = date.today()
        subjects = self._repo.get_study_subjects(active_only=True)
        stats = self._repo.get_study_subject_stats(today, today)
        by_id = {row["id"]: row for row in stats}
        week_start = today - timedelta(days=today.weekday())
        weekly_stats = self._repo.get_study_subject_stats(week_start, today)
        weekly_by_id = {row["id"]: row for row in weekly_stats}
        sessions = self._repo.get_student_study_sessions_for_range(today, today)
        total_seconds = sum(session.actual_work_s for session in sessions)
        completed = sum(session.status == "completed" for session in sessions)
        session_noun = "session" if len(sessions) == 1 else "sessions"
        self._today_summary.setText(
            f"Today: {format_duration(total_seconds, compact=True)} focused · "
            f"{len(sessions)} {session_noun} · {completed} completed"
        )
        self._populate_student_insights(today)
        self._reload_subject_combo(subjects)
        self._populate_subjects(subjects, by_id, weekly_by_id)
        self._populate_timetable()
        self._populate_planner_tasks()
        self._populate_recent_sessions(sessions, subjects)
        self._update_active_session()

    def _populate_student_insights(self, today: date) -> None:
        week_start = today - timedelta(days=today.weekday())
        sessions = self._repo.get_student_study_sessions_for_range(week_start, today)
        actual_seconds = sum(session.actual_work_s for session in sessions)
        planned_seconds = sum(session.target_work_s for session in sessions)
        completed = sum(session.status == "completed" for session in sessions)
        completion_rate = (completed / len(sessions) * 100.0) if sessions else None
        rate_text = f"{completion_rate:.0f}% completed" if completion_rate is not None else "no sessions yet"
        session_noun = "session" if len(sessions) == 1 else "sessions"
        self._weekly_summary.setText(
            f"{format_duration(actual_seconds, compact=True)} focused · "
            f"{format_duration(planned_seconds, compact=True)} planned · "
            f"{completed} of {len(sessions)} {session_noun} completed ({rate_text})"
        )

        daily_seconds: dict[date, float] = {}
        for session in sessions:
            daily_seconds[session.started_at.date()] = (
                daily_seconds.get(session.started_at.date(), 0.0) + session.actual_work_s
            )
        self._clear_layout(self._weekly_trend_layout)
        trend_dates = [week_start + timedelta(days=offset) for offset in range(today.weekday() + 1)]
        trend_max = max((daily_seconds.get(day, 0.0) for day in trend_dates), default=0.0)
        for day in trend_dates:
            row = QHBoxLayout()
            label = QLabel(day.strftime("%a"))
            label.setMinimumWidth(34)
            bar = QProgressBar()
            bar.setRange(0, 100)
            seconds = daily_seconds.get(day, 0.0)
            bar.setValue(int(seconds / trend_max * 100) if trend_max else 0)
            bar.setTextVisible(False)
            bar.setMaximumHeight(8)
            bar.setAccessibleName(f"Study time on {day.strftime('%A')}")
            value = QLabel(format_duration(seconds, compact=True))
            value.setMinimumWidth(72)
            row.addWidget(label)
            row.addWidget(bar, 1)
            row.addWidget(value)
            self._weekly_trend_layout.addLayout(row)

        self._clear_layout(self._weekly_breakdown_layout)
        subject_stats = self._repo.get_study_subject_stats(week_start, today, active_only=False)
        subjects_with_time = [row for row in subject_stats if row["actual_work_s"] > 0]
        if subjects_with_time:
            subject_line = QLabel(
                "By subject: "
                + " · ".join(
                    f"{row['name']} {format_duration(row['actual_work_s'], compact=True)}"
                    for row in subjects_with_time[:5]
                )
            )
            subject_line.setObjectName("student_hint")
            subject_line.setWordWrap(True)
            self._weekly_breakdown_layout.addWidget(subject_line)

        distractions: dict[str, int] = {}
        for session in sessions:
            try:
                entries = json.loads(session.distractions_json or "[]")
            except (TypeError, ValueError):
                continue
            for entry in entries:
                process_name = str(entry.get("process_name", "")).strip()
                if process_name:
                    distractions[process_name] = distractions.get(process_name, 0) + int(entry.get("count", 0))
        if distractions:
            top = sorted(distractions.items(), key=lambda item: (-item[1], item[0].casefold()))[:3]
            distraction_line = QLabel(
                "Most blocked app attempts: "
                + " · ".join(f"{name} ({count})" for name, count in top)
            )
            distraction_line.setObjectName("student_hint")
            distraction_line.setWordWrap(True)
            self._weekly_breakdown_layout.addWidget(distraction_line)

    def _reload_subject_combo(self, subjects: list[StudySubject]) -> None:
        selected_id = self._subject_combo.currentData()
        self._subject_combo.blockSignals(True)
        self._subject_combo.clear()
        self._subject_combo.addItem("No subject", None)
        for subject in subjects:
            self._subject_combo.addItem(subject.name, subject.id)
        new_index = self._subject_combo.findData(selected_id) if selected_id is not None else 0
        self._subject_combo.setCurrentIndex(max(0, new_index))
        self._subject_combo.blockSignals(False)

    def _populate_subjects(
        self,
        subjects: list[StudySubject],
        stats: dict[int, dict],
        weekly_stats: dict[int, dict],
    ) -> None:
        self._clear_layout(self._subjects_layout)
        if not subjects:
            empty = QLabel("Add subjects to see study time and daily targets here.")
            empty.setObjectName("student_hint")
            self._subjects_layout.addWidget(empty)
            return

        for subject in subjects:
            row = QFrame()
            row.setObjectName("student_subject_row")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(5)
            metric = stats.get(subject.id, {})
            actual = float(metric.get("actual_work_s", 0.0))
            target_seconds = subject.daily_target_minutes * 60
            weekly_metric = weekly_stats.get(subject.id, {})
            weekly_actual = float(weekly_metric.get("actual_work_s", 0.0))
            weekly_target_seconds = subject.weekly_target_minutes * 60
            title_row = QHBoxLayout()
            name = QLabel(subject.name)
            name.setObjectName("student_subject_name")
            title_row.addWidget(name)
            title_row.addStretch()
            daily_text = (
                f"{format_duration(actual, compact=True)} / {format_duration(target_seconds, compact=True)} today"
                if target_seconds else f"{format_duration(actual, compact=True)} today"
            )
            weekly_text = (
                f"{format_duration(weekly_actual, compact=True)} / "
                f"{format_duration(weekly_target_seconds, compact=True)} this week"
                if weekly_target_seconds else f"{format_duration(weekly_actual, compact=True)} this week"
            )
            title_row.addWidget(QLabel(f"{daily_text} · {weekly_text}"))
            archive = QPushButton("Archive")
            archive.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            archive.clicked.connect(lambda _checked=False, sid=subject.id: self._archive_subject(sid))
            title_row.addWidget(archive)
            row_layout.addLayout(title_row)
            if target_seconds:
                progress = QProgressBar()
                progress.setMaximum(100)
                progress.setValue(min(100, int(actual / target_seconds * 100)))
                progress.setTextVisible(False)
                progress.setMaximumHeight(7)
                progress.setAccessibleName(f"{subject.name} daily study target progress")
                row_layout.addWidget(progress)
            if weekly_target_seconds:
                weekly_progress = QProgressBar()
                weekly_progress.setMaximum(100)
                weekly_progress.setValue(min(100, int(weekly_actual / weekly_target_seconds * 100)))
                weekly_progress.setTextVisible(False)
                weekly_progress.setMaximumHeight(7)
                weekly_progress.setAccessibleName(f"{subject.name} weekly study target progress")
                row_layout.addWidget(weekly_progress)
            self._subjects_layout.addWidget(row)

    def _populate_recent_sessions(self, sessions, subjects: list[StudySubject]) -> None:
        self._clear_layout(self._recent_layout)
        names = {subject.id: subject.name for subject in self._repo.get_study_subjects(active_only=False)}
        if not sessions:
            empty = QLabel("Study sessions you start here will appear in this list.")
            empty.setObjectName("student_hint")
            self._recent_layout.addWidget(empty)
            return

        for session in sessions[:8]:
            subject_name = names.get(session.subject_id, "No subject")
            label = dict(STUDY_MODES).get(session.study_mode or "", "Study")
            row = QLabel(
                f"{session.goal} · {subject_name} · {label} · "
                f"{format_duration(session.actual_work_s, compact=True)} focused · "
                f"{session.status.replace('_', ' ')}"
            )
            row.setObjectName("student_session_row")
            row.setWordWrap(True)
            self._recent_layout.addWidget(row)

    def _archive_subject(self, subject_id: int) -> None:
        self._repo.set_study_subject_active(subject_id, False)
        self.on_data_changed()

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _apply_theme(self, _is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QWidget#student_workspace_page,
            QWidget#student_workspace_content,
            QScrollArea#student_workspace_scroll {{
                background-color: {tm.color('bg')};
            }}
            QFrame#student_card {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
            }}
            QFrame#student_active_frame, QFrame#student_subject_row {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#section_title, QLabel#student_active_title {{
                color: {tm.color('text_main')}; font-size: 16px; font-weight: 700;
            }}
            QLabel#student_hint {{ color: {tm.color('text_sub')}; }}
            QLabel#student_today_summary {{
                color: {tm.color('accent')}; font-size: 14px; font-weight: 700;
                padding: 2px 0;
            }}
            QLabel#student_weekly_summary {{
                color: {tm.color('text_main')}; font-weight: 600; padding: 2px 0;
            }}
            QLabel#student_subject_name {{ color: {tm.color('text_main')}; font-weight: 700; }}
            QLabel#student_session_row {{
                color: {tm.color('text_sub')}; padding: 8px 2px;
                border-bottom: 1px solid {tm.color('border')};
            }}
            QPushButton#primary_action {{
                background: {tm.color('accent')}; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 10px 16px; font-weight: 700;
            }}
            QPushButton#primary_action:hover {{ background: {tm.color('accent_hover')}; }}
            QPushButton#primary_action:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QProgressBar {{
                background: {tm.color('border')}; border: none; border-radius: 4px;
            }}
            QProgressBar::chunk {{ background: {tm.color('accent')}; border-radius: 4px; }}
        """)
