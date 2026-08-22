from __future__ import annotations

import json
import os
import threading
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from PySide6.QtCore import QObject, Signal

from core.constants import APP_NAME, APP_VERSION
from core.logger import logger
from settings.manager import SettingsManager


GITHUB_OWNER = "akshitvudutha"
GITHUB_REPO = "digital-wellbeing"
# Allow overriding API base (for GitHub Enterprise) via env
GITHUB_API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com")
GITHUB_API_RELEASES_LATEST = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


class Updater(QObject):
    """Simple GitHub Releases based updater.

    - Non-blocking check_for_updates() spawns a background thread.
    - Emits update_available when a newer release with a matching installer asset is found.
    - download_progress emits percent ints during download.
    - download_complete emits the local installer path when finished.
    - error emitted on failures.
    """

    update_available = Signal(object)  # dict with keys: version, notes, asset_name, asset_url
    no_update = Signal()
    error = Signal(str)
    download_progress = Signal(int)
    download_complete = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sm = SettingsManager()
        self._checking = threading.Event()
        self._download_thread: Optional[threading.Thread] = None
        # Allow using a GitHub token for private releases; read from env or settings
        self._api_base = os.environ.get("GITHUB_API_BASE", GITHUB_API_BASE)
        token_env = os.environ.get("GITHUB_TOKEN")
        token_setting = self._sm.get("github_token", "")
        self._token = token_env or (token_setting if token_setting else None)

    def _compare_versions(self, a: str, b: str) -> int:
        """Return -1 if a<b, 0 if equal, 1 if a>b. Basic numeric-semver compare.
        Non-numeric parts are compared lexically. Treat empty/Unknown as older than any real version.
        """
        if not a or str(a).strip().lower() == "unknown":
            if not b or str(b).strip().lower() == "unknown":
                return 0
            return -1
        if not b or str(b).strip().lower() == "unknown":
            return 1

        def norm(v: str):
            return [int(x) if x.isdigit() else x for x in v.replace('v', '').split('.')]
        try:
            na = norm(str(a))
            nb = norm(str(b))
            for x, y in zip(na, nb):
                if x == y:
                    continue
                try:
                    return 1 if x > y else -1
                except Exception:
                    return 1 if str(x) > str(y) else -1
            # longer sequence with additional numeric parts is considered greater
            if len(na) == len(nb):
                return 0
            return 1 if len(na) > len(nb) else -1
        except Exception:
            # fallback to lexical compare of full strings
            try:
                if str(a) == str(b):
                    return 0
                return 1 if str(a) > str(b) else -1
            except Exception:
                return 0

    def check_for_updates(self, force: bool = False) -> None:
        if not force and not self._sm.get_bool("auto_update_check", True):
            logger.info("Auto-update check disabled in settings")
            return
        if self._checking.is_set():
            logger.info("Update check already in progress")
            return
        t = threading.Thread(target=self._check_thread, name="Updater-check-thread", daemon=True)
        t.start()

    def _check_thread(self) -> None:
        self._checking.set()
        try:
            logger.info("Updater: querying GitHub releases for latest... %s", self._api_base)
            headers = {"User-Agent": APP_NAME}
            if self._token:
                headers["Authorization"] = f"token {self._token}"

            req = Request(f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases", headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.load(resp)
            
            best_release = None
            best_version = APP_VERSION
            
            for release in data:
                if release.get("draft") or release.get("prerelease"):
                    continue
                tag = release.get("tag_name") or release.get("name") or ""
                if self._compare_versions(best_version, str(tag)) < 0:
                    best_version = str(tag)
                    best_release = release

            if not best_release or self._compare_versions(APP_VERSION, best_version) >= 0:
                self.no_update.emit()
                return

            # find an installer asset (Windows exe) — prefer asset name containing 'DigitalWellbeing' or 'Setup' and '.exe'
            assets = best_release.get("assets", []) or []
            chosen = None
            for a in assets:
                name = a.get("name", "").lower()
                if name.endswith(".exe") and ("setup" in name or "digitalwellbeing" in name):
                    chosen = a
                    break
            if not chosen and assets:
                # fallback to first exe
                for a in assets:
                    if a.get("name", "").lower().endswith(".exe"):
                        chosen = a
                        break
            if not chosen:
                self.error.emit("No suitable installer asset found in release")
                return
                
            asset_name = chosen.get("name")
            asset_url = chosen.get("browser_download_url")
            asset_id = chosen.get("id")
            
            # Find checksum asset if available
            checksum_asset = None
            for a in assets:
                if a.get("name", "").endswith(".sha256"):
                    checksum_asset = a
                    break
                    
            checksum_url = checksum_asset.get("browser_download_url") if checksum_asset else None
            checksum_id = checksum_asset.get("id") if checksum_asset else None
            
            notes = best_release.get("body", "")
            payload = {
                "version": best_version, 
                "notes": notes, 
                "asset_name": asset_name, 
                "asset_url": asset_url, 
                "asset_id": asset_id,
                "checksum_url": checksum_url,
                "checksum_id": checksum_id
            }
            self.update_available.emit(payload)
        except HTTPError as e:
            logger.exception("Updater HTTP error: %s", e)
            self.error.emit(f"HTTP error when checking updates: {e}")
        except URLError as e:
            logger.exception("Updater URL error: %s", e)
            self.error.emit(f"Network error when checking updates: {e}")
        except Exception as e:
            logger.exception("Updater unexpected error: %s", e)
            self.error.emit(f"Unexpected error when checking updates: {e}")
        finally:
            self._checking.clear()

    def download_installer(self, asset_url: str, asset_name: str, asset_id: Optional[int] = None, checksum_url: Optional[str] = None, checksum_id: Optional[int] = None) -> None:
        if self._download_thread and self._download_thread.is_alive():
            logger.info("Download already in progress")
            return
        self._download_thread = threading.Thread(target=self._download_thread_fn, args=(asset_url, asset_name, asset_id, checksum_url, checksum_id), daemon=True)
        self._download_thread.start()

    def _download_thread_fn(self, asset_url: str, asset_name: str, asset_id: Optional[int], checksum_url: Optional[str], checksum_id: Optional[int]) -> None:
        try:
            logger.info("Updater: downloading asset. asset_id=%s, url=%s", str(asset_id), asset_url)
            headers = {"User-Agent": APP_NAME}
            req_url = asset_url
            if self._token and asset_id:
                req_url = f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{asset_id}"
                headers["Accept"] = "application/octet-stream"
                headers["Authorization"] = f"token {self._token}"
            req = Request(req_url, headers=headers)
            with urlopen(req, timeout=60) as resp:
                total = resp.getheader("Content-Length")
                total = int(total) if total and total.isdigit() else None
                tmp_dir = Path(tempfile.gettempdir()) / APP_NAME.replace(" ", "_")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                out_path = tmp_dir / asset_name
                written = 0
                chunk_size = 64 * 1024
                with open(out_path, "wb") as out_f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        written += len(chunk)
                        if total:
                            percent = int(written * 100 / total)
                            self.download_progress.emit(percent)
                if total and written != total:
                    raise IOError("Downloaded size does not match Content-Length")
                    
                # Download and Verify Checksum
                if checksum_url:
                    chk_req_url = checksum_url
                    if self._token and checksum_id:
                        chk_req_url = f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{checksum_id}"
                    
                    try:
                        chk_req = Request(chk_req_url, headers=headers)
                        with urlopen(chk_req, timeout=15) as chk_resp:
                            expected_hash = chk_resp.read().decode('utf-8').strip().split()[0].lower()
                            
                        import hashlib
                        sha256_hash = hashlib.sha256()
                        with open(out_path, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                                
                        actual_hash = sha256_hash.hexdigest().lower()
                        if actual_hash != expected_hash:
                            out_path.unlink(missing_ok=True)
                            raise ValueError(f"Checksum verification failed! Expected: {expected_hash}, Actual: {actual_hash}")
                        logger.info("Checksum verified successfully.")
                    except Exception as ce:
                        logger.warning(f"Checksum verification process encountered an error: {ce}")
                        if isinstance(ce, ValueError):
                            raise ce # Propagate the checksum mismatch error
                            
                logger.info("Updater: download complete %s", out_path)
                self.download_complete.emit(str(out_path))
        except Exception as e:
            logger.exception("Updater download failed: %s", e)
            self.error.emit(str(e))

    def launch_installer_and_exit(self, installer_path: str) -> None:
        """Spawn installer via a temporary PowerShell script that waits for the installer
        to finish, deletes temporary artifacts, then restarts the application.
        The script is launched in a detached process so the updater can exit immediately.
        """
        try:
            p = Path(installer_path)
            if not p.exists():
                raise FileNotFoundError("Installer not found: %s" % installer_path)

            import sys
            app_exec = sys.executable

            tmp_dir = Path(tempfile.gettempdir()) / APP_NAME.replace(" ", "_")
            tmp_dir.mkdir(parents=True, exist_ok=True)
            ps1 = tmp_dir / f"{APP_NAME.replace(' ','_')}_run_update.ps1"

            # Use /SILENT instead of /VERYSILENT so user sees the progress, per requirements.
            ps_contents = f"Start-Process -FilePath '{str(p)}' -ArgumentList '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait\nStart-Sleep -Seconds 1\nTry {{ Remove-Item -LiteralPath '{str(p)}' -Force -ErrorAction SilentlyContinue }} Catch {{}}\nTry {{ Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue }} Catch {{}}\nStart-Process -FilePath '{app_exec}'\n"

            with open(ps1, "w", encoding="utf-8") as f:
                f.write(ps_contents)

            logger.info("Updater: launching installer PowerShell wrapper %s", ps1)
            DETACHED = 0x00000008
            subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)], shell=False, creationflags=DETACHED)
        except Exception as e:
            logger.exception("Failed to launch installer: %s", e)
            self.error.emit(str(e))
