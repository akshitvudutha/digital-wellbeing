import psutil
import time

def kill_running_instances():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = p.info['name'].lower()
            cmd = p.info.get('cmdline') or []
            
            # Kill Python processes running main.py
            is_python_main = 'python' in name and any('main.py' in c for c in cmd)
            # Kill compiled exe processes
            is_exe = 'digitalwellbeing.exe' in name or 'digital wellbeing.exe' in name
            
            if is_python_main or is_exe:
                print(f"Killing process {name} (PID: {p.info['pid']})")
                p.terminate()
                p.wait(timeout=3)
        except Exception as e:
            pass

if __name__ == "__main__":
    kill_running_instances()
    print("Instances killed.")
