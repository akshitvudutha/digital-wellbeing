from __future__ import annotations

import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import autostart


class AutostartTests(unittest.TestCase):
    def test_linux_desktop_entry_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "autostart" / "digital-wellbeing.desktop"
            with (
                patch.object(sys, "platform", "linux"),
                patch("utils.autostart._autostart_file", return_value=path),
            ):
                autostart.enable_autostart()
                contents = path.read_text(encoding="utf-8")
                self.assertIn("[Desktop Entry]", contents)
                self.assertIn("--background", contents)
                self.assertTrue(autostart.is_autostart_enabled())
                autostart.disable_autostart()
                self.assertFalse(path.exists())

    def test_macos_launch_agent_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "io.github.nyw.autostart.plist"
            with (
                patch.object(sys, "platform", "darwin"),
                patch("utils.autostart._autostart_file", return_value=path),
            ):
                autostart.enable_autostart()
                with path.open("rb") as stream:
                    payload = plistlib.load(stream)
                self.assertEqual(payload["Label"], "io.github.nyw.autostart")
                self.assertTrue(payload["RunAtLoad"])
                self.assertIn("--background", payload["ProgramArguments"])
                self.assertTrue(autostart.is_autostart_enabled())
                autostart.disable_autostart()
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
