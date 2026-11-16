# Notch — Canonical Architecture & Development Rules

This document establishes the permanent architectural boundaries for this repository.
All future development by engineers and AI coding agents MUST strictly follow these rules.

---

## 1. Zero Root Pollution Rule

**NEVER create a new file in the repository root directory simply because it is convenient.**

The root directory is strictly reserved for canonical project-level files:
- Runtime entry point: `main.py`
- Build & packaging configuration: `build.py`, `digital_wellbeing.spec`, `app.manifest`, `file_version_info.txt`, `version.json`
- Dependency & toolchain configs: `requirements.txt`, `pytest.ini`, `vercel.json`, `.gitignore`
- Project governance & documentation: `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `AGENTS.md`
- Source image artifact: `Logo`

Do not create implementation files, tests, scripts, temporary notes, or media in the root directory.

---

## 2. Architectural Boundaries & Responsibilities

### Native Windows Desktop Application
The desktop application is built with Python 3.11+ and PySide6 (Qt). Its packages are top-level domain packages:

- `core/`: Application-wide constants (`constants.py`), centralized logging (`logger.py`), and version management (`version.py`).
- `database/`: SQLite data persistence layer:
  - `schema.py`: Table DDL, migrations, and index definitions.
  - `models.py`: Domain dataclasses (`AppUsage`, `AppLimit`, `LockedApp`, `WebsiteLimit`, etc.).
  - `repository.py`: Data access object, queries, rollups, and cache.
- `tracker/`: OS-level background activity monitoring:
  - Active window and title polling via Win32 (`foreground.py`).
  - Active browser URL and domain extraction via UIAutomation (`browser_domain.py`).
  - Idle detection via Win32 `GetLastInputInfo` (`idle.py`).
  - WinRT media playback state monitoring (`media.py`).
  - SleepGuard inactivity state machine (`sleepguard.py`).
  - Usage categorization (`categorizer.py`) and diagnostic telemetry (`diagnostics.py`, `telemetry.py`).
- `protection/`: User wellbeing policy enforcement:
  - Process termination and launch interception (`app_locker.py`).
  - Hosts file blocking and DNS sinkholing (`website_blocker.py`).
  - Application and website daily timers and limits (`limits.py`, `timer.py`, `website_limits.py`, `website_timer.py`).
  - Focus session lifecycle (`focus_manager.py`).
  - PBKDF2 PIN hashing and Windows Hello biometrics (`pin.py`, `windows_hello.py`).
- `analytics/`: Historical metric computation, usage aggregation, trends, and KPI calculations (`engine.py`).
- `notifications/`: Native Windows toast notifications via WinRT / plyer fallback (`notifier.py`).
- `settings/`: Persistent user settings storage (`manager.py`).
- `ui/`: PySide6 desktop user interface:
  - `app.py`: `QApplication` lifecycle, single-instance mutex, and system tray.
  - `main_window.py`: Primary application shell, sidebar navigation, and page router.
  - `pages/`: Individual view screens (dashboard, history, limits, sleepguard, settings, etc.).
  - `widgets/`: Reusable UI components, cards, charts, and dialogs.
  - `theme/`: Theme tokens, color palettes, and QSS styling.
- `utils/`: System utilities (Win32 window helpers, Windows startup registry, updater, icon extraction, power actions).

**Boundary Rules for Desktop Code:**
- Presentation code in `ui/` must NOT directly execute raw Win32 APIs or raw SQL; use services and `repository.py`.
- Background monitoring threads in `tracker/` must communicate with `ui/` via Qt signals or thread-safe callbacks.
- Do NOT wrap these Python packages into generic `desktop/`, `backend/`, or `frontend/` folders.

### Web Platform (`website/`)
- An independent Next.js 15+ (App Router) application serving marketing, telemetry, and distribution.
- Source code strictly lives inside `website/src/`:
  - `src/app/`: Next.js pages, layouts, and API routes (`api/download/`, `api/stats/`).
  - `src/components/`: Reusable React components (`ui/`, `layout/`, `interactive/`).
  - `src/config/`: Web-specific site constants and feature configurations.
  - `src/lib/`: Web utility functions.
  - `src/__tests__/`: Web unit tests.
- Do not mix desktop Python code into `website/` or web code into desktop packages.

### Automated & Manual Tests (`tests/`)
- All automated unit and regression tests live directly in `tests/` matching `test_*.py`.
- `tests/manual/`: Manual test harnesses, interactive Qt previews, screenshot tests, and live QA runners.
- `tests/e2e/`: End-to-end integration simulation scripts (e.g., `e2e_test.py`).
- Automated tests are scoped by `pytest.ini` (`testpaths = tests`, ignoring `tests/manual` and `tests/e2e`).
- All automated tests must run headless and pass cleanly.

### Developer & Automation Scripts (`scripts/`)
Non-runtime automation belongs strictly in `scripts/`:
- `scripts/capture/`: UI screenshot and visual test automation.
- `scripts/dev/`: Developer diagnostics, inspection scripts, process helpers.
- `scripts/media/`: Video rendering, icon generation, and audio processing tools.
- `scripts/packaging/`: Inno Setup and release packaging helpers.
- Scripts must resolve the project root robustly via `Path(__file__).resolve().parents[2]` rather than brittle relative paths.

### Scratch & Local Artifacts (`scratch/`)
- `scratch/` is reserved strictly for untracked local experimentation, browser test profiles (`chrome_profile`, `brave_profile`), test databases, and promotional media renders (`scratch/media/`).
- Do NOT turn `scratch/` into a permanent source-code archive.
- Do NOT commit generated scratch media or browser profile data to git.

---

## 3. Mandatory Pre-Creation Checklist

BEFORE creating ANY new file:
1. **Determine responsibility**: What is the single purpose of this file?
2. **Identify architectural owner**: Which directory above owns this responsibility?
3. **Check for existing modules**: Does an existing file/module already handle this? Prefer extending an existing appropriate module over creating another duplicate file.
4. **Place immediately in its destination**: Never create files in the root with the intention of moving them later.
5. **Verify path resolution**: Ensure any file paths or imports use project-root relative references or standard package imports.
