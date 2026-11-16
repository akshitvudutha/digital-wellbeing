import time
import datetime
import sys
from tracker.foreground import get_foreground_app, ForegroundApp
from tracker.idle import get_idle_seconds
import win32api
import win32gui

def main():
    print("Starting foreground tracking investigation...")
    print("Press Ctrl+C to stop and generate the final report.\n")
    
    log_file = open("tracking_report.txt", "w", encoding="utf-8")
    def log(msg):
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    total_foreground_time = 0.0
    total_brave_time = 0.0
    total_unassigned_time = 0.0
    total_idle_time = 0.0
    total_system_time = 0.0
    
    last_category = None  # "APP", "UNASSIGNED", "SYSTEM"
    last_reason = ""
    last_app: ForegroundApp = None
    state_start_time = time.time()
    
    # Known system processes that might steal focus
    SYSTEM_PROCESSES = {
        "dwm.exe", "csrss.exe", "winlogon.exe", "smss.exe", "lockapp.exe", 
        "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe",
        "taskmgr.exe"
    }

    try:
        while True:
            time.sleep(1.0)
            now = time.time()
            
            # Determine current state
            idle_s = get_idle_seconds()
            is_idle = idle_s > 60  # Typical idle threshold
            
            app = get_foreground_app(last_app)
            
            current_category = "APP"
            reason = ""
            
            if is_idle:
                current_category = "UNASSIGNED"
                reason = f"Idle ({idle_s:.0f}s)"
            elif app is None:
                current_category = "UNASSIGNED"
                reason = "Window detection failed or unknown process"
            elif app.process_name.lower() in SYSTEM_PROCESSES:
                current_category = "SYSTEM"
                reason = f"System process: {app.process_name}"
                
            # Detect changes
            changed = False
            if current_category != last_category:
                changed = True
            elif current_category == "APP" and last_category == "APP":
                if not last_app or app.process_name != last_app.process_name or app.window_title != last_app.window_title:
                    changed = True
            elif current_category == "UNASSIGNED" and last_category == "UNASSIGNED":
                if reason != last_reason:
                    changed = True
                    
            if changed:
                elapsed = now - state_start_time
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                prev_app_name = last_app.process_name if last_app else "None"
                new_app_name = app.process_name if app else "None"
                
                # Credit time to previous state
                if last_category == "APP" and last_app:
                    log(f"[{timestamp}] CHANGE: {prev_app_name} -> {new_app_name} | Credited {elapsed:.1f}s to {prev_app_name}")
                    total_foreground_time += elapsed
                    if last_app.process_name.lower() == "brave.exe":
                        total_brave_time += elapsed
                elif last_category == "SYSTEM":
                    log(f"[{timestamp}] CHANGE: SYSTEM -> {new_app_name} | Credited {elapsed:.1f}s to SYSTEM")
                    total_system_time += elapsed
                elif last_category == "UNASSIGNED":
                    log(f"[{timestamp}] CHANGE: UNASSIGNED -> {new_app_name} | Credited {elapsed:.1f}s to UNASSIGNED")
                    if "Idle" in last_reason:
                        total_idle_time += elapsed
                    total_unassigned_time += elapsed
                
                # Log new state details
                if current_category == "APP" and app:
                    log(f"    New App: {app.process_name}")
                    log(f"    Title: {app.window_title}")
                    log(f"    Path: {app.exe_path}")
                else:
                    log(f"    No app receives credit. Reason: {reason}")
                log("") # blank line for readability
                
                last_category = current_category
                last_app = app
                last_reason = reason
                state_start_time = now

    except KeyboardInterrupt:
        now = time.time()
        elapsed = now - state_start_time
        
        # Credit final state
        if last_category == "APP" and last_app:
            total_foreground_time += elapsed
            if last_app.process_name.lower() == "brave.exe":
                total_brave_time += elapsed
        elif last_category == "SYSTEM":
            total_system_time += elapsed
        elif last_category == "UNASSIGNED":
            if "Idle" in last_reason:
                total_idle_time += elapsed
            total_unassigned_time += elapsed

        log("\n================ REPORT ================")
        log(f"Total foreground time: {total_foreground_time:.1f} seconds")
        log(f"Total Brave time: {total_brave_time:.1f} seconds")
        log(f"Total unassigned time: {total_unassigned_time:.1f} seconds")
        log(f"Total idle time: {total_idle_time:.1f} seconds")
        log(f"Total system process time: {total_system_time:.1f} seconds")
        log("========================================")
        log_file.close()

if __name__ == '__main__':
    main()
