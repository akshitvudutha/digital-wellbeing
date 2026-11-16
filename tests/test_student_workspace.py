from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLineEdit, QPushButton

from database.models import (
    DeepWorkSession,
    StudyBlock,
    StudyExamTopic,
    StudyPlannerTask,
    StudySubject,
)
from database.repository import Repository
from protection.deep_work import DeepWorkController
from protection.focus_manager import FocusManager
from ui.pages.student_workspace import StudentWorkspacePage
from ui.theme import ThemeManager
from ui.widgets.focus_timer import FocusTimerWidget


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repo(tmp_path: Path):
    Repository.set_db_path_override(tmp_path / "student_workspace.sqlite")
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_subject_crud_archives_without_erasing_study_history(repo):
    subject = StudySubject(
        name="Mathematics",
        daily_target_minutes=90,
        weekly_target_minutes=480,
    )
    subject_id = repo.save_study_subject(subject)
    now = datetime.now()
    session = DeepWorkSession(
        goal="Revise vectors",
        preset="25/5",
        target_work_s=1500,
        actual_work_s=900,
        actual_break_s=0,
        intervals_completed=0,
        total_intervals=1,
        status="finished_early",
        started_at=now - timedelta(minutes=15),
        ended_at=now,
        subject_id=subject_id,
        study_mode="revision",
        distractions_json='[{"process_name":"discord.exe","count":1}]',
    )
    repo.record_deep_work_session(session)

    assert subject.id == subject_id
    assert repo.get_study_subject(subject_id).name == "Mathematics"
    assert repo.get_study_subject(subject_id).weekly_target_minutes == 480
    assert repo.get_student_study_sessions_for_range(date.today(), date.today(), subject_id)[0].study_mode == "revision"
    assert repo.get_study_subject_stats(date.today(), date.today())[0]["actual_work_s"] == 900

    assert repo.set_study_subject_active(subject_id, False)
    assert repo.get_study_subjects() == []
    archived = repo.get_study_subject(subject_id)
    assert archived is not None and archived.is_active is False
    assert len(repo.get_student_study_sessions_for_range(date.today(), date.today())) == 1


def test_old_deep_work_rows_survive_additive_student_metadata_migration(tmp_path: Path):
    db_path = tmp_path / "legacy_deep_work.sqlite"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE deep_work_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL DEFAULT '',
            preset TEXT NOT NULL DEFAULT '25/5',
            target_work_s REAL NOT NULL,
            actual_work_s REAL NOT NULL DEFAULT 0,
            actual_break_s REAL NOT NULL DEFAULT 0,
            intervals_completed INTEGER NOT NULL DEFAULT 0,
            total_intervals INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'completed',
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE study_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            color TEXT NOT NULL DEFAULT '#10B981',
            daily_target_minutes INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    connection.execute(
        "INSERT INTO study_subjects (name, daily_target_minutes) VALUES (?, ?)",
        ("Legacy Physics", 45),
    )
    started = datetime.now()
    connection.execute(
        """
        INSERT INTO deep_work_sessions
            (goal, target_work_s, actual_work_s, started_at, ended_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Legacy session", 1500, 600, started.isoformat(), (started + timedelta(minutes=10)).isoformat()),
    )
    connection.commit()
    connection.close()

    Repository.set_db_path_override(db_path)
    migrated = Repository()
    try:
        row = migrated.get_deep_work_sessions_for_range(date.today(), date.today())[0]
        assert row.goal == "Legacy session"
        assert row.actual_work_s == 600
        assert row.subject_id is None
        assert row.study_mode is None
        assert row.distractions_json == "[]"
        migrated_subject = migrated.get_study_subjects()[0]
        assert migrated_subject.name == "Legacy Physics"
        assert migrated_subject.daily_target_minutes == 45
        assert migrated_subject.weekly_target_minutes == 0
        with migrated._cursor() as cur:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='study_exam_topics'"
            )
            assert cur.fetchone() is not None
    finally:
        migrated.close()
        Repository.set_db_path_override(None)


def test_student_workspace_starts_and_records_subject_tagged_focus(repo, qapp):
    focus = FocusManager(repo)
    focus.suggest_mode_apps = lambda _mode: ["code.exe"]
    focus._run_enforcement_scan = lambda: None
    clock = FakeClock()
    controller = DeepWorkController(repo, focus_mgr=focus, notifier=MagicMock(), clock=clock)
    subject = StudySubject(name="Programming", daily_target_minutes=60)
    repo.save_study_subject(subject)
    page = StudentWorkspacePage(repo=repo, controller=controller)
    page._subject_combo.setCurrentIndex(page._subject_combo.findData(subject.id))
    page._mode_combo.setCurrentIndex(page._mode_combo.findData("reading"))
    page._objective_edit.setText("Read the recursion chapter")
    page._work_minutes.setValue(1)
    page._intervals.setValue(1)

    page._start_btn.click()
    assert controller.is_active
    assert controller.study_mode == "reading"
    assert controller.subject_id == subject.id
    assert focus.current_mode == "reading"
    assert focus.current_mode_apps == ["code.exe"]

    focus.app_blocked.emit("Discord.exe", "study", 60)
    clock.advance(60)
    controller._on_tick()

    sessions = repo.get_student_study_sessions_for_range(date.today(), date.today())
    assert len(sessions) == 1
    assert sessions[0].goal == "Read the recursion chapter"
    assert sessions[0].actual_work_s == pytest.approx(60)
    assert sessions[0].subject_id == subject.id
    assert sessions[0].study_mode == "reading"
    assert json.loads(sessions[0].distractions_json) == [
        {"process_name": "discord.exe", "count": 1}
    ]
    assert "1 of 1 session completed" in page._weekly_summary.text()
    assert page._weekly_breakdown_layout.count() >= 2

    page.deleteLater()
    qapp.processEvents()


def test_student_focus_profiles_are_selectable_and_keep_independent_settings(repo, qapp):
    focus = FocusManager(repo)
    focus.suggest_mode_apps = lambda _mode: []
    widget = FocusTimerWidget(focus_manager=focus)

    reading_index = widget._student_profile_combo.findData("reading")
    revision_index = widget._student_profile_combo.findData("revision")
    assert reading_index > 0 and revision_index > 0

    widget._student_profile_combo.setCurrentIndex(reading_index)
    focus.save_mode_apps("reading", ["reader.exe"])
    focus.save_mode_websites("reading", ["example.com"])

    widget._student_profile_combo.setCurrentIndex(revision_index)
    focus.save_mode_apps("revision", ["notes.exe"])
    focus.save_mode_websites("revision", ["videos.example"])

    widget._student_profile_combo.setCurrentIndex(reading_index)
    assert focus.current_mode == "reading"
    assert focus.current_mode_apps == ["reader.exe"]
    assert focus.current_mode_websites == ["example.com"]

    widget._student_profile_combo.setCurrentIndex(revision_index)
    assert focus.current_mode == "revision"
    assert focus.current_mode_apps == ["notes.exe"]
    assert focus.current_mode_websites == ["videos.example"]

    widget.deleteLater()
    qapp.processEvents()


def test_student_workspace_does_not_start_with_empty_study_allowlist(repo, qapp):
    focus = FocusManager(repo)
    focus._mode_apps["study"] = []
    focus.ensure_mode_app_suggestions = lambda _mode: []
    controller = DeepWorkController(repo, focus_mgr=focus, notifier=MagicMock(), clock=FakeClock())
    visited_focus = []
    page = StudentWorkspacePage(
        repo=repo,
        controller=controller,
        navigate_to_focus=lambda: visited_focus.append(True),
    )

    page._mode_combo.setCurrentIndex(page._mode_combo.findData("revision"))
    assert "Revision focus profile" in page._active_status.text()
    page._start_btn.click()
    assert controller.is_active is False
    assert visited_focus == [True]

    page.deleteLater()
    qapp.processEvents()


def test_weekly_study_blocks_keep_completion_per_occurrence_date(repo):
    block = StudyBlock(
        name="Physics problems",
        weekday=0,
        start_time="09:30",
        work_minutes=25,
        break_minutes=5,
        intervals=2,
    )
    block_id = repo.save_study_block(block)
    monday = date(2026, 11, 16)
    next_monday = date(2026, 11, 23)

    first = repo.get_study_blocks(on_date=monday)
    assert first[0].id == block_id
    assert first[0].completed_for_date is False
    assert repo.set_study_block_completed(block_id, monday, True)
    assert repo.get_study_blocks(on_date=monday)[0].completed_for_date is True
    assert repo.get_study_blocks(on_date=next_monday)[0].completed_for_date is False

    assert repo.set_study_block_completed(block_id, monday, False)
    assert repo.get_study_blocks(on_date=monday)[0].completed_for_date is False


def test_planner_task_completion_and_reminder_are_deduplicated(repo):
    now = datetime(2026, 11, 15, 10, 0, 0)
    task = StudyPlannerTask(
        title="Submit physics lab",
        task_type="assignment",
        due_at=now + timedelta(days=1),
        reminder_at=now - timedelta(minutes=1),
    )
    task_id = repo.save_study_planner_task(task)

    due = repo.claim_due_study_reminders(now)
    assert [item.id for item in due] == [task_id]
    assert repo.claim_due_study_reminders(now) == []
    saved = repo.get_study_planner_tasks()[0]
    assert saved.reminder_sent_at == now

    assert repo.set_study_planner_task_completed(task_id, True)
    completed = repo.get_study_planner_tasks()[0]
    assert completed.is_completed is True
    assert completed.completed_at is not None
    assert repo.get_study_planner_tasks(include_completed=False) == []
    assert repo.set_study_planner_task_completed(task_id, False)
    assert repo.get_study_planner_tasks()[0].is_completed is False


def test_exam_topics_track_status_targets_and_countdown(repo, qapp, monkeypatch):
    today = date(2026, 11, 15)
    exam_id = repo.save_study_planner_task(
        StudyPlannerTask(
            title="Physics final",
            task_type="exam",
            due_at=datetime(2026, 11, 18, 9, 0),
        )
    )
    first_topic = StudyExamTopic(exam_task_id=exam_id, title="Kinematics", revision_target_minutes=30)
    second_topic = StudyExamTopic(
        exam_task_id=exam_id,
        title="Newton's laws",
        status="in_progress",
        revision_target_minutes=45,
    )
    repo.save_study_exam_topic(first_topic)
    repo.save_study_exam_topic(second_topic)
    assert first_topic.id is not None and second_topic.id is not None

    first_topic.status = "revised"
    repo.save_study_exam_topic(first_topic)
    assert [(topic.title, topic.status, topic.revision_target_minutes) for topic in repo.get_study_exam_topics(exam_id)] == [
        ("Kinematics", "revised", 30),
        ("Newton's laws", "in_progress", 45),
    ]
    assert StudentWorkspacePage._exam_countdown(datetime(2026, 11, 18, 9, 0), today) == "Exam in 3 days"
    assert StudentWorkspacePage._exam_countdown(datetime(2026, 11, 16, 9, 0), today) == "Exam tomorrow"
    assert StudentWorkspacePage._exam_countdown(datetime(2026, 11, 15, 9, 0), today) == "Exam today"
    assert StudentWorkspacePage._exam_countdown(datetime(2026, 11, 14, 9, 0), today) == "Exam date passed by 1 day"

    revision_task_id = repo.save_study_planner_task(
        StudyPlannerTask(title="Review calculus", task_type="revision", due_at=datetime(2026, 11, 16, 9, 0))
    )
    with pytest.raises(ValueError, match="existing exam"):
        repo.save_study_exam_topic(
            StudyExamTopic(exam_task_id=revision_task_id, title="Limits")
        )

    focus = FocusManager(repo)
    controller = DeepWorkController(repo, focus_mgr=focus, notifier=MagicMock(), clock=FakeClock())
    page = StudentWorkspacePage(repo=repo, controller=controller)
    topic_button = next(
        button for button in page.findChildren(QPushButton)
        if button.text() == "Topics"
    )
    assert topic_button.accessibleName() == "Manage revision topics for Physics final"

    def mark_first_topic_revised(dialog):
        status = next(combo for combo in dialog.findChildren(QComboBox) if combo.findData("revised") >= 0)
        status.setCurrentIndex(status.findData("revised"))
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", mark_first_topic_revised)
    page._manage_exam_topics(exam_id)
    assert repo.get_study_exam_topics(exam_id)[0].status == "revised"
    assert repo.delete_study_planner_task(exam_id)
    assert repo.get_study_exam_topics(exam_id) == []
    page.deleteLater()
    qapp.processEvents()


def test_student_workspace_starts_and_completes_today_timetable_block(repo, qapp):
    focus = FocusManager(repo)
    focus.suggest_mode_apps = lambda _mode: ["code.exe"]
    focus._run_enforcement_scan = lambda: None
    clock = FakeClock()
    controller = DeepWorkController(repo, focus_mgr=focus, notifier=MagicMock(), clock=clock)
    subject = StudySubject(name="Chemistry")
    subject_id = repo.save_study_subject(subject)
    block = StudyBlock(
        name="Chemistry review",
        weekday=date.today().weekday(),
        start_time="10:00",
        work_minutes=1,
        break_minutes=5,
        intervals=1,
        subject_id=subject_id,
    )
    block_id = repo.save_study_block(block)
    page = StudentWorkspacePage(repo=repo, controller=controller, notifier=MagicMock())

    page._start_study_block(block_id)
    assert controller.is_active
    assert controller.subject_id == subject_id
    assert controller.remaining_seconds == 60
    assert page._pending_block_id == block_id

    clock.advance(60)
    controller._on_tick()
    saved_block = next(item for item in repo.get_study_blocks(on_date=date.today()) if item.id == block_id)
    assert saved_block.completed_for_date is True
    assert page._pending_block_id is None
    assert "1 of 1 session completed" in page._weekly_summary.text()

    page.deleteLater()
    qapp.processEvents()


def test_student_workspace_delivers_a_planner_reminder_once(repo, qapp):
    now = datetime.now().replace(microsecond=0)
    task = StudyPlannerTask(
        title="Revise calculus",
        task_type="revision",
        due_at=now + timedelta(hours=1),
        reminder_at=now - timedelta(seconds=1),
    )
    repo.save_study_planner_task(task)
    notifier = MagicMock()
    page = StudentWorkspacePage(
        repo=repo,
        controller=DeepWorkController(repo, focus_mgr=FocusManager(repo), notifier=MagicMock(), clock=FakeClock()),
        notifier=notifier,
    )

    page._check_due_reminders(now)
    page._check_due_reminders(now)

    notifier.notify.assert_called_once()
    assert notifier.notify.call_args.args[0] == "Revision reminder"
    assert "Revise calculus" in notifier.notify.call_args.args[1]

    page.deleteLater()
    qapp.processEvents()


def test_student_planner_dialogs_save_blocks_and_deadlines(repo, qapp, monkeypatch):
    def accept_with_title(dialog):
        edits = dialog.findChildren(QLineEdit)
        if edits:
            edits[0].setText("Weekly programming review")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_with_title)
    focus = FocusManager(repo)
    controller = DeepWorkController(repo, focus_mgr=focus, notifier=MagicMock(), clock=FakeClock())
    page = StudentWorkspacePage(repo=repo, controller=controller, notifier=MagicMock())
    theme = ThemeManager.instance()
    original_theme = theme.is_dark
    theme.set_theme("Dark")
    assert "#080A0D" in page.styleSheet()
    assert "QPushButton#primary_action:focus" in page.styleSheet()
    theme.set_theme("Light")
    assert "#F8FAFC" in page.styleSheet()

    page._add_study_block()
    page._add_planner_task()

    blocks = repo.get_study_blocks()
    tasks = repo.get_study_planner_tasks()
    assert len(blocks) == 1
    assert blocks[0].name == "Weekly programming review"
    assert len(tasks) == 1
    assert tasks[0].title == "Weekly programming review"
    assert tasks[0].task_type == "assignment"

    monkeypatch.setattr(QDialog, "exec", lambda _dialog: QDialog.DialogCode.Rejected)
    page._add_study_block(blocks[0].id)
    page._add_planner_task(tasks[0].id)
    theme.set_theme("Dark" if original_theme else "Light")

    page.deleteLater()
    qapp.processEvents()
