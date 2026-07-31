import sys
import logging
import threading
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from tracker.manager import TrackingManager
from tracker.sleepguard import SleepGuardController
from PySide6.QtCore import QTimer
import tracker.idle

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Monkeypatch is_idle to trigger immediately
original_is_idle = tracker.idle.is_idle
def fake_is_idle(*args, **kwargs):
    logging.info("--- TEST SCRIPT: fake_is_idle returning True! ---")
    return True
tracker.idle.is_idle = fake_is_idle

app = QApplication(sys.argv)
tracker_mgr = TrackingManager()
sleepguard = SleepGuardController()

# Set small countdown
sleepguard._settings.countdown_seconds = 3

# Need to start sleepguard's loop
sleepguard.start()

window = MainWindow(tracker=tracker_mgr, sleepguard=sleepguard)
window.show()

# Auto close after 7 seconds
QTimer.singleShot(7000, app.quit)

sys.exit(app.exec())
