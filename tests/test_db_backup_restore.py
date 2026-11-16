"""
tests/test_db_backup_restore.py — Comprehensive tests for Notch database backup & restore safety:
1. Rejection of non-existent or directory paths.
2. Rejection of files too small to be valid SQLite databases.
3. Rejection of invalid SQLite file headers (corrupted / text files).
4. Rejection of corrupted SQLite databases failing PRAGMA integrity_check.
5. Rejection of unrelated SQLite databases missing required Notch tables.
6. Successful validation and restoration of a genuine Notch database backup.
7. Verification that a pre-restore safety snapshot (.pre_restore.bak) is created.
8. Verification that active data is preserved intact if validation or restore fails.
9. Verification of rollback to pre-restore snapshot if restore raises an exception midway.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.constants import AppCategory
from database.repository import Repository
from database.models import AppSession


@pytest.fixture
def temp_db_env(tmp_path):
    """Provides an isolated database environment for testing backup/restore."""
    active_db = tmp_path / f"active_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(active_db)
    repo = Repository()
    yield repo, active_db, tmp_path
    Repository.set_db_path_override(None)


@pytest.fixture(scope="session")
def qapp():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app



def test_validate_rejects_nonexistent_and_directory(temp_db_env):
    """Non-existent files or directories are rejected with clear messages."""
    repo, _, tmp_path = temp_db_env
    non_existent = tmp_path / "does_not_exist.db"
    ok, msg = repo.validate_backup_file(non_existent)
    assert ok is False
    assert "does not exist" in msg

    a_dir = tmp_path / "some_dir"
    a_dir.mkdir()
    ok, msg = repo.validate_backup_file(a_dir)
    assert ok is False
    assert "not a file" in msg


def test_validate_rejects_too_small_file(temp_db_env):
    """Files smaller than 100 bytes are rejected."""
    repo, _, tmp_path = temp_db_env
    tiny_file = tmp_path / "tiny.db"
    tiny_file.write_bytes(b"hello world")
    ok, msg = repo.validate_backup_file(tiny_file)
    assert ok is False
    assert "too small" in msg


def test_validate_rejects_invalid_sqlite_header(temp_db_env):
    """Files without the canonical SQLite 3 magic header are rejected."""
    repo, _, tmp_path = temp_db_env
    fake_db = tmp_path / "fake.db"
    fake_db.write_bytes(b"This is a text file that was renamed to .db to simulate user error" * 5)
    ok, msg = repo.validate_backup_file(fake_db)
    assert ok is False
    assert "header" in msg.lower() or "sqlite 3 format" in msg.lower()

    # Calling restore_database directly raises ValueError with the same message
    with pytest.raises(ValueError, match="SQLite 3 format"):
        repo.restore_database(fake_db)


def test_validate_rejects_corrupted_sqlite_database(temp_db_env):
    """Databases that fail PRAGMA integrity_check are rejected."""
    repo, _, tmp_path = temp_db_env
    corrupt_db = tmp_path / "corrupt.db"

    # Create a small valid SQLite db, then corrupt its payload
    conn = sqlite3.connect(str(corrupt_db))
    conn.execute("CREATE TABLE t1(x TEXT);")
    conn.execute("INSERT INTO t1 VALUES('some data');")
    conn.commit()
    conn.close()

    # Overwrite bytes in the middle of page 1 while preserving the header
    data = bytearray(corrupt_db.read_bytes())
    for i in range(100, min(len(data), 250)):
        data[i] = 0xFF
    corrupt_db.write_bytes(bytes(data))

    ok, msg = repo.validate_backup_file(corrupt_db)
    assert ok is False
    assert "integrity check failed" in msg.lower() or "error" in msg.lower()

    with pytest.raises(ValueError):
        repo.restore_database(corrupt_db)


def test_validate_rejects_unrelated_sqlite_database_missing_schema(temp_db_env):
    """Valid SQLite databases that lack Notch's required schema tables are rejected."""
    repo, _, tmp_path = temp_db_env
    unrelated_db = tmp_path / "unrelated.db"

    conn = sqlite3.connect(str(unrelated_db))
    conn.execute("CREATE TABLE bookmarks(id INTEGER PRIMARY KEY, url TEXT);")
    conn.execute("CREATE TABLE cookies(id INTEGER PRIMARY KEY, value TEXT);")
    conn.commit()
    conn.close()

    ok, msg = repo.validate_backup_file(unrelated_db)
    assert ok is False
    assert "missing required notch tables" in msg.lower()
    assert "app_sessions" in msg

    with pytest.raises(ValueError, match="Missing required Notch tables"):
        repo.restore_database(unrelated_db)


def test_valid_backup_and_restoration(temp_db_env):
    """A valid Notch backup passes validation and cleanly restores active data."""
    repo, active_db, tmp_path = temp_db_env

    # 1. Seed unique data into active database
    repo.set_setting("user_preference_test", "original_value")
    session = AppSession(
        process_name="code.exe",
        exe_path="C:\\Program Files\\VSCode\\Code.exe",
        window_title="Workspace",
        start_time=datetime(2026, 10, 18, 10, 0, 0),
        end_time=datetime(2026, 10, 18, 11, 0, 0),
        duration_s=3600.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    )
    repo.insert_session(session)

    # 2. Backup to file
    backup_file = tmp_path / "valid_backup.db"
    dest = repo.backup_database(backup_file)
    assert dest.exists()
    assert dest.stat().st_size > 100

    # 3. Validation must succeed
    ok, msg = repo.validate_backup_file(backup_file)
    assert ok is True
    assert "Valid" in msg

    # 4. Modify active database to something else
    repo.set_setting("user_preference_test", "modified_value")
    assert repo.get_setting("user_preference_test") == "modified_value"

    # 5. Restore from backup
    restored_path = repo.restore_database(backup_file)
    assert restored_path == active_db

    # 6. Verify restored data matches the original backup snapshot
    assert repo.get_setting("user_preference_test") == "original_value"
    sessions = repo.get_sessions_for_date(datetime(2026, 10, 18).date())
    assert len(sessions) >= 1
    assert sessions[0].process_name == "code.exe"
    assert sessions[0].duration_s == 3600.0

    # 7. Check pre-restore snapshot was created
    snapshot_path = active_db.with_name(f"{active_db.name}.pre_restore.bak")
    assert snapshot_path.exists()


def test_failed_validation_leaves_active_db_untouched(temp_db_env):
    """Attempting to restore an invalid file leaves active data 100% intact."""
    repo, _, tmp_path = temp_db_env

    repo.set_setting("critical_user_key", "must_not_be_lost")
    fake_file = tmp_path / "corrupt.txt"
    fake_file.write_text("Not a database")

    with pytest.raises(ValueError):
        repo.restore_database(fake_file)

    assert repo.get_setting("critical_user_key") == "must_not_be_lost"


def test_rollback_to_snapshot_on_midway_restore_exception(temp_db_env):
    """If an unexpected exception occurs during restore, rollback preserves active data."""
    repo, active_db, tmp_path = temp_db_env

    repo.set_setting("safe_state_key", "safe_state_value")
    backup_file = tmp_path / "valid.db"
    repo.backup_database(backup_file)

    # Change active state
    repo.set_setting("safe_state_key", "active_unrestored_value")

    real_conn = repo._connection()
    mock_conn = MagicMock(wraps=real_conn)
    mock_conn.commit.side_effect = sqlite3.OperationalError("Simulated disk write failure")

    with patch.object(repo, "_connection", return_value=mock_conn):
        with pytest.raises(RuntimeError, match="Database restore failed"):
            repo.restore_database(backup_file)

    # Active database must still be accessible
    assert repo.get_setting("safe_state_key") in ("active_unrestored_value", "safe_state_value")


def test_settings_ui_reflects_restored_values(temp_db_env, qapp):
    """After a successful database restore via SettingsPage, UI controls reflect the restored database values."""
    from PySide6.QtWidgets import QMessageBox, QFileDialog
    from settings.manager import SettingsManager
    from ui.pages.settings import SettingsPage

    repo, active_db, tmp_path = temp_db_env

    # 1. Prepare backup database with distinct settings
    backup_db_path = tmp_path / "custom_settings_backup.db"
    Repository.set_db_path_override(backup_db_path)
    backup_repo = Repository()
    backup_sm = SettingsManager()
    backup_sm.display_name = "Restored Alice"
    backup_sm.idle_timeout_minutes = 45
    backup_sm.countdown_seconds = 25
    backup_sm.sleepguard_sound_enabled = False
    backup_sm.sleepguard_sound_reminders = False
    backup_sm.sleepguard_sound_chime = "SystemHand"
    Repository.set_db_path_override(active_db)

    # 2. Seed active database with original settings
    active_sm = SettingsManager()
    active_sm.display_name = "Original Bob"
    active_sm.idle_timeout_minutes = 15
    active_sm.countdown_seconds = 60
    active_sm.sleepguard_sound_enabled = True
    active_sm.sleepguard_sound_reminders = True
    active_sm.sleepguard_sound_chime = "SystemExclamation"

    # 3. Create SettingsPage instance — initial widgets must show original values
    page = SettingsPage()
    try:
        assert page._display_name_edit.text() == "Original Bob"
        assert page._sg_timeout_spin.value() == 15
        assert page._sg_countdown_spin.value() == 60
        assert page._sg_sound_enable_check.isChecked() is True
        assert page._sg_sound_remind_check.isChecked() is True
        assert page._sg_chime_combo.currentData() == "SystemExclamation"

        # 4. Trigger _on_restore_db with mocked confirmation and file picker
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QFileDialog, "getOpenFileName", return_value=(str(backup_db_path), "Database Files (*.db)")):
            page._on_restore_db()

        # 5. Success status banner is displayed
        assert "✓ Database restored successfully from:" in page._data_status_lbl.text()
        assert backup_db_path.name in page._data_status_lbl.text()

        # 6. Verify Settings UI controls immediately reflect restored values without restart
        assert page._display_name_edit.text() == "Restored Alice"
        assert page._sg_timeout_spin.value() == 45
        assert page._sg_countdown_spin.value() == 25
        assert page._sg_sound_enable_check.isChecked() is False
        assert page._sg_sound_remind_check.isChecked() is False
        assert page._sg_chime_combo.currentData() == "SystemHand"
    finally:
        page.deleteLater()


def test_settings_ui_leaves_controls_unchanged_on_failed_restore(temp_db_env, qapp):
    """When a restore fails validation, SettingsPage displays an error banner and leaves controls unchanged."""
    from PySide6.QtWidgets import QMessageBox, QFileDialog
    from settings.manager import SettingsManager
    from ui.pages.settings import SettingsPage

    repo, active_db, tmp_path = temp_db_env

    # 1. Seed active database
    active_sm = SettingsManager()
    active_sm.display_name = "Keep Me"
    active_sm.idle_timeout_minutes = 20

    corrupt_file = tmp_path / "invalid.db"
    corrupt_file.write_text("invalid plain text database")

    page = SettingsPage()
    try:
        assert page._display_name_edit.text() == "Keep Me"

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QFileDialog, "getOpenFileName", return_value=(str(corrupt_file), "Database Files (*.db)")):
            page._on_restore_db()

        # Error banner displayed
        assert "✗ Restore failed:" in page._data_status_lbl.text()
        # UI controls remain untouched
        assert page._display_name_edit.text() == "Keep Me"
        assert page._sg_timeout_spin.value() == 20
    finally:
        page.deleteLater()

