from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.doctor import (
    DiagnosticReport,
    _desktop_session,
    _safe_display_path,
    format_human,
)
from tracker.platform_support import Capability


def report_with(*capabilities: Capability) -> DiagnosticReport:
    return DiagnosticReport(
        application="Not Your Wellbeing",
        version="1.2.3",
        python="3.11.0",
        operating_system="TestOS 1",
        desktop_session="test",
        data_directory="~/data",
        database_file="~/data/digital_wellbeing.db",
        log_file="~/data/digital_wellbeing.log",
        capabilities=list(capabilities),
    )


class DoctorTests(unittest.TestCase):
    def test_report_is_ready_when_core_capabilities_are_available(self) -> None:
        report = report_with(
            Capability("foreground_tracking", True, "ready"),
            Capability("idle_detection", True, "ready"),
            Capability("media_detection", False, "optional"),
        )
        self.assertTrue(report.is_ready)
        self.assertTrue(report.to_dict()["ready"])

    def test_report_is_degraded_when_required_capability_is_missing(self) -> None:
        report = report_with(
            Capability("foreground_tracking", False, "Wayland is unsupported"),
            Capability("idle_detection", True, "ready"),
        )
        self.assertFalse(report.is_ready)
        output = format_human(report)
        self.assertIn("[UNAVAILABLE] foreground_tracking", output)
        self.assertIn("Core tracking ready: no", output)

    def test_json_payload_is_machine_readable(self) -> None:
        report = report_with(
            Capability("foreground_tracking", True, "ready"),
            Capability("idle_detection", True, "ready"),
        )
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["capabilities"][0]["name"], "foreground_tracking")

    def test_home_path_masks_account_name(self) -> None:
        shown = _safe_display_path(
            Path("/Users/private-name/Library/Application Support/DigitalWellbeing"),
            home=Path("/Users/private-name"),
        )
        self.assertEqual(shown, str(Path("~") / "Library" / "Application Support" / "DigitalWellbeing"))
        self.assertNotIn("private-name", shown)

    def test_desktop_session_detection(self) -> None:
        self.assertEqual(_desktop_session("linux", {"XDG_SESSION_TYPE": "wayland"}), "wayland")
        self.assertEqual(_desktop_session("linux", {"DISPLAY": ":0"}), "X11")
        self.assertEqual(_desktop_session("darwin", {}), "Aqua")


if __name__ == "__main__":
    unittest.main()
