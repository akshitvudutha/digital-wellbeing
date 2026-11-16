import ctypes
import win32gui
import win32ui
from PIL import Image
from pathlib import Path

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

hwnd = 6753718

rect = (ctypes.c_long * 4)()
user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
w = rect[2] - rect[0]
h = rect[3] - rect[1]
print(f"HWND {hwnd} rect: {rect[:]} size={w}x{h}")

hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()
saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitMap)

res = user32.PrintWindow(ctypes.c_void_p(hwnd), saveDC.GetSafeHdc(), 2)
if not res:
    res = user32.PrintWindow(ctypes.c_void_p(hwnd), saveDC.GetSafeHdc(), 0)

bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
im = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)

out_path = Path("scratch/live_installed_app_verified.png")
im.save(out_path)
print(f"Successfully saved live installed window capture to {out_path} (size={w}x{h})")
