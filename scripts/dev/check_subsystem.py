import struct
import sys

def get_subsystem(p):
    try:
        with open(p, 'rb') as f:
            f.seek(0x3c)
            pe = struct.unpack('<I', f.read(4))[0]
            f.seek(pe)
            if f.read(4) != b'PE\x00\x00':
                return 'Not PE'
            f.seek(pe + 24)
            opt = struct.unpack('<H', f.read(2))[0]
            f.seek(pe + 24 + 68)
            return struct.unpack('<H', f.read(2))[0]
    except Exception as e:
        return str(e)

import os
installed = r"C:\Program Files\DigitalWellbeing\DigitalWellbeing.exe"
dist = r"dist\DigitalWellbeing\DigitalWellbeing.exe"

print(f"Installed exists: {os.path.exists(installed)}")
print(f"Installed Subsystem: {get_subsystem(installed)}")
print(f"Dist exists: {os.path.exists(dist)}")
print(f"Dist Subsystem: {get_subsystem(dist)}")
