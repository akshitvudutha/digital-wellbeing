import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from database.repository import Repository
from database.models import AppSession, AppCategory
from ui.app import DigitalWellbeingApp

def main():
    import os
    os.environ["DW_TEST_MODE"] = "1"
    repo = Repository()
    repo.clear_all_sessions()
    repo.insert_session(AppSession(
        id=0,
        process_name="brave.exe",
        exe_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        window_title="Brave",
        start_time=datetime.now(),
        end_time=None,
        duration_s=3600,
        category=AppCategory.OTHER,
        is_idle=False,
        was_closed=False
    ))
    
    app_instance = DigitalWellbeingApp(start_minimized=False)
    win = app_instance._window
    
    # Mock data to ensure Brave shows up
    win._dashboard_page._screen_time_card.set_data(3600, [], [{"process_name": "brave.exe", "total_s": 3600}])
    
    # Set limit to 0 to simulate limit reached
    pm = app_instance._protection_manager
    pm.limits.set_limit_rule("brave.exe", {
        "limit_seconds": 3600,
        "repeat_days": [0,1,2,3,4,5,6],
        "notifications": [15, 10, 5, 1],
        "on_expire": "pin"
    })
    pm.timer.add_time("brave.exe", 3601) # exceed limit
    
    def run_tests():
        print("[Manual Test] Simulating tick to trigger limit...")
        QTimer.singleShot(1000, step_2_capture_limit_dialog)
        pm.tick("brave.exe", 1.0)

    def step_2_capture_limit_dialog():
        dialog = QApplication.activeModalWidget()
        if not dialog:
            print("[Manual Test] Error: Limit dialog did not appear!")
            app_instance._app.quit()
            return
            
        def capture():
            print("[Manual Test] Limit dialog captured.")
            path_limit = r"C:\Users\akshi\.gemini\antigravity-ide\brain\77176abb-7214-42a2-a272-188483d8d5a7\scratch\limit_dialog.png"
            dialog.grab().save(path_limit)
            
            # Click close app
            dialog.btn_close.click()
            QTimer.singleShot(1000, step_3_test_enforcement)
            
        QTimer.singleShot(500, capture)

    def step_3_test_enforcement():
        print("[Manual Test] Simulating tick AFTER closing dialog to test continuous enforcement...")
        QTimer.singleShot(1000, step_4_verify_respawn)
        pm.tick("brave.exe", 1.0)
        
    def step_4_verify_respawn():
        dialog = QApplication.activeModalWidget()
        if not dialog:
            print("[Manual Test] Error: Limit dialog did NOT respawn! Enforcement broken.")
        else:
            print("[Manual Test] Success: Limit dialog respawned, blocking app.")
            
            def enter_pin():
                dialog.btn_pin.click()
                QTimer.singleShot(1000, step_5_pin_dialog)
                
            QTimer.singleShot(500, enter_pin)

    def step_5_pin_dialog():
        pin_dlg = QApplication.activeModalWidget()
        if pin_dlg:
            path_pin = r"C:\Users\akshi\.gemini\antigravity-ide\brain\77176abb-7214-42a2-a272-188483d8d5a7\scratch\pin_dialog.png"
            pin_dlg.grab().save(path_pin)
            print("[Manual Test] PIN dialog captured.")
        
        app_instance._app.quit()

    QTimer.singleShot(1500, run_tests)
    
    exit_code = app_instance.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
