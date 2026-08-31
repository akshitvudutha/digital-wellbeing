import sys
import os
import time
from pathlib import Path

# Force UTF-8 and test mode
sys.path.insert(0, str(Path(__file__).parent))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage
from PySide6.QtCore import Qt

from settings.manager import SettingsManager
from ui.theme import ThemeManager
from ui.app import DigitalWellbeingApp

def validate_image(image_path, min_size_kb=20, expected_width=1920, expected_height=1080):
    img = QImage(str(image_path))
    if img.isNull():
        print(f"Validation failed: Image is null/invalid ({image_path.name})")
        return False
        
    # Due to DPI scaling, check for aspect ratio (approx 16:9) and minimum dimensions instead of exact
    aspect_ratio = img.width() / img.height()
    expected_ratio = 1920 / 1080
    if abs(aspect_ratio - expected_ratio) > 0.1 or img.width() < 1024 or img.height() < 720:
        print(f"Validation failed: Invalid dimensions {img.width()}x{img.height()} vs expected ~16:9 ({image_path.name})")
        return False
        
    size_kb = image_path.stat().st_size / 1024
    if size_kb < min_size_kb:
        print(f"Validation failed: File size too small ({size_kb:.1f}KB < {min_size_kb}KB), likely blank ({image_path.name})")
        return False

    # Calculate basic variance to detect blank/uniform images
    img_scaled = img.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pixels = []
    for y in range(img_scaled.height()):
        for x in range(img_scaled.width()):
            c = img_scaled.pixelColor(x, y)
            pixels.append((c.red(), c.green(), c.blue()))
    
    if not pixels:
        return False
        
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)
    
    var_r = sum((p[0] - avg_r)**2 for p in pixels) / len(pixels)
    var_g = sum((p[1] - avg_g)**2 for p in pixels) / len(pixels)
    var_b = sum((p[2] - avg_b)**2 for p in pixels) / len(pixels)
    
    total_var = var_r + var_g + var_b
    if total_var < 500: # Threshold for a very uniform image (like mostly just solid gray/black)
        print(f"Validation failed: Image too uniform (variance {total_var:.1f}), likely blank ({image_path.name})")
        return False
        
    return True

def capture_all_screenshots():
    # Force dark mode
    sm = SettingsManager()
    sm.theme = "dark"
    tm = ThemeManager.instance()
    tm.set_theme("dark")

    # Start the actual app
    app = DigitalWellbeingApp(start_minimized=False)
    
    win = app._window
    win._apply_theme(True)
    win.resize(1440, 900)
    
    # Wait for initial render and data load (much longer wait than before)
    qapp = QApplication.instance()
    start = time.time()
    print("Waiting for initial application render and data load...")
    while time.time() - start < 5.0:
        qapp.processEvents()
        time.sleep(0.05)

    website_images_dir = Path(__file__).parent / "website" / "public" / "images" / "app"
    website_images_dir.mkdir(parents=True, exist_ok=True)

    pages = [
        (0, "home-dark.png", "Home/Dashboard"),
        (1, "usage-dark.png", "Usage"),
        (2, "focus-dark.png", "Focus"),
        (3, "app-locker-dark.png", "App Locker"),
        (4, "insights-dark.png", "Insights"),
        (5, "sleepguard-dark.png", "SleepGuard"),
        (7, "settings-dark.png", "Settings")
    ]

    all_passed = True
    for index, filename, desc in pages:
        print(f"\nNavigating to {desc} (index {index})...")
        win._navigate(index)
        
        screenshot_path = website_images_dir / filename
        
        max_retries = 3
        success = False
        
        for attempt in range(1, max_retries + 1):
            print(f"  Attempt {attempt} for {desc}...")
            
            # Process events in loop to complete transition animation and data fetch
            # Increase delay depending on attempt
            wait_time = 3.0 + (attempt * 2.0)
            start = time.time()
            while time.time() - start < wait_time:
                qapp.processEvents()
                time.sleep(0.05)
                
            # Create a solid dark background pixmap to replace Mica transparency
            bg_pixmap = QPixmap(win.size())
            bg_pixmap.fill(QColor("#111111"))
            win.render(bg_pixmap)
            
            bg_pixmap.save(str(screenshot_path), "PNG")
            
            if validate_image(screenshot_path):
                print(f"  [PASS] Saved {filename} successfully.")
                success = True
                break
            else:
                print(f"  [RETRY] Screenshot {filename} failed validation.")
                if attempt == max_retries:
                    print(f"  [FAIL] Could not capture a valid screenshot for {desc} after {max_retries} attempts.")
                    all_passed = False
                    
    # --- Capture Authentication Dialog ---
    print("\nNavigating to App Locker to capture Authentication Dialog...")
    win._navigate(3)
    
    from ui.widgets.pin_dialog import PinDialog
    class FakePinManager:
        def verify_pin(self, pin): return False
    
    auth_dialog = PinDialog(FakePinManager(), win)
    # Center the dialog manually since it might use desktop center normally
    auth_dialog.show()
    
    start = time.time()
    while time.time() - start < 3.0:
        qapp.processEvents()
        time.sleep(0.05)
        
    auth_screenshot_path = website_images_dir / "authentication-dark.png"
    pix = win.grab() # grab() captures child widgets like the dialog
    auth_bg = QPixmap(win.size())
    auth_bg.fill(QColor("#111111"))
    painter = QPainter(auth_bg)
    painter.drawPixmap(0, 0, pix)
    painter.end()
    
    auth_bg.save(str(auth_screenshot_path), "PNG")
    if validate_image(auth_screenshot_path):
        print("  [PASS] Saved authentication-dark.png successfully.")
    else:
        print("  [FAIL] Failed to capture valid authentication-dark.png.")
        all_passed = False

    QApplication.instance().quit()
    print("\n--- Final Report ---")
    if all_passed:
        print("ALL screenshots captured and validated successfully.")
    else:
        print("Some screenshots FAILED validation.")
        sys.exit(1)

if __name__ == "__main__":
    capture_all_screenshots()
