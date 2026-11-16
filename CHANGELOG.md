# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Replaced overlapping mouse-retained Qt button/tab focus rectangles with shared, theme-aware keyboard focus indicators while preserving selected-state styling.
- Made Focus, Deep Work, and SleepGuard countdowns calculate remaining time from monotonic deadlines so delayed UI callbacks do not extend sessions.
- Preserved exact remaining seconds when recurring Focus Schedules start or reconcile after wake.
- Moved Windows Hello availability checks off the UI thread to prevent App Locker initialization from stalling application startup.
- Preserved usage entries shorter than one minute and corrected App Details totals to use repository-backed active time and week-to-date averages.
- Fully decoupled focus enforcement process checks and website inspections from the UI thread to maintain sub-millisecond dispatch latency and eliminate UI stutter.
- Corrected low-contrast empty-state and placeholder labels in Usage, Focus, and Insights using centralized ThemeManager tokens compliant with WCAG AA in both dark and light modes.
- Established canonical session-scoped Qt application fixture in automated test harness, eliminating PySide6 heap corruption during full test suite runs.

## [3.1.5] — 2026-08-30
### Added
- **Insights & Analytics** — Substantially improved data visualization, usage metrics, and historical reporting pages.
- **Settings UI** — Cleaned up the settings architecture to be premium, responsive, and functional.
- **SleepGuard** — Enhanced stability and shutdown warning presentation.

### Changed
- **Focus Mode** — Focus Mode is currently an Application-Only blocker. Website blocking has been temporarily disabled while the enforcement architecture undergoes refinement.

### Fixed
- **App Locker** — General stability and reliability improvements for native Windows Hello authentication integration.
- **Installer & Startup** — Stable and robust installer with automatic process termination on updates and clean application lifecycle management.
### Fixed
- Fixed App Locker UI obscuring the native Windows Hello authentication prompt by intelligently dropping topmost window privileges and presenting a minimal status surface while OS verification is active.

## [3.1.0] — 2026-08-23
### Added
- **App Locker** — Persistent per-application protection using Windows Hello (face, fingerprint, PIN) with NYW PIN as fallback.
- **Windows Hello integration** — Native WinRT `UserConsentVerifier` API via async QThread bridge; never blocks UI.
- **Authentication dialog** — Premium lock dialog with Windows Hello button, PIN fallback toggle, all result states handled gracefully.
- **Process picker** — Running-process browser + .exe file picker to add applications to the lock list.
- **App Locker page** — Dedicated sidebar navigation item (🔒 App Locker) with full settings (method, duration, locked app list).
- **Temporary access grants** — Once / 5 min / 15 min (default) / Until app closes. Grants are in-memory only (cleared on restart for safety).
- **Security guards** — Disabling App Locker, removing apps, or changing settings all require authentication.
- **SYSTEM_SAFE list** — explorer.exe, dwm.exe, csrss.exe, lsass.exe, NYW itself, and other critical Windows processes cannot be locked.
- App Locker configuration persists in SQLite (`app_locker_apps` table) and survives crashes/restarts.

### Fixed
- **Strict Focus Mode PIN unlock** — Correct PIN now properly stops Focus Mode. Fixed double-verification bug where `stop_focus()` re-checked PIN after dialog already validated it.

### Changed
- Navigation sidebar renumbered: App Locker = page 3, Settings = page 4, Dev = page 5.
- `requirements.txt` — Added `winrt-Windows.Security.Credentials.UI>=3.2.1`.

## [Unreleased]
### Added
- Initial project structure for Digital Wellbeing.
- PySide6 UI and Win32 tracking services.
- Local SQLite database implementation for crash-safe analytics.
