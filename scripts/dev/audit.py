import os
import sys
import hashlib
import time

def hash_file(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()
    except Exception as e:
        return str(e)

def get_mtime(path):
    try:
        return time.ctime(os.path.getmtime(path))
    except Exception as e:
        return str(e)

def main():
    print("1. FULL ABSOLUTE PATH of the project you are editing:")
    print(r"C:\Users\akshi\OneDrive\Documents\personal\DIGITAL WELLBEING")
    
    print("\n2. FULL ABSOLUTE PATH from which python main.py is executed:")
    # We will assume it's the cwd, but we can also print sys.executable
    print(sys.executable)
    
    print("\n3. Print os.getcwd():")
    print(os.getcwd())
    
    print("\n4. Print __file__ from modules:")
    # Import them to get __file__
    sys.path.insert(0, os.getcwd())
    import main
    import ui.app as app
    import ui.main_window as main_window
    import ui.pages.dashboard as dashboard
    import ui.pages.activity as activity
    
    print("main.py:", main.__file__)
    print("app.py:", app.__file__)
    print("main_window.py:", main_window.__file__)
    print("dashboard.py:", dashboard.__file__)
    print("activity.py:", activity.__file__)
    
    print("\n6 & 7. Print the SHA256 hash and mtime of:")
    files = [
        r"ui\pages\dashboard.py",
        r"ui\pages\activity.py",
        r"ui\main_window.py"
    ]
    for f in files:
        full_path = os.path.join(os.getcwd(), f)
        print(f"\n{f}:")
        print("Hash:", hash_file(full_path))
        print("Mtime:", get_mtime(full_path))

if __name__ == "__main__":
    main()
