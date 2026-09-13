# Platform support

NYW keeps usage history and settings on the local computer. Its core tracker
selects a native backend at runtime instead of importing Windows APIs on every
operating system.

## Windows

Foreground tracking, idle detection, session events, media detection, app
protection, and autostart use the existing Windows APIs. Install with:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## macOS

Foreground applications are read with AppKit and window metadata/idle time with
Quartz. macOS may ask for Screen Recording permission before window titles are
available. NYW continues tracking application names when a title is unavailable.

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Autostart uses a per-user LaunchAgent. Media-session detection and native
lock/sleep event notifications are not available yet; the regular foreground
and idle polling loop continues to operate.

## Linux

Foreground tracking currently supports X11 through EWMH and `python-xlib`.
Idle time uses the XScreenSaver extension. Most distributions provide the
required X11 libraries by default; Debian/Ubuntu users can install missing
runtime libraries with:

```bash
sudo apt install libx11-6 libxss1
python3 -m pip install -r requirements.txt
python3 main.py
```

Wayland intentionally prevents applications from globally inspecting active
windows. If `DISPLAY` is unavailable, NYW disables foreground/idle collection
instead of crashing or recording misleading activity. Use an X11 desktop
session until a suitable desktop portal becomes available.

Autostart uses the XDG autostart directory. Power actions use `systemctl` and
screen locking uses `loginctl` with an `xdg-screensaver` fallback.

## Check a setup

Run the diagnostic command before starting the GUI or background tracker:

```bash
python main.py --doctor
```

Use `python main.py --doctor --json` for scripts and support tooling. The
command reports platform capabilities and home-relative local data paths. It
does not start tracking or print window titles, application names, or activity
history.

## Graceful feature fallbacks

Unavailable session-event and media APIs do not prevent the app or headless
tracker from starting. Idle detection fails safe at zero seconds, which prevents
SleepGuard from treating an unsupported backend as evidence that the user is
away.
