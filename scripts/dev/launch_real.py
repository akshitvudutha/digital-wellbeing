import subprocess
import os
import sys

def main():
    env = os.environ.copy()
    env["DW_TEST_MODE"] = "1"
    env["DW_SCREENSHOT_MODE"] = "1"
    
    print("Launching real main.py...")
    proc = subprocess.run([sys.executable, "main.py"], env=env, cwd=os.getcwd())
    print("Finished running main.py.")

if __name__ == "__main__":
    main()
