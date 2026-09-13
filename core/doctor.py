from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from core.constants import APP_NAME, APP_VERSION, DB_FILENAME
from core.logger import get_log_path
from tracker.platform_support import Capability, get_tracking_capabilities
from utils.win_utils import get_app_user_data_dir

_REQUIRED_CAPABILITIES = {"foreground_tracking", "idle_detection"}


@dataclass(frozen=True)
class DiagnosticReport:
    application: str
    version: str
    python: str
    operating_system: str
    desktop_session: str
    data_directory: str
    database_file: str
    log_file: str
    capabilities: list[Capability]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ready"] = self.is_ready
        return payload

    @property
    def is_ready(self) -> bool:
        by_name = {item.name: item.available for item in self.capabilities}
        return all(by_name.get(name, False) for name in _REQUIRED_CAPABILITIES)


def _safe_display_path(path: Path, home: Path | None = None) -> str:
    """Display home-relative paths without leaking the account name."""
    resolved_home = (home or Path.home()).resolve()
    resolved_path = path.expanduser().resolve()
    try:
        relative = resolved_path.relative_to(resolved_home)
    except ValueError:
        return str(resolved_path)
    return str(Path("~") / relative)


def _desktop_session(platform_name: str, environ: dict[str, str]) -> str:
    if platform_name.startswith("linux"):
        return environ.get("XDG_SESSION_TYPE") or ("Wayland" if environ.get("WAYLAND_DISPLAY") else "X11" if environ.get("DISPLAY") else "unknown")
    if platform_name == "darwin":
        return "Aqua"
    if platform_name.startswith("win"):
        return "Windows desktop"
    return "unknown"


def build_report() -> DiagnosticReport:
    platform_name = sys.platform.lower()
    environ = dict(os.environ)
    data_dir = get_app_user_data_dir()
    return DiagnosticReport(
        application=APP_NAME,
        version=APP_VERSION,
        python=platform.python_version(),
        operating_system=f"{platform.system()} {platform.release()}",
        desktop_session=_desktop_session(platform_name, environ),
        data_directory=_safe_display_path(data_dir),
        database_file=_safe_display_path(data_dir / DB_FILENAME),
        log_file=_safe_display_path(get_log_path()),
        capabilities=get_tracking_capabilities(
            platform_name=platform_name,
            environ=environ,
        ),
    )


def format_human(report: DiagnosticReport) -> str:
    lines = [
        f"{report.application} {report.version} setup report",
        f"Python: {report.python}",
        f"Operating system: {report.operating_system}",
        f"Desktop session: {report.desktop_session}",
        f"Local data: {report.data_directory}",
        f"Local SQLite file: {report.database_file}",
        f"Log file: {report.log_file}",
        "Capabilities:",
    ]
    for capability in report.capabilities:
        marker = "OK" if capability.available else "UNAVAILABLE"
        lines.append(f"  [{marker}] {capability.name}: {capability.detail}")
    lines.append(f"Core tracking ready: {'yes' if report.is_ready else 'no'}")
    return "\n".join(lines)


def run_doctor(*, as_json: bool = False) -> int:
    report = build_report()
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_human(report))
    return 0 if report.is_ready else 1
