import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.logger import logger
from tracker.manager import TrackingManager
from tracker.sleepguard import SleepGuardController
from ui.main_window import MainWindow
from ui.theme import apply_theme

# Mock SettingsManager for test
os.environ["DW_TEST_MODE"] = "1"

def main():
    app = QApplication(sys.argv)
    apply_theme(app, True)
    
    tracker = TrackingManager()
    sleepguard = SleepGuardController()
    
    window = MainWindow(tracker, sleepguard)
    window.show()
    
    output_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\08810c96-653f-4f09-8c2b-87d4285f5d28\scratch")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_pages():
        print("Capturing UI...")
        
        # 0. Dashboard
        window._navigate(0)
        QApplication.processEvents()
        window.grab().save(str(output_dir / "screenshot_home.png"))
        
        # 1. Activity
        window._navigate(1)
        QApplication.processEvents()
        window.grab().save(str(output_dir / "screenshot_activity.png"))
        
        # 4. Settings
        window._navigate(4)
        QApplication.processEvents()
        window.grab().save(str(output_dir / "screenshot_settings.png"))
        
        # 5. About
        window._navigate(5)
        QApplication.processEvents()
        window.grab().save(str(output_dir / "screenshot_about.png"))
        
        print("Done capturing.")
        app.quit()

    QTimer.singleShot(1000, capture_pages)
    app.exec()

if __name__ == "__main__":
    main()
