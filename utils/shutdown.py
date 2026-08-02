"""
shutdown.py — Windows Shutdown Executor for Digital Wellbeing Platform v2.

Provides a safe interface for triggering an automated PC shutdown with pre-shutdown hook execution.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


class ShutdownManager:
    def __init__(self) -> None:
        self._hooks: list[callable] = []

    def register_pre_shutdown_hook(self, callback: callable) -> None:
        self._hooks.append(callback)
        logger.debug("Pre-shutdown hook registered: %s", callback)

    def _run_hooks(self) -> None:
        for hook in self._hooks:
            try:
                hook()
            except Exception as exc:
                logger.error("Pre-shutdown hook error (%r): %s", hook, exc)

    def shutdown_now(self) -> bool:
        logger.warning("Executing immediate system shutdown...")
        self._run_hooks()
        return self._execute_shutdown()

    def cancel_shutdown(self) -> None:
        logger.info("Cancelling any pending scheduled shutdown...")
        try:
            subprocess.run(
                ["shutdown", "/a"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            logger.error("Failed to cancel shutdown: %s", exc)

    @staticmethod
    def _execute_shutdown() -> bool:
        from datetime import datetime
        logger.info(f"[INSTRUMENTATION] _execute_shutdown() invoking shutdown.exe at {datetime.now().isoformat()}")


        try:
            subprocess.run(
                ["shutdown", "/s", "/t", "0"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("shutdown command failed (exit %d): %s", exc.returncode, exc.stderr)
            return False
        except OSError as exc:
            logger.error("Failed to invoke shutdown command: %s", exc)
            return False

        logger.info("Shutdown command accepted by Windows.")
        return True
