"""
tests/test_theme_system.py - Focused tests for ThemeManager, WCAG AA contrast tokens,
dynamic icon colors, theme switching without restart, and keyboard focus indicators.
"""
import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtGui import QColor
from ui.theme import ThemeManager, is_system_dark
from ui.icons import get_pixmap, get_icon, get_theme_icon, clear_icon_cache, _pixmap_cache
from settings.manager import SettingsManager
from database.repository import Repository


def srgb_to_lin(c: int) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def rel_luminance(hex_str: str) -> float:
    c = QColor(hex_str)
    return 0.2126 * srgb_to_lin(c.red()) + 0.7152 * srgb_to_lin(c.green()) + 0.0722 * srgb_to_lin(c.blue())


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1, l2 = rel_luminance(hex1), rel_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


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
    assert tm.color("focus_ring") == "#10B981"
    assert "rgba" in tm.color("surface")
    assert tm.color("secondary_btn_text") == "#F8FAFC"
    
    # Test Light Mode Tokens
    tm.set_theme("light", app=qapp)
    assert tm.is_dark is False
    assert tm.color("text_main") == "#0F172A"
    assert tm.color("text_sub") == "#475569"
    assert tm.color("text_muted") == "#526071"
    assert tm.color("accent") == "#047857"
    assert tm.color("accent_amber") == "#B45309"
    assert tm.color("focus_ring") == "#047857"
    assert tm.color("card_bg") == "#FFFFFF"
    assert tm.color("secondary_btn_bg") == "#FFFFFF"
    assert tm.color("secondary_btn_text") == "#0F172A"


def test_wcag_aa_contrast_ratios(qapp):
    """Verify that light-theme normal text and buttons meet or exceed WCAG AA 4.5:1."""
    tm = ThemeManager.instance()
    tm.set_theme("light", app=qapp)

    bg = tm.color("bg")               # #F8FAFC
    white = "#FFFFFF"                 # Surface / Card
    card_pressed = tm.color("card_pressed")  # #F1F5F9

    # Text hierarchy contrast
    assert contrast_ratio(tm.color("text_main"), bg) >= 4.5
    assert contrast_ratio(tm.color("text_main"), white) >= 4.5
    assert contrast_ratio(tm.color("text_sub"), bg) >= 4.5
    assert contrast_ratio(tm.color("text_sub"), white) >= 4.5
    assert contrast_ratio(tm.color("text_muted"), bg) >= 4.5
    assert contrast_ratio(tm.color("text_muted"), white) >= 4.5
    assert contrast_ratio(tm.color("text_muted"), card_pressed) >= 4.5

    # Semantic & accent text contrast
    assert contrast_ratio(tm.color("accent"), white) >= 4.5
    assert contrast_ratio(tm.color("accent"), bg) >= 4.5
    assert contrast_ratio(tm.color("accent_amber"), white) >= 4.5
    assert contrast_ratio(tm.color("warning_text"), white) >= 4.5
    assert contrast_ratio(tm.color("danger_text"), white) >= 4.5
    assert contrast_ratio(tm.color("info_text"), white) >= 4.5
    assert contrast_ratio(tm.color("success_text"), white) >= 4.5
    assert contrast_ratio(tm.color("indigo_text"), white) >= 4.5

    # Button contrast
    # Primary button: white text on dark emerald gradient end-stop
    assert contrast_ratio("#FFFFFF", tm.color("accent")) >= 4.5
    # Secondary button: text on secondary button bg
    assert contrast_ratio(tm.color("secondary_btn_text"), tm.color("secondary_btn_bg")) >= 4.5


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


def test_dynamic_icon_colors_and_caching(qapp):
    """Verify icon rendering uses active theme colors, resolves token names, and clears cache."""
    tm = ThemeManager.instance()

    # 1. Dark Mode Icons
    tm.set_theme("dark", app=qapp)
    clear_icon_cache()
    pm_dark = get_pixmap("home", size=24)
    assert not pm_dark.isNull()
    assert (("home", "#F8FAFC", 24) in _pixmap_cache)

    # 2. Token resolution
    pm_accent = get_pixmap("focus", color="accent", size=24)
    assert not pm_accent.isNull()
    assert (("focus", tm.color("accent"), 24) in _pixmap_cache)

    pm_sub = get_pixmap("usage", color="text_sub", size=24)
    assert not pm_sub.isNull()
    assert (("usage", tm.color("text_sub"), 24) in _pixmap_cache)

    # 3. Light Mode Icons: cache invalidation on theme switch
    tm.set_theme("light", app=qapp)
    # The cache should have been cleared by theme_changed signal
    pm_light = get_pixmap("home", size=24)
    assert not pm_light.isNull()
    assert (("home", "#0F172A", 24) in _pixmap_cache)

    # 4. Multi-state theme icon
    ico = get_theme_icon("settings", size=18)
    assert not ico.isNull()


def test_sidebar_dynamic_icons_on_theme_switch(qapp):
    """Verify switching Dark -> Light -> Dark updates sidebar icons without restart."""
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)

    btn_home = QPushButton(" Home")
    btn_home.setProperty("icon_name", "home")

    btn_settings = QPushButton(" Settings")
    btn_settings.setProperty("icon_name", "settings")

    buttons = [btn_home, btn_settings]

    def update_icons():
        active_color = tm.color("accent")
        normal_color = tm.color("text_sub")
        for btn in buttons:
            name = btn.property("icon_name")
            is_active = (btn == btn_home)
            col = active_color if is_active else normal_color
            btn.setIcon(get_icon(name, color=col, size=18))

    # Initial Dark Theme
    update_icons()
    assert not btn_home.icon().isNull()
    assert not btn_settings.icon().isNull()
    assert ("home", "#10B981", 18) in _pixmap_cache
    assert ("settings", "#94A3B8", 18) in _pixmap_cache

    # Dynamic Switch to Light Theme
    tm.set_theme("light", app=qapp)
    update_icons()
    assert not btn_home.icon().isNull()
    assert not btn_settings.icon().isNull()
    assert ("home", "#047857", 18) in _pixmap_cache
    assert ("settings", "#475569", 18) in _pixmap_cache

    # Dynamic Switch back to Dark Theme
    tm.set_theme("dark", app=qapp)
    update_icons()
    assert ("home", "#10B981", 18) in _pixmap_cache
    assert ("settings", "#94A3B8", 18) in _pixmap_cache



def test_keyboard_focus_indicators(qapp):
    """Verify global stylesheet does not globally strip focus outlines and defines accessible focus."""
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)

    qss = qapp.styleSheet()

    # Verify outline: none was removed from QWidget
    assert "outline: none;" not in qss.split("/* ─── Keyboard Focus Indicators")[0]

    # Verify focus indicators are defined for interactive controls
    assert "QAbstractButton:focus" in qss
    assert "QLineEdit:focus" in qss
    assert "QTabBar::tab:focus" in qss
    assert "border: 2px solid" in qss


def test_settings_manager_theme_storage(tmp_path):
    Repository.set_db_path_override(tmp_path / "settings_theme_test.db")
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
        sm._repo.close()
        Repository.set_db_path_override(None)
