"""
test_updater.py - Automated tests for the updater module.
"""
import pytest
from pathlib import Path

from core.updater import parse_version, is_newer, check_for_update, set_mock_release_data


def test_parse_version():
    assert parse_version("2.5.2") == (2, 5, 2)
    assert parse_version("v2.5.2") == (2, 5, 2)
    assert parse_version("V2.5.2-beta") == (2, 5, 2)
    assert parse_version("invalid") == (0, 0, 0)
    assert parse_version("2.5") == (0, 0, 0)


def test_is_newer():
    assert is_newer("2.5.1", "2.5.2") is True
    assert is_newer("2.5.2", "2.6.0") is True
    assert is_newer("2.5.9", "2.5.10") is True
    assert is_newer("2.5.2", "2.5.2") is False
    assert is_newer("2.6.0", "2.5.2") is False
    assert is_newer("invalid", "2.5.2") is False
    assert is_newer("2.5.2", "invalid") is False


def test_check_for_update_newer():
    mock_data = [
        {
            "tag_name": "v2.5.3",
            "draft": False,
            "prerelease": False,
            "body": "Bug fixes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.3.exe", "browser_download_url": "http://example.com/exe"},
                {"name": "DigitalWellbeingSetup-2.5.3.exe.sha256", "browser_download_url": "http://example.com/sha256"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    assert info is not None
    assert info.version == "2.5.3"
    assert info.release_notes == "Bug fixes"
    assert info.installer_url == "http://example.com/exe"
    assert info.checksum_url == "http://example.com/sha256"


def test_check_for_update_not_newer():
    mock_data = [
        {
            "tag_name": "v2.5.2",
            "draft": False,
            "prerelease": False,
            "body": "Same version",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.2.exe", "browser_download_url": "http://example.com/exe"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    assert info is None


def test_check_for_update_ignores_prerelease():
    mock_data = [
        {
            "tag_name": "v2.6.0-beta",
            "draft": False,
            "prerelease": True,
            "body": "Beta version",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.6.0.exe", "browser_download_url": "http://example.com/exe"}
            ]
        },
        {
            "tag_name": "v2.5.1",
            "draft": False,
            "prerelease": False,
            "body": "Stable version",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.1.exe", "browser_download_url": "http://example.com/exe"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    assert info is None  # beta is ignored, and 2.5.1 is older

def test_check_for_update_malformed():
    mock_data = [{"invalid": "data"}]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    assert info is None

# Cleanup mock data
set_mock_release_data(None)
