from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _setup_path() -> None:
    root = Path(__file__).parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def run_headless_service() -> None:
    from core.logger import logger
    logger.info("Starting Digital Wellbeing Headless Tracking Service")
    
    from tracker.manager import TrackingManager
    tracker = TrackingManager()
    
    try:
        tracker.start()
        # Keep the main thread alive while tracker runs in its daemon thread
        while tracker.is_running:
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Headless service interrupted. Stopping tracker.")
    except Exception as exc:
        logger.critical("Headless service fatal error: %s", exc, exc_info=True)
    finally:
        tracker.stop()


def main() -> None:
    _setup_path()
    
    # Set AppUserModelID for proper Windows Taskbar grouping
    import platform
    if platform.system() == "Windows":
        try:
            import ctypes
            app_id = "AkshitVudutha.DigitalWellbeing.App.2"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            from core.logger import logger
            logger.warning(f"Could not set AppUserModelID: {e}")

    parser = argparse.ArgumentParser(description="Digital Wellbeing Windows Tracker")
    parser.add_argument(
        "--service",
        action="store_true",
        help="Run the tracking engine as a headless background service.",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Launch the GUI application minimized to the system tray.",
    )
    args = parser.parse_args()

    from core.logger import logger
    
    if args.service:
        run_headless_service()
        sys.exit(0)

    logger.info("[LIFECYCLE] Starting Digital Wellbeing GUI Application (main.py entry)")
    try:
        from ui.app import DigitalWellbeingApp
        from utils.debug_lifecycle import log_lifecycle_state
        
        log_lifecycle_state("main.py: before DigitalWellbeingApp instantiation")
        app = DigitalWellbeingApp(start_minimized=args.background)
        
        import datetime
        import sys
        import os
        import os
        
        logger.info(f"[DEBUG BUILD] Build timestamp: {datetime.datetime.now().isoformat()}")
        logger.info(f"EXECUTABLE PATH: {sys.executable}")
        logger.info(f"FILE PATH: {__file__}")
        logger.info(f"CWD: {os.getcwd()}")
        
        logger.info("[LIFECYCLE] Entering QApplication.exec()")
        log_lifecycle_state("main.py: before QApplication.exec()")
        
        exit_code = app.run()
        
        logger.info("[LIFECYCLE] QApplication.exec() RETURNED with exit code %d", exit_code)
        log_lifecycle_state("main.py: after QApplication.exec() returned")
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        exit_code = 1

    import os
    logger.info("[LIFECYCLE] Exiting process via os._exit(%d)", exit_code)
    os._exit(exit_code)


if __name__ == "__main__":
    main()
