from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from core.constants import AppCategory
from utils.time_format import format_duration


@dataclass
class AppSession:
    process_name: str
    window_title: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_s: float
    category: AppCategory
    is_idle: bool
    exe_path: str = ""
    was_closed: bool = False
    id: Optional[int] = field(default=None)

    @property
    def duration_formatted(self) -> str:
        return format_duration(self.duration_s)

    @property
    def is_open(self) -> bool:
        return self.end_time is None


@dataclass
class WebsiteSession:
    domain: str
    browser_process: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_s: float
    was_closed: bool = False
    id: Optional[int] = field(default=None)

    @property
    def duration_formatted(self) -> str:
        return format_duration(self.duration_s)

    @property
    def is_open(self) -> bool:
        return self.end_time is None



@dataclass
class AppInfo:
    process_name: str
    display_name: str
    category: AppCategory
    icon_path: Optional[str]
    first_seen: datetime
    exe_path: str = ""
    last_seen: Optional[datetime] = None
    total_time_s: float = 0.0
    session_count: int = 0


@dataclass
class DailyStat:
    date: date
    total_screen_time_s: float
    active_time_s: float
    idle_time_s: float
    top_app: Optional[str]
    session_count: int
    unlock_count: int = 0
    category_usage_json: str = "{}"
    app_usage_json: str = "[]"
    timeline_json: str = "[]"


@dataclass
class EventLogEntry:
    timestamp: datetime
    event_type: str
    detail: str
    id: Optional[int] = field(default=None)


@dataclass
class Setting:
    key: str
    value: str


@dataclass
class FocusSchedule:
    name: str
    days_of_week: str  # comma-separated '0,1,2,3,4' (0=Monday, 6=Sunday)
    start_time: str    # 'HH:MM' (24-hour)
    end_time: str      # 'HH:MM' (24-hour)
    mode: str = "work"
    strict_mode: bool = False
    is_enabled: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = field(default=None)

    @property
    def days_list(self) -> list[int]:
        if not self.days_of_week:
            return []
        try:
            return [int(d.strip()) for d in self.days_of_week.split(",") if d.strip()]
        except ValueError:
            return []

    def is_active_on_day(self, weekday: int) -> bool:
        return weekday in self.days_list


@dataclass
class DeepWorkSession:
    goal: str
    preset: str  # '25/5', '50/10', 'custom'
    target_work_s: float
    actual_work_s: float
    actual_break_s: float
    intervals_completed: int
    total_intervals: int
    status: str  # 'completed', 'finished_early', 'cancelled'
    started_at: datetime
    ended_at: datetime
    notes: str = ""
    id: Optional[int] = field(default=None)
    subject_id: Optional[int] = None
    study_mode: Optional[str] = None
    distractions_json: str = "[]"

    @property
    def duration_formatted(self) -> str:
        return format_duration(self.actual_work_s)


@dataclass
class StudySubject:
    name: str
    color: str = "#10B981"
    daily_target_minutes: int = 0
    weekly_target_minutes: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = field(default=None)


@dataclass
class StudyBlock:
    """A recurring weekly study block in the student's timetable."""

    name: str
    weekday: int
    start_time: str
    work_minutes: int
    break_minutes: int = 5
    intervals: int = 1
    subject_id: Optional[int] = None
    is_enabled: bool = True
    id: Optional[int] = field(default=None)
    completed_for_date: bool = False


@dataclass
class StudyPlannerTask:
    """An assignment, exam, or revision task with an optional reminder."""

    title: str
    task_type: str
    due_at: datetime
    subject_id: Optional[int] = None
    reminder_at: Optional[datetime] = None
    reminder_sent_at: Optional[datetime] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    notes: str = ""
    id: Optional[int] = field(default=None)


@dataclass
class StudyExamTopic:
    """A revision topic tracked under an exam deadline."""

    exam_task_id: int
    title: str
    status: str = "not_started"
    revision_target_minutes: int = 0
    id: Optional[int] = field(default=None)


@dataclass
class ScreenTimeBudget:
    target_type: str  # "total", "category", "app"
    target_name: str  # "Total Screen Time", "Social", "Entertainment", "chrome.exe", etc.
    daily_budget_seconds: int = 7200  # Default 2 hours
    is_enabled: bool = True
    enforce_lock: bool = False
    created_at: Optional[datetime] = None
    id: Optional[int] = field(default=None)

    @property
    def budget_formatted(self) -> str:
        h, m = divmod(self.daily_budget_seconds // 60, 60)
        if h > 0 and m > 0:
            return f"{h}h {m}m"
        elif h > 0:
            return f"{h}h"
        return f"{m}m"
