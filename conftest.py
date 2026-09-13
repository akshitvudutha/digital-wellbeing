"""Pytest collection rules for automated tests.

The repository also keeps manual launch, screenshot, and exploratory scripts at
the project root. Their historical names match pytest's discovery pattern, so
they must be explicitly excluded until they can be moved under a tools folder.
"""

collect_ignore = [
    "e2e_test.py",
    "manual_test.py",
    "scratch_test.py",
    "test_all.py",
    "test_click.py",
    "test_features.py",
    "test_render.py",
    "test_timer_dialog.py",
    "test_timer_ui.py",
    "test_tracking.py",
    "test_ui.py",
    "test_ui_and_screenshot.py",
]
