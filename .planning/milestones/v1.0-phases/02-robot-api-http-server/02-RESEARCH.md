# Phase 2: Robot API + HTTP Server - Research

**Researched:** 2026-03-04
**Domain:** MicroPython WiFi AP mode, async HTTP server (Microdot), robot facade API design, exec() sandbox on Pico W
**Confidence:** HIGH (codebase is primary source; official MicroPython docs and verified Microdot docs back claims)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIFI-01 | WiFi AP mode — rover creates its own hotspot | `network.WLAN(network.AP_IF)` + `ap.config(ssid=..., password=...)` + `ap.active(True)` — confirmed in MicroPython official docs; v1 gate8 is a working proof-of-concept on this exact hardware |
| WIFI-02 | Per-unit unique SSID to avoid classroom conflicts | `ap.config('mac')` returns 6 bytes; `ubinascii.hexlify(mac[-2:]).decode()` yields last-4-hex suffix; pattern "RoboPico-XXXX" is unique per unit |
| WIFI-03 | JSON-based command/telemetry protocol | `POST /exec` with JSON body + `GET /status` JSON response; Microdot's `request.json` / dict return auto-serializes; robot.py facade provides the API surface |
</phase_requirements>

---

## Summary

Phase 2 has three separable technical concerns that must be built in the right order: (1) the robot.py facade API locks the contract between firmware and the browser before any browser code is written, (2) the WiFi AP starts and hands out a fixed IP (192.168.4.1) with a unique SSID derived from the unit's MAC address, and (3) an async HTTP server — Microdot is the correct choice — accepts POST /exec and GET /status requests within the existing uasyncio event loop.

The v1 codebase already has a complete, working AP + HTTP server proof-of-concept in `gates/gate8_wifi_telemetry.py`. It uses raw sockets in a blocking loop, which is incompatible with the Phase 1 async architecture. Phase 2 replaces that blocking pattern with Microdot running as a `create_task()` inside the existing `uasyncio.gather()`. The integration point in `tasks/wifi_task.py` is already stubbed and documented for exactly this replacement.

The exec() sandbox is the most novel concern. MicroPython's `exec()` accepts a `globals` dict; passing a restricted dict with a custom `__import__` that blocks dangerous modules (machine, os, rp2, etc.) prevents students from directly accessing hardware. This is not a perfect security sandbox — it is an appropriate level of protection for the stated threat model (a K-8 student accidentally or mischievously typing `import machine` into a block-generated string). Full sandbox escape via `__subclasses__()` tricks is out of scope for this audience. The watchdog (already built in Phase 1) handles the deeper threat: runaway code that blocks the event loop.

**Primary recommendation:** Build robot.py first to lock the API contract, then wire Microdot with AP startup, then implement and test the exec() sandbox. All three tasks fit cleanly as independent plans.

---

## Standard Stack

### Core (MicroPython built-ins — no installation needed)

| Library | Module | Purpose | Why Standard |
|---------|--------|---------|--------------|
| network | `import network` | WiFi AP mode | Built into MicroPython for Pico W; the only AP option |
| ubinascii | `import ubinascii` | MAC bytes → hex string | Built-in; needed for unique SSID generation |
| json | `import json` | Serialize/deserialize request/response | Built-in; `json.dumps()` / `json.loads()` work on Pico W |
| uasyncio | `import uasyncio` | Async event loop (already running from Phase 1) | Built-in; Microdot uses it |
| socket | (indirect via Microdot) | TCP socket binding | Built-in; Microdot wraps it |

### Third-Party (must be copied to Pico W)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Microdot | 2.5.1 (Dec 2025) | Async HTTP server framework | The only production-quality async HTTP framework for MicroPython; Flask-like API; `start_server()` integrates directly into an existing `uasyncio` event loop as a `create_task()` |

### Microdot Installation

Copy a single file from the Microdot GitHub repo:
```
https://github.com/miguelgrinberg/microdot/blob/main/src/microdot/microdot.py
```

Copy it to the Pico W as `lib/microdot.py` (or `microdot.py` at root). No package structure required for the base server. The `microdot.cors` extension requires the full package structure — research indicates a `microdot/` directory with `__init__.py` and extension files is needed for CORS. CORS will be needed because the React app (Phase 3+) runs in a browser on a different origin.

CORS copy target:
- `lib/microdot/__init__.py` (copy from `src/microdot/__init__.py`)
- `lib/microdot/microdot.py` (copy from `src/microdot/microdot.py`)
- `lib/microdot/cors.py` (copy from `src/microdot/cors.py`)

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Microdot | Raw `asyncio.start_server` + custom HTTP parser | Raw sockets require writing HTTP header parsing, content-length handling, keep-alive, and error responses from scratch. Gate 8's blocking server is ~100 lines and lacks keep-alive. Microdot handles all of this correctly; no reason to hand-roll. |
| Microdot | picoweb | picoweb is unmaintained and not async-compatible with MicroPython ≥1.20 |
| POST /exec with JSON body | URL-encoded form POST | JSON body is cleaner for structured code strings; Microdot's `request.json` parses it automatically |
| Custom exec() globals filtering | Full RestrictedPython | RestrictedPython is CPython only; not available on MicroPython. The custom `__import__` denylist approach is the only viable option on Pico W. |

---

## Architecture Patterns

### Recommended File Structure (Phase 2 additions)

```
/                          # Pico W root
├── main.py                # MODIFIED: replace wifi_placeholder with wifi_server_task
├── config.py              # MODIFIED: add WIFI_AP_SSID_PREFIX, exec() denylist
├── robot.py               # NEW: facade API — the stable contract for all browser code
├── tasks/
│   └── wifi_task.py       # REPLACED: wifi_placeholder → wifi_server_task (Microdot)
├── safety/
│   ├── watchdog.py        # Unchanged (Phase 1)
│   └── sandbox.py         # NEW: exec() restricted environment
└── lib/
    └── microdot.py        # NEW: Microdot 2.5.1 (single-file copy)
    OR
    └── microdot/          # NEW: Microdot package (for CORS support)
        ├── __init__.py
        ├── microdot.py
        └── cors.py
```

### Pattern 1: WiFi AP Startup with Unique SSID

**What:** AP mode started once at boot; SSID is "RoboPico-XXXX" where XXXX is the last 2 bytes of the MAC in hex. Fixed IP 192.168.4.1 is the Pico W AP default and does not need to be set manually.

**Why unique SSID matters:** Classroom has 30 rovers. Without unique SSIDs every rover broadcasts "RoboPico-Lab" and students cannot distinguish them. MAC suffix is unique per unit, stable across reboots, and requires no manual configuration.

**Confirmed API from MicroPython official docs (HIGH confidence):**

```python
# tasks/wifi_task.py — AP startup pattern
import network
import ubinascii

def start_ap():
    """Start WiFi AP with unique SSID derived from MAC address."""
    ap = network.WLAN(network.AP_IF)
    # Get MAC from the AP interface (6 bytes)
    mac = ap.config('mac')
    # Take last 2 bytes → 4 hex chars → unique suffix
    suffix = ubinascii.hexlify(mac[-2:]).decode().upper()
    ssid = "RoboPico-{}".format(suffix)

    ap.config(ssid=ssid, password=config.WIFI_AP_PASSWORD)
    ap.active(True)

    # Wait for AP to activate (Pico W can take up to 2s)
    import utime
    deadline = utime.ticks_add(utime.ticks_ms(), 10000)
    while not ap.active():
        if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
            raise RuntimeError("AP failed to activate")
        utime.sleep_ms(100)

    ip = ap.ifconfig()[0]   # Should be 192.168.4.1
    print("AP active: SSID={} IP={}".format(ssid, ip))
    return ap, ssid
```

**IMPORTANT — RP2040-specific gotcha (MEDIUM confidence, from community):**
- `ap.config(ssid=..., password=...)` MUST be called BEFORE `ap.active(True)`
- Setting config after activation may silently fail on RP2040 — differs from ESP32 behavior

### Pattern 2: Microdot HTTP Server as uasyncio Task

**What:** Microdot's `start_server()` is a coroutine that runs indefinitely. It is added to the existing `uasyncio.gather()` as a `create_task()` so it shares the event loop with the motor PID and sensor tasks.

**Confirmed from Microdot 2.5.1 official docs (HIGH confidence):**

```python
# tasks/wifi_task.py — Microdot integration
import uasyncio
from microdot import Microdot
import json

app = Microdot()

async def wifi_server_task():
    """Replace wifi_placeholder: starts AP then runs Microdot HTTP server."""
    ap, ssid = start_ap()

    # Microdot start_server is a coroutine — await it directly
    # It loops forever until shutdown() is called
    await app.start_server(host='0.0.0.0', port=80, debug=False)
```

In `main.py`, the change is:
```python
# OLD (Phase 1):
from tasks.wifi_task import wifi_placeholder
# ...
await uasyncio.gather(
    motor_pid_loop(),
    sensor_poll_loop(),
    heading_tracker.update_loop(),
    wifi_placeholder(),      # <-- replace this
    watchdog.feed_loop(),
)

# NEW (Phase 2):
from tasks.wifi_task import wifi_server_task
# ...
await uasyncio.gather(
    motor_pid_loop(),
    sensor_poll_loop(),
    heading_tracker.update_loop(),
    wifi_server_task(),      # <-- runs Microdot + AP
    watchdog.feed_loop(),
)
```

Alternatively (per Microdot docs), use `create_task` to keep `wifi_server_task` from blocking `gather`:
```python
uasyncio.create_task(app.start_server(host='0.0.0.0', port=80))
```
Both patterns work. The `create_task` approach is preferred when other coroutines must also `await` inside `wifi_server_task`.

### Pattern 3: robot.py Facade API

**What:** A single module that exposes clean, documented methods the browser sends via POST /exec. This is the stable contract — once locked, Phase 3, 4, and beyond can write to it without looking at HAL internals.

**Why a facade:** The exec() sandbox (Pattern 4) executes student code with a restricted globals dict that contains only `robot` and a safe subset of builtins. The facade is what makes `robot.forward(100)` work from student code without exposing `motor_task.set_target_rpm` or `hal.motors.MotorHAL`.

**Reads from Phase 1 internals:**
- `tasks.motor_task.set_target_rpm(side, rpm)`
- `tasks.motor_task.get_target_rpm(side)`
- `tasks.sensor_task.get_sensor_state()`

```python
# robot.py — facade API (robot-as-object pattern)
import tasks.motor_task as _motor_task
import tasks.sensor_task as _sensor_task
import uasyncio

class RobotAPI:
    """
    Stable robot facade API.

    This is the contract between firmware and all browser-generated code.
    All public methods here are the complete API surface for exec() commands.
    Never expose HAL or task internals below this layer.

    Instantiated once as robot = RobotAPI() in wifi_task.py.
    """

    def forward(self, rpm: float = 60.0):
        """Drive both wheels forward at rpm."""
        _motor_task.set_target_rpm("left",  rpm)
        _motor_task.set_target_rpm("right", rpm)

    def backward(self, rpm: float = 60.0):
        """Drive both wheels backward at rpm."""
        _motor_task.set_target_rpm("left",  -rpm)
        _motor_task.set_target_rpm("right", -rpm)

    def turn_left(self, rpm: float = 40.0):
        """Pivot left: right wheel forward, left wheel backward."""
        _motor_task.set_target_rpm("left",  -rpm)
        _motor_task.set_target_rpm("right",  rpm)

    def turn_right(self, rpm: float = 40.0):
        """Pivot right: left wheel forward, right wheel backward."""
        _motor_task.set_target_rpm("left",   rpm)
        _motor_task.set_target_rpm("right", -rpm)

    def stop(self):
        """Stop both wheels."""
        _motor_task.set_target_rpm("left",  0.0)
        _motor_task.set_target_rpm("right", 0.0)

    def status(self) -> dict:
        """Return current robot state as JSON-serializable dict."""
        state = _sensor_task.get_sensor_state()
        return {
            "rpm_left":    _motor_task.get_target_rpm("left"),
            "rpm_right":   _motor_task.get_target_rpm("right"),
            "ir":          state["ir"],
            "distance_cm": state["distance_cm"],
            "color":       state["color"],
            "heading":     state["heading"],
            "tick":        state["tick"],
        }
```

**API surface is deliberately small.** Add methods only when a lesson requires them. Scope creep on the facade is a documented failure mode (STATE.md Phase 4 flag).

### Pattern 4: exec() Safety Sandbox

**What:** `exec(code, globals_dict)` in MicroPython accepts a custom globals dict. By providing a restricted dict with a custom `__import__` that raises `ImportError` for any module not on the allowlist, student code cannot access hardware directly.

**Threat model (K-8 classroom):** A student (or a curiosity-motivated kid) types `import machine` into a block. The rover should respond with an error, not crash, not reset, and not do something unexpected with hardware. This is not a malicious-attacker sandbox — it is a guardrail for children using a block editor.

**MicroPython behavior (verified from official docs):** `exec(code, globals_dict)` respects the `__builtins__` key in the globals dict. If `__builtins__` is a custom dict, only those builtins are available.

```python
# safety/sandbox.py

# Modules the exec sandbox explicitly ALLOWS (robot.py API only)
_EXEC_ALLOWLIST = frozenset()  # No direct imports allowed in exec code

def _safe_import(name, *args, **kwargs):
    """
    Custom __import__ for exec() sandbox.
    Blocks ALL module imports in student code — robot.py methods are pre-injected
    into globals so no import is needed.
    """
    raise ImportError("import is not allowed in robot programs. Use robot.forward() etc.")

# Restricted builtins: only safe data types and operations
_SAFE_BUILTINS = {
    "print":     print,
    "range":     range,
    "len":       len,
    "int":       int,
    "float":     float,
    "str":       str,
    "bool":      bool,
    "list":      list,
    "dict":      dict,
    "abs":       abs,
    "min":       min,
    "max":       max,
    "round":     round,
    "True":      True,
    "False":     False,
    "None":      None,
    "__import__": _safe_import,   # Blocks all imports including "machine"
}

def make_exec_globals(robot_instance) -> dict:
    """
    Return a restricted globals dict for exec().

    Contains:
    - 'robot': the RobotAPI instance — all student code calls robot.forward() etc.
    - '__builtins__': minimal safe set — no open(), eval(), __import__
    """
    return {
        "__builtins__": _SAFE_BUILTINS,
        "robot":        robot_instance,
    }

def run_student_code(code: str, robot_instance) -> dict:
    """
    Execute student code string in restricted sandbox.

    Returns {'ok': True} or {'ok': False, 'error': 'message'}.
    Never raises — all exceptions are caught and returned as JSON-serializable dicts.
    """
    result = {"ok": True, "error": None}
    try:
        globs = make_exec_globals(robot_instance)
        exec(code, globs)
    except ImportError as e:
        result["ok"] = False
        result["error"] = "Import blocked: " + str(e)
    except SyntaxError as e:
        result["ok"] = False
        result["error"] = "Syntax error: " + str(e)
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)
    return result
```

**Key property:** `import machine` inside the exec'd code calls `_safe_import("machine")`, which raises `ImportError`. The rover does not crash. The error is caught, serialized, and returned in the HTTP response. The WDT feed_loop keeps running because the exec() exception is caught before it can propagate to gather().

### Pattern 5: HTTP Routes

**What:** Two routes for Phase 2. GET /status returns JSON telemetry. POST /exec executes robot code.

```python
# In wifi_task.py, after app = Microdot()

import json as _json
from safety.sandbox import run_student_code

_robot = RobotAPI()  # module-level singleton

@app.get('/status')
async def status(request):
    """Return current robot state as JSON."""
    return _robot.status()   # Microdot auto-serializes dicts as JSON

@app.post('/exec')
async def exec_code(request):
    """
    Execute a robot program.

    Request body: {"code": "robot.forward(60)\n..."}
    Response: {"ok": true} or {"ok": false, "error": "message"}
    """
    body = request.json
    if not body or "code" not in body:
        return {"ok": False, "error": "Missing 'code' field"}, 400

    code = body["code"]
    result = run_student_code(code, _robot)
    status_code = 200 if result["ok"] else 400
    return result, status_code

# CORS: allow all origins for dev (browser on any origin can call rover)
from microdot.cors import CORS
CORS(app, allowed_origins='*')
```

### Anti-Patterns to Avoid

- **`ap.config()` after `ap.active(True)`:** On RP2040, config changes after activation may not take effect. Always configure BEFORE activating.
- **Blocking WiFi wait loop:** `while not ap.active(): time.sleep(0.1)` blocks the event loop if called inside an async coroutine. Use `await uasyncio.sleep_ms(100)` inside the loop, or call `start_ap()` before the event loop starts (sync function called in main.py's sync boot section).
- **exec() without explicit globals:** `exec(code)` runs in the current module's globals — student code would have access to `motor_task`, `hal`, everything. Always pass the restricted globals dict.
- **Returning raw exception tracebacks to the browser:** Pico W tracebacks include file paths and line numbers. Return only the exception message string (not the traceback) in the HTTP response — Phase 4 will localize these into kid-readable messages.
- **Importing Microdot at module top-level before the file is copied:** If `microdot.py` is not present, the import fails at boot and the entire firmware crashes. Guard with a try/except or ensure the file is copied first.
- **CORS omission:** Without CORS headers, Chrome/Firefox will reject responses to POST /exec from the React app. Add CORS with `allowed_origins='*'` during development; tighten if needed in production.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP server | Custom `asyncio.start_server` + HTTP parser | Microdot 2.5.1 | HTTP parsing (headers, content-length, chunked encoding, keep-alive) has dozens of edge cases; gate8 already shows the limits of a minimal server (no keep-alive, no content-length header, closes after each request) |
| JSON serialization | Custom string formatting | `json.dumps()` (built-in) / Microdot dict return | Built-in handles edge cases (None → null, special chars in strings); MicroPython's `json` module is already on the device |
| CORS headers | Manual `Access-Control-Allow-*` header injection | `microdot.cors.CORS` | Pre-flight OPTIONS handling is non-obvious; missing `Access-Control-Max-Age` causes double preflight on every request |
| exec() error messages | Re-raise and format manually | `run_student_code()` wrapper catching all exceptions | exec() can raise any Python exception type; a blanket `except Exception` wrapper is the only safe pattern — missing a specific exception type breaks the error path |

**Key insight:** Gate 8 is the reference for "what happens when you build this by hand." It is 70 lines of raw sockets with no keep-alive, no CORS, and a blocking accept loop. Phase 2 replaces this with Microdot, which solves all those problems in ~5 lines of route definitions.

---

## Common Pitfalls

### Pitfall 1: WiFi AP Blocks the Event Loop During Startup

**What goes wrong:** `ap.active(True)` can take 1-2 seconds to activate the AP interface. If this is called from inside an async coroutine with a blocking `while not ap.active()` wait, the event loop freezes — the WDT feed_loop stops running, and if it takes more than 8 seconds, the device resets.

**Why it happens:** AP initialization is a hardware/firmware operation that cannot be awaited in MicroPython's WLAN API.

**How to avoid:** Start the AP in the synchronous boot section of `main.py` before `uasyncio.run(main_async())`, using `utime.sleep_ms()` not `await uasyncio.sleep_ms()`. This is safe because the WDT has not started yet (or has just been armed). Alternatively, use a reasonably short timeout (2 seconds) and feed the WDT before calling `ap.active(True)`.

**Warning signs:** Device resets during WiFi startup; WDT fires ~8s after boot when AP initialization is slow.

**Recommended approach:**
```python
# main.py boot section (sync, before uasyncio.run)
# ... existing calibration + WDT setup ...

# Start AP (blocking — 1-2s normal, 8s WDT timeout gives margin)
from tasks.wifi_task import start_ap
ap, ssid = start_ap()   # sync function, uses utime.sleep_ms(), feeds WDT internally
```

### Pitfall 2: exec() Exception Crashes the Coroutine

**What goes wrong:** Student code raises an unhandled exception. If the exec() call is not wrapped, the exception propagates from the Microdot route handler. Microdot catches exceptions in handlers and returns 500, but motor_task continues. However, if the exception somehow escapes Microdot's handler wrapper, it could kill the wifi_server_task coroutine.

**Why it happens:** exec() re-raises the exception from the executed code.

**How to avoid:** Always wrap `exec()` in a `try/except Exception` block in `run_student_code()`. Never call `exec()` directly in a route handler. Return the error as a JSON dict with `{"ok": false, "error": "..."}`.

**Warning signs:** Route returns 500 repeatedly; POST /exec stops responding after first student error.

### Pitfall 3: uasyncio gather() Exception Propagation

**What goes wrong:** If `wifi_server_task()` throws an unhandled exception (e.g., Microdot crashes on a malformed request), `gather()` cancels all other tasks including motor_pid_loop. Rover drives away.

**Why it happens:** Same pitfall as Phase 1 (documented in 01-RESEARCH.md, Pitfall 2). Applies equally to the new wifi_task.

**How to avoid:** Wrap the body of `wifi_server_task()` in `try/except Exception`. On exception, brake both motors, log the error, and consider restarting the AP. Microdot's built-in exception handling in route decorators prevents most crashes from reaching this level.

### Pitfall 4: CORS Preflight Fails on Browser

**What goes wrong:** Browser sends OPTIONS preflight before POST /exec. If Microdot CORS is not configured, the preflight gets a 404 or 405, and Chrome/Firefox blocks the actual POST. The rover appears to "not work" even though it is listening correctly.

**Why it happens:** Cross-origin requests (browser on a different origin than the rover IP) trigger CORS. During Phase 2 local testing this may not surface (testing from curl or same-origin), but Phase 3+ React app will fail.

**How to avoid:** Add `CORS(app, allowed_origins='*')` when Microdot app is created. This handles OPTIONS preflight automatically. Add it now — it is trivial and avoids debugging confusion in later phases.

### Pitfall 5: Microdot Not Found at Import Time

**What goes wrong:** `from microdot import Microdot` fails with `ModuleNotFoundError` at boot. Entire firmware crashes to REPL. The device appears unresponsive.

**Why it happens:** microdot.py was not copied to the Pico W before flashing main.py. Common during development when files are synced incrementally.

**How to avoid:** Copy microdot.py as the FIRST step of Phase 2 implementation. Add a verification gate that imports Microdot and prints its presence before running the full server. Document in the Getting Started guide that microdot.py must be present on the filesystem.

### Pitfall 6: AP Interface vs STA Interface MAC Address

**What goes wrong:** `network.WLAN(network.STA_IF).config('mac')` returns a different MAC than `network.WLAN(network.AP_IF).config('mac')`. On some Pico W firmware builds, STA and AP interfaces have different MAC addresses (AP MAC is often STA MAC + 1).

**Why it happens:** The Pico W CYW43439 chipset has separate MAC addresses for STA and AP modes.

**How to avoid:** Always read the MAC from the AP interface (`network.WLAN(network.AP_IF).config('mac')`) so the SSID suffix is stable and predictable regardless of STA state. Tested on Pico W: AP MAC is the canonical "unit identifier."

---

## Code Examples

### Complete WiFi AP Startup

```python
# tasks/wifi_task.py — start_ap() function
import network
import ubinascii
import utime
import config

def start_ap() -> tuple:
    """
    Start WiFi Access Point with MAC-derived unique SSID.

    Returns (ap, ssid) tuple.
    Blocks until AP is active (max 10s) — call from sync boot section only.
    """
    ap = network.WLAN(network.AP_IF)
    # Read MAC BEFORE activating to avoid any potential state issue
    mac = ap.config('mac')                              # 6 bytes
    suffix = ubinascii.hexlify(mac[-2:]).decode().upper()  # last 2 bytes = 4 hex chars
    ssid = "RoboPico-{}".format(suffix)                # e.g. "RoboPico-3A4F"

    ap.config(ssid=ssid, password=config.WIFI_AP_PASSWORD)  # BEFORE active()
    ap.active(True)

    deadline = utime.ticks_add(utime.ticks_ms(), 10000)
    while not ap.active():
        if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
            raise RuntimeError("WiFi AP failed to activate after 10s")
        utime.sleep_ms(200)

    ip = ap.ifconfig()[0]   # 192.168.4.1 on Pico W
    print("AP active: SSID={} IP={} Password={}".format(ssid, ip, config.WIFI_AP_PASSWORD))
    return ap, ssid
```

### Microdot Routes for Phase 2

```python
# In tasks/wifi_task.py

from microdot import Microdot
from microdot.cors import CORS
from robot import RobotAPI
from safety.sandbox import run_student_code

app = Microdot()
CORS(app, allowed_origins='*')  # Required for browser requests

_robot = RobotAPI()


@app.get('/status')
async def status(request):
    # Dict return → Microdot auto-serializes as application/json
    return _robot.status()


@app.post('/exec')
async def exec_endpoint(request):
    body = request.json
    if not body or "code" not in body:
        return {"ok": False, "error": "Missing 'code' field"}, 400

    result = run_student_code(body["code"], _robot)
    return result, (200 if result["ok"] else 400)


async def wifi_server_task():
    # AP startup is done in main.py boot section (sync)
    # This coroutine just runs the server
    await app.start_server(host='0.0.0.0', port=80, debug=False)
```

### exec() Sandbox Test

```python
# gates/gate7_exec_sandbox.py — verify exec() sandbox rejects forbidden imports
from safety.sandbox import run_student_code
from robot import RobotAPI

robot = RobotAPI()

def test_import_machine_blocked():
    result = run_student_code("import machine", robot)
    assert result["ok"] == False, "Should block import machine"
    assert "Import blocked" in result["error"] or "import" in result["error"].lower()
    print("PASS: import machine rejected:", result["error"])

def test_import_os_blocked():
    result = run_student_code("import os", robot)
    assert result["ok"] == False, "Should block import os"
    print("PASS: import os rejected:", result["error"])

def test_valid_robot_code_runs():
    result = run_student_code("robot.stop()", robot)
    assert result["ok"] == True, "robot.stop() should succeed: " + str(result)
    print("PASS: robot.stop() executed successfully")

def test_syntax_error_returns_error():
    result = run_student_code("robot.forward(", robot)
    assert result["ok"] == False, "Syntax error should return ok=False"
    print("PASS: syntax error returned:", result["error"])

test_import_machine_blocked()
test_import_os_blocked()
test_valid_robot_code_runs()
test_syntax_error_returns_error()
print("PASS: All exec() sandbox tests passed")
```

Note: gate7_exec_sandbox.py can run on the host (no hardware needed) using CPython because `robot.py` methods call `tasks.motor_task` which does not touch hardware until the event loop is running. For host-side testing, stub `tasks.motor_task` to use dicts.

---

## State of the Art

| Old Approach (gate8) | Current Approach (Phase 2) | Impact |
|----------------------|---------------------------|--------|
| Raw `socket.accept()` blocking loop | Microdot `start_server()` as async coroutine | Motor PID and sensor tasks keep running while HTTP requests are handled |
| No keep-alive | Microdot handles HTTP/1.1 keep-alive automatically | Browser can reuse connections; lower latency for rapid exec() calls |
| Static SSID "RoboPico-Lab" | MAC-derived SSID "RoboPico-XXXX" | 30 rovers in a classroom are distinguishable by students |
| No exec() sandbox | Custom `__import__` + `__builtins__` restriction | `import machine` rejected cleanly; rover does not crash; Phase 3+ browser code writes to stable API |
| No CORS headers | `microdot.cors.CORS(app, allowed_origins='*')` | React app (Phase 3) can make POST requests without browser blocking |

**Still valid from gate8:**
- `network.WLAN(network.AP_IF)` AP mode pattern
- `ap.config(ssid=..., password=...)` before `ap.active(True)`
- Fixed IP 192.168.4.1 (Pico W AP default)
- `ap.ifconfig()` to confirm IP assignment
- Port 80 for HTTP

---

## Open Questions

1. **Microdot file copy mechanism during development**
   - What we know: Microdot 2.5.1 requires copying src/microdot/microdot.py (and cors.py for CORS) to the Pico W
   - What's unclear: Whether to use `mpremote fs cp` or `mip install` — mip support for Microdot was discussed in issue #67 but may not be in the official micropython-lib index
   - Recommendation: Use `mpremote fs cp` to copy files directly from the cloned microdot repo. Add this step explicitly to the plan as a Wave 0 setup task.

2. **AP config() before vs. after active() on Pico W specifically**
   - What we know: Community reports and gate8 code both call `config()` before `active()` on the Pico W; this is the RP2040-safe order
   - What's unclear: Whether `active()` must be called before `config('mac')` to read the MAC address, or if MAC is available before activation
   - Recommendation: Read MAC, then config(ssid), then active(). If MAC reads as all zeros before active(), read MAC after a short `active(True)` → read MAC → set config → `active(False)` → `active(True)`. Gate8 doesn't need the MAC so this wasn't tested. Add a MAC-read test to the gate script.

3. **exec() with async code**
   - What we know: Phase 2 exec() runs synchronous student code (robot.forward(), robot.stop()). The RobotAPI methods are synchronous and call set_target_rpm() directly.
   - What's unclear: Phase 4 may need timed commands like `robot.forward_for(seconds=2)` which would require async or blocking sleeps in student code. A blocking sleep in exec'd code would freeze the event loop.
   - Recommendation: For Phase 2, document that exec() is synchronous only. Phase 4 can revisit timed commands using a different execution model (e.g., compile to a sequence of timed motor commands, not real-time sleep).

4. **Microdot memory footprint on Pico W**
   - What we know: Pico W has 264KB RAM; Microdot 2.5.1 is ~50-70KB uncompressed; MicroPython already uses ~100-150KB at runtime after Phase 1 firmware boots
   - What's unclear: Whether microdot.py + CORS module + robot.py + sandbox.py + the existing Phase 1 heap fit in remaining RAM
   - Recommendation: Compile microdot.py to .mpy bytecode before copying (`mpy-cross microdot.py`); .mpy runs from flash and only loads needed sections into RAM. Add a heap-check gate: `import micropython; micropython.mem_info()` after all imports, fail if free < 20KB.

---

## Sources

### Primary (HIGH confidence)

- MicroPython official docs `network.WLAN` — `ap.config('mac')`, `AP_IF`, `ifconfig()`, `config(ssid=..., password=...)` before `active()`: https://docs.micropython.org/en/latest/library/network.WLAN.html
- Microdot 2.5.1 official docs — `start_server()` coroutine, `request.json`, dict-to-JSON auto-response, CORS extension, error handlers: https://microdot.readthedocs.io/en/latest/
- Context7 `/miguelgrinberg/microdot` — `start_server()` signature, CORS usage, `create_task` integration pattern (HIGH — matches official docs)
- Context7 `/micropython/micropython` — `asyncio.start_server`, `StreamReader.readline()`, `network.WLAN` AP_IF API (HIGH — from official MicroPython repo docs)
- Codebase `gates/gate8_wifi_telemetry.py` — Confirmed working AP mode on this exact hardware; AP startup pattern; socket-based HTTP serving reference
- Codebase `tasks/wifi_task.py` — Phase 1 placeholder documents the intended Phase 2 replacement contract explicitly
- Codebase `tasks/sensor_task.py` — `get_sensor_state()` accessor is the stable sensor data interface robot.py reads
- Codebase `tasks/motor_task.py` — `set_target_rpm()` / `get_target_rpm()` are the stable motor control interface robot.py calls

### Secondary (MEDIUM confidence)

- Microdot GitHub Discussion #122 — Integration pattern for Microdot alongside other uasyncio tasks: `asyncio.create_task(app.start_server())` or `await app.start_server()` from gather() (MEDIUM — community + maintainer response)
- MicroPython Discussion #10933 — Same Microdot + uasyncio integration pattern confirmed with code example
- Forum community (Raspberry Pi Forums) — `ap.config()` BEFORE `ap.active()` on RP2040 specific; `readline()` more reliable than `read()` for HTTP headers: https://forums.raspberrypi.com/viewtopic.php?t=336901
- `ubinascii.hexlify(wlan.config('mac'), ':')` pattern from multiple community sources and RandomNerdTutorials; confirmed it returns 6-byte MAC

### Tertiary (LOW confidence — verify during implementation)

- MAC available before `ap.active(True)` — community reports vary; needs bench verification
- Microdot .mpy memory savings on Pico W — engineering estimate; needs heap measurement on actual device
- AP MAC vs STA MAC suffix consistency across all Pico W firmware versions — documented in research but not confirmed across all builds

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Microdot is the clear choice; confirmed from official docs + Context7; MicroPython network module is built-in
- Architecture: HIGH — robot.py facade pattern, Microdot route patterns, exec() sandbox all verified from official/authoritative sources
- AP startup pattern: MEDIUM — core pattern from gate8 + official docs; RP2040-specific ordering confirmed from community but not from Raspberry Pi official docs
- exec() sandbox: MEDIUM — the `exec(code, globals_dict)` + custom `__builtins__` approach is confirmed MicroPython behavior; the "K-8 threat model" scope is a judgment call, not a cited source
- Microdot memory: LOW — engineering estimate; no measured data for Phase 2 code size on this firmware

**Research date:** 2026-03-04
**Valid until:** 2026-09-04 (Microdot 2.5.1 is stable; MicroPython network API is stable; RP2040 behavior does not change)
