from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.paths import get_data_dir, get_database_path, get_log_path


class DataPathTests(unittest.TestCase):
    def test_windows_uses_local_app_data(self) -> None:
        path = get_data_dir(
            platform_name="win32",
            environ={"LOCALAPPDATA": "C:/Users/example/AppData/Local"},
            home=Path("C:/Users/example"),
            create=False,
        )
        self.assertEqual(path, Path("C:/Users/example/AppData/Local/DigitalWellbeing"))

    def test_windows_falls_back_to_home(self) -> None:
        path = get_data_dir(
            platform_name="win32",
            environ={},
            home=Path("C:/Users/example"),
            create=False,
        )
        self.assertEqual(path, Path("C:/Users/example/AppData/Local/DigitalWellbeing"))

    def test_macos_uses_application_support(self) -> None:
        path = get_data_dir(
            platform_name="darwin",
            environ={},
            home=Path("/Users/example"),
            create=False,
        )
        self.assertEqual(path, Path("/Users/example/Library/Application Support/DigitalWellbeing"))

    def test_linux_honors_xdg_data_home(self) -> None:
        path = get_data_dir(
            platform_name="linux",
            environ={"XDG_DATA_HOME": "/var/tmp/example-data"},
            home=Path("/home/example"),
            create=False,
        )
        self.assertEqual(path, Path("/var/tmp/example-data/digital-wellbeing"))

    def test_linux_falls_back_to_local_share(self) -> None:
        path = get_data_dir(
            platform_name="linux",
            environ={},
            home=Path("/home/example"),
            create=False,
        )
        self.assertEqual(path, Path("/home/example/.local/share/digital-wellbeing"))

    def test_override_keeps_database_and_log_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"NYW_DATA_DIR": temp_dir}
            data_dir = get_data_dir(environ=env)
            self.assertTrue(data_dir.is_dir())
            self.assertEqual(get_database_path(environ=env), data_dir / "digital_wellbeing.db")
            self.assertEqual(get_log_path(environ=env), data_dir / "digital_wellbeing.log")


if __name__ == "__main__":
    unittest.main()
