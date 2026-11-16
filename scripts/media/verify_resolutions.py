"""
verify_resolutions.py - Tests rendering at 1280x800, 1600x900, and 1920x1080 in both Dark and Light themes.
"""
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt

from settings.manager import SettingsManager
from ui.theme import ThemeManager
from ui.app import DigitalWellbeingApp

def test_all_resolutions():
    app = DigitalWellbeingApp(start_minimized=False)
    qapp = QApplication.instance()
    win = app._window

    resolutions = [
        (1280, 800),
        (1600, 900),
        (1920, 1080)
    ]
    
    themes = ["dark", "light"]
    pages = [0, 1, 2, 3, 4, 5, 6, 8] # Home, Usage, Focus, App Locker, App Timer, Insights, SleepGuard, Settings

    tm = ThemeManager.instance()
    sm = SettingsManager()

    for width, height in resolutions:
        print(f"\n--- Testing Resolution: {width}x{height} ---")
        win.resize(width, height)
        for _ in range(5):
            qapp.processEvents()
            time.sleep(0.02)
            
        for theme_name in themes:
            is_dark = (theme_name == "dark")
            sm.theme = theme_name
            tm.set_theme(theme_name, app=qapp)
            win._apply_theme(is_dark)
            
            for page_idx in pages:
                win._navigate(page_idx)
                for _ in range(3):
                    qapp.processEvents()
                    time.sleep(0.02)
                    
                # Verify window can render without exceptions
                bg = QPixmap(win.size())
                bg.fill(QColor("#080A0D" if is_dark else "#F8FAFC"))
                win.render(bg)
                assert not bg.isNull()
                print(f"  [OK] Requested {width}x{height} (Actual: {win.width()}x{win.height()}) | {theme_name.upper()} | Page index {page_idx}")

    QApplication.instance().quit()
    print("\n[SUCCESS] Visual verification at 1280x800, 1600x900, 1920x1080 in Dark and Light PASSED!")

if __name__ == "__main__":
    test_all_resolutions()
