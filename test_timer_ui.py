import sys
from PySide6.QtWidgets import QApplication
from ui.theme import ThemeManager
from ui.widgets.app_timer_widgets import TimerConfigDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    tm = ThemeManager.instance()
    
    rule = {
        "limit_seconds": 7200,
        "repeat_days": [0, 1, 2, 3, 4],
        "notifications": [15, 10, 5, 1],
        "on_expire": "lock"
    }
    
    dialog = TimerConfigDialog(None, rule)
    
    # Render and screenshot
    dialog.show()
    
    # Wait for animation
    from PySide6.QtCore import QTimer
    def take_screenshot():
        pixmap = dialog.grab()
        pixmap.save("C:\\Users\\akshi\\.gemini\\antigravity-ide\\brain\\77176abb-7214-42a2-a272-188483d8d5a7\\scratch\\timer_dialog.png")
        app.quit()
        
    QTimer.singleShot(300, take_screenshot)
    
    app.exec()
    print("Screenshot saved.")
