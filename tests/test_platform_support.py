from __future__ import annotations

import unittest

from tracker.platform_support import get_tracking_capabilities


def finder_with(*available: str):
    modules = set(available)
    return lambda name: object() if name in modules else None


class PlatformSupportTests(unittest.TestCase):
    def test_windows_reports_pywin32_requirement(self) -> None:
        capabilities = get_tracking_capabilities(
            platform_name="win32",
            finder=finder_with("win32gui"),
        )
        by_name = {item.name: item for item in capabilities}
        self.assertFalse(by_name["foreground_tracking"].available)
        self.assertIn("pywin32", by_name["foreground_tracking"].detail)
        self.assertTrue(by_name["idle_detection"].available)

    def test_macos_reports_native_backends(self) -> None:
        capabilities = get_tracking_capabilities(
            platform_name="darwin",
            finder=finder_with("AppKit", "Quartz"),
        )
        by_name = {item.name: item for item in capabilities}
        self.assertTrue(by_name["foreground_tracking"].available)
        self.assertTrue(by_name["idle_detection"].available)
        self.assertFalse(by_name["media_detection"].available)

    def test_linux_x11_is_supported(self) -> None:
        capabilities = get_tracking_capabilities(
            platform_name="linux",
            environ={"DISPLAY": ":0"},
            finder=finder_with("Xlib"),
        )
        by_name = {item.name: item for item in capabilities}
        self.assertTrue(by_name["foreground_tracking"].available)
        self.assertTrue(by_name["idle_detection"].available)

    def test_wayland_only_session_explains_limitation(self) -> None:
        capabilities = get_tracking_capabilities(
            platform_name="linux",
            environ={"WAYLAND_DISPLAY": "wayland-0"},
            finder=finder_with("Xlib"),
        )
        foreground = next(item for item in capabilities if item.name == "foreground_tracking")
        self.assertFalse(foreground.available)
        self.assertIn("Wayland", foreground.detail)

    def test_unknown_platform_fails_safely(self) -> None:
        capabilities = get_tracking_capabilities(
            platform_name="plan9",
            finder=finder_with(),
        )
        self.assertTrue(all(not item.available for item in capabilities))
        self.assertTrue(all("Unsupported" in item.detail for item in capabilities))


if __name__ == "__main__":
    unittest.main()
