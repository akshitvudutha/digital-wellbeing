from __future__ import annotations

from database.repository import Repository


class SettingsManager:
    _BOOL_KEYS = {"autostart", "dark_mode", "minimize_to_tray", "notifications_enabled", "debug_tracking"}
    _INT_KEYS = {"idle_threshold_s", "daily_limit_minutes"}

    def __init__(self) -> None:
        self._repo = Repository()

    def get(self, key: str, default: str = "") -> str:
        return self._repo.get_setting(key) or default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self._repo.get_setting(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    def get_int(self, key: str, default: int = 0) -> int:
        val = self._repo.get_setting(key)
        try:
            return int(val) if val is not None else default
        except ValueError:
            return default

    def set(self, key: str, value: str) -> None:
        self._repo.set_setting(key, value)

    def set_bool(self, key: str, value: bool) -> None:
        self._repo.set_setting(key, "true" if value else "false")

    def set_int(self, key: str, value: int) -> None:
        self._repo.set_setting(key, str(value))

    def all(self) -> dict[str, str]:
        return self._repo.get_all_settings()

    # Theme & Appearance Extensions
    @property
    def theme(self) -> str:
        val = self.get("theme", "").lower()
        if val in ("light", "dark", "system"):
            return val
        return "dark" if self.get_bool("dark_mode", True) else "light"

    @theme.setter
    def theme(self, value: str) -> None:
        val = value.lower()
        if val not in ("light", "dark", "system"):
            val = "dark"
        self.set("theme", val)
        if val in ("light", "dark"):
            self.set_bool("dark_mode", val == "dark")

    # SleepGuard Extensions
    @property
    def sleepguard_enabled(self) -> bool:
        return self.get_bool("sleepguard_enabled", True)

    @sleepguard_enabled.setter
    def sleepguard_enabled(self, value: bool) -> None:
        self.set_bool("sleepguard_enabled", value)

    @property
    def sleepguard_action(self) -> str:
        """The power action to execute when SleepGuard timer expires.
        Valid values: lock, sleep, hibernate, shutdown, cancel.
        Default: 'lock' (safest option).
        """
        val = self.get("sleepguard_action", "lock").lower()
        if val not in ("lock", "sleep", "hibernate", "shutdown", "cancel"):
            val = "lock"
        return val

    @sleepguard_action.setter
    def sleepguard_action(self, value: str) -> None:
        val = value.lower()
        if val not in ("lock", "sleep", "hibernate", "shutdown", "cancel"):
            val = "lock"
        self.set("sleepguard_action", val)

    @property
    def idle_timeout_minutes(self) -> int:
        return self.get_int("idle_timeout_minutes", 20)

    @idle_timeout_minutes.setter
    def idle_timeout_minutes(self, value: int) -> None:
        self.set_int("idle_timeout_minutes", value)

    @property
    def countdown_seconds(self) -> int:
        return self.get_int("countdown_seconds", 60)

    @countdown_seconds.setter
    def countdown_seconds(self, value: int) -> None:
        self.set_int("countdown_seconds", value)

    @property
    def shutdown_mode(self) -> str:
        val = self.get("shutdown_mode", "smart").lower()
        if val not in ("smart", "media", "strict"):
            # Map old values if upgrading
            if val == "idle_only": val = "strict"
            elif val == "media_only": val = "smart"
            else: val = "smart"
        return val

    @shutdown_mode.setter
    def shutdown_mode(self, value: str) -> None:
        val = value.lower()
        if val not in ("smart", "media", "strict"):
            val = "smart"
        self.set("shutdown_mode", val)

    @property
    def media_idle_timeout_minutes(self) -> int:
        return self.get_int("media_idle_timeout_minutes", 15)

    @media_idle_timeout_minutes.setter
    def media_idle_timeout_minutes(self, value: int) -> None:
        self.set_int("media_idle_timeout_minutes", value)

    @property
    def bedtime_start(self) -> str:
        return self.get("bedtime_start", "23:00")

    @bedtime_start.setter
    def bedtime_start(self, value: str) -> None:
        self.set("bedtime_start", value)

    @property
    def bedtime_end(self) -> str:
        return self.get("bedtime_end", "06:00")

    @bedtime_end.setter
    def bedtime_end(self, value: str) -> None:
        self.set("bedtime_end", value)

    @property
    def debug_tracking(self) -> bool:
        return self.get_bool("debug_tracking", False)

    @debug_tracking.setter
    def debug_tracking(self, value: bool) -> None:
        self.set_bool("debug_tracking", value)

