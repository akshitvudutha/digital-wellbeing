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
            def get_all_limits(self, pname):
                if pname == "chrome.exe":
                    return {
                        "reddit.com": {"limit_seconds": 1800},
                        "instagram.com": {"limit_seconds": 900}
                    }
                return {}
        class WebsiteTimer:
            def get_time(self, domain):
                return 1500 if domain == "reddit.com" else 300
        class WebsiteLimits:
            def get_all_limits(self, pname):
                return MockProtectionManager.Limits().get_all_limits(pname)
            
        def __init__(self):
            self.limits = self.Limits()
            self.website_timer = self.WebsiteTimer()
            self.website_limits = self.WebsiteLimits()
            self.pin = "1234"
        def has_active_override(self, pname):
            return False

    pm = MockProtectionManager()
    page = AppDetailsPage(protection_manager=pm)
    page.resize(1000, 800)
    
    # Simulate Chrome Browser to show website timers
    page.set_app("chrome.exe")
    page._title_lbl.setText("Google Chrome")
    page._progress_widget.update_progress(1200, 7200) # 20m elapsed
    
    page.show()
    
    def take_screenshot():
        pixmap = page.grab()
        pixmap.save("C:\\Users\\akshi\\.gemini\\antigravity-ide\\brain\\77176abb-7214-42a2-a272-188483d8d5a7\\scratch\\app_details_website_timers.png")
        app.quit()
        
    QTimer.singleShot(1000, take_screenshot)
    
    app.exec()
    print("Screenshot saved.")
