"""
scripts/capture/capture_dashboard_baseline.py — Capture baseline screenshots of the current Dashboard
before redesigning it for Batch 3.
"""

import sys
import os
from pathlib import Path

# Resolve project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui.main_window import MainWindow
from ui.theme import ThemeManager


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    artifact_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\5b5c87fa-4527-4927-b157-cf16a0059107")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scratch_media_dir = project_root / "scratch" / "media"
    scratch_media_dir.mkdir(parents=True, exist_ok=True)

    tm = ThemeManager.instance()
    tm.set_theme("dark", app=app)

    window = MainWindow(tracker=None, protection_manager=None, sleepguard=None)
    window.resize(1200, 800)
    window.show()

    def capture_sequence():
        print("Capturing Baseline Dashboard Screenshots...")
        QApplication.processEvents()

        # 1. Dark Baseline
        dark_pixmap = window.grab()
        dark_artifact = artifact_dir / "baseline_dashboard_dark.png"
        dark_scratch = scratch_media_dir / "baseline_dashboard_dark.png"
        dark_pixmap.save(str(dark_artifact))
        dark_pixmap.save(str(dark_scratch))
        print(f"Saved Dark Baseline: {dark_artifact}")

        # 2. Light Baseline
        tm.set_theme("light", app=app)
        QApplication.processEvents()
        light_pixmap = window.grab()
        light_artifact = artifact_dir / "baseline_dashboard_light.png"
        light_scratch = scratch_media_dir / "baseline_dashboard_light.png"
        light_pixmap.save(str(light_artifact))
        light_pixmap.save(str(light_scratch))
        print(f"Saved Light Baseline: {light_artifact}")

        # Switch back to dark
        tm.set_theme("dark", app=app)
        QApplication.processEvents()

        window.close()
        app.quit()

    QTimer.singleShot(700, capture_sequence)
    app.exec()


if __name__ == "__main__":
    main()
