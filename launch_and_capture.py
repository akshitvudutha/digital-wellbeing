import subprocess
import time
import sys
import os

def main():
    print("Killing existing instances...")
    subprocess.run([sys.executable, "kill_all.py"])
    
    print("Launching python main.py...")
    env = os.environ.copy()
    if "DW_SCREENSHOT_MODE" in env:
        del env["DW_SCREENSHOT_MODE"]
    if "DW_TEST_MODE" in env:
        del env["DW_TEST_MODE"]
        
    proc = subprocess.Popen([sys.executable, "main.py"], env=env)
    
    print("Waiting 5 seconds for window to fully render...")
    time.sleep(5)
    
    print("Taking OS-level screenshot...")
    subprocess.run([sys.executable, "real_screenshot.py"])
    
    print("Terminating application...")
    proc.terminate()
    proc.wait(timeout=3)
    
    print("Done.")

if __name__ == "__main__":
    main()
