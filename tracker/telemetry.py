import threading
import requests
from core.logger import logger
from core.constants import APP_VERSION
from settings.manager import SettingsManager

class TelemetryManager:
    _instance = None

    @classmethod
    def instance(cls) -> "TelemetryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.settings = SettingsManager()
        self._endpoint = "https://notyourwellbeing.vercel.app/api/telemetry/heartbeat"
        self._thread = None

    def start_heartbeat(self):
        """Spawns a daemon thread to send the telemetry heartbeat."""
        if self._thread and self._thread.is_alive():
            return
        
        self._thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        self._thread.start()

    def _send_heartbeat(self):
        install_id = self.settings.install_id
        if not install_id:
            return

        payload = {
            "installId": install_id,
            "version": APP_VERSION
        }

        try:
            # Short timeout so it doesn't block or linger silently
            requests.post(self._endpoint, json=payload, timeout=5.0)
            logger.info("Anonymous telemetry heartbeat sent successfully.")
        except Exception as e:
            # Swallow all exceptions to ensure offline capability
            logger.debug(f"Telemetry heartbeat failed (offline or server unreachable): {e}")
