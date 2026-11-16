"""
scripts/capture/capture_v363_stabilization.py
Captures visual verification screenshots for Notch v3.6.3 stabilization:
- Home selected after mouse click (no green rectangle outline).
- Navigation focused via keyboard (clean rounded focus ring).
- Both dark and light themes.
- Confirms StatCard trend is embedded inside the card and creates no auxiliary windows.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Force isolated test environment
os.environ["DW_TEST_MODE"] = "1"
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))
scratch_dir = root_dir / "scratch"
scratch_dir.mkdir(exist_ok=True)
os.environ["DW_DB_PATH"] = str(scratch_dir / "test_iso.db")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import ThemeManager

def main():
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
        "last_poll_ms": 0.0
    }
    mock_sleepguard = MagicMock()
    mock_sleepguard.is_running = False
    mock_prot = MagicMock()

    tm = ThemeManager.instance()

    # 1. Dark Mode: Home Selected via Mouse Click
    tm.set_theme("Dark")
    window = MainWindow(mock_tracker, mock_sleepguard, mock_prot)
    window.resize(1280, 800)
    window.show()
    app.processEvents()

    # Simulate mouse click on Home
    window._home_btn.click()
    app.processEvents()
    
    # Update stat card with sample metrics and trend
    window._dashboard_page._screen_time_card.set_metric("8h 39m")
    window._dashboard_page._screen_time_card.set_subtext("Active: 8h 39m • Idle: 0s")
    window._dashboard_page._screen_time_card.set_trend("↑ 362.1% vs yesterday", direction="up")
    app.processEvents()

    # Capture 1: Dark Mode Mouse Click (selected Home, no rectangular outline, trend in card)
    dark_click_path = scratch_dir / "v363_dark_home_mouse_click.png"
    window.grab().save(str(dark_click_path))
    print(f"Captured: {dark_click_path}")

    # 2. Dark Mode: Keyboard Focus on Home
    window._home_btn.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    dark_focus_path = scratch_dir / "v363_dark_home_keyboard_focus.png"
    window.grab().save(str(dark_focus_path))
    print(f"Captured: {dark_focus_path}")

    # 3. Light Mode: Home Selected via Mouse Click
    tm.set_theme("Light")
    window._apply_theme(False)
    app.processEvents()
    window._home_btn.clearFocus()
    window._home_btn.click()
    app.processEvents()
    
    light_click_path = scratch_dir / "v363_light_home_mouse_click.png"
    window.grab().save(str(light_click_path))
    print(f"Captured: {light_click_path}")

    # 4. Light Mode: Keyboard Focus on Home
    window._home_btn.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    light_focus_path = scratch_dir / "v363_light_home_keyboard_focus.png"
    window.grab().save(str(light_focus_path))
    print(f"Captured: {light_focus_path}")

    window.close()
    print("All captures completed successfully.")

if __name__ == "__main__":
    main()
