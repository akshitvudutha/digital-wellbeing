import subprocess
import time
import sys

def main():
    print("Launching python main.py...")
    proc = subprocess.Popen([sys.executable, "main.py"])
    
    print("Waiting 5 seconds for window to fully render...")
    time.sleep(5)
    
    print("Listing windows...")
    subprocess.run([sys.executable, "list_windows.py"])
    
    print("Terminating application...")
    proc.terminate()
    proc.wait(timeout=3)
    
    print("Done.")

if __name__ == "__main__":
    main()
