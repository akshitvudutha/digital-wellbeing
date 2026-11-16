import time
import win32gui
import win32con
from PIL import ImageGrab

def callback(hwnd, windows):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if "Digital Wellbeing" in title:
            windows.append((hwnd, title))
    return True

def take_window_screenshot(output_path):
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if not windows:
        print("Window 'Digital Wellbeing' not found!")
        return False
        
    hwnd, title = windows[0]
    print(f"Found window '{title}' with HWND {hwnd}")
    
    # Restore if minimized
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    
    # Bring to front
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"SetForegroundWindow failed: {e}")
        
    time.sleep(1.0)  # Wait for window to come to front and render
    
    # Get window rect
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    print(f"Window rect: {left}, {top}, {right}, {bottom}")
    
    # Capture bounding box
    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(output_path)
    print(f"Screenshot saved to {output_path}")
    return True

if __name__ == "__main__":
    take_window_screenshot(r"C:\Users\akshi\.gemini\antigravity-ide\brain\08810c96-653f-4f09-8c2b-87d4285f5d28\scratch\live_window.png")
