import subprocess
import time
import psutil
from PIL import ImageGrab
import os

def kill_running_instances():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = p.info['cmdline']
            if cmd and 'python' in p.info['name'].lower() and any('main.py' in c for c in cmd):
                p.terminate()
                p.wait(timeout=3)
        except:
            pass

def main():
    print("Killing existing instances...")
    kill_running_instances()

    print("Launching python main.py as a subprocess...")
    proc = subprocess.Popen(["python", "main.py"], cwd=os.getcwd())

    print("Waiting 4 seconds for window to render...")
    time.sleep(4)

    print("Capturing full desktop screenshot to prove main.py launched the window...")
    screenshot_path = r"C:\Users\akshi\.gemini\antigravity-ide\brain\2a916beb-1ca0-41a9-80f8-940c213c0137\scratch\real_main_py_capture.png"
    ImageGrab.grab().save(screenshot_path)
    print(f"Saved screenshot to {screenshot_path}")

    print("Terminating main.py...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Done.")

if __name__ == "__main__":
    main()
