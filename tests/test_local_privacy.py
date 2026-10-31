from __future__ import annotations

import unittest
from pathlib import Path


class LocalPrivacyTests(unittest.TestCase):
    def test_production_code_has_no_telemetry_heartbeat(self) -> None:
        root = Path(__file__).parent.parent
        production_paths = [
            root / "main.py",
            *(root / folder for folder in ("core", "database", "settings", "tracker", "ui", "utils")),
        ]
        source_files: list[Path] = []
        for path in production_paths:
            source_files.extend(path.rglob("*.py") if path.is_dir() else [path])

        combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
        self.assertNotIn("/api/telemetry/heartbeat", combined_source)
        self.assertNotIn("TelemetryManager", combined_source)
        self.assertNotIn('get("install_id"', combined_source)


if __name__ == "__main__":
    unittest.main()
