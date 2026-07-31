"""
Headless page construction test — verifies all V2 UI pages can be instantiated
without a display by mocking QApplication minimally.
"""
import sys
sys.path.insert(0, ".")

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

# Apply theme
from ui.theme import apply_windows11_dark_palette, load_stylesheet
apply_windows11_dark_palette(app)
ss = load_stylesheet()
if ss:
    app.setStyleSheet(ss)

errors = []

# Dashboard Page V2
try:
    from ui.pages.dashboard import DashboardPage
    p = DashboardPage()
    p._refresh()
    print("[OK] DashboardPage V2 — instantiated and refreshed")
except Exception as e:
    errors.append(f"[FAIL] DashboardPage V2: {e}")
    print(errors[-1])

# Activity Page V2
try:
    from ui.pages.activity import ActivityPage
    p = ActivityPage()
    p._refresh()
    print("[OK] ActivityPage V2 — instantiated and refreshed")
except Exception as e:
    import traceback
    errors.append(f"[FAIL] ActivityPage V2: {e}")
    print(errors[-1])
    traceback.print_exc()

# Wellbeing Page V2
try:
    from ui.pages.wellbeing import WellbeingPage
    p = WellbeingPage()
except Exception as e:
    errors.append(f"[FAIL] WellbeingPage V2: {e}")
    print(errors[-1])

# Settings Page V2
try:
    from ui.pages.settings import SettingsPage
    p = SettingsPage()
    print("[OK] SettingsPage V2 — instantiated")
except Exception as e:
    errors.append(f"[FAIL] SettingsPage V2: {e}")
    print(errors[-1])

# About Page V2
try:
    from ui.pages.about import AboutPage
    p = AboutPage()
    print("[OK] AboutPage V2 — instantiated")
except Exception as e:
    errors.append(f"[FAIL] AboutPage V2: {e}")
    print(errors[-1])

# Widgets
try:
    from ui.widgets.hero_card import HeroCard
    c = HeroCard()
    c.set_data("3h 45m", 12.5, True)
    print("[OK] HeroCard V2 widget")

    from ui.widgets.stat_card import StatCard
    s = StatCard("Active Focus", "2h 30m", "⚡", "#4ade80")
    print("[OK] StatCard V2 widget")

    from ui.widgets.donut_chart import DonutChart
    d = DonutChart()
    d.set_data([("Browser", 3600, "#4FC3F7"), ("Gaming", 1800, "#FF8A65")], "1h", "total")
    print("[OK] DonutChart widget")

    from ui.widgets.app_row import AppUsageRow
    from core.constants import AppCategory
    r = AppUsageRow(1, "chrome.exe", "Google Chrome", AppCategory.BROWSER, 3600, 3600)
    print("[OK] AppUsageRow widget")
except Exception as e:
    errors.append(f"[FAIL] Widgets V2: {e}")
    print(errors[-1])

if __name__ == '__main__':
    # Main window V2
    try:
        from tracker.manager import TrackingManager
        from ui.main_window import MainWindow
        tracker = TrackingManager()
        w = MainWindow(tracker)
        print("[OK] MainWindow V2 — instantiated with all pages")
    except Exception as e:
        import traceback
        errors.append(f"[FAIL] MainWindow V2: {e}")
        print(errors[-1])
        traceback.print_exc()

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        sys.exit(1)
    else:
        print("=== ALL V2 UI COMPONENTS PASS ===")
        sys.exit(0)
