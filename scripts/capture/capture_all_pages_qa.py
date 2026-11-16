"""
scripts/capture/capture_all_pages_qa.py
Automated visual QA capture script for all 17 Notch desktop routes and subviews
in both Dark and Light themes to verify contrast, focus styling, and UI layout.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Resolve project root robustly
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

os.environ["DW_TEST_MODE"] = "1"
scratch_dir = project_root / "scratch" / "qa_v364_stabilization"
scratch_dir.mkdir(parents=True, exist_ok=True)
os.environ["DW_DB_PATH"] = str(scratch_dir / "qa_isolated.db")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import ThemeManager


def capture_all() -> None:
    app = QApplication.instance() or QApplication(sys.argv)

    mock_tracker = MagicMock()
    mock_tracker.is_running = True
    mock_tracker.get_debug_state.return_value = {
        "debug_enabled": False,
        "process_name": "None",
        "window_title": "None",
        "category": "Other",
        "poll_count": 0,
        "active_duration_s": 0.0,
        "idle_duration_s": 0.0,
        "last_poll_ms": 0.0,
    }
    mock_sleepguard = MagicMock()
    mock_sleepguard.is_running = False
    mock_prot = None

    tm = ThemeManager.instance()
    window = MainWindow(mock_tracker, mock_sleepguard, mock_prot)
    window.resize(1280, 800)
    window.show()
    app.processEvents()

    routes = [
        ("00_home", 0, None),
        ("01_usage", 1, None),
        ("02_focus", 2, lambda w: w._wellbeing_page._stack.setCurrentIndex(0) if hasattr(w._wellbeing_page, "_stack") else None),
        ("02_deep_work", 2, lambda w: w._wellbeing_page._stack.setCurrentIndex(1) if hasattr(w._wellbeing_page, "_stack") else None),
        ("02_smart_scheduler", 2, lambda w: w._wellbeing_page._stack.setCurrentIndex(2) if hasattr(w._wellbeing_page, "_stack") else None),
        ("03_app_locker", 3, None),
        ("04_app_timer", 4, lambda w: w._app_timer_page._stack.setCurrentIndex(0) if hasattr(w._app_timer_page, "_stack") else None),
        ("04_daily_budgets", 4, lambda w: w._app_timer_page._stack.setCurrentIndex(1) if hasattr(w._app_timer_page, "_stack") else None),
        ("05_insights", 5, lambda w: w._insights_page._stack.setCurrentIndex(0) if hasattr(w._insights_page, "_stack") else None),
        ("05_weekly_report", 5, lambda w: w._insights_page._stack.setCurrentIndex(1) if hasattr(w._insights_page, "_stack") else None),
        ("06_sleepguard", 6, None),
        ("07_history", 7, None),
        ("08_settings", 8, None),
        ("09_dev_mode", 9, None),
        ("10_screen_time_details", 10, None),
        ("11_app_details", 11, lambda w: w._app_details_page.set_app("Code.exe") if hasattr(w, "_app_details_page") else None),
        ("12_student_workspace", 12, None),
    ]

    for theme_name, is_dark in [("dark", True), ("light", False)]:
        tm.set_theme(theme_name, app=app)
        window._apply_theme(is_dark)
        app.processEvents()

        for route_name, stack_idx, subview_action in routes:
            window._navigate(stack_idx)
            app.processEvents()
            if subview_action:
                try:
                    subview_action(window)
                    app.processEvents()
                except Exception as exc:
                    print(f"Warning on {route_name} subview: {exc}")

            out_path = scratch_dir / f"{theme_name}_{route_name}.png"
            window.grab().save(str(out_path))
            print(f"Captured: {out_path.name}")

    window.close()
    app.quit()
    print(f"\nAll QA captures saved to: {scratch_dir}")


if __name__ == "__main__":
    capture_all()
