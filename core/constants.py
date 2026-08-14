from __future__ import annotations

from enum import Enum, auto


class AppCategory(str, Enum):
    BROWSER = "Browser"
    PROGRAMMING = "Programming"
    GAMING = "Gaming"
    COMMUNICATION = "Communication"
    PRODUCTIVITY = "Productivity"
    ENTERTAINMENT = "Entertainment"
    SYSTEM = "System"
    UTILITIES = "Utilities"
    EDUCATION = "Education"
    SOCIAL = "Social"
    FINANCE = "Finance"
    OTHER = "Other"


class TimePeriod(str, Enum):
    TODAY = "Today"
    WEEK = "This Week"
    MONTH = "This Month"


class EventType(str, Enum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    IDLE_START = "idle_start"
    IDLE_END = "idle_end"
    LOCK = "lock"
    UNLOCK = "unlock"
    SLEEP = "sleep"
    RESUME = "resume"


APP_NAME = "Not Your Wellbeing"
from core.version import get_version
APP_VERSION = get_version()
DB_FILENAME = "digital_wellbeing.db"
LOG_FILENAME = "digital_wellbeing.log"

POLL_INTERVAL_MS = 500
DEFAULT_IDLE_THRESHOLD_S = 300
MAX_SESSION_GAP_S = 30

CATEGORY_COLORS: dict[AppCategory, str] = {
    AppCategory.BROWSER: "#3B82F6",       # Blue
    AppCategory.OTHER: "#06B6D4",         # Cyan
    AppCategory.PRODUCTIVITY: "#22C55E",  # Green
    AppCategory.SYSTEM: "#9CA3AF",        # Gray
    
    # Defaults for others to prevent crashes:
    AppCategory.COMMUNICATION: "#10B981", 
    AppCategory.ENTERTAINMENT: "#F59E0B", 
    AppCategory.GAMING: "#8B5CF6",        
    AppCategory.FINANCE: "#EAB308",       
    AppCategory.EDUCATION: "#14B8A6",     
    AppCategory.PROGRAMMING: "#6366F1",   
    AppCategory.UTILITIES: "#64748B",     
    AppCategory.SOCIAL: "#EC4899",        
}

CATEGORY_ICONS: dict[AppCategory, str] = {
    AppCategory.BROWSER: "🌐",
    AppCategory.PROGRAMMING: "💻",
    AppCategory.GAMING: "🎮",
    AppCategory.COMMUNICATION: "💬",
    AppCategory.PRODUCTIVITY: "📊",
    AppCategory.ENTERTAINMENT: "🎬",
    AppCategory.SYSTEM: "⚙️",
    AppCategory.UTILITIES: "🔧",
    AppCategory.EDUCATION: "🎓",
    AppCategory.SOCIAL: "👥",
    AppCategory.FINANCE: "💰",
    AppCategory.OTHER: "📌",
}
