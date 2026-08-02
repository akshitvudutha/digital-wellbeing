from __future__ import annotations

import subprocess
import time
from core.logger import logger

class ProcessController:
    @staticmethod
    def close_process(process_name: str) -> bool:
        """Attempt graceful shutdown first, fallback to forceful termination."""
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
