# Digital Wellbeing

A production-quality Samsung-style Digital Wellbeing application for Windows, built with Python + PySide6.

## Overview
Digital Wellbeing helps you understand and manage your screen time. It tracks active windows, idle time, and provides detailed analytics and insights into your daily, weekly, and monthly computer usage habits. It is designed to be lightweight, running as a background service and providing a beautiful, modern Windows 11 Fluent style interface when you want to review your data.

## Features
- Real-time foreground application tracking (process name, executable path, window title)
- Idle detection via `GetLastInputInfo` (wraparound-safe)
- Lock/Unlock and Sleep/Resume/Shutdown detection via native Win32 window message loop
- Crash-safe tracking with a 30s heartbeat DB synchronization
- System tray integration with background tracking
- Light and Dark mode options (Windows 11 Fluent style)
- Autostart with Windows (registry)
- CSV reports export
- Rotating log file

## Screenshots
*(Add screenshots of the application here once captured)*
- **Dashboard:** `![Dashboard Screenshot](docs/screenshots/dashboard.png)`
- **Timeline:** `![Timeline Screenshot](docs/screenshots/timeline.png)`
- **Analytics:** `![Analytics Screenshot](docs/screenshots/analytics.png)`

## Installation

```powershell
pip install -r requirements.txt
```

## Running

Launch the main GUI application:
```powershell
python main.py
```

Launch minimized to the system tray (ideal for startup / task scheduler):
```powershell
python main.py --background
```

Run as a headless background tracking service (ultra-low CPU/memory, no GUI instantiated):
```powershell
python main.py --service
```

## Building Executable

```powershell
pyinstaller digital_wellbeing.spec
```

The built executable will be in `dist/DigitalWellbeing/`.

## Technologies Used
- **Python 3.13+**: Core programming language.
- **PySide6 (Qt for Python)**: UI framework for the desktop application.
- **PyQtGraph**: For high-performance charting and analytics data visualization.
- **SQLite**: Local, crash-safe database using WAL-mode for robust data storage.
- **Win32 API**: Native Windows API calls for tracking window focus and idle times.
- **PyInstaller**: For packaging into a standalone Windows executable.

## Project Structure

```
digital_wellbeing/
├── main.py               # Entry point (handles CLI service & background arguments)
├── core/                 # Constants, logging
├── database/             # Schema, models, repository (WAL-mode transaction management)
├── tracker/              # Foreground, idle, session, categorizer, manager
├── analytics/            # Aggregation engine
├── settings/             # Settings manager
├── notifications/        # Windows toast notifications
├── ui/                   # PySide6 UI (main window, pages, widgets)
└── utils/                # Autostart, CSV export, Windows utils
```

## Future Roadmap
- [ ] Implement goal setting and app limits with notifications
- [ ] Add support for cloud syncing across multiple devices
- [ ] Export reports as PDF documents
- [ ] Provide AI-driven insights on productivity patterns
- [ ] Add more comprehensive categorization rules

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
