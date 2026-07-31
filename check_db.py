import sys
sys.path.insert(0, ".")
from database.repository import Repository
from datetime import date

repo = Repository()
sessions = repo.get_sessions_for_date(date.today())
print(f"Sessions in DB today: {len(sessions)}")

top = repo.get_top_apps_for_range(date.today(), date.today())
print("Top apps tracked today:")
for i, app in enumerate(top[:5], 1):
    mins = int(app["total_s"] // 60)
    secs = int(app["total_s"] % 60)
    name = app["process_name"]
    cat = app["category"]
    print(f"  {i}. {name} — {mins}m {secs}s ({cat})")

from analytics.engine import AnalyticsEngine
engine = AnalyticsEngine()
s = engine.get_today_summary()
print(f"\nToday summary:")
print(f"  Active time : {engine.format_duration(s.active_time_s)}")
print(f"  Total time  : {engine.format_duration(s.total_screen_time_s)}")
print(f"  Longest     : {engine.format_duration(s.longest_session_s)}")
