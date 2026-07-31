import subprocess
import sys
import os

def main():
    print("Killing existing instances...")
    subprocess.run([sys.executable, "kill_all.py"])
    
    print("Launching python main.py detached on user desktop...")
    env = os.environ.copy()
    if "DW_SCREENSHOT_MODE" in env:
        del env["DW_SCREENSHOT_MODE"]
    if "DW_TEST_MODE" in env:
        del env["DW_TEST_MODE"]
        
    # Launch completely detached so it stays open
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([sys.executable, "main.py"], env=env, creationflags=DETACHED_PROCESS)
    print("Application launched. It should now be visible on your desktop.")

if __name__ == "__main__":
    main()
