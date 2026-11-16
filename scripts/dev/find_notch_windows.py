import ctypes
import win32gui
import win32ui
import win32process
import psutil
from PIL import Image
from pathlib import Path


out_dir = Path(r"d:\Projects\Digital Wellbeing\scratch")
out_dir.mkdir(exist_ok=True)

def capture_hwnd(hwnd, filename):
    r = win32gui.GetWindowRect(hwnd)
    w = r[2] - r[0]
    h = r[3] - r[1]
    if w <= 0 or h <= 0:
        print(f"HWND {hwnd} has invalid dimensions {w}x{h}")
        return
    
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)
    
    result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
    if not result:
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
    
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
    
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    
    out_path = out_dir / filename
    im.save(out_path)
    print(f"Saved HWND {hwnd} capture to {out_path} (size={w}x{h})")

# Find all DigitalWellbeing processes
dw_pids = []
for p in psutil.process_iter(['pid', 'name']):
    if p.info['name'] and 'digitalwellbeing' in p.info['name'].lower():
        dw_pids.append(p.info['pid'])

print(f"DigitalWellbeing PIDs: {dw_pids}")

found_windows = []
def enum_cb(hwnd, _):
    try:
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in dw_pids:
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                found_windows.append((hwnd, pid, title, rect, (w, h)))
    except Exception as e:
        print("Error in cb:", e)
    return True

import pywintypes
try:
    win32gui.EnumWindows(enum_cb, None)
except pywintypes.error:
    pass
print(f"Total windows found: {len(found_windows)}")
for hwnd, pid, title, rect, size in found_windows:
    print(f"PID={pid} HWND={hwnd} Title='{title}' Size={size} Rect={rect}")
    if title:
        safe_name = "".join(c for c in title if c.isalnum() or c in "._- ")
        capture_hwnd(hwnd, f"window_{pid}_{safe_name}.png")
