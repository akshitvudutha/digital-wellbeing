"""
scripts/capture/capture_batch3_dashboard.py — Capture screenshots of the redesigned Dashboard
for Notch UI Redesign Batch 3 in both Dark and Light themes.
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta

# Resolve project root robustly
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.constants import AppCategory
from database.models import AppSession
from database.repository import Repository
from ui.main_window import MainWindow
from ui.theme import ThemeManager


def seed_demo_data_if_empty():
    """Ensure realistic activity data exists so screenshots show full fidelity."""
    repo = Repository()
    today_sessions = repo.get_sessions_for_date(date.today())
    if not today_sessions:
        now = datetime.now()
        sessions = [
            AppSession("Code.exe", "dashboard.py - Notch", now - timedelta(hours=3, minutes=15), now - timedelta(minutes=45), 9000.0, AppCategory.PROGRAMMING, False),
            AppSession("brave.exe", "GitHub - akshitvudutha/digital-wellbeing", now - timedelta(minutes=40), now - timedelta(minutes=10), 1800.0, AppCategory.BROWSER, False),
            AppSession("Spotify.exe", "Focus Beats - Deep Flow", now - timedelta(hours=2), now, 2400.0, AppCategory.MEDIA, False),
            AppSession("WindowsTerminal.exe", "PowerShell - pytest tests", now - timedelta(minutes=30), now - timedelta(minutes=15), 900.0, AppCategory.SYSTEM, False),
            AppSession("slack.exe", "Team Chat", now - timedelta(minutes=15), now - timedelta(minutes=5), 600.0, AppCategory.COMMUNICATION, False),
        ]
        for s in sessions:
            repo.insert_session(s)


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    artifact_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\5b5c87fa-4527-4927-b157-cf16a0059107")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scratch_media_dir = project_root / "scratch" / "media"
    scratch_media_dir.mkdir(parents=True, exist_ok=True)

    seed_demo_data_if_empty()

    tm = ThemeManager.instance()
    tm.set_theme("dark", app=app)

    window = MainWindow(tracker=None, protection_manager=None, sleepguard=None)
    window.resize(1200, 800)
    window.show()

    def capture_sequence():
        print("Capturing Redesigned Dashboard Screenshots...")
        QApplication.processEvents()

        # 1. Dark Theme Screenshot
        dark_pixmap = window.grab()
        dark_artifact = artifact_dir / "batch3_dashboard_dark.png"
        dark_scratch = scratch_media_dir / "batch3_dashboard_dark.png"
        dark_pixmap.save(str(dark_artifact))
        dark_pixmap.save(str(dark_scratch))
        print(f"Saved Redesigned Dark Dashboard: {dark_artifact}")

        # 2. Light Theme Screenshot
        tm.set_theme("light", app=app)
        QApplication.processEvents()
        light_pixmap = window.grab()
        light_artifact = artifact_dir / "batch3_dashboard_light.png"
        light_scratch = scratch_media_dir / "batch3_dashboard_light.png"
        light_pixmap.save(str(light_artifact))
        light_pixmap.save(str(light_scratch))
        print(f"Saved Redesigned Light Dashboard: {light_artifact}")

        # Revert back to dark theme
        tm.set_theme("dark", app=app)
        QApplication.processEvents()

        window.close()
        app.quit()

    QTimer.singleShot(800, capture_sequence)
    app.exec()


if __name__ == "__main__":
    main()
