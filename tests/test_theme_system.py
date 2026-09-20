"""
tests/test_theme_system.py - Unit tests for ThemeManager, theme resolution, and token verification.
"""
import pytest
from PySide6.QtWidgets import QApplication
from ui.theme import ThemeManager, is_system_dark
from settings.manager import SettingsManager

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_theme_resolution_explicit(qapp):
    tm = ThemeManager.instance()
    assert tm.resolve_dark_mode("dark") is True
    assert tm.resolve_dark_mode("light") is False
    assert tm.resolve_dark_mode(True) is True
    assert tm.resolve_dark_mode(False) is False
    assert tm.resolve_dark_mode("system") == is_system_dark()

def test_theme_tokens_light_vs_dark(qapp):
    tm = ThemeManager.instance()
    
    # Test Dark Mode Tokens
    tm.set_theme("dark", app=qapp)
    assert tm.is_dark is True
    assert tm.color("text_main") == "#F8FAFC"
    assert tm.color("accent") == "#10B981"
    assert "rgba" in tm.color("surface")
    
    # Test Light Mode Tokens
    tm.set_theme("light", app=qapp)
    assert tm.is_dark is False
    assert tm.color("text_main") == "#0F172A"
    assert tm.color("text_sub") == "#475569"
    assert tm.color("text_muted") == "#64748B"
    assert tm.color("accent") == "#059669"
    assert tm.color("card_bg") == "#FFFFFF"

def test_theme_changed_signal(qapp):
    tm = ThemeManager.instance()
    emitted_values = []
    
    def on_theme_changed(is_dark: bool):
        emitted_values.append(is_dark)
        
    tm.theme_changed.connect(on_theme_changed)
    try:
        tm.set_theme("dark", app=qapp)
        tm.set_theme("light", app=qapp)
        tm.set_theme("dark", app=qapp)
        
        assert emitted_values[-3:] == [True, False, True]
    finally:
        tm.theme_changed.disconnect(on_theme_changed)

def test_settings_manager_theme_storage():
    sm = SettingsManager()
    orig = sm.theme
    try:
        sm.theme = "light"
        assert sm.theme == "light"
        sm.theme = "system"
        assert sm.theme == "system"
        sm.theme = "dark"
        assert sm.theme == "dark"
    finally:
        sm.theme = orig
