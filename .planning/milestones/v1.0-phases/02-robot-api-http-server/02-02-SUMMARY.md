---
phase: 02-robot-api-http-server
plan: "02"
subsystem: api
tags: [microdot, wifi, http, cors, micropython, asyncio, pico-w]

# Dependency graph
requires:
  - phase: 02-01
    provides: "RobotAPI facade and run_student_code() exec sandbox"
  - phase: 01-firmware-foundation
    provides: "uasyncio gather() architecture, motor_task, sensor_task, watchdog"
provides:
  - "Microdot 2.5.2 async HTTP server library in lib/microdot/"
  - "WiFi AP with MAC-derived unique SSID (RoboPico-XXXX) via start_ap()"
  - "GET /status endpoint returning robot state JSON"
  - "POST /exec endpoint executing student code through sandbox"
  - "CORS enabled for all browser cross-origin requests"
  - "wifi_server_task() coroutine running concurrently with motor/sensor loops"
affects: [03-block-editor-ui, 04-block-definitions, phase-3-onwards]

# Tech tracking
tech-stack:
  added: [microdot-2.5.2, micropython-network, ubinascii]
  patterns:
    - "sync-before-async: blocking hardware init (AP startup) done in sync boot section before event loop"
    - "exception-isolation: wifi_server_task wraps body in try/except to prevent gather() cascade failure"
    - "singleton-at-module-level: RobotAPI instantiated once as _robot at module load"

key-files:
  created:
    - lib/microdot/__init__.py
    - lib/microdot/microdot.py
    - lib/microdot/cors.py
    - tasks/wifi_task.py (rewritten)
  modified:
    - main.py
    - config.py

key-decisions:
  - "start_ap() is sync — AP activation blocks for 1-2s, must NOT be inside event loop"
  - "CORS(app, allowed_origins='*') initialized at module level — browser blocking prevention baked in from day one"
  - "Route handler named exec_endpoint (not exec) — avoids shadowing Python builtin"
  - "WIFI_AP_SSID_PREFIX in config.py replaces static SSID — MAC suffix makes each rover uniquely identifiable"
  - "wifi_server_task() catches all exceptions and logs without re-raising — prevents gather() cascade cancelling motor/sensor tasks"

patterns-established:
  - "Sync-before-async for hardware init: blocking startup code goes in main.py sync section before uasyncio.run()"
  - "Route isolation: each HTTP endpoint is a thin wrapper delegating to RobotAPI or sandbox"
  - "MAC-derived naming: last 2 bytes of AP MAC in hex appended to prefix for unique device IDs"

requirements-completed: [WIFI-01, WIFI-02]

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 02 Plan 02: WiFi AP + Microdot HTTP Server Summary

**Microdot 2.5.2 async HTTP server wired into uasyncio gather() with MAC-derived WiFi AP SSID, GET /status and POST /exec routes, and CORS enabled for browser access**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-04T23:47:35Z
- **Completed:** 2026-03-04T23:50:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Microdot 2.5.2 library (3 files) downloaded from GitHub and placed in lib/microdot/
- tasks/wifi_task.py fully rewritten: start_ap() creates WiFi hotspot with RoboPico-XXXX SSID derived from AP MAC address; wifi_server_task() runs Microdot on port 80
- GET /status and POST /exec routes wired to RobotAPI.status() and run_student_code() sandbox
- main.py updated: AP started synchronously in Step 7 before event loop, wifi_server_task() replaces old placeholder in gather()
- config.py updated: WIFI_AP_SSID_PREFIX replaces static WIFI_AP_SSID constant

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy Microdot library and rewrite wifi_task.py** - `5e757ee` (feat)
2. **Task 2: Update main.py boot sequence and config.py** - `0b9e3f5` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `lib/microdot/__init__.py` - Microdot package init, re-exports Microdot, Request, Response
- `lib/microdot/microdot.py` - Microdot async HTTP server framework (59KB, full implementation)
- `lib/microdot/cors.py` - CORS extension for cross-origin browser requests
- `tasks/wifi_task.py` - Rewritten: start_ap() + wifi_server_task() + GET /status + POST /exec
- `main.py` - Step 7 sync AP startup added; gather() updated to use wifi_server_task()
- `config.py` - WIFI_AP_SSID replaced with WIFI_AP_SSID_PREFIX = "RoboPico"

## Decisions Made
- start_ap() is synchronous (called before event loop) — AP activation requires blocking wait up to 10s; doing this inside the event loop would starve all coroutines
- Route named exec_endpoint (not exec) to avoid shadowing Python's built-in exec() function
- CORS initialized at module level with allowed_origins='*' — Phase 3 browser UI needs this from day one, no retroactive patching
- WIFI_AP_SSID_PREFIX gives each rover a unique SSID without manual configuration — critical for classroom deployments with multiple rovers
- wifi_server_task() swallows exceptions and logs them — prevents a Microdot crash from cascade-cancelling motor/sensor/watchdog tasks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed "wifi_placeholder" string from wifi_task.py docstring**
- **Found during:** Task 1 (verification)
- **Issue:** Plan verification script checks `'wifi_placeholder' not in content` — the module docstring contained the phrase as historical reference, causing assertion failure
- **Fix:** Rewrote the docstring line from "Phase 2 replacement for the wifi_placeholder() coroutine" to "Phase 2: replaces the placeholder coroutine with a real HTTP server"
- **Files modified:** tasks/wifi_task.py
- **Verification:** Verification script passed after change
- **Committed in:** 5e757ee (Task 1 commit)

**2. [Rule 1 - Bug] Removed "wifi_placeholder" string from main.py inline comment**
- **Found during:** Task 2 (verification)
- **Issue:** Plan verification script checks main.py for absence of "wifi_placeholder" — the inline comment `# replaces wifi_placeholder()` triggered assertion failure
- **Fix:** Changed comment to `# HTTP server — AP started in Step 7 above`
- **Files modified:** main.py
- **Verification:** Verification script passed after change
- **Committed in:** 0b9e3f5 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (Rule 1 - comment string matching verification checks)
**Impact on plan:** Minor comment wording changes only. No behavioral impact.

## Issues Encountered
None — Microdot files downloaded cleanly from GitHub, verification checks passed after minor comment adjustments.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rover now creates its own WiFi hotspot (RoboPico-XXXX) on boot
- HTTP API on port 80 ready for browser connections at 192.168.4.1
- GET /status returns live sensor state JSON
- POST /exec runs student code through the safety sandbox
- Phase 3 (Block Editor UI) can connect to this API immediately
- On-device validation via mpremote is the next manual step (outside automated testing scope)

---
*Phase: 02-robot-api-http-server*
*Completed: 2026-03-05*

## Self-Check: PASSED

- FOUND: lib/microdot/__init__.py
- FOUND: lib/microdot/microdot.py
- FOUND: lib/microdot/cors.py
- FOUND: tasks/wifi_task.py
- FOUND: main.py
- FOUND: config.py
- FOUND: .planning/phases/02-robot-api-http-server/02-02-SUMMARY.md
- FOUND commit: 5e757ee (Task 1 — Microdot library + wifi_task.py rewrite)
- FOUND commit: 0b9e3f5 (Task 2 — main.py boot sequence + config.py SSID prefix)
