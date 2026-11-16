import time
import win32gui
import win32con

def callback(hwnd, windows):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            windows.append((hwnd, title))
    return True

def list_windows():
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    print("Visible windows:")
    for hwnd, title in windows:
        print(f"[{hwnd}] {title}")
    return True

if __name__ == "__main__":
    list_windows()
