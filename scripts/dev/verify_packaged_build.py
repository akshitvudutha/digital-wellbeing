"""
scripts/dev/verify_packaged_build.py — Verifies the newly compiled onedir executable in an isolated test environment.
Checks:
1. Launches dist/DigitalWellbeing/DigitalWellbeing.exe with DW_DB_PATH pointing to scratch/isolated_pkg_test.db.
2. Checks that the process only creates one top-level window titled 'Notch v3.6.3'.
3. Verifies that NO rogue floating window titled 'Notch' exists.
4. Captures the window to scratch/packaged_app_verified.png.
5. Shuts down cleanly.
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
import sqlite3
from pathlib import Path
from datetime import date, timedelta

import ctypes
import win32gui
import win32process
import win32ui
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from core.version import get_version
SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_DIR.mkdir(exist_ok=True)

TEST_DB = SCRATCH_DIR / "isolated_pkg_test.db"
EXE_PATH = PROJECT_ROOT / "dist" / "DigitalWellbeing" / "DigitalWellbeing.exe"


def setup_test_db(db_path: Path):
    if db_path.exists():
        db_path.unlink()
    from database.repository import Repository
    Repository.set_db_path_override(db_path)
    repo = Repository()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with repo._connection() as conn:
        cur = conn.cursor()
        # Yesterday: 2 hours (7200s)
        cur.execute(
            "INSERT INTO app_sessions (process_name, window_title, category, duration_s, is_idle, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("chrome.exe", "Chrome", "Browser", 7200.0, 0, f"{yesterday}T10:00:00", f"{yesterday}T12:00:00")
        )
        # Today: 8 hours (28800s) -> +300% trend
        cur.execute(
            "INSERT INTO app_sessions (process_name, window_title, category, duration_s, is_idle, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("code.exe", "Visual Studio Code", "Programming", 28800.0, 0, f"{today}T08:00:00", f"{today}T16:00:00")
        )
        conn.commit()


def find_windows_for_pid(target_pid: int):
    found = []
    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == target_pid:
            text = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w > 0 and h > 0:
                found.append((hwnd, text, rect, (w, h)))
        return True
    win32gui.EnumWindows(enum_cb, None)
    return found


def capture_hwnd(hwnd: int, out_path: Path):
    r = win32gui.GetWindowRect(hwnd)
    w = r[2] - r[0]
    h = r[3] - r[1]
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)
    res = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
    if not res:
        ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    im.save(out_path)


def main():
    if not EXE_PATH.exists():
        print(f"Error: {EXE_PATH} does not exist!")
        sys.exit(1)

    print("Setting up isolated test database...")
    setup_test_db(TEST_DB)

    env = os.environ.copy()
    env["DW_TEST_MODE"] = "1"
    env["DW_DB_PATH"] = str(TEST_DB)
    # Use isolated IPC server name so it doesn't conflict with any background instance
    env["DW_IPC_NAME"] = "Notch_Verification_Isolated_Test"

    print(f"Launching packaged executable: {EXE_PATH}...")
    proc = subprocess.Popen([str(EXE_PATH)], env=env)
    print(f"Launched packaged app PID={proc.pid}")

    try:
        # Wait up to 30 seconds for main window to appear
        windows = []
        for _ in range(60):
            time.sleep(0.5)
            windows = find_windows_for_pid(proc.pid)
            if any("Notch" in title for _, title, _, _ in windows):
                break
        print(f"Found {len(windows)} visible windows for PID {proc.pid}:")
        main_window_found = False
        rogue_window_found = False

        for hwnd, title, rect, size in windows:
            print(f"  - HWND={hwnd} Title='{title}' Size={size} Rect={rect}")
            if f"Notch v{get_version()}" in title:
                main_window_found = True
                capture_path = SCRATCH_DIR / "packaged_app_verified.png"
                capture_hwnd(hwnd, capture_path)
                print(f"    -> Captured main window to {capture_path}")
            elif title == "Notch" and size[0] < 300 and size[1] < 150:
                rogue_window_found = True
                print("    -> ALERT: Rogue mini window detected!")

        assert main_window_found, f"Main window titled 'Notch v{get_version()}' was not found!"
        assert not rogue_window_found, "Rogue floating window was detected!"
        assert len(windows) == 1, f"Expected exactly 1 top-level window, but found {len(windows)}: {windows}"

        print("SUCCESS: Packaged application verified! Exactly 1 top-level window, zero rogue windows!")
    finally:
        print("Terminating test process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Test process terminated cleanly.")


if __name__ == "__main__":
    main()
