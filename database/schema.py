from __future__ import annotations

CREATE_APP_SESSIONS = """
CREATE TABLE IF NOT EXISTS app_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name    TEXT    NOT NULL,
    exe_path        TEXT    NOT NULL DEFAULT '',
    window_title    TEXT    NOT NULL DEFAULT '',
    start_time      TEXT    NOT NULL,
    end_time        TEXT,
    duration_s      REAL    NOT NULL DEFAULT 0,
    category        TEXT    NOT NULL DEFAULT 'Other',
    is_idle         INTEGER NOT NULL DEFAULT 0,
    was_closed      INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_APP_INFO = """
CREATE TABLE IF NOT EXISTS app_info (
    process_name    TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'Other',
    exe_path        TEXT NOT NULL DEFAULT '',
    icon_path       TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL
);
"""

CREATE_DAILY_STATS = """
CREATE TABLE IF NOT EXISTS daily_stats (
    date                TEXT PRIMARY KEY,
    total_screen_time_s REAL NOT NULL DEFAULT 0,
    active_time_s       REAL NOT NULL DEFAULT 0,
    idle_time_s         REAL NOT NULL DEFAULT 0,
    top_app             TEXT,
    session_count       INTEGER NOT NULL DEFAULT 0,
    unlock_count        INTEGER NOT NULL DEFAULT 0,
    category_usage_json TEXT NOT NULL DEFAULT '{}',
    app_usage_json      TEXT NOT NULL DEFAULT '[]',
    timeline_json       TEXT NOT NULL DEFAULT '[]'
);
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

CREATE_EVENT_LOG = """
CREATE TABLE IF NOT EXISTS event_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    detail      TEXT    NOT NULL DEFAULT ''
);
"""

CREATE_WEBSITE_SESSIONS = """
CREATE TABLE IF NOT EXISTS website_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT    NOT NULL,
    browser_process TEXT    NOT NULL,
    start_time      TEXT    NOT NULL,
    end_time        TEXT,
    duration_s      REAL    NOT NULL DEFAULT 0,
    was_closed      INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_APP_LOCKER_APPS = """
CREATE TABLE IF NOT EXISTS app_locker_apps (
    process_name    TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    exe_path        TEXT NOT NULL DEFAULT '',
    icon_path       TEXT,
    added_at        TEXT NOT NULL
);
"""

CREATE_FOCUS_SCHEDULES = """
CREATE TABLE IF NOT EXISTS focus_schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL DEFAULT '',
    days_of_week    TEXT    NOT NULL,
    start_time      TEXT    NOT NULL,
    end_time        TEXT    NOT NULL,
    mode            TEXT    NOT NULL DEFAULT 'work',
    strict_mode     INTEGER NOT NULL DEFAULT 0,
    is_enabled      INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL
);
"""

CREATE_STUDY_SUBJECTS = """
CREATE TABLE IF NOT EXISTS study_subjects (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    color                TEXT    NOT NULL DEFAULT '#10B981',
    daily_target_minutes INTEGER NOT NULL DEFAULT 0 CHECK (daily_target_minutes >= 0),
    weekly_target_minutes INTEGER NOT NULL DEFAULT 0 CHECK (weekly_target_minutes >= 0),
    is_active            INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_DEEP_WORK_SESSIONS = """
CREATE TABLE IF NOT EXISTS deep_work_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    goal                TEXT    NOT NULL DEFAULT '',
    preset              TEXT    NOT NULL DEFAULT '25/5',
    target_work_s       REAL    NOT NULL,
    actual_work_s       REAL    NOT NULL DEFAULT 0,
    actual_break_s      REAL    NOT NULL DEFAULT 0,
    intervals_completed INTEGER NOT NULL DEFAULT 0,
    total_intervals     INTEGER NOT NULL DEFAULT 1,
    status              TEXT    NOT NULL DEFAULT 'completed',
    started_at          TEXT    NOT NULL,
    ended_at            TEXT    NOT NULL,
    notes               TEXT    NOT NULL DEFAULT '',
    subject_id          INTEGER REFERENCES study_subjects(id) ON DELETE SET NULL,
    study_mode          TEXT,
    distractions_json   TEXT    NOT NULL DEFAULT '[]'
);
"""

CREATE_STUDY_BLOCKS = """
CREATE TABLE IF NOT EXISTS study_blocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL DEFAULT '',
    weekday         INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time      TEXT    NOT NULL,
    work_minutes    INTEGER NOT NULL CHECK (work_minutes BETWEEN 1 AND 180),
    break_minutes   INTEGER NOT NULL DEFAULT 5 CHECK (break_minutes BETWEEN 1 AND 30),
    intervals       INTEGER NOT NULL DEFAULT 1 CHECK (intervals BETWEEN 1 AND 8),
    subject_id      INTEGER REFERENCES study_subjects(id) ON DELETE SET NULL,
    is_enabled      INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_STUDY_BLOCK_COMPLETIONS = """
CREATE TABLE IF NOT EXISTS study_block_completions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id        INTEGER NOT NULL REFERENCES study_blocks(id) ON DELETE CASCADE,
    occurrence_date TEXT    NOT NULL,
    session_id      INTEGER REFERENCES deep_work_sessions(id) ON DELETE SET NULL,
    completed_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (block_id, occurrence_date)
);
"""

CREATE_STUDY_PLANNER_TASKS = """
CREATE TABLE IF NOT EXISTS study_planner_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    task_type       TEXT    NOT NULL CHECK (task_type IN ('assignment', 'exam', 'revision')),
    due_at          TEXT    NOT NULL,
    subject_id      INTEGER REFERENCES study_subjects(id) ON DELETE SET NULL,
    reminder_at     TEXT,
    reminder_sent_at TEXT,
    is_completed    INTEGER NOT NULL DEFAULT 0,
    completed_at    TEXT,
    notes           TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_STUDY_EXAM_TOPICS = """
CREATE TABLE IF NOT EXISTS study_exam_topics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_task_id            INTEGER NOT NULL REFERENCES study_planner_tasks(id) ON DELETE CASCADE,
    title                   TEXT    NOT NULL,
    status                  TEXT    NOT NULL DEFAULT 'not_started'
                                    CHECK (status IN ('not_started', 'in_progress', 'revised')),
    revision_target_minutes INTEGER NOT NULL DEFAULT 0 CHECK (revision_target_minutes >= 0),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (exam_task_id, title)
);
"""

CREATE_SCREEN_TIME_BUDGETS = """
CREATE TABLE IF NOT EXISTS screen_time_budgets (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type          TEXT    NOT NULL,
    target_name          TEXT    NOT NULL,
    daily_budget_seconds INTEGER NOT NULL,
    is_enabled           INTEGER NOT NULL DEFAULT 1,
    enforce_lock         INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_start      ON app_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_process    ON app_sessions(process_name);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_category   ON app_sessions(category);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_end        ON app_sessions(end_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_open       ON app_sessions(end_time) WHERE end_time IS NULL;",
    "CREATE INDEX IF NOT EXISTS idx_event_log_time      ON event_log(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_event_log_type      ON event_log(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_start ON website_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_domain ON website_sessions(domain);",
    "CREATE INDEX IF NOT EXISTS idx_focus_schedules_enabled ON focus_schedules(is_enabled);",
    "CREATE INDEX IF NOT EXISTS idx_deep_work_started   ON deep_work_sessions(started_at);",
    "CREATE INDEX IF NOT EXISTS idx_deep_work_status    ON deep_work_sessions(status);",
    "CREATE INDEX IF NOT EXISTS idx_budgets_enabled     ON screen_time_budgets(is_enabled);",
    "CREATE INDEX IF NOT EXISTS idx_study_blocks_weekday ON study_blocks(weekday, is_enabled, start_time);",
    "CREATE INDEX IF NOT EXISTS idx_study_tasks_due ON study_planner_tasks(due_at, is_completed);",
    "CREATE INDEX IF NOT EXISTS idx_study_tasks_reminder ON study_planner_tasks(reminder_at, reminder_sent_at);",
]

MIGRATE_ADD_EXE_PATH = """
ALTER TABLE app_sessions ADD COLUMN exe_path TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_WAS_CLOSED = """
ALTER TABLE app_sessions ADD COLUMN was_closed INTEGER NOT NULL DEFAULT 0;
"""

MIGRATE_ADD_APP_INFO_LAST_SEEN = """
ALTER TABLE app_info ADD COLUMN last_seen TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_APP_INFO_EXE_PATH = """
ALTER TABLE app_info ADD COLUMN exe_path TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_DS_UNLOCK_COUNT = """
ALTER TABLE daily_stats ADD COLUMN unlock_count INTEGER NOT NULL DEFAULT 0;
"""

MIGRATE_ADD_DS_CATEGORY_JSON = """
ALTER TABLE daily_stats ADD COLUMN category_usage_json TEXT NOT NULL DEFAULT '{}';
"""

MIGRATE_ADD_DS_APP_JSON = """
ALTER TABLE daily_stats ADD COLUMN app_usage_json TEXT NOT NULL DEFAULT '[]';
"""

MIGRATE_ADD_DS_TIMELINE_JSON = """
ALTER TABLE daily_stats ADD COLUMN timeline_json TEXT NOT NULL DEFAULT '[]';
"""

ALL_DDL = [
    CREATE_APP_SESSIONS,
    CREATE_APP_INFO,
    CREATE_DAILY_STATS,
    CREATE_SETTINGS,
    CREATE_EVENT_LOG,
    CREATE_WEBSITE_SESSIONS,
    CREATE_APP_LOCKER_APPS,
    CREATE_FOCUS_SCHEDULES,
    CREATE_STUDY_SUBJECTS,
    CREATE_DEEP_WORK_SESSIONS,
    CREATE_STUDY_BLOCKS,
    CREATE_STUDY_BLOCK_COMPLETIONS,
    CREATE_STUDY_PLANNER_TASKS,
    CREATE_STUDY_EXAM_TOPICS,
    CREATE_SCREEN_TIME_BUDGETS,
    *CREATE_INDEXES,
]


MIGRATIONS = [
    ("exe_path",    "app_sessions",  MIGRATE_ADD_EXE_PATH),
    ("was_closed",  "app_sessions",  MIGRATE_ADD_WAS_CLOSED),
    ("last_seen",   "app_info",      MIGRATE_ADD_APP_INFO_LAST_SEEN),
    ("exe_path",    "app_info",      MIGRATE_ADD_APP_INFO_EXE_PATH),
    ("unlock_count", "daily_stats",  MIGRATE_ADD_DS_UNLOCK_COUNT),
    ("category_usage_json", "daily_stats", MIGRATE_ADD_DS_CATEGORY_JSON),
    ("app_usage_json", "daily_stats", MIGRATE_ADD_DS_APP_JSON),
    ("timeline_json", "daily_stats", MIGRATE_ADD_DS_TIMELINE_JSON),
    ("subject_id", "deep_work_sessions", "ALTER TABLE deep_work_sessions ADD COLUMN subject_id INTEGER REFERENCES study_subjects(id) ON DELETE SET NULL;"),
    ("study_mode", "deep_work_sessions", "ALTER TABLE deep_work_sessions ADD COLUMN study_mode TEXT;"),
    ("distractions_json", "deep_work_sessions", "ALTER TABLE deep_work_sessions ADD COLUMN distractions_json TEXT NOT NULL DEFAULT '[]';"),
    ("weekly_target_minutes", "study_subjects", "ALTER TABLE study_subjects ADD COLUMN weekly_target_minutes INTEGER NOT NULL DEFAULT 0 CHECK (weekly_target_minutes >= 0);"),
]

DEFAULT_SETTINGS = {
    "idle_threshold_s": "300",
    "autostart": "false",
    "dark_mode": "true",
    "minimize_to_tray": "true",
    "notifications_enabled": "true",
    "daily_limit_minutes": "480",
    "export_path": "",
    # App Locker defaults
    "app_locker_enabled": "false",
    "app_locker_auth_method": "hello_pin",  # hello | pin | hello_pin
    "app_locker_auth_duration": "15_min",   # every_launch | 5_min | 15_min | until_close
}
