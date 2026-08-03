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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Main layout holds the inner frame centered
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(0, 0, 0, 220); /* Darken entire browser */
            }
            QFrame#inner_frame {
                background-color: rgba(30, 30, 30, 255);
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

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("inner_frame")
        self.inner_frame.setFixedSize(500, 300)
        
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(40, 40, 40, 40)
        inner_layout.setSpacing(20)
        
        # Center the inner frame inside the QDialog
        self.layout().addWidget(self.inner_frame, 0, Qt.AlignmentFlag.AlignCenter)

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
        
        inner_layout.addWidget(title)
        inner_layout.addWidget(domain_label)
        inner_layout.addWidget(msg)
        inner_layout.addLayout(btn_layout)
        
        self.btn_close_tab.clicked.connect(self._on_close_tab)
        self.btn_override.clicked.connect(self._on_override)
        
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self._update_position)
        self._position_timer.start(50) # Update position frequently to stick to browser

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
            
            # The dialog must fill the entire browser bounds to intercept ALL input
            self.setGeometry(rect[0], rect[1], bw, bh)
            
            # Force focus so keyboard shortcuts don't reach the browser
            if not self.isActiveWindow():
                self.activateWindow()
                self.setFocus()
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
