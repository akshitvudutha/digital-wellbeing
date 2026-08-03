import sys
import os
import time

# Set env to test mode to avoid single-instance check blocks
os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.app import DigitalWellbeingApp

def run_qa():
    print("Starting QA Runner...")
    
    # We must ensure there is only one QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    dw_app = DigitalWellbeingApp(start_minimized=False)
    
    window = dw_app._window
    if not window:
        print("ERROR: Main window failed to initialize.")
        sys.exit(1)
        
    print("Main window loaded successfully.")
    
    def test_sequence():
        try:
            print("--- Testing Dashboard ---")
            window._navigate(0)
            app.processEvents()
            assert window._dashboard_page is not None
            print("Dashboard OK.")
            
            print("--- Stress Testing Refresh Button ---")
            for i in range(30):
                window._dashboard_page._refresh_btn.click()
                app.processEvents()
            assert window._dashboard_page._is_refreshing == True
            print("Refresh stress test OK.")
            
            print("--- Testing Activity Trends ---")
            window._navigate(1)
            app.processEvents()
            assert window._activity_page is not None
            print("Activity Trends OK.")
            
            print("--- Testing Focus / Wellbeing ---")
            window._navigate(2)
            app.processEvents()
            assert window._wellbeing_page is not None
            print("Focus Page OK.")
            
            print("--- Testing Settings ---")
            window._navigate(4)
            app.processEvents()
            assert window._settings_page is not None
            print("Settings OK.")
            
            print("--- Testing App Details Routing ---")
            window._dashboard_page.request_app_details.emit("test.exe")
            app.processEvents()
            print("App Details OK.")
            
            print("--- Testing Category Details Routing ---")
            window._dashboard_page.request_category_details.emit("Programming")
            app.processEvents()
            print("Category Details OK.")
            
            print("All navigation and routing tests passed!")
            print("Initiating shutdown...")
            dw_app._quit()
            
        except Exception as e:
            print(f"QA Error: {e}")
            import traceback
            traceback.print_exc()
            dw_app._quit()
            sys.exit(1)
            
    # Schedule the test sequence shortly after startup
    QTimer.singleShot(2000, test_sequence)
    
    dw_app.run()
    print("QA Runner finished successfully.")
    sys.exit(0)

if __name__ == "__main__":
    run_qa()
