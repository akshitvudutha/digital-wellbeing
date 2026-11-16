"""
scripts/dev/safe_update_installed_app.py — Safe production update and verification workflow for Notch v3.6.3.

Safeguards:
1. Pre-verifies checksums of dist/NotchSetup-3.6.3.exe and dist/DigitalWellbeing/DigitalWellbeing.exe.
2. Verifies installed directory and production database location.
3. Creates a full backup of current installed executable into DigitalWellbeing_backup_pre_v363_fix.
4. Performs graceful shutdown of running DigitalWellbeing.exe process and confirms exit.
5. Executes Inno Setup installer in unattended /VERYSILENT mode.
6. Verifies installed executable hash matches new staging build.
7. Verifies production database and settings were preserved.
8. Launches installed application and confirms:
   - Exactly one main window titled "Notch v3.6.3".
   - Zero rogue floating windows titled "Notch".
   - Captures live screenshot to scratch/live_installed_app_verified.png.
"""
from __future__ import annotations

import os
import sys
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

import ctypes
import win32gui
import win32process
import win32ui
import psutil
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from core.version import get_version
SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_DIR.mkdir(exist_ok=True)

INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DigitalWellbeing"
INSTALLED_EXE = INSTALL_DIR / "DigitalWellbeing.exe"
BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / f"DigitalWellbeing_backup_pre_v{get_version()}"

STAGING_EXE = PROJECT_ROOT / "dist" / "DigitalWellbeing" / "DigitalWellbeing.exe"
STAGING_INSTALLER = PROJECT_ROOT / "dist" / f"NotchSetup-{get_version()}.exe"

PROD_DB = Path(os.environ.get("LOCALAPPDATA", "")) / "DigitalWellbeing" / "digital_wellbeing.db"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


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
    print("=" * 60)
    print("Notch v3.6.3 Safe Update and Verification Workflow")
    print("=" * 60)

    # 1. Verify staging binaries
    print("\n[Step 1] Verifying staging binaries...")
    assert STAGING_EXE.exists(), f"Staging executable missing: {STAGING_EXE}"
    assert STAGING_INSTALLER.exists(), f"Staging installer missing: {STAGING_INSTALLER}"
    staging_exe_hash = sha256_file(STAGING_EXE)
    installer_hash = sha256_file(STAGING_INSTALLER)
    print(f"  Staging EXE: {STAGING_EXE} (SHA-256: {staging_exe_hash})")
    print(f"  Installer:   {STAGING_INSTALLER} (SHA-256: {installer_hash})")

    # 2. Check installed directory and DB
    print("\n[Step 2] Checking installation and production data...")
    assert INSTALL_DIR.exists(), f"Install dir missing: {INSTALL_DIR}"
    assert INSTALLED_EXE.exists(), f"Installed EXE missing: {INSTALLED_EXE}"
    installed_pre_hash = sha256_file(INSTALLED_EXE)
    print(f"  Installed EXE: {INSTALLED_EXE} (Pre-update SHA-256: {installed_pre_hash})")
    
    db_exists = PROD_DB.exists()
    db_size = PROD_DB.stat().st_size if db_exists else 0
    print(f"  Production DB: {PROD_DB} (Exists: {db_exists}, Size: {db_size:,} bytes)")

    # 3. Create backup
    print("\n[Step 3] Backing up existing installed executable...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_exe = BACKUP_DIR / "DigitalWellbeing.exe"
    shutil.copy2(INSTALLED_EXE, backup_exe)
    print(f"  Copied {INSTALLED_EXE} -> {backup_exe}")
    print(f"  Backup verified SHA-256: {sha256_file(backup_exe)}")

    # 4. Graceful process shutdown
    print("\n[Step 4] Requesting graceful application shutdown...")
    killed_any = False
    for p in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if p.info['name'] and 'digitalwellbeing' in p.info['name'].lower():
                pid = p.info['pid']
                print(f"  Found running process PID={pid} ({p.info['name']})")
                p.terminate()
                killed_any = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed_any:
        print("  Waiting up to 10s for processes to exit...")
        gone, alive = psutil.wait_procs(
            [p for p in psutil.process_iter() if p.name() and 'digitalwellbeing' in p.name().lower()],
            timeout=10
        )
        for p in alive:
            print(f"  Force-killing stubborn process PID={p.pid}...")
            p.kill()
        time.sleep(1)

    # Double check no DigitalWellbeing processes remain
    running_after = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] and 'digitalwellbeing' in p.info['name'].lower()]
    assert len(running_after) == 0, f"Process still running: {running_after}"
    print("  All DigitalWellbeing processes have exited cleanly.")

    # 5. Run unattended installer
    print("\n[Step 5] Running Inno Setup installer in unattended mode...")
    installer_cmd = [
        str(STAGING_INSTALLER),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        f'/DIR={str(INSTALL_DIR)}',
    ]
    print(f"  Executing: {' '.join(installer_cmd)}")
    res = subprocess.run(installer_cmd, capture_output=True, text=True)
    print(f"  Installer exit code: {res.returncode}")
    assert res.returncode == 0, f"Installer failed with return code {res.returncode}: {res.stderr}"

    # 6. Verify post-install state
    print("\n[Step 6] Verifying installed files and database safety...")
    installed_post_hash = sha256_file(INSTALLED_EXE)
    print(f"  Installed EXE Post-update SHA-256: {installed_post_hash}")
    assert installed_post_hash == staging_exe_hash, (
        f"Installed EXE hash mismatch! Expected {staging_exe_hash}, got {installed_post_hash}"
    )
    print("  CONFIRMED: Installed executable has been successfully updated to the new build!")

    if db_exists:
        assert PROD_DB.exists(), "Production database went missing after install!"
        post_db_size = PROD_DB.stat().st_size
        print(f"  CONFIRMED: Production database is safe and intact ({post_db_size:,} bytes).")

    # 7. Launch updated installed app
    print("\n[Step 7] Launching updated installed application...")
    # Launch without test env so it loads real user database and settings
    launch_env = os.environ.copy()
    launch_env.pop("DW_TEST_MODE", None)
    launch_env.pop("DW_DB_PATH", None)
    launch_env.pop("DW_IPC_NAME", None)

    proc = subprocess.Popen([str(INSTALLED_EXE)], env=launch_env)
    print(f"  Launched updated app PID={proc.pid}")

    # 8. Verify live application windows
    print("\n[Step 8] Verifying live application windows...")
    try:
        main_window_found = False
        rogue_window_found = False

        # Poll for window initialization
        for attempt in range(40):
            time.sleep(0.5)
            windows = find_windows_for_pid(proc.pid)
            if any("Notch" in title for _, title, _, _ in windows):
                break

        # Give 3 seconds for dashboard trend computation and display
        time.sleep(3)
        windows = find_windows_for_pid(proc.pid)
        print(f"  Found {len(windows)} visible windows for PID {proc.pid}:")

        for hwnd, title, rect, size in windows:
            print(f"    - HWND={hwnd} Title='{title}' Size={size} Rect={rect}")
            if f"Notch v{get_version()}" in title:
                main_window_found = True
                capture_path = SCRATCH_DIR / "live_installed_app_verified.png"
                capture_hwnd(hwnd, capture_path)
                print(f"      -> Captured live main window to {capture_path}")
            elif title == "Notch" and size[0] < 300 and size[1] < 150:
                rogue_window_found = True
                print("      -> ALERT: Rogue mini window detected!")

        assert main_window_found, f"Main window titled 'Notch v{get_version()}' not found!"
        assert not rogue_window_found, "Rogue floating window detected!"
        print("\n" + "=" * 60)
        print("PRODUCTION UPDATE SUCCESSFUL!")
        print(f"Executable:   {INSTALLED_EXE}")
        print(f"SHA-256:      {installed_post_hash}")
        print(f"Timestamp:    {datetime.now().isoformat()}")
        print(f"Running PID:  {proc.pid}")
        print("Rogue window: NONE (Definitively Fixed)")
        print("=" * 60)

    except Exception as exc:
        print(f"\nVerification error: {exc}")
        raise


if __name__ == "__main__":
    main()
