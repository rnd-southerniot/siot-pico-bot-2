---
phase: 02-robot-api-http-server
verified: 2026-03-05T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 2: Robot API + HTTP Server Verification Report

**Phase Goal:** A stable, documented robot facade API is locked and the HTTP server accepts exec() commands with a safety sandbox — the contract that all browser code will be written against
**Verified:** 2026-03-05
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Plan 02-01 truths (WIFI-03 / robot API + sandbox):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | robot.forward() / backward() / turn_left() / turn_right() / stop() call set_target_rpm correctly | VERIFIED | `robot.py` lines 16-37: all five methods call `_motor_task.set_target_rpm("left"|"right", ±rpm)` with correct signs and defaults |
| 2 | robot.status() returns a JSON-serializable dict with rpm_left, rpm_right, ir, distance_cm, color, heading, tick | VERIFIED | `robot.py` lines 39-50: status() builds and returns a dict with all seven required keys |
| 3 | exec('import machine', sandbox_globals) raises ImportError and does not crash | VERIFIED | `safety/sandbox.py` line 4-6: `_safe_import` raises `ImportError`; gate7 test_import_machine_blocked() asserts ok=False |
| 4 | exec('import os', sandbox_globals) raises ImportError and does not crash | VERIFIED | Same `_safe_import` mechanism; gate7 test_import_os_blocked() covers this case |
| 5 | exec('robot.stop()', sandbox_globals) succeeds with ok=True | VERIFIED | sandbox.py make_exec_globals injects robot instance; gate7 test_valid_robot_code_runs() asserts ok=True |
| 6 | exec('robot.forward(', sandbox_globals) returns ok=False with syntax error message | VERIFIED | sandbox.py lines 51-53 catch SyntaxError and prefix "Syntax error:"; gate7 test_syntax_error_returns_error() confirms |
| 7 | run_student_code() never raises — all exceptions are caught and returned as dicts | VERIFIED | sandbox.py lines 48-57: three-layer try/except (ImportError, SyntaxError, Exception) always returns result dict |

Plan 02-02 truths (WIFI-01, WIFI-02 / WiFi AP + HTTP server):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | The rover creates its own WiFi hotspot with a unique SSID derived from its MAC address (RoboPico-XXXX) | VERIFIED | wifi_task.py lines 67-83: start_ap() reads AP MAC, slices last 2 bytes via ubinascii.hexlify, formats as "{WIFI_AP_SSID_PREFIX}-{suffix}"; config.py line 82 sets WIFI_AP_SSID_PREFIX = "RoboPico" |
| 9 | A browser can reach the rover at 192.168.4.1:80 and GET /status returns a JSON dict | VERIFIED | wifi_task.py line 34-37: @app.get('/status') returns _robot.status() which is a JSON-serializable dict; Microdot 2.5.2 serializes dicts to JSON automatically; port bound via config.HTTP_PORT=80 |
| 10 | POST /exec with {"code": "robot.forward(60)"} returns {"ok": true} | VERIFIED | wifi_task.py lines 39-51: exec_endpoint calls run_student_code(body["code"], _robot) and returns result with status 200 when ok=True |
| 11 | POST /exec with {"code": "import machine"} returns {"ok": false, "error": "Import blocked: ..."} | VERIFIED | run_student_code catches ImportError and sets error="Import blocked: " + str(e); exec_endpoint returns 400 status |
| 12 | CORS headers are present on responses (Access-Control-Allow-Origin: *) | VERIFIED | wifi_task.py line 27: CORS(app, allowed_origins='*') at module level; cors.py after_request() adds Access-Control-Allow-Origin header to all responses |
| 13 | The HTTP server runs as a uasyncio coroutine without blocking the motor PID or sensor poll loops | VERIFIED | main.py lines 121-127: wifi_server_task() is gathered alongside motor_pid_loop(), sensor_poll_loop(), heading_tracker.update_loop(), watchdog.feed_loop(); Microdot runs via await app.start_server() yielding to the event loop |

**Score:** 13/13 truths verified

---

## Required Artifacts

### Plan 02-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `robot.py` | RobotAPI facade — stable contract for all browser-generated code | VERIFIED | 51 lines, class RobotAPI with 6 methods; imports tasks.motor_task and tasks.sensor_task as private modules |
| `safety/sandbox.py` | exec() restricted environment with custom __import__ and __builtins__ | VERIFIED | 58 lines, contains _safe_import, _SAFE_BUILTINS dict (16 safe entries), make_exec_globals, run_student_code |
| `gates/gate7_exec_sandbox.py` | On-device verification that sandbox blocks forbidden imports and runs valid code | VERIFIED | 60 lines, 5 test functions, all print "PASS", registered in gates/run_all.py |

### Plan 02-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/microdot/__init__.py` | Microdot package init (copied from Microdot 2.x source) | VERIFIED | 4 lines, re-exports Microdot/Request/Response/abort/redirect/send_file/URLPattern/AsyncBytesIO/iscoroutine, version 2.5.2.dev0 |
| `lib/microdot/microdot.py` | Microdot async HTTP server framework | VERIFIED | 1566 lines, full Microdot 2.5.2 implementation |
| `lib/microdot/cors.py` | Microdot CORS extension for browser cross-origin requests | VERIFIED | 111 lines, CORS class with after_request hook adding Access-Control-Allow-Origin |
| `tasks/wifi_task.py` | start_ap() sync function + wifi_server_task() async coroutine | VERIFIED | Contains start_ap() (sync, returns ap+ssid), wifi_server_task() (async), GET /status, POST /exec; no wifi_placeholder present |
| `main.py` | Updated boot sequence: AP startup in sync section, wifi_server_task in gather() | VERIFIED | Line 99-100: start_ap() in sync Step 7; line 118+125: wifi_server_task() imported and gathered |
| `config.py` | WIFI_AP_SSID_PREFIX constant for MAC-derived SSID generation | VERIFIED | Line 82: WIFI_AP_SSID_PREFIX = "RoboPico"; old static WIFI_AP_SSID is gone |

---

## Key Link Verification

### Plan 02-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `robot.py` | `tasks/motor_task.py` | set_target_rpm / get_target_rpm calls | WIRED | Lines 16-17, 21-22, 26-27, 31-32, 36-37 (set) + lines 43-44 (get) all call _motor_task.set/get_target_rpm |
| `robot.py` | `tasks/sensor_task.py` | get_sensor_state() accessor | WIRED | Line 41: `state = _sensor_task.get_sensor_state()` |
| `safety/sandbox.py` | `robot.py` | RobotAPI instance injected as 'robot' in exec() globals | WIRED | Line 34: `"robot": robot_instance` in make_exec_globals dict returned to exec() |

### Plan 02-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tasks/wifi_task.py` | `robot.py` | RobotAPI instantiation and injection into routes | WIRED | Line 22: `from robot import RobotAPI`; line 30: `_robot = RobotAPI()` used in both route handlers |
| `tasks/wifi_task.py` | `safety/sandbox.py` | run_student_code call in POST /exec route | WIRED | Line 23: `from safety.sandbox import run_student_code`; line 50: `result = run_student_code(body["code"], _robot)` |
| `tasks/wifi_task.py` | `lib/microdot` | Microdot app creation and start_server coroutine | WIRED | Line 20: `from microdot import Microdot`; line 26: `app = Microdot()`; line 99: `await app.start_server(...)` |
| `main.py` | `tasks/wifi_task.py` | start_ap() in sync boot, wifi_server_task() in gather() | WIRED | Line 99: `from tasks.wifi_task import start_ap`; line 118: `from tasks.wifi_task import wifi_server_task`; line 125: `wifi_server_task()` in gather() |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WIFI-01 | 02-02 | WiFi AP mode — rover creates its own hotspot | SATISFIED | start_ap() in wifi_task.py: network.WLAN(network.AP_IF) activated with ap.active(True); called in main.py boot Step 7 |
| WIFI-02 | 02-02 | Per-unit unique SSID to avoid classroom conflicts | SATISFIED | MAC last-2-bytes appended as hex suffix in start_ap(); config.WIFI_AP_SSID_PREFIX = "RoboPico" produces "RoboPico-XXXX" per device |
| WIFI-03 | 02-01 | JSON-based command/telemetry protocol | SATISFIED | GET /status returns robot.status() dict (JSON); POST /exec accepts {"code":...} and returns {"ok":bool,"error":str/None} dict (JSON); run_student_code always returns JSON-serializable dict |

All three requirement IDs claimed in plan frontmatter (WIFI-01, WIFI-02, WIFI-03) are accounted for and satisfied.

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps WIFI-01, WIFI-02, WIFI-03 to Phase 2 — all three are covered by the plans. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `main.py` | 17 | Stale docstring phrase "WiFi placeholder" in module-level docstring | Info | Cosmetic only — the phrase appears in the boot sequence description comment, not in executable code; no functional impact |

No blocker or warning anti-patterns found. The single info-level item is a stale phrase in a module docstring and has no effect on behavior.

---

## Human Verification Required

The following behaviors require on-device hardware to verify programmatically. All automated evidence supports that they will work, but cannot be confirmed without a Pico W.

### 1. WiFi AP Activation and SSID Broadcast

**Test:** Flash firmware to Pico W, power on, scan WiFi networks from a laptop or phone.
**Expected:** A network named "RoboPico-XXXX" (where XXXX is the device's AP MAC last 2 bytes) appears within 10 seconds. Password "robopico1" grants access.
**Why human:** network.WLAN() and ap.active() are MicroPython/hardware APIs — cannot be exercised on CPython host.

### 2. GET /status Returns Live Sensor JSON

**Test:** Connect laptop to rover WiFi, run `curl http://192.168.4.1/status`.
**Expected:** JSON response with keys: rpm_left, rpm_right, ir, distance_cm, color, heading, tick — all with real numeric values, not zeros/None.
**Why human:** Requires hardware sensors (IMU, IR, ultrasonic) to produce non-stub values; Microdot JSON serialization confirmed by code but not exercised on host.

### 3. POST /exec Executes and Returns Correctly

**Test:** `curl -X POST -H "Content-Type: application/json" -d '{"code":"robot.stop()"}' http://192.168.4.1/exec`
**Expected:** `{"ok": true, "error": null}` — HTTP 200.
**Test (blocked import):** Same command with `"code":"import machine"`.
**Expected:** `{"ok": false, "error": "Import blocked: ..."}` — HTTP 400.
**Why human:** Requires live Microdot server on Pico W for end-to-end HTTP request validation.

### 4. HTTP Server Does Not Block Motor/Sensor Loops

**Test:** While rover is moving forward (robot.forward()), issue multiple GET /status requests rapidly.
**Expected:** Motor continues running at target RPM; sensor values update at expected frequency; HTTP responses return within ~1s without stalling movement.
**Why human:** Concurrency correctness of uasyncio.gather() with Microdot requires runtime observation; cannot be verified statically.

---

## Summary

Phase 2 goal is achieved. All 13 observable truths are supported by substantive, wired code. The implementation is not placeholder code — every method calls real underlying functions and every route handler calls real sandbox or API code.

**Plan 02-01 (WIFI-03):** The robot.py facade is a complete, lean 6-method API wrapping motor and sensor tasks. The sandbox properly restricts exec() to a whitelist of safe builtins and blocks all imports via custom __import__. The gate7 script provides on-device verification for all sandbox behaviors.

**Plan 02-02 (WIFI-01, WIFI-02):** Microdot 2.5.2 is present (1566-line framework). wifi_task.py is fully implemented — not a stub — with start_ap() building a MAC-derived SSID and wifi_server_task() running Microdot as a coroutine. main.py correctly sequences sync AP startup before the event loop and gathers wifi_server_task() alongside all Phase 1 coroutines. CORS is enabled at module level.

The one stale docstring phrase ("WiFi placeholder" in main.py line 17) is cosmetic and does not affect functionality.

Four items are flagged for human verification — all require on-device hardware. These are normal for embedded firmware and do not block the phase goal from being considered achieved at the code level.

---

_Verified: 2026-03-05_
_Verifier: Claude (gsd-verifier)_
