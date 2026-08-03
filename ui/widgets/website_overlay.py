from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QTimer
import win32gui
import win32process

try:
    import uiautomation as auto
except ImportError:
    auto = None

class WebsiteLimitOverlayDialog(QDialog):
    override_requested = Signal(str, str) # process_name, domain
    close_tab_requested = Signal(str, str) # process_name, domain

    def __init__(self, process_name: str, domain: str, limit_seconds: int, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.process_name = process_name
        self.domain = domain
        self.limit_seconds = limit_seconds
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setup_ui()
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self._update_position)
        self._position_timer.start(50) # Update position frequently to stick to browser

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 245);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 8px;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
            }
            QPushButton#closeBtn {
                background-color: rgba(255, 80, 80, 200);
                border: none;
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(255, 80, 80, 255);
            }
        """)

        title = QLabel("Website Limit Reached")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        domain_label = QLabel(self.domain)
        domain_label.setStyleSheet("font-size: 18px; color: #888888;")
        domain_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        limit_mins = self.limit_seconds // 60
        msg = QLabel(f"You have reached your daily limit of {limit_mins} minutes for this website.")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        self.btn_close_tab = QPushButton("Close Tab")
        self.btn_close_tab.setObjectName("closeBtn")
        self.btn_override = QPushButton("PIN Override")
        
        btn_layout.addWidget(self.btn_close_tab)
        btn_layout.addWidget(self.btn_override)
        
        layout.addWidget(title)
        layout.addWidget(domain_label)
        layout.addWidget(msg)
        layout.addLayout(btn_layout)
        
        self.btn_close_tab.clicked.connect(self._on_close_tab)
        self.btn_override.clicked.connect(self._on_override)

    def _find_browser_hwnd(self) -> int:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd: return 0
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            import psutil
            p = psutil.Process(pid)
            if self.process_name.lower() in p.name().lower():
                return hwnd
        except Exception:
            pass
        return 0

    def _update_position(self):
        hwnd = self._find_browser_hwnd()
        if not hwnd:
            self.hide()
            return
            
        if auto:
            try:
                from tracker.browser_url import BrowserURLProvider
                current_domain = BrowserURLProvider.get_active_domain(hwnd, self.process_name)
                if current_domain != self.domain:
                    self.hide()
                    return
            except Exception:
                pass

        if not self.isVisible():
            self.show()

        try:
            rect = win32gui.GetWindowRect(hwnd)
            bw = rect[2] - rect[0]
            bh = rect[3] - rect[1]
            
            dialog_w = self.width()
            dialog_h = self.height()
            
            x = rect[0] + (bw - dialog_w) // 2
            y = rect[1] + (bh - dialog_h) // 2
            
            self.move(x, y)
        except Exception:
            pass

    def _on_close_tab(self):
        hwnd = self._find_browser_hwnd()
        if hwnd:
            import ctypes
            VK_CONTROL = 0x11
            VK_W = 0x57
            KEYEVENTF_KEYUP = 0x0002
            
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_W, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_W, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            
        self.close_tab_requested.emit(self.process_name, self.domain)
        self.accept()

    def _on_override(self):
        self.override_requested.emit(self.process_name, self.domain)
