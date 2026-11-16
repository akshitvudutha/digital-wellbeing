"""
capture_redesigned_screenshots.py - Captures pixel-perfect screenshots of the redesigned v3.1.6 desktop application in Dark and Light themes.
"""
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage
from PySide6.QtCore import Qt

from settings.manager import SettingsManager
from ui.theme import ThemeManager
from ui.app import DigitalWellbeingApp

def validate_screenshot(path: Path, min_kb: int = 15) -> bool:
    if not path.exists():
        print(f"  [ERROR] File does not exist: {path}")
        return False
    size_kb = path.stat().st_size / 1024
    if size_kb < min_kb:
        print(f"  [WARN] Image size too small ({size_kb:.1f} KB): {path.name}")
        return False
    img = QImage(str(path))
    if img.isNull() or img.width() < 800 or img.height() < 500:
        print(f"  [WARN] Invalid image dimensions: {img.width()}x{img.height()}")
        return False
    return True

def capture_all():
    output_dir = Path(__file__).parent / "website" / "public" / "images" / "app"
    output_dir.mkdir(parents=True, exist_ok=True)

    app = DigitalWellbeingApp(start_minimized=False)
    qapp = QApplication.instance()
    win = app._window
    win.resize(1440, 900)

    sm = SettingsManager()
    tm = ThemeManager.instance()

    # Initial wait for application to settle
    start = time.time()
    while time.time() - start < 3.0:
        qapp.processEvents()
        time.sleep(0.05)

    def render_and_save(target_path: Path, is_dark: bool):
        for _ in range(5):
            qapp.processEvents()
            time.sleep(0.05)

        bg_color = QColor("#080A0D") if is_dark else QColor("#F8FAFC")
        pix = QPixmap(win.size())
        pix.fill(bg_color)
        win.render(pix)
        pix.save(str(target_path), "PNG")
        assert validate_screenshot(target_path), f"Failed validation: {target_path.name}"
        print(f"  [PASS] Successfully captured {target_path.name} ({target_path.stat().st_size // 1024} KB)")

    # Page mapping: (index, filename_base, description)
    # 0: Home, 1: Usage, 2: Focus, 3: App Locker, 4: App Timer, 5: Insights, 6: SleepGuard, 8: Settings
    pages = [
        (0, "home", "Home / Dashboard"),
        (1, "usage", "Usage / Activity"),
        (2, "focus", "Focus Mode (Inactive)"),
        (3, "app-locker", "App Locker"),
        (4, "app-timer", "App Timer"),
        (5, "insights", "Insights"),
        (6, "sleepguard", "SleepGuard"),
        (8, "settings", "Settings")
    ]

    print("\n=================== CAPTURING DARK THEME ===================")
    sm.theme = "dark"
    tm.set_theme("dark", app=qapp)
    win._apply_theme(True)
    time.sleep(0.5)

    for index, base_name, desc in pages:
        target = output_dir / f"{base_name}-dark.png"
        print(f"Capturing Dark: {desc} (index {index})...")
        win._navigate(index)
        if index == 1 and hasattr(win, "_activity_page"):
            win._activity_page._on_range_changed(1)
            time.sleep(0.3)
        time.sleep(0.6)
        render_and_save(target, is_dark=True)

    # Capture Focus Active state in Dark
    focus_act_target = output_dir / "focus-active-dark.png"
    print("Capturing Focus Active state in Dark...")
    win._navigate(2) # Focus page
    if hasattr(win, "_wellbeing_page") and hasattr(win._wellbeing_page, "_focus_timer"):
        ft = win._wellbeing_page._focus_timer
        if hasattr(ft, "_stack"):
            ft._stack.setCurrentIndex(1)
            time.sleep(0.5)
            render_and_save(focus_act_target, is_dark=True)
            ft._stack.setCurrentIndex(0)
            time.sleep(0.3)

    print("\n=================== CAPTURING LIGHT THEME ===================")
    sm.theme = "light"
    tm.set_theme("light", app=qapp)
    win._apply_theme(False)
    time.sleep(0.3)

    for index, base_name, desc in pages:
        target = output_dir / f"{base_name}-light.png"
        print(f"Capturing Light: {desc} (index {index})...")
        win._navigate(index)
        if index == 1 and hasattr(win, "_activity_page"):
            win._activity_page._on_range_changed(1)
            time.sleep(0.3)
        time.sleep(0.6)
        render_and_save(target, is_dark=False)

    print("\n=================== CAPTURING MODAL DIALOGS ===================")
    # Switch back to Dark for dialog captures
    sm.theme = "dark"
    tm.set_theme("dark", app=qapp)
    win._apply_theme(True)
    time.sleep(0.4)

    def capture_dialog_over_win(dlg, target_path: Path):
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        for _ in range(10):
            qapp.processEvents()
            time.sleep(0.05)
        
        dlg_pix = dlg.grab()
        win_pix = win.grab()
        
        bg = QPixmap(win.size())
        bg.fill(QColor("#080A0D"))
        p = QPainter(bg)
        p.drawPixmap(0, 0, win_pix)
        p.fillRect(win.rect(), QColor(0, 0, 0, 150))
        x = max(0, (win.width() - dlg.width()) // 2)
        y = max(0, (win.height() - dlg.height()) // 2)
        p.drawPixmap(x, y, dlg_pix)
        p.end()
        bg.save(str(target_path), "PNG")
        dlg.close()
        assert validate_screenshot(target_path), f"Failed validation: {target_path.name}"
        print(f"  [PASS] Successfully captured {target_path.name}")

    # 1. App Locker Authentication (PIN Dialog)
    print("Capturing App Locker Authentication Dialog...")
    win._navigate(3)
    from ui.widgets.pin_dialog import PinDialog
    class DummyPinManager:
        def verify_pin(self, pin): return False
    auth_dlg = PinDialog(DummyPinManager(), parent=win)
    capture_dialog_over_win(auth_dlg, output_dir / "authentication-dark.png")

    # 2. Blocked App Feedback Dialog
    print("Capturing Blocked App Feedback Dialog...")
    from ui.widgets.blocked_app_dialog import BlockedAppFeedbackDialog
    block_dlg = BlockedAppFeedbackDialog("discord.exe", "Deep Focus", 1440, parent=win)
    capture_dialog_over_win(block_dlg, output_dir / "blocked-app-dark.png")

    # 3. App Timer Configuration Dialog
    print("Capturing App Timer Configuration Dialog...")
    win._navigate(4)
    from ui.widgets.app_timer_widgets import TimerConfigDialog
    timer_dlg = TimerConfigDialog(parent=win)
    capture_dialog_over_win(timer_dlg, output_dir / "app-timer-config-dark.png")

    # 4. SleepGuard Countdown Dialog
    print("Capturing SleepGuard Countdown Dialog...")
    win._navigate(6)
    from ui.widgets.countdown_dialog import ShutdownCountdownDialog
    sg_dlg = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", parent=win)
    capture_dialog_over_win(sg_dlg, output_dir / "sleepguard-countdown-dark.png")

    # 5. Focus Preflight Dialog
    print("Capturing Focus Preflight Dialog...")
    win._navigate(2)
    from ui.widgets.focus_timer import DeepFocusPreflightDialog
    preflight_dlg = DeepFocusPreflightDialog(
        mode="Deep Focus",
        allowed_apps=["Code.exe", "WindowsTerminal.exe", "Obsidian.exe", "Figma.exe"],
        blocked_websites=["instagram.com", "youtube.com", "reddit.com", "twitter.com", "x.com"],
        parent=win
    )
    capture_dialog_over_win(preflight_dlg, output_dir / "focus-preflight-dark.png")
    print("  [PASS] Saved focus-preflight-dark.png")

    # Reset theme to dark as default
    sm.theme = "dark"
    tm.set_theme("dark", app=qapp)

    # Sync with brain artifacts directory
    brain_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\5c8f6a38-c225-4d7b-9411-209ce953c71b")
    import shutil
    for img_file in output_dir.glob("*.png"):
        shutil.copy(img_file, brain_dir / img_file.name)
    print("  [PASS] Copied all screenshots to brain artifacts directory.")
    
    QApplication.instance().quit()
    print("\n[SUCCESS] All redesigned v3.1.6 screenshots captured successfully!")

if __name__ == "__main__":
    capture_all()
