import os
import sys
import time
from pathlib import Path

search_dirs = [
    Path("d:/Projects/Digital Wellbeing"),
    Path("d:/Projects"),
    Path("d:/"),
    Path("C:/Users/akshi/Downloads"),
    Path("C:/Users/akshi/Desktop"),
    Path("C:/Users/akshi/Videos"),
    Path("C:/Users/akshi/OneDrive/Videos"),
    Path("C:/Users/akshi/OneDrive/Desktop"),
    Path("C:/Users/akshi/OneDrive/Documents"),
    Path("C:/Users/akshi/Documents"),
]

video_exts = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
found = []

for d in search_dirs:
    if not d.exists():
        continue
    try:
        for root, dirs, files in os.walk(d):
            # limit depth to 3
            rel = Path(root).relative_to(d)
            if len(rel.parts) > 3:
                continue
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in video_exts:
                    fp = Path(root) / f
                    try:
                        mtime = fp.stat().st_mtime
                        size = fp.stat().st_size
                        found.append((mtime, fp, size))
                    except Exception:
                        pass
    except Exception:
        pass

found.sort(key=lambda x: x[0], reverse=True)
print(f"Total videos found: {len(found)}")
print("-" * 80)
for mtime, fp, size in found[:25]:
    dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
    print(f"{dt_str} | {size/1024/1024:7.2f} MB | {fp}")
