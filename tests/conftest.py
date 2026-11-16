"""Keep automated desktop tests isolated from user data and Windows hosts."""
from __future__ import annotations

import sys
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication instance for all headless Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def isolate_user_database_and_focus_blocking(monkeypatch, tmp_path):
    """Route implicit repositories to per-test storage and stub Focus hosts I/O."""
    from database.repository import Repository
    from protection.website_blocker import WebsiteBlocker as RealWebsiteBlocker
    from protection.windows_hello import HelloAvailability, WindowsHelloAuth
    import protection.focus_manager as focus_manager_module

    test_db = tmp_path / "notch_test.db"
    monkeypatch.setenv("DW_DB_PATH", str(test_db))
    Repository.set_db_path_override(None)

    class IsolatedWebsiteBlocker:
        def __init__(self, *_args, **_kwargs):
            self._active_domains = set()

        @staticmethod
        def clean_domain(domain):
            return RealWebsiteBlocker.clean_domain(domain)

        @property
        def is_active(self):
            return bool(self._active_domains)

        @property
        def is_blocking_active(self):
            return self.is_active

        def cleanup_orphaned_blocks(self):
            return True

        def block_websites(self, domains):
            self._active_domains.update(domains)
            return True, "Isolated test blocker"

        def unblock_all(self):
            self._active_domains.clear()
            return True, "Isolated test blocker"

    monkeypatch.setattr(focus_manager_module, "WebsiteBlocker", IsolatedWebsiteBlocker)
    # Automated UI tests do not need host biometric hardware. Keep WinRT out of
    # the headless suite; mapping behavior is covered independently.
    monkeypatch.setattr(
        WindowsHelloAuth,
        "check_availability",
        lambda self: HelloAvailability.UNAVAILABLE,
    )
    monkeypatch.setattr(
        WindowsHelloAuth,
        "_query_availability",
        staticmethod(lambda: HelloAvailability.UNAVAILABLE),
    )
    yield

    instance = Repository._instance
    if instance is not None:
        instance.close()
    Repository.set_db_path_override(None)
