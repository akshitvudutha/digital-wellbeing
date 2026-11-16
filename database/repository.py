from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generator, List, Optional

from core.constants import AppCategory
from core.logger import logger
from database.models import (
    AppInfo, AppSession, EventLogEntry, DailyStat, Setting,
    WebsiteSession, FocusSchedule, DeepWorkSession, ScreenTimeBudget, StudySubject,
    StudyBlock, StudyPlannerTask, StudyExamTopic
)
from database.schema import ALL_DDL, DEFAULT_SETTINGS, MIGRATIONS


def _get_db_path() -> Path:
    env_path = os.environ.get("DW_DB_PATH")
    if env_path:
        p = Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    app_data = Path.home() / "AppData" / "Local" / "DigitalWellbeing"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data / "digital_wellbeing.db"


class Repository:
    _instance: Optional["Repository"] = None
    _class_lock = threading.Lock()
    _db_path_override: Optional[Path] = None

    @classmethod
    def set_db_path_override(cls, path: Optional[Path]) -> None:
        with cls._class_lock:
            cls._db_path_override = path
            cls._instance = None

    def __new__(cls) -> "Repository":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._db_path = Repository._db_path_override or _get_db_path()
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._initialize_schema()
        self._run_migrations()
        self._seed_default_settings()
        self._cleanup_test_data()
        self._close_orphaned_sessions()
        self._initialized = True
        logger.info("Repository initialized at %s", self._db_path)

    # ─── Connection management ─────────────────────────────────────────────────

    def _connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-8000;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connection()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except sqlite3.OperationalError as exc:
            conn.rollback()
            logger.error("DB operational error: %s", exc)
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ─── Schema ───────────────────────────────────────────────────────────────

    def _initialize_schema(self) -> None:
        with self._write_lock:
            conn = self._connection()
            cur = conn.cursor()
            try:
                for ddl in ALL_DDL:
                    cur.execute(ddl)
                conn.commit()
            finally:
                cur.close()

    def _run_migrations(self) -> None:
        with self._write_lock:
            conn = self._connection()
            cur = conn.cursor()
            try:
                for column, table, sql in MIGRATIONS:
                    cur.execute(f"PRAGMA table_info({table})")
                    cols = [row["name"] for row in cur.fetchall()]
                    if column not in cols:
                        cur.execute(sql)
                        logger.info("Migration applied: ADD %s.%s", table, column)
                conn.commit()
            finally:
                cur.close()

    def _seed_default_settings(self) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                for key, value in DEFAULT_SETTINGS.items():
                    cur.execute(
                        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                        (key, value),
                    )

    def _close_orphaned_sessions(self) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE app_sessions
                    SET end_time = COALESCE(end_time, start_time),
                        duration_s = CASE
                            WHEN end_time IS NOT NULL AND start_time IS NOT NULL THEN
                                MAX(0.0, (JULIANDAY(end_time) - JULIANDAY(start_time)) * 86400.0)
                            ELSE 0.0
                        END,
                        was_closed = 1
                    WHERE end_time IS NULL OR was_closed = 0
                    """,
                )
                
                cur.execute(
                    """
                    UPDATE website_sessions
                    SET end_time = COALESCE(end_time, start_time),
                        duration_s = CASE
                            WHEN end_time IS NOT NULL AND start_time IS NOT NULL THEN
                                MAX(0.0, (JULIANDAY(end_time) - JULIANDAY(start_time)) * 86400.0)
                            ELSE 0.0
                        END,
                        was_closed = 1
                    WHERE end_time IS NULL OR was_closed = 0
                    """,
                )
                count = cur.rowcount
                if count:
                    logger.warning("Closed %d orphaned sessions from previous run", count)

    # ─── Website Sessions ────────────────────────────────────────────────────
    
    def insert_website_session(self, session: WebsiteSession) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO website_sessions
                        (domain, browser_process, start_time, end_time, duration_s, was_closed)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.domain,
                        session.browser_process,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else None,
                        session.duration_s,
                        int(session.was_closed),
                    ),
                )
                return cur.lastrowid or 0

    def update_website_session_end(
        self,
        session_id: int,
        end_time: datetime,
        duration_s: float,
        was_closed: bool = True,
    ) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE website_sessions
                    SET end_time=?, duration_s=?, was_closed=?
                    WHERE id=?
                    """,
                    (end_time.isoformat(), duration_s, int(was_closed), session_id),
                )
                
    def get_website_usage_today(self, domain: str) -> float:
        today = date.today()
        start = datetime.combine(today, datetime.min.time()).isoformat()
        end = datetime.combine(today, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s
                FROM website_sessions
                WHERE domain=? AND start_time >= ? AND start_time <= ?
                """,
                (domain, start, end),
            )
            row = cur.fetchone()
            return row["total_s"] or 0.0

    def get_top_websites_for_browser_today(self, browser_process: str) -> List[dict]:
        today = date.today()
        start = datetime.combine(today, datetime.min.time()).isoformat()
        end = datetime.combine(today, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT domain, SUM(duration_s) AS total_s
                FROM website_sessions
                WHERE browser_process=? AND start_time >= ? AND start_time <= ?
                GROUP BY domain
                ORDER BY total_s DESC
                """,
                (browser_process, start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    # ─── Sessions ────────────────────────────────────────────────────────────

    def insert_session(self, session: AppSession) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_sessions
                        (process_name, exe_path, window_title, start_time,
                         end_time, duration_s, category, is_idle, was_closed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.process_name,
                        session.exe_path,
                        session.window_title,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else None,
                        session.duration_s,
                        session.category.value,
                        int(session.is_idle),
                        int(session.was_closed),
                    ),
                )
                return cur.lastrowid or 0

    def update_session_end(
        self,
        session_id: int,
        end_time: datetime,
        duration_s: float,
        was_closed: bool = True,
    ) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE app_sessions
                    SET end_time=?, duration_s=?, was_closed=?
                    WHERE id=?
                    """,
                    (end_time.isoformat(), duration_s, int(was_closed), session_id),
                )

    def update_session_title(self, session_id: int, new_title: str) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE app_sessions SET window_title=? WHERE id=?",
                    (new_title[:512], session_id),
                )

    def delete_session(self, session_id: int) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions WHERE id=?", (session_id,))

    def clear_all_sessions(self) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions")
                return cur.rowcount

    def cleanup_old_sessions(self, retention_days: int) -> int:
        if retention_days < 0:
            return 0
            
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions WHERE start_time < ?", (cutoff,))
                deleted = cur.rowcount
                cur.execute("DELETE FROM event_log WHERE timestamp < ?", (cutoff,))
                deleted += cur.rowcount
                return deleted

    def backup_database(self, dest_path: Path) -> Path:
        with self._write_lock:
            conn = self._connection()
            dest_conn = sqlite3.connect(str(dest_path))
            try:
                conn.backup(dest_conn)
            finally:
                dest_conn.close()
            return dest_path

    REQUIRED_TABLES = frozenset({"app_sessions", "settings", "daily_stats", "app_info"})

    @classmethod
    def validate_backup_file(cls, src_path: Path) -> tuple[bool, str]:
        """
        Validates candidate SQLite database backup file:
        1. Checks file existence and minimum size.
        2. Validates SQLite magic header (first 16 bytes match b'SQLite format 3\\x00').
        3. Executes PRAGMA integrity_check in read-only mode.
        4. Validates required Notch schema tables (app_sessions, settings, daily_stats, app_info).
        Returns (is_valid: bool, reason: str).
        """
        if not src_path.exists():
            return False, f"Backup file does not exist: {src_path.name}"
        if not src_path.is_file():
            return False, f"Selected path is not a file: {src_path.name}"
        if src_path.stat().st_size < 100:
            return False, "Invalid file: File size is too small to be a SQLite database."

        # 1. Header validation
        try:
            with open(src_path, "rb") as f:
                header = f.read(16)
            if header != b"SQLite format 3\x00":
                return False, "Invalid file: File header does not match SQLite 3 format."
        except Exception as exc:
            return False, f"Failed to read file header: {exc}"

        # 2. Integrity and Schema check in read-only mode
        try:
            # as_uri percent-encodes URI delimiters (notably # and ? in a user
            # profile or temp path) so SQLite opens the exact filename.
            uri = f"{src_path.resolve().as_uri()}?mode=ro"
            test_conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            try:
                cur = test_conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                res = cur.fetchall()
                if not res or res[0][0] != "ok":
                    check_msg = res[0][0] if res else "empty result"
                    return False, f"Corrupted database: SQLite integrity check failed ({check_msg})."

                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                existing_tables = {row[0] for row in cur.fetchall()}
                missing = cls.REQUIRED_TABLES - existing_tables
                if missing:
                    return False, f"Incompatible database: Missing required Notch tables ({', '.join(sorted(missing))})."
            finally:
                test_conn.close()
        except Exception as exc:
            return False, f"Database integrity check failed: {exc}"

        return True, "Valid Notch database backup"

    def restore_database(self, src_path: Path) -> Path:
        """
        Safely restores the active database from a validated backup file.
        1. Pre-validates the backup file header, integrity, and schema.
        2. Creates a pre-restore safety snapshot of the active database before any changes.
        3. Restores into active database using SQLite online backup under write lock.
        4. In case of unexpected restore error, automatically rolls back to the pre-restore snapshot.
        """
        is_valid, reason = self.validate_backup_file(src_path)
        if not is_valid:
            logger.warning("[RESTORE_SAFETY] Restore aborted: %s", reason)
            raise ValueError(reason)

        with self._write_lock:
            active_path = Path(self._db_path)
            snapshot_path = active_path.with_name(f"{active_path.name}.pre_restore.bak")

            # Create pre-restore safety snapshot
            try:
                if hasattr(self._local, "conn") and self._local.conn is not None:
                    self._local.conn.commit()
                    snap_conn = sqlite3.connect(str(snapshot_path), timeout=10.0)
                    try:
                        self._local.conn.backup(snap_conn)
                    finally:
                        snap_conn.close()
                elif active_path.exists():
                    import shutil
                    shutil.copy2(active_path, snapshot_path)
                logger.info("[RESTORE_SAFETY] Created pre-restore safety snapshot: %s", snapshot_path)
            except Exception as snap_exc:
                logger.error("[RESTORE_SAFETY] Failed to create pre-restore snapshot: %s", snap_exc)
                raise RuntimeError(f"Could not create pre-restore safety backup: {snap_exc}")

            # Execute online restore
            src_conn = sqlite3.connect(str(src_path), timeout=10.0)
            try:
                conn = self._connection()
                src_conn.backup(conn)
                conn.commit()
                logger.info("[RESTORE_SAFETY] Successfully restored database from: %s", src_path)
            except Exception as restore_exc:
                logger.critical("[RESTORE_SAFETY] Restore failed midway: %s. Rolling back from snapshot.", restore_exc)
                if snapshot_path.exists():
                    try:
                        snap_conn = sqlite3.connect(str(snapshot_path), timeout=10.0)
                        try:
                            conn = self._connection()
                            snap_conn.backup(conn)
                            conn.commit()
                            logger.info("[RESTORE_SAFETY] Successfully rolled back to pre-restore snapshot.")
                        finally:
                            snap_conn.close()
                    except Exception as rb_exc:
                        logger.critical("[RESTORE_SAFETY] Critical failure during rollback: %s", rb_exc)
                raise RuntimeError(f"Database restore failed: {restore_exc}")
            finally:
                src_conn.close()

        # Ensure any newly restored schema additions or migrations are validated
        try:
            self._run_migrations()
        except Exception as mig_exc:
            logger.warning("[RESTORE_SAFETY] Post-restore migrations check: %s", mig_exc)

        return active_path

    def get_open_sessions(self) -> List[AppSession]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM app_sessions WHERE end_time IS NULL ORDER BY start_time"
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_sessions_for_date(self, target_date: date) -> List[AppSession]:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_sessions_for_range(
        self, start_date: date, end_date: date
    ) -> List[AppSession]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_top_apps_for_range(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT process_name, category,
                       SUM(duration_s) AS total_s,
                       COUNT(*) AS sessions
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY process_name
                ORDER BY total_s DESC
                LIMIT ?
                """,
                (start, end, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_category_breakdown_for_range(
        self, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT LOWER(category) AS raw_category, SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY LOWER(category)
                ORDER BY total_s DESC
                """,
                (start, end),
            )
            
            # Format back to title case to maintain expected format
            return [{"category": row["raw_category"].title() if row["raw_category"] else "Other", "total_s": row["total_s"]} for row in cur.fetchall()]

    def get_hourly_breakdown_for_date(self, target_date: date) -> List[dict]:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%H', start_time) AS hour,
                       SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY hour
                ORDER BY hour
                """,
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_daily_totals_for_range(
        self, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day,
                       SUM(CASE WHEN is_idle=0 THEN duration_s ELSE 0 END) AS active_s,
                       SUM(CASE WHEN is_idle=1 THEN duration_s ELSE 0 END) AS idle_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND duration_s > 0
                GROUP BY day
                ORDER BY day
                """,
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def search_sessions(
        self,
        query: str,
        category: Optional[AppCategory],
        start_date: Optional[date],
        end_date: Optional[date],
        limit: int = 200,
    ) -> List[AppSession]:
        conditions = ["duration_s > 0"]
        params: list = []

        if query:
            conditions.append("(process_name LIKE ? OR window_title LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("category = ?")
            params.append(category.value)
        if start_date:
            conditions.append("start_time >= ?")
            params.append(datetime.combine(start_date, datetime.min.time()).isoformat())
        if end_date:
            conditions.append("start_time <= ?")
            params.append(datetime.combine(end_date, datetime.max.time()).isoformat())

        sql = (
            f"SELECT * FROM app_sessions WHERE {' AND '.join(conditions)} "
            f"ORDER BY start_time DESC LIMIT ?"
        )
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_longest_session_for_range(
        self, start_date: date, end_date: date
    ) -> Optional[AppSession]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle=0 AND duration_s > 0
                ORDER BY duration_s DESC LIMIT 1
                """,
                (start, end),
            )
            row = cur.fetchone()
            return self._row_to_session(row) if row else None

    def get_total_screen_time_for_range(
        self, start_date: date, end_date: date
    ) -> float:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(duration_s), 0) AS total
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (start, end),
            )
            row = cur.fetchone()
            return float(row["total"]) if row else 0.0

    def get_app_usage_for_range(
        self, process_name: str, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day,
                       SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ?
                  AND is_idle=0 AND duration_s > 0
                GROUP BY day ORDER BY day
                """,
                (process_name, start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def export_sessions_csv_data(
        self, start_date: date, end_date: date
    ) -> List[tuple]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT process_name, exe_path, window_title, start_time, end_time,
                       duration_s, category, is_idle
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ? AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return cur.fetchall()

    # ─── App Info ─────────────────────────────────────────────────────────────

    def upsert_app_info(self, info: AppInfo) -> None:
        now = info.last_seen or datetime.now()
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_info
                        (process_name, display_name, category, exe_path, icon_path,
                         first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(process_name) DO UPDATE SET
                        display_name = excluded.display_name,
                        exe_path = COALESCE(NULLIF(excluded.exe_path,''), app_info.exe_path),
                        icon_path = COALESCE(excluded.icon_path, app_info.icon_path),
                        last_seen = excluded.last_seen
                    """,
                    (
                        info.process_name,
                        info.display_name,
                        info.category.value,
                        info.exe_path,
                        info.icon_path,
                        info.first_seen.isoformat(),
                        now.isoformat(),
                    ),
                )

    def get_app_info(self, process_name: str) -> Optional[AppInfo]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM app_info WHERE process_name=?", (process_name,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return self._row_to_app_info(row, cols)

    def update_app_category(self, process_name: str, category: AppCategory) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE app_info SET category=? WHERE process_name=?",
                    (category.value, process_name),
                )
                cur.execute(
                    "UPDATE app_sessions SET category=? WHERE process_name=?",
                    (category.value, process_name),
                )

    # ─── Event Log ────────────────────────────────────────────────────────────

    def log_event(self, event_type: str, detail: str = "") -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO event_log (timestamp, event_type, detail) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), event_type, detail),
                )

    def get_recent_events(self, limit: int = 100) -> List[EventLogEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                EventLogEntry(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    event_type=row["event_type"],
                    detail=row["detail"],
                )
                for row in cur.fetchall()
            ]

    # ─── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key: str) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )

    def get_all_settings(self) -> dict[str, str]:
        with self._cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    # ─── Aggregation Methods for Digital Wellbeing Views ─────────────────────

    def get_aggregated_apps_for_range(
        self,
        start_date: date,
        end_date: date,
        query: str = "",
        category: Optional[AppCategory] = None,
        limit: int = 200,
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()

        conditions = ["start_time >= ?", "start_time <= ?", "is_idle = 0", "duration_s > 0"]
        params: list[object] = [start, end]

        if query:
            conditions.append("(process_name LIKE ? OR window_title LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q])

        if category:
            conditions.append("category = ?")
            params.append(category.value)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT process_name, category, exe_path,
                   SUM(duration_s) AS total_s,
                   COUNT(*) AS open_count,
                   MAX(duration_s) AS max_session_s,
                   AVG(duration_s) AS avg_session_s
            FROM app_sessions
            WHERE {where_clause}
            GROUP BY process_name
            ORDER BY total_s DESC
            LIMIT ?
        """
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "process_name": r["process_name"],
                    "category": r["category"],
                    "exe_path": r["exe_path"] if "exe_path" in r.keys() else "",
                    "total_s": r["total_s"],
                    "open_count": r["open_count"],
                    "max_session_s": r["max_session_s"],
                    "avg_session_s": r["avg_session_s"],
                })
            return results

    def get_app_detail_stats(self, process_name: str) -> dict:
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time()).isoformat()
        today_end = datetime.combine(today, datetime.max.time()).isoformat()
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time()).isoformat()
        yesterday_end = datetime.combine(yesterday, datetime.max.time()).isoformat()

        week_start_date = today - timedelta(days=today.weekday())
        week_start = datetime.combine(week_start_date, datetime.min.time()).isoformat()

        month_start_date = today.replace(day=1)
        month_start = datetime.combine(month_start_date, datetime.min.time()).isoformat()

        with self._cursor() as cur:
            # Today stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, today_start, today_end),
            )
            r_today = cur.fetchone()
            today_s = r_today["total_s"] or 0.0 if r_today else 0.0
            today_opens = r_today["open_count"] or 0 if r_today else 0

            # Yesterday stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, yesterday_start, yesterday_end),
            )
            r_yesterday = cur.fetchone()
            yesterday_s = r_yesterday["total_s"] or 0.0 if r_yesterday else 0.0
            yesterday_opens = r_yesterday["open_count"] or 0 if r_yesterday else 0

            # Week stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, week_start, today_end),
            )
            r_week = cur.fetchone()
            week_s = r_week["total_s"] or 0.0 if r_week else 0.0
            week_opens = r_week["open_count"] or 0 if r_week else 0
            weekly_average_s = week_s / (today.weekday() + 1)

            # Month stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count, MAX(duration_s) AS max_s, AVG(duration_s) AS avg_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, month_start, today_end),
            )
            r_month = cur.fetchone()
            month_s = r_month["total_s"] or 0.0 if r_month else 0.0
            month_opens = r_month["open_count"] or 0 if r_month else 0
            max_session_s = r_month["max_s"] or 0.0 if r_month else 0.0
            avg_session_s = r_month["avg_s"] or 0.0 if r_month else 0.0

            # Past 7 days daily breakdown chart for this app
            start_7 = today - timedelta(days=6)
            s_7 = datetime.combine(start_7, datetime.min.time()).isoformat()
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day, SUM(duration_s) AS daily_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                GROUP BY day
                """,
                (process_name, s_7, today_end),
            )
            daily_rows = {r["day"]: r["daily_s"] for r in cur.fetchall()}

            chart_data = []
            curr = start_7
            while curr <= today:
                k = curr.strftime("%Y-%m-%d")
                chart_data.append({"day": k, "duration_s": daily_rows.get(k, 0.0)})
                curr += timedelta(days=1)

            # Hourly distribution for today's app detail chart
            cur.execute(
                """
                SELECT CAST(strftime('%H', start_time) AS INTEGER) AS hour,
                       SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ?
                  AND is_idle=0 AND duration_s > 0
                GROUP BY hour
                """,
                (process_name, today_start, today_end),
            )
            hourly_totals = {hour: 0.0 for hour in range(24)}
            for row in cur.fetchall():
                hourly_totals[int(row["hour"])] = float(row["total_s"] or 0.0)
            hourly_chart_data = [
                {"hour": hour, "total_s": hourly_totals[hour]}
                for hour in range(24)
            ]

            return {
                "process_name": process_name,
                "today_s": today_s,
                "today_opens": today_opens,
                "yesterday_s": yesterday_s,
                "yesterday_opens": yesterday_opens,
                "week_s": week_s,
                "week_opens": week_opens,
                "weekly_average_s": weekly_average_s,
                "month_s": month_s,
                "month_opens": month_opens,
                "longest_session_s": max_session_s,
                "avg_session_s": avg_session_s,
                "daily_chart_data": chart_data,
                "hourly_chart_data": hourly_chart_data,
            }

    # ─── Daily Stats & Snapshots ──────────────────────────────────────────────

    def upsert_daily_stat(self, stat: DailyStat) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_stats
                        (date, total_screen_time_s, active_time_s, idle_time_s,
                         top_app, session_count, unlock_count, category_usage_json,
                         app_usage_json, timeline_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        total_screen_time_s = excluded.total_screen_time_s,
                        active_time_s = excluded.active_time_s,
                        idle_time_s = excluded.idle_time_s,
                        top_app = excluded.top_app,
                        session_count = excluded.session_count,
                        unlock_count = excluded.unlock_count,
                        category_usage_json = excluded.category_usage_json,
                        app_usage_json = excluded.app_usage_json,
                        timeline_json = excluded.timeline_json
                    """,
                    (
                        stat.date.isoformat(),
                        stat.total_screen_time_s,
                        stat.active_time_s,
                        stat.idle_time_s,
                        stat.top_app,
                        stat.session_count,
                        stat.unlock_count,
                        stat.category_usage_json,
                        stat.app_usage_json,
                        stat.timeline_json,
                    ),
                )

    def get_daily_stat(self, target_date: date) -> Optional[DailyStat]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM daily_stats WHERE date=?", (target_date.isoformat(),))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_daily_stat(row)

    def get_all_daily_stats(self, order_desc: bool = True) -> List[DailyStat]:
        with self._cursor() as cur:
            order = "DESC" if order_desc else "ASC"
            cur.execute(f"SELECT * FROM daily_stats ORDER BY date {order}")
            return [self._row_to_daily_stat(row) for row in cur.fetchall()]

    def get_unlock_count_for_date(self, target_date: date) -> int:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as unlocks
                FROM event_log
                WHERE event_type = 'unlock' AND timestamp >= ? AND timestamp <= ?
                """,
                (start, end),
            )
            row = cur.fetchone()
            return row["unlocks"] if row else 0

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> AppSession:
        keys = row.keys()
        return AppSession(
            id=row["id"],
            process_name=row["process_name"],
            exe_path=row["exe_path"] if "exe_path" in keys else "",
            window_title=row["window_title"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            duration_s=row["duration_s"],
            category=AppCategory(row["category"]),
            is_idle=bool(row["is_idle"]),
            was_closed=bool(row["was_closed"]) if "was_closed" in keys else False,
        )

    @staticmethod
    def _row_to_app_info(row: sqlite3.Row, cols: list[str]) -> AppInfo:
        return AppInfo(
            process_name=row["process_name"],
            display_name=row["display_name"],
            category=AppCategory(row["category"]),
            exe_path=row["exe_path"] if "exe_path" in cols else "",
            icon_path=row["icon_path"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
        )

    @staticmethod
    def _row_to_daily_stat(row: sqlite3.Row) -> DailyStat:
        keys = row.keys()
        return DailyStat(
            date=date.fromisoformat(row["date"]),
            total_screen_time_s=row["total_screen_time_s"],
            active_time_s=row["active_time_s"],
            idle_time_s=row["idle_time_s"],
            top_app=row["top_app"],
            session_count=row["session_count"],
            unlock_count=row["unlock_count"] if "unlock_count" in keys else 0,
            category_usage_json=row["category_usage_json"] if "category_usage_json" in keys else "{}",
            app_usage_json=row["app_usage_json"] if "app_usage_json" in keys else "[]",
            timeline_json=row["timeline_json"] if "timeline_json" in keys else "[]",
        )

    def close(self) -> None:
        """Close the SQLite connection for the current thread if open.
        Repository uses thread-local connections; calling close() from the current
        thread will close that thread's connection.
        """
        try:
            if hasattr(self._local, "conn") and self._local.conn:
                try:
                    self._local.conn.close()
                    logger.info("Closed repository DB connection for thread %s", threading.current_thread().name)
                except Exception as exc:
                    logger.warning("Error closing DB connection: %s", exc)
                finally:
                    try:
                        self._local.conn = None
                    except Exception:
                        pass
        except Exception:
            logger.exception("Unexpected error while closing DB connection")

    # Backwards-compatible alias
    def close_thread_connection(self) -> None:
        self.close()

    def _cleanup_test_data(self) -> None:
        if Repository._db_path_override is not None:
            return
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM app_sessions WHERE "
                    "(process_name = 'chrome.exe' AND window_title = 'GitHub - Test') OR "
                    "(process_name = 'test_tracker.exe') OR "
                    "(process_name = 'chrome.exe' AND window_title = 'Tracker Test Window')"
                )
        except Exception as e:
            logger.error("Failed to clean up test database data: %s", e)

    # ─── App Locker ───────────────────────────────────────────────────────────

    def get_locked_apps(self) -> List[dict]:
        """Return all locked apps as a list of dicts with keys:
        process_name, display_name, exe_path, icon_path, added_at."""
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT process_name, display_name, exe_path, icon_path, added_at "
                    "FROM app_locker_apps ORDER BY display_name COLLATE NOCASE"
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("get_locked_apps failed: %s", e)
            return []

    def add_locked_app(self, process_name: str, display_name: str,
                       exe_path: str = "", icon_path: Optional[str] = None) -> bool:
        """Insert or replace a locked app entry. Returns True on success."""
        try:
            added_at = datetime.now(timezone.utc).isoformat()
            with self._cursor() as cur:
                cur.execute(
                    "INSERT OR REPLACE INTO app_locker_apps "
                    "(process_name, display_name, exe_path, icon_path, added_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (process_name.lower(), display_name, exe_path, icon_path, added_at),
                )
            return True
        except Exception as e:
            logger.error("add_locked_app failed for %s: %s", process_name, e)
            return False

    def remove_locked_app(self, process_name: str) -> bool:
        """Remove a locked app by process name. Returns True on success."""
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM app_locker_apps WHERE process_name = ?",
                    (process_name.lower(),),
                )
            return True
        except Exception as e:
            logger.error("remove_locked_app failed for %s: %s", process_name, e)
            return False

    def clear_locked_apps(self) -> bool:
        """Remove ALL locked app entries. Returns True on success."""
        try:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_locker_apps")
            return True
        except Exception as e:
            logger.error("clear_locked_apps failed: %s", e)
            return False

    # ─── Focus Schedules (v3.6.3) ─────────────────────────────────────────────

    def save_focus_schedule(self, schedule: FocusSchedule) -> int:
        """Insert or update a focus schedule. Returns schedule id."""
        created_at = (schedule.created_at or datetime.now(timezone.utc)).isoformat()
        with self._write_lock:
            with self._cursor() as cur:
                if schedule.id is None:
                    cur.execute(
                        """
                        INSERT INTO focus_schedules
                            (name, days_of_week, start_time, end_time, mode, strict_mode, is_enabled, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            schedule.name,
                            schedule.days_of_week,
                            schedule.start_time,
                            schedule.end_time,
                            schedule.mode,
                            int(schedule.strict_mode),
                            int(schedule.is_enabled),
                            created_at,
                        ),
                    )
                    schedule.id = cur.lastrowid
                    return cur.lastrowid or 0
                else:
                    cur.execute(
                        """
                        UPDATE focus_schedules SET
                            name = ?,
                            days_of_week = ?,
                            start_time = ?,
                            end_time = ?,
                            mode = ?,
                            strict_mode = ?,
                            is_enabled = ?
                        WHERE id = ?
                        """,
                        (
                            schedule.name,
                            schedule.days_of_week,
                            schedule.start_time,
                            schedule.end_time,
                            schedule.mode,
                            int(schedule.strict_mode),
                            int(schedule.is_enabled),
                            schedule.id,
                        ),
                    )
                    return schedule.id

    def get_focus_schedules(self, only_enabled: bool = False) -> List[FocusSchedule]:
        """Return all or only enabled focus schedules ordered by start_time."""
        sql = "SELECT * FROM focus_schedules"
        if only_enabled:
            sql += " WHERE is_enabled = 1"
        sql += " ORDER BY start_time ASC"

        with self._cursor() as cur:
            cur.execute(sql)
            return [self._row_to_focus_schedule(row) for row in cur.fetchall()]

    def get_focus_schedule(self, schedule_id: int) -> Optional[FocusSchedule]:
        """Fetch a single focus schedule by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM focus_schedules WHERE id = ?", (schedule_id,))
            row = cur.fetchone()
            return self._row_to_focus_schedule(row) if row else None

    def delete_focus_schedule(self, schedule_id: int) -> bool:
        """Delete a focus schedule by ID. Returns True if deleted."""
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM focus_schedules WHERE id = ?", (schedule_id,))
                return cur.rowcount > 0

    def set_focus_schedule_enabled(self, schedule_id: int, is_enabled: bool) -> bool:
        """Toggle or set the enabled status of a focus schedule."""
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE focus_schedules SET is_enabled = ? WHERE id = ?",
                    (int(is_enabled), schedule_id),
                )
                return cur.rowcount > 0

    @staticmethod
    def _row_to_focus_schedule(row: sqlite3.Row) -> FocusSchedule:
        created_raw = row["created_at"]
        try:
            created_dt = datetime.fromisoformat(created_raw)
        except Exception:
            created_dt = datetime.now(timezone.utc)

        return FocusSchedule(
            id=row["id"],
            name=row["name"],
            days_of_week=row["days_of_week"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            mode=row["mode"],
            strict_mode=bool(row["strict_mode"]),
            is_enabled=bool(row["is_enabled"]),
            created_at=created_dt,
        )

    # ─── Deep Work Sessions (v3.6.3) ──────────────────────────────────────────

    def save_study_subject(self, subject: StudySubject) -> int:
        """Insert or update a subject without rewriting historical sessions."""
        name = subject.name.strip()
        if not name:
            raise ValueError("A study subject name is required.")
        if subject.daily_target_minutes < 0:
            raise ValueError("A daily study target cannot be negative.")
        if subject.weekly_target_minutes < 0:
            raise ValueError("A weekly study target cannot be negative.")

        with self._write_lock:
            with self._cursor() as cur:
                if subject.id is None:
                    cur.execute(
                        """
                        INSERT INTO study_subjects
                            (name, color, daily_target_minutes, weekly_target_minutes, is_active)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            name, subject.color, subject.daily_target_minutes,
                            subject.weekly_target_minutes, int(subject.is_active),
                        ),
                    )
                    subject.id = cur.lastrowid
                    subject.name = name
                    return cur.lastrowid or 0

                cur.execute(
                    """
                    UPDATE study_subjects
                    SET name=?, color=?, daily_target_minutes=?, weekly_target_minutes=?, is_active=?
                    WHERE id=?
                    """,
                    (
                        name, subject.color, subject.daily_target_minutes,
                        subject.weekly_target_minutes, int(subject.is_active), subject.id,
                    ),
                )
                subject.name = name
                return subject.id

    def get_study_subjects(self, active_only: bool = True) -> List[StudySubject]:
        sql = "SELECT * FROM study_subjects"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY name COLLATE NOCASE ASC"
        with self._cursor() as cur:
            cur.execute(sql)
            return [self._row_to_study_subject(row) for row in cur.fetchall()]

    def get_study_subject(self, subject_id: int) -> Optional[StudySubject]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM study_subjects WHERE id = ?", (subject_id,))
            row = cur.fetchone()
            return self._row_to_study_subject(row) if row else None

    def set_study_subject_active(self, subject_id: int, is_active: bool) -> bool:
        """Archive or reactivate a subject, preserving all linked study sessions."""
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE study_subjects SET is_active = ? WHERE id = ?",
                    (int(is_active), subject_id),
                )
                return cur.rowcount > 0

    @staticmethod
    def _row_to_study_subject(row: sqlite3.Row) -> StudySubject:
        created_at = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None
        return StudySubject(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            daily_target_minutes=row["daily_target_minutes"],
            weekly_target_minutes=row["weekly_target_minutes"] if "weekly_target_minutes" in row.keys() else 0,
            is_active=bool(row["is_active"]),
            created_at=created_at,
        )

    def get_student_study_sessions_for_range(
        self,
        start_date: date,
        end_date: date,
        subject_id: Optional[int] = None,
    ) -> List[DeepWorkSession]:
        """Return only sessions explicitly started in Student Workspace."""
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        sql = """
            SELECT * FROM deep_work_sessions
            WHERE study_mode IS NOT NULL AND started_at >= ? AND started_at <= ?
        """
        params: list = [start, end]
        if subject_id is not None:
            sql += " AND subject_id = ?"
            params.append(subject_id)
        sql += " ORDER BY started_at DESC"
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_deep_work_session(row) for row in cur.fetchall()]

    def get_study_subject_stats(
        self, start_date: date, end_date: date, active_only: bool = True
    ) -> List[dict]:
        """Aggregate explicit student-study time by subject."""
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        subject_filter = "WHERE s.is_active = 1" if active_only else ""
        with self._cursor() as cur:
            cur.execute(
                f"""
                SELECT s.id, s.name, s.color, s.daily_target_minutes, s.weekly_target_minutes,
                       COALESCE(SUM(d.actual_work_s), 0) AS actual_work_s,
                       COUNT(d.id) AS session_count,
                       COALESCE(SUM(CASE WHEN d.status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_count
                FROM study_subjects s
                LEFT JOIN deep_work_sessions d
                    ON d.subject_id = s.id
                    AND d.study_mode IS NOT NULL
                    AND d.started_at >= ? AND d.started_at <= ?
                {subject_filter}
                GROUP BY s.id
                ORDER BY actual_work_s DESC, s.name COLLATE NOCASE ASC
                """,
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def save_study_block(self, block: StudyBlock) -> int:
        """Insert or update a recurring weekly study block."""
        name = block.name.strip()
        if not 0 <= block.weekday <= 6:
            raise ValueError("Choose a weekday for this study block.")
        try:
            datetime.strptime(block.start_time, "%H:%M")
        except (TypeError, ValueError) as exc:
            raise ValueError("Study block start time must use HH:MM format.") from exc
        if not 1 <= block.work_minutes <= 180:
            raise ValueError("Work intervals must be between 1 and 180 minutes.")
        if not 1 <= block.break_minutes <= 30:
            raise ValueError("Breaks must be between 1 and 30 minutes.")
        if not 1 <= block.intervals <= 8:
            raise ValueError("Choose between 1 and 8 work intervals.")

        values = (
            name, block.weekday, block.start_time, block.work_minutes,
            block.break_minutes, block.intervals, block.subject_id, int(block.is_enabled),
        )
        with self._write_lock:
            with self._cursor() as cur:
                if block.id is None:
                    cur.execute(
                        """
                        INSERT INTO study_blocks
                            (name, weekday, start_time, work_minutes, break_minutes,
                             intervals, subject_id, is_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    block.id = cur.lastrowid
                    block.name = name
                    return cur.lastrowid or 0
                cur.execute(
                    """
                    UPDATE study_blocks
                    SET name=?, weekday=?, start_time=?, work_minutes=?, break_minutes=?,
                        intervals=?, subject_id=?, is_enabled=?
                    WHERE id=?
                    """,
                    (*values, block.id),
                )
                if cur.rowcount == 0:
                    raise ValueError("This study block no longer exists.")
                block.name = name
                return block.id

    def get_study_blocks(
        self, enabled_only: bool = True, on_date: Optional[date] = None
    ) -> List[StudyBlock]:
        sql = """
            SELECT b.*, CASE WHEN c.id IS NULL THEN 0 ELSE 1 END AS completed_for_date
            FROM study_blocks b
            LEFT JOIN study_block_completions c
                ON c.block_id = b.id AND c.occurrence_date = ?
        """
        params: list = [on_date.isoformat() if on_date else ""]
        if enabled_only:
            sql += " WHERE b.is_enabled = 1"
        sql += " ORDER BY b.weekday ASC, b.start_time ASC, b.id ASC"
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_study_block(row) for row in cur.fetchall()]

    def set_study_block_completed(
        self,
        block_id: int,
        occurrence_date: date,
        completed: bool,
        session_id: Optional[int] = None,
    ) -> bool:
        """Set completion for one occurrence of a recurring timetable block."""
        with self._write_lock:
            with self._cursor() as cur:
                if completed:
                    cur.execute(
                        """
                        INSERT INTO study_block_completions (block_id, occurrence_date, session_id)
                        VALUES (?, ?, ?)
                        ON CONFLICT(block_id, occurrence_date) DO UPDATE SET
                            session_id=COALESCE(excluded.session_id, study_block_completions.session_id),
                            completed_at=datetime('now', 'localtime')
                        """,
                        (block_id, occurrence_date.isoformat(), session_id),
                    )
                    return cur.rowcount > 0
                cur.execute(
                    "DELETE FROM study_block_completions WHERE block_id=? AND occurrence_date=?",
                    (block_id, occurrence_date.isoformat()),
                )
                return cur.rowcount > 0

    def delete_study_block(self, block_id: int) -> bool:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM study_blocks WHERE id=?", (block_id,))
                return cur.rowcount > 0

    @staticmethod
    def _row_to_study_block(row: sqlite3.Row) -> StudyBlock:
        return StudyBlock(
            id=row["id"],
            name=row["name"],
            weekday=row["weekday"],
            start_time=row["start_time"],
            work_minutes=row["work_minutes"],
            break_minutes=row["break_minutes"],
            intervals=row["intervals"],
            subject_id=row["subject_id"],
            is_enabled=bool(row["is_enabled"]),
            completed_for_date=bool(row["completed_for_date"]),
        )

    @staticmethod
    def _local_iso(value: datetime) -> str:
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value.isoformat(timespec="seconds")

    def save_study_planner_task(self, task: StudyPlannerTask) -> int:
        """Insert or update an assignment, exam, or revision task."""
        title = task.title.strip()
        if not title:
            raise ValueError("Enter a title for this study task.")
        if task.task_type not in {"assignment", "exam", "revision"}:
            raise ValueError("Choose assignment, exam, or revision as the task type.")
        due_value = task.due_at.astimezone().replace(tzinfo=None) if task.due_at.tzinfo else task.due_at
        reminder_value = (
            task.reminder_at.astimezone().replace(tzinfo=None)
            if task.reminder_at and task.reminder_at.tzinfo
            else task.reminder_at
        )
        due_at = self._local_iso(due_value)
        reminder_at = self._local_iso(reminder_value) if reminder_value else None
        if reminder_value and reminder_value > due_value:
            raise ValueError("A reminder must be set for the due time or earlier.")
        values = (title, task.task_type, due_at, task.subject_id, reminder_at, task.notes.strip())

        with self._write_lock:
            with self._cursor() as cur:
                if task.id is None:
                    cur.execute(
                        """
                        INSERT INTO study_planner_tasks
                            (title, task_type, due_at, subject_id, reminder_at, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    task.id = cur.lastrowid
                    task.title = title
                    return cur.lastrowid or 0

                cur.execute(
                    "SELECT reminder_at FROM study_planner_tasks WHERE id=?", (task.id,)
                )
                existing = cur.fetchone()
                if existing is None:
                    raise ValueError("This study task no longer exists.")
                reminder_changed = existing["reminder_at"] != reminder_at
                cur.execute(
                    """
                    UPDATE study_planner_tasks
                    SET title=?, task_type=?, due_at=?, subject_id=?, reminder_at=?, notes=?,
                        reminder_sent_at=CASE WHEN ? THEN NULL ELSE reminder_sent_at END
                    WHERE id=?
                    """,
                    (*values, int(reminder_changed), task.id),
                )
                task.title = title
                return task.id

    def get_study_planner_tasks(self, include_completed: bool = True) -> List[StudyPlannerTask]:
        sql = "SELECT * FROM study_planner_tasks"
        if not include_completed:
            sql += " WHERE is_completed = 0"
        sql += " ORDER BY due_at ASC, id ASC"
        with self._cursor() as cur:
            cur.execute(sql)
            return [self._row_to_study_planner_task(row) for row in cur.fetchall()]

    def save_study_exam_topic(self, topic: StudyExamTopic) -> int:
        title = topic.title.strip()
        if not title:
            raise ValueError("Enter a topic or chapter name.")
        if topic.status not in {"not_started", "in_progress", "revised"}:
            raise ValueError("Choose not started, in progress, or revised.")
        target_minutes = int(topic.revision_target_minutes)
        if target_minutes < 0:
            raise ValueError("Revision target cannot be negative.")

        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT task_type FROM study_planner_tasks WHERE id=?",
                    (topic.exam_task_id,),
                )
                exam = cur.fetchone()
                if exam is None or exam["task_type"] != "exam":
                    raise ValueError("Choose an existing exam before adding revision topics.")

                if topic.id is None:
                    cur.execute(
                        """
                        INSERT INTO study_exam_topics
                            (exam_task_id, title, status, revision_target_minutes)
                        VALUES (?, ?, ?, ?)
                        """,
                        (topic.exam_task_id, title, topic.status, target_minutes),
                    )
                    topic.id = cur.lastrowid
                    topic.title = title
                    return cur.lastrowid or 0

                cur.execute(
                    """
                    UPDATE study_exam_topics
                    SET title=?, status=?, revision_target_minutes=?,
                        updated_at=datetime('now', 'localtime')
                    WHERE id=? AND exam_task_id=?
                    """,
                    (title, topic.status, target_minutes, topic.id, topic.exam_task_id),
                )
                if cur.rowcount == 0:
                    raise ValueError("This exam topic no longer exists.")
                topic.title = title
                return topic.id

    def get_study_exam_topics(self, exam_task_id: int) -> List[StudyExamTopic]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM study_exam_topics WHERE exam_task_id=? ORDER BY id ASC",
                (exam_task_id,),
            )
            return [self._row_to_study_exam_topic(row) for row in cur.fetchall()]

    def delete_study_exam_topic(self, topic_id: int) -> bool:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM study_exam_topics WHERE id=?", (topic_id,))
                return cur.rowcount > 0

    def set_study_planner_task_completed(self, task_id: int, completed: bool) -> bool:
        now = datetime.now().isoformat(timespec="seconds") if completed else None
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE study_planner_tasks
                    SET is_completed=?, completed_at=?
                    WHERE id=?
                    """,
                    (int(completed), now, task_id),
                )
                return cur.rowcount > 0

    def delete_study_planner_task(self, task_id: int) -> bool:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM study_planner_tasks WHERE id=?", (task_id,))
                return cur.rowcount > 0

    def claim_due_study_reminders(
        self, now: Optional[datetime] = None
    ) -> List[StudyPlannerTask]:
        """Atomically mark due reminders as sent before returning them to the UI."""
        now = now or datetime.now()
        now_iso = self._local_iso(now)
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM study_planner_tasks
                    WHERE is_completed=0 AND reminder_at IS NOT NULL
                      AND reminder_sent_at IS NULL AND reminder_at <= ?
                    ORDER BY reminder_at ASC, id ASC
                    """,
                    (now_iso,),
                )
                rows = cur.fetchall()
                if rows:
                    cur.executemany(
                        "UPDATE study_planner_tasks SET reminder_sent_at=? WHERE id=? AND reminder_sent_at IS NULL",
                        [(now_iso, row["id"]) for row in rows],
                    )
                return [self._row_to_study_planner_task(row) for row in rows]

    @staticmethod
    def _row_to_study_planner_task(row: sqlite3.Row) -> StudyPlannerTask:
        return StudyPlannerTask(
            id=row["id"],
            title=row["title"],
            task_type=row["task_type"],
            due_at=datetime.fromisoformat(row["due_at"]),
            subject_id=row["subject_id"],
            reminder_at=datetime.fromisoformat(row["reminder_at"]) if row["reminder_at"] else None,
            reminder_sent_at=datetime.fromisoformat(row["reminder_sent_at"]) if row["reminder_sent_at"] else None,
            is_completed=bool(row["is_completed"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            notes=row["notes"],
        )

    @staticmethod
    def _row_to_study_exam_topic(row: sqlite3.Row) -> StudyExamTopic:
        return StudyExamTopic(
            id=row["id"],
            exam_task_id=row["exam_task_id"],
            title=row["title"],
            status=row["status"],
            revision_target_minutes=row["revision_target_minutes"],
        )

    def record_deep_work_session(self, session: DeepWorkSession) -> int:
        """Record a completed, early-finished, or cancelled deep work session."""
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO deep_work_sessions
                        (goal, preset, target_work_s, actual_work_s, actual_break_s,
                         intervals_completed, total_intervals, status, started_at, ended_at, notes,
                         subject_id, study_mode, distractions_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.goal,
                        session.preset,
                        session.target_work_s,
                        session.actual_work_s,
                        session.actual_break_s,
                        session.intervals_completed,
                        session.total_intervals,
                        session.status,
                        session.started_at.isoformat(),
                        session.ended_at.isoformat(),
                        session.notes,
                        session.subject_id,
                        session.study_mode,
                        session.distractions_json,
                    ),
                )
                session.id = cur.lastrowid
                return cur.lastrowid or 0

    def get_deep_work_sessions_for_range(
        self, start_date: date, end_date: date
    ) -> List[DeepWorkSession]:
        """Fetch deep work sessions started within the given date range (inclusive)."""
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM deep_work_sessions
                WHERE started_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
                """,
                (start, end),
            )
            return [self._row_to_deep_work_session(row) for row in cur.fetchall()]

    def get_deep_work_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> dict:
        """Compute aggregated statistics for deep work sessions in range (or all-time)."""
        conditions = []
        params: list = []
        if start_date:
            conditions.append("started_at >= ?")
            params.append(datetime.combine(start_date, datetime.min.time()).isoformat())
        if end_date:
            conditions.append("started_at <= ?")
            params.append(datetime.combine(end_date, datetime.max.time()).isoformat())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                COUNT(*) AS total_sessions,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_sessions,
                COALESCE(SUM(actual_work_s), 0) AS total_work_s,
                COALESCE(SUM(actual_break_s), 0) AS total_break_s,
                COALESCE(AVG(actual_work_s), 0) AS avg_work_s,
                COALESCE(SUM(intervals_completed), 0) AS total_intervals
            FROM deep_work_sessions
            {where_clause}
        """
        with self._cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            total = int(row["total_sessions"] or 0) if row else 0
            completed = int(row["completed_sessions"] or 0) if row else 0
            return {
                "total_sessions": total,
                "completed_sessions": completed,
                "total_work_s": float(row["total_work_s"] or 0.0) if row else 0.0,
                "total_break_s": float(row["total_break_s"] or 0.0) if row else 0.0,
                "avg_work_s": float(row["avg_work_s"] or 0.0) if row else 0.0,
                "total_intervals": int(row["total_intervals"] or 0) if row else 0,
                "completion_rate": (completed / total * 100.0) if total > 0 else 0.0,
            }

    @staticmethod
    def _row_to_deep_work_session(row: sqlite3.Row) -> DeepWorkSession:
        return DeepWorkSession(
            id=row["id"],
            goal=row["goal"],
            preset=row["preset"],
            target_work_s=row["target_work_s"],
            actual_work_s=row["actual_work_s"],
            actual_break_s=row["actual_break_s"],
            intervals_completed=row["intervals_completed"],
            total_intervals=row["total_intervals"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]),
            notes=row["notes"] if "notes" in row.keys() else "",
            subject_id=row["subject_id"] if "subject_id" in row.keys() else None,
            study_mode=row["study_mode"] if "study_mode" in row.keys() else None,
            distractions_json=row["distractions_json"] if "distractions_json" in row.keys() else "[]",
        )

    # ─── Screen-Time Budgets ───────────────────────────────────────────────────

    def save_budget(self, budget: ScreenTimeBudget) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                if budget.id is not None:
                    cur.execute(
                        """
                        UPDATE screen_time_budgets
                        SET target_type=?, target_name=?, daily_budget_seconds=?, is_enabled=?, enforce_lock=?
                        WHERE id=?
                        """,
                        (
                            budget.target_type,
                            budget.target_name,
                            budget.daily_budget_seconds,
                            int(budget.is_enabled),
                            int(budget.enforce_lock),
                            budget.id,
                        ),
                    )
                    return budget.id
                else:
                    cur.execute(
                        """
                        INSERT INTO screen_time_budgets
                        (target_type, target_name, daily_budget_seconds, is_enabled, enforce_lock)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            budget.target_type,
                            budget.target_name,
                            budget.daily_budget_seconds,
                            int(budget.is_enabled),
                            int(budget.enforce_lock),
                        ),
                    )
                    budget.id = cur.lastrowid or 0
                    return budget.id

    def get_budgets(self) -> List[ScreenTimeBudget]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM screen_time_budgets ORDER BY id ASC")
            return [self._row_to_budget(row) for row in cur.fetchall()]

    def get_active_budgets(self) -> List[ScreenTimeBudget]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM screen_time_budgets WHERE is_enabled = 1 ORDER BY id ASC")
            return [self._row_to_budget(row) for row in cur.fetchall()]

    def get_budget(self, budget_id: int) -> Optional[ScreenTimeBudget]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM screen_time_budgets WHERE id = ?", (budget_id,))
            row = cur.fetchone()
            return self._row_to_budget(row) if row else None

    def delete_budget(self, budget_id: int) -> bool:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM screen_time_budgets WHERE id = ?", (budget_id,))
                return cur.rowcount > 0

    def set_budget_enabled(self, budget_id: int, enabled: bool) -> bool:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE screen_time_budgets SET is_enabled = ? WHERE id = ?",
                    (int(enabled), budget_id),
                )
                return cur.rowcount > 0

    def get_budget_usage_today(
        self, target_type: str, target_name: str, target_date: Optional[date] = None
    ) -> float:
        """Calculate total active seconds used for the given budget target today (or target_date)."""
        d = target_date or date.today()
        start = datetime.combine(d, datetime.min.time()).isoformat()
        end = datetime.combine(d, datetime.max.time()).isoformat()

        with self._cursor() as cur:
            if target_type == "total":
                cur.execute(
                    """
                    SELECT COALESCE(SUM(duration_s), 0) AS total_s
                    FROM app_sessions
                    WHERE start_time >= ? AND start_time <= ?
                      AND is_idle = 0
                      AND duration_s > 0
                    """,
                    (start, end),
                )
            elif target_type == "category":
                cur.execute(
                    """
                    SELECT COALESCE(SUM(duration_s), 0) AS total_s
                    FROM app_sessions
                    WHERE start_time >= ? AND start_time <= ?
                      AND is_idle = 0
                      AND duration_s > 0
                      AND LOWER(category) = LOWER(?)
                    """,
                    (start, end, target_name),
                )
            elif target_type == "app":
                cur.execute(
                    """
                    SELECT COALESCE(SUM(duration_s), 0) AS total_s
                    FROM app_sessions
                    WHERE start_time >= ? AND start_time <= ?
                      AND is_idle = 0
                      AND duration_s > 0
                      AND LOWER(process_name) = LOWER(?)
                    """,
                    (start, end, target_name),
                )
            else:
                return 0.0

            row = cur.fetchone()
            return float(row["total_s"] or 0.0) if row else 0.0

    @staticmethod
    def _row_to_budget(row: sqlite3.Row) -> ScreenTimeBudget:
        created = None
        if "created_at" in row.keys() and row["created_at"]:
            try:
                created = datetime.fromisoformat(row["created_at"])
            except Exception:
                created = None
        return ScreenTimeBudget(
            id=row["id"],
            target_type=row["target_type"],
            target_name=row["target_name"],
            daily_budget_seconds=int(row["daily_budget_seconds"]),
            is_enabled=bool(row["is_enabled"]),
            enforce_lock=bool(row["enforce_lock"]),
            created_at=created,
        )

