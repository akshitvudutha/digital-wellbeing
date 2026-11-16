import ctypes
import psutil

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
print("Input desktop handle:", hdesk)

dw_pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] and 'digitalwellbeing' in p.info['name'].lower()]
print("DigitalWellbeing PIDs:", dw_pids)

found = []
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

def enum_cb(hwnd, lParam):
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in dw_pids:
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        is_vis = user32.IsWindowVisible(hwnd)
        rect = (ctypes.c_long * 4)()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append((hwnd, pid.value, buff.value, bool(is_vis), (rect[2]-rect[0], rect[3]-rect[1])))
    return True

cb_func = WNDENUMPROC(enum_cb)
res = user32.EnumDesktopWindows(hdesk, cb_func, 0)
print(f"EnumDesktopWindows result: {res}, total windows found: {len(found)}")
for h, p, t, v, s in found:
    print(f"  PID={p} HWND={h} Visible={v} Title='{t}' Size={s}")
