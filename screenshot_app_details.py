import sys
from PySide6.QtWidgets import QApplication
from ui.pages.app_details import AppDetailsPage
from ui.theme import apply_theme, ThemeManager
from PySide6.QtCore import QTimer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    apply_theme(app, "dark")
    
    class MockProtectionManager:
        class Limits:
            def get_limit_rule(self, pname):
                return {
                    "limit_seconds": 7200,
                    "repeat_days": [0, 1, 2, 3, 4],
                    "notifications": [15, 10, 5],
                    "on_expire": "pin"
                }
        def __init__(self):
            self.limits = self.Limits()
            self.pin = "1234"
        def has_active_override(self, pname):
            return False

    pm = MockProtectionManager()
    page = AppDetailsPage(protection_manager=pm)
    page.resize(1000, 800)
    
    # Manually trigger paint with a dummy app
    page.set_app("dummy.exe")
    page._title_lbl.setText("Dummy Application")
    page._progress_widget.update_progress(1200, 7200) # 20m elapsed
    
    page.show()
    
    def take_screenshot():
        pixmap = page.grab()
        pixmap.save("C:\\Users\\akshi\\.gemini\\antigravity-ide\\brain\\77176abb-7214-42a2-a272-188483d8d5a7\\scratch\\app_details_fixed.png")
        app.quit()
        
    QTimer.singleShot(500, take_screenshot)
    
    app.exec()
    print("Screenshot saved.")
