"""
capture_v363_focus_and_timer.py — Verification & screenshot capture for Notch v3.6.3
Validates:
1. Removal of rectangular focus outlines on mouse clicks (e.g., Weekly Wellbeing Report, Home nav button).
2. Keyboard Tab focus retains clean, rounded, non-overlapping borders.
3. 15-minute timer correctly initializes to 15:00 / 15m remaining and supports pause/resume.
4. Both Dark and Light themes.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from ui.theme import ThemeManager
from ui.main_window import MainWindow
from ui.pages.insights import InsightsPage
from ui.widgets.focus_timer import FocusTimerWidget
from protection.focus_manager import FocusManager


def run_qa_captures():
    out_dir = PROJECT_ROOT / "scratch" / "focus_timer_qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[QA] Output directory: {out_dir}")

    app = QApplication.instance() or QApplication([])
    tm = ThemeManager.instance()

    # -------------------------------------------------------------
    # 1. Dark Theme: Insights Page Subtab (Weekly Wellbeing Report)
    # -------------------------------------------------------------
    print("[QA] 1. Testing Insights Page - Weekly Wellbeing Report (Dark)...")
    tm.set_theme("dark", app)
    insights = InsightsPage()
    insights.resize(1100, 800)
    insights.show()
    app.processEvents()

    # Capture initial
    insights.grab().save(str(out_dir / "01_insights_dark_initial.png"))

    # Mouse click on Weekly Wellbeing Report
    weekly_btn = insights._btn_subtab_weekly
    QTest.mouseClick(weekly_btn, Qt.MouseButton.LeftButton)
    app.processEvents()
    insights.grab().save(str(out_dir / "02_insights_dark_weekly_clicked.png"))
    weekly_btn.grab().save(str(out_dir / "02b_weekly_btn_dark_clicked.png"))
    print(f"  - weekly_btn hasFocus after mouse click: {weekly_btn.hasFocus()} (expected: False)")

    # Keyboard Tab focus on Weekly Wellbeing Report
    weekly_btn.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    insights.grab().save(str(out_dir / "03_insights_dark_weekly_keyboard_focus.png"))
    weekly_btn.grab().save(str(out_dir / "03b_weekly_btn_dark_keyboard_focus.png"))

    # -------------------------------------------------------------
    # 2. Light Theme: Insights Page Subtab
    # -------------------------------------------------------------
    print("[QA] 2. Testing Insights Page - Weekly Wellbeing Report (Light)...")
    tm.set_theme("light", app)
    app.processEvents()
    QTest.mouseClick(weekly_btn, Qt.MouseButton.LeftButton)
    app.processEvents()
    insights.grab().save(str(out_dir / "04_insights_light_weekly_clicked.png"))
    weekly_btn.grab().save(str(out_dir / "04b_weekly_btn_light_clicked.png"))

    insights.close()

    # -------------------------------------------------------------
    # 3. MainWindow Nav Items (Home nav button click & focus)
    # -------------------------------------------------------------
    print("[QA] 3. Testing MainWindow Sidebar Navigation...")
    tm.set_theme("dark", app)
    main_win = MainWindow()
    main_win.resize(1200, 800)
    main_win.show()
    app.processEvents()

    # Click Home nav button
    home_btn = main_win._nav_buttons.get("dashboard")
    if home_btn:
        QTest.mouseClick(home_btn, Qt.MouseButton.LeftButton)
        app.processEvents()
        main_win.grab().save(str(out_dir / "05_mainwindow_home_clicked.png"))
        home_btn.grab().save(str(out_dir / "05b_home_btn_clicked.png"))
        print(f"  - home_btn hasFocus after mouse click: {home_btn.hasFocus()} (expected: False)")

    main_win.close()

    # -------------------------------------------------------------
    # 4. 15-Minute Timer Configuration & Active Countdown
    # -------------------------------------------------------------
    print("[QA] 4. Testing 15-Minute Timer Configuration & Lifecycle...")
    tm.set_theme("dark", app)
    fm = FocusManager.instance()
    if fm.is_active:
        fm.cancel_focus()

    timer_widget = FocusTimerWidget()
    timer_widget.resize(750, 520)
    timer_widget.show()
    app.processEvents()

    # Click 15m preset chip
    chip_15 = next((c for c in timer_widget._chips if c.property("minutes") == 15), None)
    if chip_15:
        QTest.mouseClick(chip_15, Qt.MouseButton.LeftButton)
        app.processEvents()
        print(f"  - Configured duration text: {timer_widget._time_display.text()} (expected: 15:00)")
        print(f"  - Status text: {timer_widget._status_lbl.text()}")
        timer_widget.grab().save(str(out_dir / "06_timer_configured_15m.png"))

    # Start 15m Focus session directly via FocusManager to test active widget sync
    fm.start_focus(minutes=15, strict_mode=False)
    app.processEvents()

    print(f"  - Active timer countdown readout: {timer_widget._active_time_display.text()} (expected: 15:00)")
    print(f"  - Active timer remaining label: {timer_widget._active_remaining_lbl.text()} (expected: 15m remaining)")
    timer_widget.grab().save(str(out_dir / "07_timer_active_15m_countdown.png"))

    # Pause 15m Focus session
    fm.pause_focus()
    app.processEvents()
    print(f"  - Status pill when paused: {timer_widget._active_status_pill.text()} (expected: FOCUS PAUSED)")
    print(f"  - Pause/Resume button text: {timer_widget._active_pause_btn.text()} (expected: Resume)")
    timer_widget.grab().save(str(out_dir / "08_timer_paused_15m.png"))

    # Resume 15m Focus session
    fm.resume_focus()
    app.processEvents()
    print(f"  - Status pill after resume: {timer_widget._active_status_pill.text()} (expected: FOCUS ACTIVE)")
    timer_widget.grab().save(str(out_dir / "09_timer_resumed_15m.png"))

    # Cancel focus
    fm.cancel_focus()
    app.processEvents()
    print(f"  - After cancellation readout: {timer_widget._time_display.text()} (expected: 15:00)")
    timer_widget.grab().save(str(out_dir / "10_timer_cancelled_reset_15m.png"))

    timer_widget.close()
    print("[QA] All verification captures completed successfully!")


if __name__ == "__main__":
    run_qa_captures()
