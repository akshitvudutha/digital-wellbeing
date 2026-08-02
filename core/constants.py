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


APP_NAME = "Digital Wellbeing"
from core.version import get_version
APP_VERSION = get_version()
DB_FILENAME = "digital_wellbeing.db"
LOG_FILENAME = "digital_wellbeing.log"

POLL_INTERVAL_MS = 500
DEFAULT_IDLE_THRESHOLD_S = 300
MAX_SESSION_GAP_S = 30

CATEGORY_COLORS: dict[AppCategory, str] = {
    AppCategory.BROWSER: "#4FC3F7",
    AppCategory.PROGRAMMING: "#81C784",
    AppCategory.GAMING: "#FF8A65",
    AppCategory.COMMUNICATION: "#CE93D8",
    AppCategory.PRODUCTIVITY: "#FFD54F",
    AppCategory.ENTERTAINMENT: "#F48FB1",
    AppCategory.SYSTEM: "#90A4AE",
    AppCategory.UTILITIES: "#80CBC4",
    AppCategory.EDUCATION: "#A5D6A7",
    AppCategory.SOCIAL: "#FFAB91",
    AppCategory.OTHER: "#78909C",
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
    AppCategory.SOCIAL: "🌍",
    AppCategory.OTHER: "📌",
}
