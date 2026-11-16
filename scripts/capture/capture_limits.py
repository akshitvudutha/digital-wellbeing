import sys
import os
os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import QApplication
from ui.app import DigitalWellbeingApp

app = QApplication.instance() or QApplication(sys.argv)
dw = DigitalWellbeingApp()

win = dw._window
if win:
    win.show()
    win.resize(1150, 720) # ensure it is large enough
    if hasattr(win, '_nav_buttons') and len(win._nav_buttons) > 2:
        win._nav_buttons[2].click()
    else:
        win._stack.setCurrentIndex(2)

    from PySide6.QtCore import QTimer
    def capture():
        pixmap = win.grab()
        pixmap.save(r"website\public\limits.png")
        QApplication.quit()
    QTimer.singleShot(1500, capture)
    app.exec()
else:
    print("No window created")
