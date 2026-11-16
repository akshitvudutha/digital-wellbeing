"""
budgets.py — Screen-Time Budgets & Goals Manager for Notch v3.6.3.
Monitors daily screen-time budgets (total, category, or app-level),
tracks milestone thresholds (50%, 80%, 100%), delivers actionable toasts,
and coordinates optional hard enforcement upon budget exhaustion.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger
from database.models import ScreenTimeBudget
from database.repository import Repository
from notifications.notifier import Notifier


class BudgetManager(QObject):
    """
    Manages daily screen-time budgets across total system screen-time,
    application categories, and specific executable applications.
    """
    _instance: Optional["BudgetManager"] = None
    _lock = threading.Lock()

    # Signals
    budget_progress = Signal(int, int, int, float)  # budget_id, used_s, total_s, pct
    milestone_reached = Signal(object, int)          # ScreenTimeBudget, milestone_pct (50, 80, 100)
    budget_exceeded = Signal(object)                # ScreenTimeBudget
    budgets_updated = Signal()

    @classmethod
    def instance(
        cls,
        repo: Optional[Repository] = None,
        notifier: Optional[Notifier] = None,
        protection_mgr=None,
    ) -> "BudgetManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(repo=repo, notifier=notifier, protection_mgr=protection_mgr)
            return cls._instance

    def __init__(
        self,
        repo: Optional[Repository] = None,
        notifier: Optional[Notifier] = None,
        protection_mgr=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo or Repository()
        self._notifier = notifier or Notifier()
        self._protection_mgr = protection_mgr

        # Tracks which milestones have fired today: {budget_id: {50, 80, 100}}
        self._milestones_notified: Dict[int, Set[int]] = defaultdict(set)
        self._last_eval_date: date = date.today()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.evaluate_budgets)

    def start(self, interval_ms: int = 15000) -> None:
        """Start the periodic budget evaluation loop."""
        if not self._timer.isActive():
            self._timer.start(interval_ms)
            logger.info("BudgetManager evaluation timer started (%d ms)", interval_ms)
            self.evaluate_budgets()

    def stop(self) -> None:
        """Stop the periodic budget evaluation loop."""
        if self._timer.isActive():
            self._timer.stop()
            logger.info("BudgetManager evaluation timer stopped")

    def evaluate_budgets(self, now: Optional[datetime] = None) -> List[dict]:
        """
        Evaluate all active budgets against today's accumulated active usage.
        Emits progress and milestone signals, triggers toast notifications,
        and optionally terminates apps if enforce_lock is configured.
        """
        current_time = now or datetime.now()
        current_date = current_time.date()

        # Midnight rollover: clear notified milestones if the day has changed
        if current_date != self._last_eval_date:
            logger.info(
                "BudgetManager rollover: date changed from %s to %s. Resetting milestone cache.",
                self._last_eval_date,
                current_date,
            )
            self._milestones_notified.clear()
            self._last_eval_date = current_date

        budgets = self._repo.get_active_budgets()
        results: List[dict] = []

        for b in budgets:
            if not b.id:
                continue

            used_s = self._repo.get_budget_usage_today(
                b.target_type, b.target_name, target_date=current_date
            )
            pct = (used_s / max(1, b.daily_budget_seconds)) * 100.0
            is_exceeded = used_s >= b.daily_budget_seconds

            self.budget_progress.emit(b.id, int(used_s), b.daily_budget_seconds, pct)

            # Check milestones: 50%, 80%, 100%
            notified_set = self._milestones_notified[b.id]
            for threshold in (50, 80, 100):
                if pct >= threshold and threshold not in notified_set:
                    notified_set.add(threshold)
                    self._fire_milestone(b, threshold, int(used_s))

            results.append({
                "budget": b,
                "used_s": int(used_s),
                "budget_s": b.daily_budget_seconds,
                "pct": pct,
                "is_exceeded": is_exceeded,
            })

        return results

    def _fire_milestone(self, budget: ScreenTimeBudget, milestone: int, used_s: int) -> None:
        """Dispatch notifications and signals for a reached milestone."""
        logger.info(
            "Screen-Time Budget milestone reached: %d%% for %s (used %ds / budget %ds)",
            milestone,
            budget.target_name,
            used_s,
            budget.daily_budget_seconds,
        )
        self.milestone_reached.emit(budget, milestone)

        target_label = budget.target_name
        if budget.target_type == "total":
            target_label = "Overall Screen Time"

        if milestone == 50:
            title = "Screen-Time Budget: Halfway Mark"
            message = f"You've used 50% of your daily budget for {target_label} ({budget.budget_formatted})."
        elif milestone == 80:
            title = "Screen-Time Budget Warning"
            message = f"80% reached for {target_label}. {budget.budget_formatted} daily limit approaching."
        else:  # 100%
            title = "Screen-Time Budget Exceeded"
            message = f"You have reached your daily screen-time limit of {budget.budget_formatted} for {target_label}."
            self.budget_exceeded.emit(budget)

            # Enforce lock if requested
            if budget.enforce_lock:
                self._enforce_budget_lock(budget)

        if self._notifier:
            if hasattr(self._notifier, "send_notification"):
                self._notifier.send_notification(title, message)
            elif hasattr(self._notifier, "notify"):
                self._notifier.notify(title, message)

    def _enforce_budget_lock(self, budget: ScreenTimeBudget) -> None:
        """Coordinate with protection engine / app locker when budget is exceeded."""
        if not budget.enforce_lock:
            return

        logger.warning(
            "Enforcing lock for budget: %s (%s)", budget.target_type, budget.target_name
        )
        if budget.target_type == "app" and self._protection_mgr:
            try:
                if hasattr(self._protection_mgr, "app_locker"):
                    self._protection_mgr.app_locker.terminate_if_running(budget.target_name)
            except Exception as exc:
                logger.error("Failed to enforce app lock for %s: %s", budget.target_name, exc)

    def get_budget_status(self, budget: ScreenTimeBudget) -> dict:
        """Return the current day's usage statistics for a specific budget."""
        used_s = self._repo.get_budget_usage_today(
            budget.target_type, budget.target_name, target_date=date.today()
        )
        budget_s = budget.daily_budget_seconds
        pct = (used_s / max(1, budget_s)) * 100.0
        remaining_s = max(0, budget_s - int(used_s))

        return {
            "used_seconds": int(used_s),
            "budget_seconds": budget_s,
            "remaining_seconds": remaining_s,
            "percentage": pct,
            "is_exceeded": used_s >= budget_s,
        }

    def add_or_update_budget(self, budget: ScreenTimeBudget) -> int:
        """Persist a budget and re-evaluate."""
        budget_id = self._repo.save_budget(budget)
        self.evaluate_budgets()
        self.budgets_updated.emit()
        return budget_id

    def delete_budget(self, budget_id: int) -> bool:
        """Remove a budget and clear its notified milestone set."""
        if budget_id in self._milestones_notified:
            del self._milestones_notified[budget_id]
        success = self._repo.delete_budget(budget_id)
        if success:
            self.budgets_updated.emit()
        return success

    def toggle_budget(self, budget_id: int, enabled: bool) -> bool:
        """Enable or disable a budget."""
        success = self._repo.set_budget_enabled(budget_id, enabled)
        if success:
            if not enabled and budget_id in self._milestones_notified:
                del self._milestones_notified[budget_id]
            self.evaluate_budgets()
            self.budgets_updated.emit()
        return success
