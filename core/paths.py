from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from core.constants import DB_FILENAME, LOG_FILENAME

DATA_DIR_ENV = "NYW_DATA_DIR"


def get_data_dir(
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    create: bool = True,
) -> Path:
    """Return NYW's platform-native, per-user data directory.

    ``NYW_DATA_DIR`` takes precedence so portable installations and tests can
    keep every local artifact in an explicitly selected directory.
    """
    env = os.environ if environ is None else environ
    custom_dir = env.get(DATA_DIR_ENV, "").strip()
    if custom_dir:
        path = Path(custom_dir).expanduser()
    else:
        platform_id = (platform_name or sys.platform).lower()
        user_home = home or Path.home()

        if platform_id.startswith("win"):
            local_app_data = env.get("LOCALAPPDATA", "").strip()
            base = Path(local_app_data).expanduser() if local_app_data else user_home / "AppData" / "Local"
            path = base / "DigitalWellbeing"
        elif platform_id == "darwin":
            path = user_home / "Library" / "Application Support" / "DigitalWellbeing"
        else:
            xdg_data_home = env.get("XDG_DATA_HOME", "").strip()
            base = Path(xdg_data_home).expanduser() if xdg_data_home else user_home / ".local" / "share"
            path = base / "digital-wellbeing"

    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path(**kwargs: object) -> Path:
    return get_data_dir(**kwargs) / DB_FILENAME


def get_log_path(**kwargs: object) -> Path:
    return get_data_dir(**kwargs) / LOG_FILENAME
