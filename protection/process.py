from __future__ import annotations

import subprocess
import sys
import time

import psutil

from core.logger import logger


class ProcessController:
    @staticmethod
    def close_process(process_name: str) -> bool:
        """Attempt graceful shutdown first, fallback to forceful termination."""
        if sys.platform != "win32":
            return ProcessController._close_posix_process(process_name)

        if not process_name.lower().endswith(".exe"):
            # Ensure it ends with .exe for taskkill
            process_name += ".exe"
            
        logger.info(f"ProcessController: Attempting graceful close for {process_name}")
        
        try:
            # Attempt graceful close
            res = subprocess.run(
                ["taskkill", "/IM", process_name], 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait for process to exit
            time.sleep(1.5)
            
            # Check if still running
            check = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}"], 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if process_name.lower() in check.stdout.lower():
                logger.warning(f"ProcessController: {process_name} did not close gracefully. Terminating forcefully.")
                subprocess.run(
                    ["taskkill", "/F", "/IM", process_name], 
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            return True
        except Exception as exc:
            logger.error(f"ProcessController failed to close {process_name}: {exc}")
            return False

    @staticmethod
    def _close_posix_process(process_name: str) -> bool:
        target = process_name.strip().lower()
        if not target:
            return False

        matches: list[psutil.Process] = []
        try:
            for process in psutil.process_iter(["name"]):
                name = (process.info.get("name") or "").lower()
                if name == target:
                    process.terminate()
                    matches.append(process)

            if not matches:
                logger.warning("ProcessController: no process named %s was found", process_name)
                return False

            _, alive = psutil.wait_procs(matches, timeout=1.5)
            for process in alive:
                process.kill()
            logger.info("ProcessController: closed %d process(es) named %s", len(matches), process_name)
            return True
        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            logger.error("ProcessController could not close %s: %s", process_name, exc)
            return False
