# ROADMAP — Version 2.1

Goal: Deliver a targeted maintenance and reliability release (v2.1) addressing critical lifecycle, concurrency, and UX issues discovered during the architecture audit, and prepare the codebase for higher-scale testing and packaging.

Release objectives
- Fix critical shutdown / minimize-to-tray / DB lifecycle bugs.
- Harden SleepGuard and media cancellation race conditions.
- Improve DB maintenance and performance (WAL checkpointing, connection cleanup).
- Reduce CPU/power usage and make tracking adaptive.
- Add packaging CI and tests for installer and migrations.

---

Phase 1 — Critical fixes (Blockers for safe production)

1. Fix start_minimized behavior
- Priority: P0 (Critical)
- Estimated difficulty: Easy
- Estimated time: 2–4 hours
- Files affected: `ui/app.py`, `ui/main_window.py`
- Dependencies: None
- Risk level: Low
- Testing checklist:
  - Unit test: simulate DigitalWellbeingApp(start_minimized=True) and assert window not shown.
  - Manual: start app with minimize flag and verify tray-only behavior.
  - Verify minimize_to_tray setting still honored in settings page.
- Completion criteria: App respects start_minimized flag; no UI shown on startup when requested; tests passing.

2. Add Repository.close_all() and ensure connections closed at shutdown
- Priority: P0 (Critical)
- Estimated difficulty: Medium
- Estimated time: 4–8 hours
- Files affected: `database/repository.py`, `ui/app.py`, `tracker/*` (where Repository used indirectly)
- Dependencies: Phase 1.1 (cleanup ordering), trace of threads using DB
- Risk level: Medium
- Testing checklist:
  - Unit test: create Repository connections in a worker thread, call close_all(), ensure file descriptors closed.
  - Integration: run app, start/stop tracker multiple times and check for leaked DB handles using psutil or lsof-equivalent on Windows.
  - Crash simulation: interrupt tracking thread and ensure orphaned connections are closed on restart.
- Completion criteria: All per-thread sqlite connections are closed on controlled shutdown and unit tests validate no handle leaks.

3. Harden thread shutdown semantics (increase join/diagnostics)
- Priority: P0 (Critical)
- Estimated difficulty: Medium
- Estimated time: 6–10 hours
- Files affected: `tracker/manager.py`, `tracker/sleepguard.py`, `tracker/media.py`, `tracker/session.py`, `tracker/debug_logger.py`, `ui/app.py`
- Dependencies: Phase 1.2 (DB close)
- Risk level: Medium
- Testing checklist:
  - Add simulated long-running/blocked thread tests and verify controlled shutdown waits and logs diagnostics.
  - Confirm no DB writes are in-flight or partial when shutdown completes.
- Completion criteria: Threads join reliably within extended timeout, diagnostics logged if not; DB left consistent; manual shutdown tests pass.

4. SleepGuard race-fix and cancellation robustness
- Priority: P0 (Critical)
- Estimated difficulty: Medium
- Estimated time: 6–12 hours
- Files affected: `tracker/sleepguard.py`, `utils/shutdown.py`, `ui/main_window.py`, `ui/widgets/countdown_dialog.py`
- Dependencies: Phase 1.2 & 1.3
- Risk level: High
- Testing checklist:
  - Unit tests for SleepGuard._poll_loop with mocked get_idle_seconds and MediaDetectionEngine.
  - Concurrency test: trigger force_trigger and cancel_warning in tight loops to ensure no shutdown executes unexpectedly.
  - Manual: trigger countdown while minimized — ensure cancel path works (dialog/tray fallback).
- Completion criteria: Cancellation reliably prevents shutdown in race conditions; all tests pass; behavioral logs demonstrate safe ordering.

---

Phase 2 — Reliability improvements (stability & data integrity)

5. Add WAL maintenance & checkpointing
- Priority: P1 (High)
- Estimated difficulty: Medium
- Estimated time: 4–8 hours
- Files affected: `database/repository.py`, periodic task placement (new module e.g., `utils/db_maintenance.py`), `ui/app.py` (hook scheduler)
- Dependencies: Phase 1.2
- Risk level: Medium
- Testing checklist:
  - Integration: run long trace, check WAL size growth, verify checkpoint runs and WAL shrinks.
  - Ensure backups still work and no DB lock during checkpoint.
- Completion criteria: PRAGMA wal_autocheckpoint or scheduled backup+checkpoint implemented; tested under load.

6. Implement DB busy retry/backoff for writes
- Priority: P1 (High)
- Estimated difficulty: Medium
- Estimated time: 6–12 hours
- Files affected: `database/repository.py`
- Dependencies: Phase 2.1 (WAL strategy)
- Risk level: Medium
- Testing checklist:
  - Simulate concurrent writes and ensure retries with exponential backoff prevent OperationalError propagation.
  - Unit tests for write-heavy scenarios.
- Completion criteria: Writes no longer throw on transient busy errors; tests validate retry logic.

7. Background analytics backfill (non-blocking startup)
- Priority: P1 (High)
- Estimated difficulty: Medium
- Estimated time: 6–12 hours
- Files affected: `analytics/engine.py`, `ui/app.py`
- Dependencies: Phase 2.2 (DB reliability)
- Risk level: Medium
- Testing checklist:
  - Startup time measured before/after change (no blocking during UI startup).
  - Background worker performs backfill and emits progress events; UI shows progress if requested.
- Completion criteria: Startup is responsive; backfill proceeds in background and snapshots created as expected.

8. Add explicit Repository health checks & backup integrity tests
- Priority: P2 (Medium)
- Estimated difficulty: Easy
- Estimated time: 4 hours
- Files affected: `database/repository.py`, `package_release.py`, `package_release.py` (test harness)
- Dependencies: Phase 2.1
- Risk level: Low
- Testing checklist:
  - Backup/restore roundtrip test.
  - DB integrity check (PRAGMA integrity_check) after restore.
- Completion criteria: Automated backup/restore works and integrity_check returns OK.

---

Phase 3 — Performance (reduce CPU/power & optimize tracking)

9. Reduce and make tracking poll adaptive
- Priority: P1 (High)
- Estimated difficulty: Medium
- Estimated time: 8–16 hours
- Files affected: `core/constants.py` (POLL_INTERVAL_MS), `tracker/manager.py`, `tracker/foreground.py`
- Dependencies: Phase 1 & 2
- Risk level: Medium
- Testing checklist:
  - Measure CPU and power before/after at idle and heavy usage scenarios.
  - Ensure no regression in tracking granularity (timing tests simulating user interactions).
- Completion criteria: Reduced average CPU usage and acceptable tracking accuracy tradeoff shown in tests.

10. Optimize get_foreground_app fallbacks (psutil/toolhelp invocation frequency)
- Priority: P2 (Medium)
- Estimated difficulty: Hard
- Estimated time: 12–24 hours
- Files affected: `tracker/foreground.py`, `tracker/session.py`, `tracker/manager.py`
- Dependencies: Phase 3.1
- Risk level: Medium-High
- Testing checklist:
  - Unit tests for cached path scenarios, verify LRU cache behavior and eviction.
  - Stress test with rapid focus changes.
- Completion criteria: Reduced expensive calls; all tests pass and low CPU in stress runs.

11. MediaDetectionEngine graceful shutdown & resource cleanup
- Priority: P2 (Medium)
- Estimated difficulty: Medium
- Estimated time: 4–8 hours
- Files affected: `tracker/media.py`
- Dependencies: Phase 1.3
- Risk level: Low
- Testing checklist:
  - Start/stop media engine repeatedly and ensure asyncio loop, thread, and events are cleaned up.
- Completion criteria: No orphaned threads or event loops after repeated starts/stops.

---

Phase 4 — UI/UX (user-visible quality)

12. Tray-based non-modal SleepGuard cancel UI and accessible notifications
- Priority: P1 (High)
- Estimated difficulty: Medium
- Estimated time: 8–12 hours
- Files affected: `ui/main_window.py`, `ui/widgets/countdown_dialog.py`, `utils/notifier.py`, `tracker/sleepguard.py`
- Dependencies: Phase 1.4
- Risk level: Medium
- Testing checklist:
  - Verify when minimized, countdown appears in tray with cancel action.
  - Manual usability test for accept/cancel flows.
- Completion criteria: Users can cancel countdown from tray; modal dialog remains for visible windows.

13. Accessibility & contrast improvements
- Priority: P2 (Medium)
- Estimated difficulty: Easy
- Estimated time: 6–10 hours
- Files affected: `ui/*.py`, `ui/widgets/*.py`, `ui/pages/*.py`
- Dependencies: None
- Risk level: Low
- Testing checklist:
  - Keyboard navigation checks
  - Color contrast validation for dark/light themes
  - Screen-reader label checks for key widgets
- Completion criteria: Accessibility QA checklist complete and fixes merged.

14. Improve theme animation performance fallback
- Priority: P3 (Low)
- Estimated difficulty: Medium
- Estimated time: 4–8 hours
- Files affected: `ui/main_window.py`, `ui/theme.py`
- Dependencies: Phase 3.1
- Risk level: Low
- Testing checklist:
  - Slow GPU simulation (software rendering) to ensure animation gracefully degrades.
- Completion criteria: Theme change works without stutter on low-end devices.

---

Phase 5 — New Features (value-add for 2.1)

15. CI packaging and automated Inno Setup build + smoke tests
- Priority: P1 (High)
- Estimated difficulty: Hard
- Estimated time: 2–4 days
- Files affected: `.github/workflows/*` (new), `installer/*`, `package_release.py` (tweaks)
- Dependencies: All previous phases to ensure stable build
- Risk level: Medium
- Testing checklist:
  - CI workflow builds installer on Windows runner, signs if secrets available.
  - Smoke test: install silently, run app, verify single-instance, create sample sessions and snapshot.
- Completion criteria: Passing CI builds with signed/unsigned artifacts; documented release steps.

16. Add unit/integration tests for SleepGuard & tracking edge cases
- Priority: P2 (Medium)
- Estimated difficulty: Medium
- Estimated time: 2–3 days
- Files affected: `tests/` (new), `tracker/*.py`, `analytics/engine.py`
- Dependencies: Phase 1, Phase 2
- Risk level: Low
- Testing checklist:
  - Unit tests for SleepGuard flows (media playing/no media, force_trigger/cancel race)
  - Integration tests for DB snapshots and session lifecycle
- Completion criteria: Test coverage improved for critical modules; automated tests pass in CI.

17. Debugging/Observability features (thread & DB handle inspector)
- Priority: P3 (Low)
- Estimated difficulty: Medium
- Estimated time: 1–2 days
- Files affected: `utils/debug_lifecycle.py`, `ui/debug` pages
- Dependencies: None
- Risk level: Low
- Testing checklist:
  - Manual: open debug page and display thread list, QThread objects, DB handles.
- Completion criteria: Debug page shows runtime state; useful for triage.

18. Privacy & security review and optional DB encryption guidance
- Priority: P3 (Low)
- Estimated difficulty: Medium
- Estimated time: 1–2 days (audit + docs)
- Files affected: Documentation (`README.md`, `installer/README.md`), optionally `database/*` if encryption implemented
- Dependencies: Legal/PM review
- Risk level: Low
- Testing checklist:
  - Review code for potential data leakage.
  - Document privacy policy and storage location.
- Completion criteria: Audit done and docs updated; optional follow-up ticket for encryption.

---

Implementation notes & sequencing
- Phase 1 tasks must complete before packaging and wide roll-out.
- Phase 2 reliability tasks should follow immediately after Phase 1; some (DB checkpointing) can be implemented in parallel with thread hardening.
- Phase 3 optimizations may require instrumentation from Phase 2 to measure improvements.
- Phase 4 UI work depends on SleepGuard fixes from Phase 1.
- Phase 5 (CI, tests, observability) should be started in parallel with Phases 2–4 to reduce release friction.

Roadmap milestones (suggested timeline)
- Week 1: Phase 1 complete (critical fixes + test coverage for shutdown paths)
- Week 2: Phase 2 core reliability (DB maintenance, retry/backoff, background backfill)
- Week 3: Phase 3 performance tuning and media engine cleanup
- Week 4: Phase 4 UX polish and accessibility
- Week 5: Phase 5 CI & packaging, extended testing and release candidate

Delivery checklist before v2.1 release
- All Phase 1–2 items implemented and tested
- CI runs with unit + integration tests
- Installer built and smoke-tested on a clean Windows VM
- Documentation updated (CHANGELOG, installer instructions, privacy notes)
- Production readiness score >= 85 (re-run audit after fixes)

If this roadmap looks good, approve and the file will be committed to the workspace for tracking.