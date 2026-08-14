"""
updater.py - Core update logic for Digital Wellbeing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.logger import logger
from core.constants import APP_VERSION


# GitHub Repository details
REPO_OWNER = "akshitvudutha"
REPO_NAME = "digital-wellbeing"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"

# Used for safe test mode / mocking
_MOCK_RELEASE_DATA = None


@dataclass
class UpdateInfo:
    version: str
    release_notes: str
    installer_url: str
    checksum_url: Optional[str]
    installer_filename: str


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a semantic version string into a tuple of integers for comparison."""
    # Strip any leading 'v'
    v = version_str.lstrip("vV")
    
    # Extract only the numeric parts (e.g., '2.5.2' from '2.5.2-beta')
    match = re.match(r"^(\d+\.\d+\.\d+)", v)
    if not match:
        return (0, 0, 0)
        
    try:
        return tuple(int(x) for x in match.group(1).split("."))
    except ValueError:
        return (0, 0, 0)


def is_newer(current: str, latest: str) -> bool:
    """Return True if latest is strictly greater than current."""
    cur_tuple = parse_version(current)
    lat_tuple = parse_version(latest)
    
    # Ignore invalid versions
    if cur_tuple == (0, 0, 0) or lat_tuple == (0, 0, 0):
        return False
        
    return lat_tuple > cur_tuple


def get_current_version() -> str:
    return APP_VERSION


def set_mock_release_data(data: list[dict] | None) -> None:
    """Set mock data to simulate GitHub API response for testing."""
    global _MOCK_RELEASE_DATA
    _MOCK_RELEASE_DATA = data


def check_for_update(current_version: str = None) -> Optional[UpdateInfo]:
    """
    Check the GitHub API for a stable release newer than current_version.
    Returns UpdateInfo if a valid update is found, otherwise None.
    """
    if current_version is None:
        current_version = get_current_version()

    try:
        if _MOCK_RELEASE_DATA is not None:
            releases = _MOCK_RELEASE_DATA
        else:
            req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to check for updates: HTTP {response.status}")
                    return None
                data = response.read()
                releases = json.loads(data)

        # Find the latest stable release by iterating all releases and picking the highest semantic version
        best_release = None
        best_version_tuple = parse_version(current_version)

        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue

            tag_name = release.get("tag_name", "")
            release_tuple = parse_version(tag_name)
            
            # Keep track of the strictly highest semantic version
            if release_tuple > best_version_tuple:
                best_version_tuple = release_tuple
                best_release = release

        if best_release:
            tag_name = best_release.get("tag_name", "")
            installer_asset = None
            checksum_asset = None
            
            for asset in best_release.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe") and "Setup" in name:
                    installer_asset = asset
                elif name.endswith(".sha256"):
                    checksum_asset = asset

            if installer_asset:
                return UpdateInfo(
                    version=tag_name.lstrip("vV"),
                    release_notes=best_release.get("body", "No release notes provided."),
                    installer_url=installer_asset.get("browser_download_url"),
                    checksum_url=checksum_asset.get("browser_download_url") if checksum_asset else None,
                    installer_filename=installer_asset.get("name", "DigitalWellbeingSetup.exe")
                )

    except urllib.error.URLError as e:
        logger.warning(f"Network error checking for updates: {e}")
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")

    return None


def download_update(update_info: UpdateInfo, progress_callback: Callable[[int, int], None] = None) -> Path:
    """
    Download the installer and its checksum (if available) to a temporary directory.
    Returns the Path to the downloaded installer.
    """
    temp_dir = Path(tempfile.gettempdir()) / "DigitalWellbeingUpdates"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    installer_path = temp_dir / update_info.installer_filename
    
    # Download installer
    try:
        req = urllib.request.Request(update_info.installer_url)
        with urllib.request.urlopen(req, timeout=15) as response:
            total_size = int(response.getheader("Content-Length", 0))
            
            with open(installer_path, "wb") as f:
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
    except Exception as e:
        logger.error(f"Failed to download installer: {e}")
        if installer_path.exists():
            installer_path.unlink(missing_ok=True)
        raise e

    # Download checksum if available
    if update_info.checksum_url:
        checksum_path = installer_path.with_suffix(".exe.sha256")
        try:
            req = urllib.request.Request(update_info.checksum_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(checksum_path, "wb") as f:
                    f.write(response.read())
        except Exception as e:
            logger.warning(f"Failed to download checksum: {e}")
            # Do not fail the whole download just because checksum download failed,
            # verification will handle it (or warn).

    return installer_path


def verify_update(installer_path: Path) -> bool:
    """
    Verify the SHA-256 checksum of the downloaded installer if a .sha256 file exists.
    Returns True if valid or if no checksum is available.
    Returns False if verification fails.
    """
    if not installer_path.exists():
        return False
        
    checksum_path = installer_path.with_suffix(".exe.sha256")
    if not checksum_path.exists():
        logger.info("No checksum file found; skipping verification.")
        return True
        
    try:
        # Read the expected checksum
        with open(checksum_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Handle formats like "SHA256 filename" or just the hash
            expected_hash = content.split()[0].lower()
            
        # Calculate actual checksum
        sha256_hash = hashlib.sha256()
        with open(installer_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        actual_hash = sha256_hash.hexdigest().lower()
        
        if actual_hash == expected_hash:
            logger.info("Checksum verification passed.")
            return True
        else:
            logger.error(f"Checksum mismatch! Expected: {expected_hash}, Actual: {actual_hash}")
            return False
            
    except Exception as e:
        logger.error(f"Error during checksum verification: {e}")
        return False


def launch_installer(installer_path: Path) -> bool:
    """
    Launch the installer in silent or semi-silent mode.
    Note: The application should be gracefully closed shortly after calling this,
    or the installer might complain that files are in use.
    """
    if not installer_path.exists():
        logger.error("Installer not found to launch.")
        return False
        
    try:
        # We launch the installer using Popen so it runs independently
        # /SP- disables the "This will install... Do you wish to continue?" prompt
        # /SILENT makes it show progress but not ask questions. 
        # But per requirements "DO NOT silently install updates... The user must explicitly press Update Now".
        # Once they press it, the install itself can be automated. 
        # Using /SILENT allows them to see it installing without clicking Next over and over.
        # But if we use /VERYSILENT it is fully hidden. /SILENT is safer for visibility.
        logger.info(f"Launching installer: {installer_path}")
        subprocess.Popen([str(installer_path), "/SILENT", "/SP-", "/SUPPRESSMSGBOXES", "/NOCANCEL"])
        return True
    except Exception as e:
        logger.error(f"Failed to launch installer: {e}")
        return False
