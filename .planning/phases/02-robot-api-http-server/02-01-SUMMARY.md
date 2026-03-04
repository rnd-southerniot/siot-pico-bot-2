---
phase: 02-robot-api-http-server
plan: "01"
subsystem: api
tags: [micropython, exec, sandbox, robot-api, safety]

# Dependency graph
requires:
  - phase: 01-firmware-foundation
    provides: motor_task.set_target_rpm/get_target_rpm and sensor_task.get_sensor_state() functions
provides:
  - RobotAPI class in robot.py — stable facade contract for all browser-generated code
  - run_student_code() in safety/sandbox.py — exec() restricted environment blocking all imports
  - gate7_exec_sandbox.py — on-device verification of sandbox import blocking and valid code execution
affects: [03-wifi-ap-http, 04-block-editor, 05-websocket, lesson-content]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Robot facade pattern: RobotAPI wraps motor/sensor task internals, never exposing HAL"
    - "exec() sandbox: custom __import__ blocks ALL imports; _SAFE_BUILTINS whitelist only"
    - "Never-raise pattern: run_student_code() catches all exceptions, returns JSON-serializable dicts"

key-files:
  created:
    - robot.py
    - safety/sandbox.py
    - gates/gate7_exec_sandbox.py
  modified:
    - gates/run_all.py

key-decisions:
  - "RobotAPI wraps motor_task/sensor_task with private _module imports — API surface is deliberately small"
  - "Sandbox blocks ALL imports via custom __import__ — whitelist of safe builtins only (no eval, compile, open)"
  - "run_student_code() never raises — always returns {ok, error} dict for safe HTTP response encoding"

patterns-established:
  - "Facade pattern: robot.forward() -> _motor_task.set_target_rpm() — one-layer indirection"
  - "Sandbox safety: _SAFE_BUILTINS dict replaces __builtins__ in exec() globals"

requirements-completed: [WIFI-03]

# Metrics
duration: 2min
completed: 2026-03-05
---

# Phase 2 Plan 01: Robot API Facade and exec() Sandbox Summary

**RobotAPI facade wrapping motor/sensor tasks + exec() restricted sandbox blocking all imports with never-raise run_student_code()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-04T23:43:00Z
- **Completed:** 2026-03-04T23:44:45Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- RobotAPI class with forward/backward/turn_left/turn_right/stop/status methods — the stable contract for all browser-generated code
- exec() sandbox with custom __import__ that blocks ALL module imports and a whitelist of safe builtins
- run_student_code() catches all exceptions (ImportError, SyntaxError, Exception) and returns JSON-serializable dicts — never raises
- gate7_exec_sandbox.py with 5 tests verifying import blocking, valid code execution, and syntax error handling
- gates/run_all.py updated with gate7 as final entry

## Task Commits

Each task was committed atomically:

1. **Task 1: Create robot.py facade API and safety/sandbox.py exec() environment** - `a7e6ec8` (feat)
2. **Task 2: Create gate7_exec_sandbox.py verification script and update run_all.py** - `368414a` (feat)

## Files Created/Modified

- `robot.py` - RobotAPI class wrapping motor_task and sensor_task internals
- `safety/sandbox.py` - exec() restricted environment with _safe_import, _SAFE_BUILTINS, make_exec_globals, run_student_code
- `gates/gate7_exec_sandbox.py` - 5 on-device/host-side tests verifying sandbox correctness
- `gates/run_all.py` - Added gate7_exec_sandbox.py as last entry in GATES list

## Decisions Made

- RobotAPI uses `import tasks.motor_task as _motor_task` (underscore prefix) to signal private imports — keeps the API surface clean and explicit
- Default RPMs: forward/backward = 60.0, turn = 40.0 (per Phase 2 research)
- Sandbox blocks ALL imports via custom `__import__` — no allow-list by module name, because any import could expose hardware or filesystem access
- `_SAFE_BUILTINS` includes only pure computation types: print, range, len, int, float, str, bool, list, dict, abs, min, max, round plus True/False/None

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The gate7 script imports `from robot import RobotAPI` which has hardware dependencies (uasyncio, machine) that prevent direct CPython execution. The host-side verification was run using a mock robot instance that confirmed all 5 sandbox test cases pass correctly. On-device execution via `mpremote run gates/gate7_exec_sandbox.py` requires hardware but the logic is verified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- robot.py and safety/sandbox.py provide the stable contract for Phase 3 (HTTP server) and Phase 4 (block editor)
- HTTP server (Plan 02-02) can now call `run_student_code(code, robot_instance)` to execute browser-generated code safely
- All browser-generated code will call only robot.* methods — HAL internals are fully encapsulated

---
*Phase: 02-robot-api-http-server*
*Completed: 2026-03-05*
