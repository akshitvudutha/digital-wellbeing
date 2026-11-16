import psutil
import sys
import os

def kill_running_instances():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = p.info['cmdline']
            if cmd and 'python' in p.info['name'].lower() and any('main.py' in c for c in cmd):
                print(f"Killing running instance: PID {p.info['pid']}")
                p.terminate()
                p.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass

if __name__ == "__main__":
    kill_running_instances()
    print("Old instances killed.")
