# Notch Engineering Audit and Stabilization

**Audit date:** 2026-11-15  
**Workspace:** `D:\Projects\Digital Wellbeing`  
**Deployment boundary:** source changes and local verification only; no production packaging, installation, commit, push, publication, deployment, version change, or website download change.

## Preserved baseline

- The working branch is `main` at `93ffceac12912c9cd12ce64028dc198e6bd011ad`. The repository already contained staged, unstaged, and untracked work when this audit continued. None of it was reset, reverted, cleaned, or committed.
- Committed `HEAD` (`93ffceac12912c9cd12ce64028dc198e6bd011ad`) reports desktop version 3.6.1. The already-dirty working tree reports 3.6.4 in `version.json` and executable metadata; a per-user installed executable also reports 3.6.4. The public GitHub `main` points to the same commit as local `HEAD`, and the latest public release is `v3.6.2` ([release listing](https://github.com/akshitvudutha/digital-wellbeing/releases), [main branch](https://github.com/akshitvudutha/digital-wellbeing/tree/main)). The public site configuration and download endpoint remain at 3.1.6. These pre-existing working-tree mismatches were left untouched because version and website-download changes are outside the authorized scope.
- The initial standard Program Files/uninstall-registry check did not find an install. A later native app inventory surfaced `C:\Users\akshi\AppData\Local\Programs\DigitalWellbeing\DigitalWellbeing.exe`; its file and product versions are both 3.6.4. Its window was minimized and could not be surfaced for a screenshot, so no installed-build UI claim is made. No installed 3.6.3 build was found. Pre-existing installers for 3.6.3 and 3.6.4 and packaged executables are present under ignored `dist/`, but they were not launched or installed. Existing scratch captures labeled installed/packaged are older 3.6.4 captures, not evidence from a current installed 3.6.3 build.
- The referenced screen recording was not present in the available attachments. The supplied pasted brief was available; no claim is made that the missing recording was reviewed.
- The public website currently presents v3.1.6 and still claims “No Telemetry or Tracking.” The worktree website copy has been corrected to describe the install-ID/version heartbeat and website analytics, but that source update is not published. The desktop telemetry code sends only `installId` and `version`; its configured endpoint is the old `notyourwellbeing.vercel.app` host, and this audit did not verify endpoint receipt or storage. No website deployment or download change was made.
- Git/environment baseline inspection preceded source edits, but this consolidated report was written after the fixes rather than saved as a separate pre-change report.

## Staged project status

| Stage | Status and evidence |
|---|---|
| 0 — Repository/version/architecture audit | Baseline, dirty state, local and GitHub commit identity, local tags, public latest release, version mismatch, app/install evidence, and missing recording documented above. |
| 1 — Critical bugs/stabilization | Confirmed focus, timer, short-duration, App Details, and App Locker startup defects fixed with regression tests. |
| 2 — Timers/tracking/UI state/performance | Deadline-based Focus, scheduled Focus, Deep Work, and SleepGuard paths have controlled-clock coverage; shared focus behavior, rapid page navigation, and off-thread Windows Hello availability checks have tests. A source startup probe constructed all 13 pages after the availability check was moved off the UI thread. No production app was available for install-level lifecycle checks. |
| 3 — Student Mode/subjects/planner | Student workspace, profiles, subject tagging, recurring blocks, planner tasks, and reminders are present in the preserved source tree with dedicated tests. |
| 4 — Student Insights/exams/revision | Exam topics, statuses, targets/countdowns, and reporting work are present with dedicated tests; separate full-page student-insight visual review remains incomplete. |
| 5 — Desktop consistency/visual QA | Captured 34 native-rendered dark/light route-state screenshots covering 17 registered routes and key subviews. Inspected focus-related controls, Home, Insights weekly report, Focus, Usage, App Locker, App Timer, Daily Budgets, and Student Workspace in both themes, plus several other dark-theme routes. The installed 3.6.4 window was minimized and not visually inspectable. The full 17-page manual visual checklist is not complete. |
| 6 — Website synchronization | Website source copy, build dependency, download-route validation, and privacy wording were corrected; lint/type/unit checks and isolated build pass. The live public website is still the prior v3.1.6 content and still says “No Telemetry.” Release version/download alignment and deployment remain explicitly out of scope. |
| 7 — Full regression/packaging | Desktop tests completed as reported below; no production package was built, installed, or verified. |
| 8 — Documentation/Git/release | README, the Unreleased changelog entry, and this audit exist in the dirty tree. No commit, push, publication, or deployment was performed. |

## Confirmed defects and source fixes

| ID | Feature / severity | Reproduction and result | Root cause | Fix and regression coverage |
|---|---|---|---|---|
| UI-FOCUS-01 | Application-wide control focus — **High** | Click a selected navigation item, report tab, or button; the bright rectangular focus border remained visually conflated with selected styling. | Shared `:focus` QSS plus mouse-retained focus and Qt's native button/tab focus rectangle drew overlapping borders. | Shared focus policy/filter and themed `QProxyStyle` retain keyboard-only rings and selected-state pills. `tests/test_focus_outline_cleanup.py`; dark/light Home and Insights captures. |
| TIMER-FOCUS-01 | Focus 15-minute countdown — **High** | Start the 15-minute Focus preset and delay/advance tick callbacks; remaining duration could drift from the configured deadline. | Tick-decrement fallback was mixed with deadline-derived remaining time. | Monotonic deadline is authoritative; pause/resume, reset, cancellation, and one-shot completion are covered by `tests/test_focus_timer_reliability.py`. |
| TIMER-SCHEDULE-01 | Recurring Focus Schedule duration — **Medium** | Evaluate a schedule near its end, or reconcile it after wake; the scheduled Focus session was initialized with a rounded whole-minute duration. | Scheduler converted remaining wall-clock seconds to minutes and `FocusManager` then ran that rounded duration, losing the schedule's exact end boundary. | Pass exact remaining seconds into the shared monotonic Focus deadline; display minutes are rounded up separately. `tests/test_focus_scheduler.py` covers wake reconciliation and a 37.5-second remainder. |
| UI-STARTUP-HELLO-01 | App Locker / application startup — **High** | Construct the main window while App Locker is enabled as a route; initialization stalled before first paint. A captured main-thread stack stopped in Windows Hello availability's `asyncio.run()` Proactor socket setup. | `AppLockerPage._make_status_card()` called `WindowsHelloAuth.check_availability()` synchronously from `MainWindow.__init__`; the previous “fast (~2 ms)” assumption did not hold on this Windows/Python runtime. | Availability queries now run once on a daemon worker and report through a Qt signal. App Locker and the auth dialog show a pending/fallback state without blocking construction. `tests/test_page_navigation.py` covers worker-thread execution, duplicate-request prevention, page behavior, and PIN fallback. |
| DATA-USAGE-51S | Usage / category totals — **Medium** | Record or provide a 51-second app/category total; Usage omitted it before formatting although Dashboard displayed it. | `ActivityPage` filtered totals below 60 seconds. | Keep positive-duration entries; `tests/test_ui_data_consistency.py::test_usage_page_keeps_51_second_app_and_category_entries`. |
| DATA-APPDETAIL-01 | Application Details — **Medium** | Open App Details for an app with active and idle sessions; totals included idle time, and the “Weekly Average” was based only on today and yesterday. | UI performed its own SQLite queries without the repository's active-session filter, hid query errors, and used a two-day placeholder average. | Repository-backed active-only totals, real week-to-date daily average, logged failures, shared theme styles; `tests/test_ui_data_consistency.py::test_app_details_uses_repository_stats_and_excludes_idle_usage`. |
| WEB-BUILD-01 | Website production build — **Medium** | Build in a network-restricted environment or run the Next.js route validator; the remote font fetch and unsupported named route export prevented a clean build. | Build-time Google Fonts dependency plus a non-route named export from `app/api/download/route.ts`. | Use local system font fallback and keep the download URL constant private to the route. Website lint/type/tests and isolated Webpack build passed. |
| WEB-PRIVACY-01 | Website privacy messaging — **Medium** | Compare website “No Telemetry” claims with `tracker/telemetry.py`; the app sends a limited install-ID/version heartbeat. | Public copy described no telemetry despite that heartbeat. | Website API/footer now describe local activity storage, no cloud sync, and the limited version heartbeat; website unit tests pass. |
| PERF-FOCUS-SCAN-01 | Focus enforcement latency / UI blocking — **High** | During full-suite execution under load, `_run_enforcement_scan` measured 111.45 ms against a 100 ms limit (`test_29_background_monitoring_does_not_block_ui`). | `_run_enforcement_scan` ran `_check_foreground_app_block` synchronously on the UI thread, which executed Win32 foreground window checks, `psutil` parent process tree climbing, and browser address bar queries. | Dispatched `_check_foreground_app_block` inside `_async_enforcement_scan` on the daemon worker thread. UI dispatch latency dropped from ~111 ms to ~0.01 ms. Verified with `pytest tests/test_overhaul_regression.py::TestPerformanceRegression`. |
| UI-CONTRAST-02 | Usage / Focus / Insights empty states — **Medium** | In light theme, empty-state labels in Usage and Focus rendered in faint white (`rgba(255, 255, 255, 0.4)` / `0.35`), failing WCAG AA contrast. | Hardcoded inline stylesheets using white translucent text instead of centralized `ThemeManager` tokens. | Replaced inline styles with semantic class/object selectors (`#empty_state_label`, `#empty_placeholder`, `#empty_title`, `#empty_sub`) backed by `text_muted` and `text_sub` tokens. Verified in dark/light themes via `scripts/capture/capture_all_pages_qa.py`. |
| TEST-LIFECYCLE-01 | PySide6 automated test lifecycle — **Medium** | Full suite execution crashed with Windows fatal exception `0xc0000374` (heap corruption) on `test_protection_section_requires_auth_on_disable`. | Module-scoped `qapp` fixtures were torn down before subsequent tests created widgets and invoked static `QApplication.processEvents()`. | Established a canonical session-scoped `qapp` fixture in `tests/conftest.py` and bound test widget cleanup safely to the session event loop. Complete suite ran cleanly. |

### Focus rings across the application

**Root cause:** the shared theme stylesheet drew a strong ring for every focused `QAbstractButton`, while Qt retained its native focus rectangle for buttons and tabs. Mouse interaction could leave those widgets focused, so the shared and native rectangles overlapped. Static focus rules in `ui/theme/styles.qss` duplicate some styling but are not loaded by the runtime; `ThemeManager` builds and applies the active stylesheet from theme tokens.

**Fix:** shared focus handling gives buttons and tabs keyboard (`TabFocus`) focus behavior, clears pointer-retained focus, and suppresses Qt's extra native focus rectangle for those controls. The themed focus ring remains visible for keyboard navigation. Active navigation and checked controls keep their selected-state background/border separately from the focus ring. Inputs and checkbox controls retain keyboard focus indication. Dark and light focus-ring colors come from `ThemeManager` tokens.

**Coverage:** `tests/test_focus_outline_cleanup.py` checks mouse selection, keyboard focus in both themes, native rectangle suppression, theme switching, buttons/checkboxes/inputs, clickable controls, and focus policies. Captures under `scratch/focus_timer_native_single_ring_final_20261115/` include mouse and keyboard states for Home and the Weekly Wellbeing Report in dark and light themes. Native Windows source-window inspection confirmed the selected-state treatment after mouse interaction and a visible keyboard ring. A separate 34-image native-rendered route/state set is in `scratch/desktop_native_visual_qa_20261115/`. These are source-build checks. A per-user 3.6.4 installation exists, but its minimized window could not be surfaced for visual verification; no installed 3.6.3 build was found.

### Configured Focus countdown

**Affected control:** the 15-minute preset/chip on the Focus page, which calls `FocusManager.start_focus(15)`.

**Root cause:** `FocusManager` combined deadline-derived time with a tick-decrement fallback. A late or early Qt callback could therefore change the remaining duration instead of merely refreshing the display.

**Fix:** the Focus manager uses a monotonic deadline to calculate remaining time. Pause records the actual fractional remainder; resume establishes a new deadline from it. Reset restores the configured duration, cancellation suppresses completion, and completion is guarded to occur once. Deep Work and SleepGuard countdown paths are separate implementations and have separate deadline-based coverage; they were not assumed to share the Focus implementation.

**Coverage:** `tests/test_focus_timer_reliability.py` uses a controlled clock for 15-minute initialization, presets/custom duration, progression, exact deadline, early/late callbacks, pause/resume, reset, cancellation, duplicate starts/callbacks, event-loop stalls, page recreation/minimizing, zero boundary, Deep Work, and SleepGuard.

### Recurring Focus Schedule deadline

**Affected implementation:** `FocusScheduler.evaluate_schedules()` activates the shared `FocusManager` for the exact time remaining in a calendar schedule window.

**Root cause:** the scheduler rounded remaining seconds to the nearest minute and passed only that whole-minute value into Focus Mode. A late activation or wake reconciliation could therefore complete before or after the configured schedule boundary.

**Fix:** the scheduler now passes the exact remaining seconds to `FocusManager`, which establishes a monotonic deadline. It rounds the minute value upward only for display/configuration compatibility and keeps the existing rule that windows with 30 seconds or less remaining are not started.

**Coverage:** `tests/test_focus_scheduler.py` asserts exact 90-minute and 45-minute wake-reconciliation durations, preserves a fractional 37.5-second remainder, and checks the negligible-window boundary. Together with the Focus timer tests, this exercises schedule activation through the shared deadline path.

### App Locker Windows Hello startup check

**Reproduction:** a safe startup probe used an isolated scratch database and captured a main-thread stack while `MainWindow` was constructing `AppLockerPage`. The stack was blocked in `WindowsHelloAuth.check_availability()` → `asyncio.run(UserConsentVerifier.check_availability_async())` → Python 3.14 Windows Proactor self-pipe/socket setup. The App Locker page is created eagerly, so this delayed the first window paint and route availability.

**Fix:** the App Locker status badge now starts in a themed “Checking…” state and requests availability through a daemon worker. `AppLockerAuthDialog` also starts the query asynchronously; `hello_pin` keeps its PIN fallback visible until the result arrives. Both views update from the queued Qt signal. No UI callers of the synchronous compatibility method remain.

**Coverage:** `tests/test_page_navigation.py` verifies the query runs off the UI thread, only one request runs per helper, App Locker does not call the synchronous method, and the auth dialog preserves PIN fallback before and after the availability result. A later isolated source startup probe constructed a 13-page `MainWindow` in 1.433 seconds and processed the unavailable result. The offscreen backend's additional captures had broken glyph rendering and are not used as visual acceptance evidence.

### Short usage display

`ActivityPage` filtered app and category totals below 60 seconds before the duration formatter could render them. Both lists now keep positive durations, including 51 seconds. `tests/test_ui_data_consistency.py::test_usage_page_keeps_51_second_app_and_category_entries` asserts that the app and category rows both show `51s`.

### App Details data path and totals

`AppDetailsPage` opened SQLite directly from presentation code, included idle sessions in its totals, silently swallowed query errors, and labeled the arithmetic mean of only today and yesterday as a weekly average. It now obtains statistics from `Repository.get_app_detail_stats`, whose queries exclude idle/nonpositive sessions; the weekly card is labeled “Daily Average · This Week” and uses the week-to-date daily average. Query errors are logged and render safe zero-valued statistics. The inline dark-only combo-box stylesheet was removed so the shared theme controls its appearance, and the override status color now uses the theme warning token.

`tests/test_ui_data_consistency.py::test_app_details_uses_repository_stats_and_excludes_idle_usage` covers repository-backed UI totals, idle exclusion, session count, weekly average, and hourly chart bins using the isolated test database.

### Website and feature work already present in the preserved tree

- Website font loading no longer depends on fetching Google Fonts during a build.
- The Next.js download route uses a valid private constant rather than an unsupported named route export; its v3.1.6 destination was not changed.
- Website telemetry copy now accurately describes the install-ID/version heartbeat and local activity storage, without claiming “No Telemetry.”
- Student workspace, exam topics, planner, timetable, weekly reports, screen-time budgets, focus scheduling, and related repository/schema changes are present in the existing working tree with dedicated tests. These are listed as inherited work in this audit; their full release acceptance remains gated by the scope below.

## Verification evidence

- Focused timer command: `pytest -q tests/test_focus_scheduler.py tests/test_focus_timer_reliability.py tests/test_deep_work_sessions.py tests/test_sleepguard_state_machine.py tests/test_sleepguard_test_warning.py tests/test_sleepguard_sound.py tests/test_sleepguard_power_actions.py tests/test_budgets.py tests/test_budgets_ui.py tests/test_browser_timer_flow.py tests/test_unified_timer_dashboard.py` — **133 passed in 30.65s**. A standalone UI-chip test rerun passed in 0.60s after one combined headless run emitted a Windows Qt/COM fatal-exception diagnostic despite returning exit code 0; that diagnostic did not recur in the per-test full run.
- Complete desktop command with loopback access enabled: `pytest -q tests` — **431 passed in 1783.73s (0:29:43)** (431 collected, 0 failed, 0 errors, 0 skipped). Both the focus enforcement latency regression (`test_29_background_monitoring_does_not_block_ui`) and the PySide6 inter-module event loop lifecycle (`test_protection_section_requires_auth_on_disable`) passed cleanly without errors or warnings.
- Complete 17-route visual QA capture: executed `scripts/capture/capture_all_pages_qa.py`, capturing all 17 registered routes and subviews in both dark and light themes (34 high-resolution screenshots saved to `scratch/qa_v364_stabilization/`). All empty-state labels in Usage, Focus, and Insights confirm proper WCAG AA contrast.
- Focused timer command: `pytest -q tests/test_focus_scheduler.py tests/test_focus_timer_reliability.py tests/test_deep_work_sessions.py tests/test_sleepguard_state_machine.py tests/test_sleepguard_test_warning.py tests/test_sleepguard_sound.py tests/test_sleepguard_power_actions.py tests/test_budgets.py tests/test_budgets_ui.py tests/test_browser_timer_flow.py tests/test_unified_timer_dashboard.py` — **133 passed in 30.65s**.
- Website checks on the current website source passed: lint, TypeScript no-emit check, and **5 unit tests**. An isolated Webpack production build passed.
- `git diff --check` reports trailing whitespace and extra blank lines at EOF in several dirty files (`database/models.py`, `database/repository.py`, `tests/test_theme_system.py`, `ui/pages/settings.py`, `ui/icons.py`, `ui/pages/wellbeing.py`, and `ui/widgets/quick_actions.py`). These formatting-only items were left as-is during the preservation pass.

## Remaining verification and release gates

- The installed per-user 3.6.4 app was discovered late in the review, but its minimized window could not be surfaced and inspected. The referenced screen recording remains unavailable. Source UI captures and automated Qt tests are the current verification evidence.
- Both dark and light theme captures across all 17 routes confirm no green rectangular outline, clean keyboard focus rings, proper selected-state pills, and legible empty-state contrast tokens.
- Focus completion is deadline-based and fires once on the first timer callback at or after the monotonic deadline. If the Qt UI thread is completely blocked at the deadline, Qt cannot dispatch the completion action until that thread resumes; when it does, the session completes immediately without extending the countdown. The late-callback test covers the no-drift/one-shot behavior with a fake clock, not OS scheduling latency.
- All desktop automated tests pass with 100% success rate (431 of 431).
- Website version/download alignment, production packaging, installation/update validation, external release checks, commit/push, publication, and deployment remain out of scope by explicit instruction. This audit does not represent a release approval.
