# Phase 8: Phase 1-2 Audit Fixes - Research

**Researched:** 2026-03-05
**Domain:** MicroPython firmware audit remediation — YAML frontmatter editing, I2C bus sharing, legacy gate cleanup
**Confidence:** HIGH (all three defects are directly observable in codebase; no external library research required)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FW-07 | Hardware watchdog for exec() safety (tracking fix only — code already verified correct) | Defect is in 01-04-SUMMARY.md YAML frontmatter: `requirements-completed` lists `[FW-05, FW-06]` instead of `[FW-07]`. One-line frontmatter edit closes the gap. REQUIREMENTS.md checkbox also unchecked. |
</phase_requirements>

---

## Summary

Phase 8 is a pure remediation phase — three distinct defects discovered during the v1.0 milestone audit, none of which require new feature code. The audit (`v1.0-MILESTONE-AUDIT.md`) identified them precisely: (1) a YAML frontmatter tracking error in plan 01-04's SUMMARY file listing the wrong requirement IDs, (2) a dual I2C bus initialization risk where `sensor_task.py` creates its own `machine.I2C(0)` instance for ColorSensor while `main.py` already holds one for MPU6050, and (3) a legacy gate script (`gate8_wifi_telemetry.py`) that imports a config constant (`WIFI_AP_SSID`) removed in Phase 2 — which would crash with `ImportError` if run standalone.

All three fixes are surgical and local. Fix 1 is a one-field YAML edit to a SUMMARY file plus unchecking/rechecking a markdown checkbox in REQUIREMENTS.md. Fix 2 requires adding a `set_i2c()` injection setter to `sensor_task.py` (following the existing `set_heading_tracker()` pattern), passing main.py's existing I2C instance into sensor_task, and removing the duplicate `I2C()` construction. Fix 3 requires updating `gate8_wifi_telemetry.py` to use `WIFI_AP_SSID_PREFIX` (the constant that replaced `WIFI_AP_SSID` in Phase 2) — or, since this gate is a legacy standalone script for manual verification only and not in `run_all.py`, optionally deleting the gate or adding a note that it requires manual SSID configuration.

**Primary recommendation:** Three atomic changes, three separate tasks in one plan. Use the established `set_X()` injection pattern for the I2C fix (already used for `set_heading_tracker()` and `set_watchdog()`). The gate8 fix should update the import to use `WIFI_AP_SSID_PREFIX` and hardcode or derive a test SSID — making the script runnable again.

---

## Defect Analysis

### Defect 1: FW-07 Tracking Error (YAML frontmatter + checkbox)

**Location:** `.planning/phases/01-firmware-foundation/01-04-SUMMARY.md` and `.planning/REQUIREMENTS.md`

**Evidence from audit:**
```
Plan 01-04 SUMMARY frontmatter incorrectly lists requirements-completed: [FW-05, FW-06]
instead of [FW-07]. REQUIREMENTS.md checkbox unchecked.
```

**Current state of 01-04-SUMMARY.md frontmatter:**
```yaml
requirements-completed: [FW-05, FW-06]
```

**Required state:**
```yaml
requirements-completed: [FW-07]
```

**Note on FW-05/FW-06:** These were completed in plan 01-03 (sensor drivers). The 01-04 SUMMARY incorrectly claims them — they should be removed from 01-04 and left only in 01-03 where they were originally declared. The 01-03-SUMMARY.md correctly lists them; this change is corrective, not additive.

**REQUIREMENTS.md:** Line 18 currently has `[ ] FW-07` — it should be `[x] FW-07` (with `*(completed 01-04, verified in v1.0 audit — code correct, tracking error fixed)*` appended). The audit description already reflects this intention in the file.

**Confidence:** HIGH — direct file inspection confirms the error.

---

### Defect 2: Dual I2C(0) Instance (sensor_task.py + main.py)

**Root cause:** `main.py` constructs an I2C(0) bus implicitly through `MPU6050(i2c_id=config.I2C_ID, ...)` — `lib/mpu6050.py` line 48 does `self._i2c = I2C(i2c_id, sda=Pin(sda), scl=Pin(scl), freq=freq)`. Then, when `config.COLOR_ANALOG_PIN is None` (the default), `tasks/sensor_task.py` lines 59-64 construct a second `I2C(0)`:

```python
_shared_i2c = I2C(
    config.I2C_ID,
    sda=Pin(config.I2C_SDA),
    scl=Pin(config.I2C_SCL),
    freq=config.I2C_FREQ,
)
_color_sensor = ColorSensor(i2c=_shared_i2c)
```

**Risk:** On RP2040/MicroPython, creating two `machine.I2C` instances on the same hardware bus (I2C0) is not guaranteed safe. The same peripheral is re-initialized with the same pins. In practice this may work, but it can cause silent bus corruption or `OSError: [Errno 5] EIO` on I2C reads — especially during concurrent async operations.

**Fix pattern:** The project already uses dependency injection via setter functions for cross-task wiring:
- `set_heading_tracker(tracker)` in sensor_task (wires in from main.py)
- `set_watchdog(wdg)` in motor_task (wires in from main.py)

The fix follows the same pattern:
1. Add `set_i2c(i2c)` setter to `sensor_task.py`
2. Remove the module-level `_shared_i2c = I2C(...)` block from sensor_task.py
3. Make `_color_sensor` initialization lazy (defer until `set_i2c()` is called, or initialize in `sensor_poll_loop()`)
4. In `main.py`, extract the I2C instance from the MPU6050 driver (or construct it separately before passing to MPU6050) and call `sensor_task.set_i2c(i2c_instance)` after IMU calibration, before starting the event loop

**Key decision — I2C instance source:** `lib/mpu6050.py` stores the I2C instance as `self._i2c`. The cleanest approach is to construct `i2c = I2C(config.I2C_ID, sda=Pin(config.I2C_SDA), scl=Pin(config.I2C_SCL), freq=config.I2C_FREQ)` explicitly in `main.py` before creating the MPU6050, pass it to MPU6050's constructor (if MPU6050 supports accepting an existing I2C object) — or since MPU6050 always creates its own, simply expose `imu._i2c` and pass that to sensor_task.

Inspection of `lib/mpu6050.py` line 48 shows MPU6050 always creates its own `I2C` internally — it does not accept a pre-built I2C object. Therefore the cleanest fix is: construct I2C explicitly in `main.py`, store as `_i2c`, pass to sensor_task.set_i2c(), AND also construct MPU6050 using that same instance. This requires a small MPU6050 constructor change to optionally accept an existing I2C, or alternatively, expose `imu._i2c` (less clean but avoids touching the library).

**Simplest viable fix:** Construct `i2c` in main.py, pass `i2c` to `sensor_task.set_i2c()`. In sensor_task, use the injected I2C for ColorSensor. Leave MPU6050 creating its own I2C internally (accept that MPU6050's I2C is separate from sensor_task's) — OR refactor MPU6050 to accept an existing I2C object.

**Recommended approach:** The least-invasive approach that avoids modifying `lib/mpu6050.py` is:
1. In `main.py`: after `imu = MPU6050(...)`, call `sensor_task.set_i2c(imu._i2c)` — this passes the I2C instance that MPU6050 already created
2. In `sensor_task.py`: add `set_i2c()` setter, delay ColorSensor construction until `set_i2c()` is called (use a module-level `_shared_i2c = None` and initialize `_color_sensor` inside `set_i2c()`)
3. Remove the standalone `_shared_i2c = I2C(...)` block from sensor_task module-level code

This eliminates the second I2C initialization entirely with minimal code change.

**Alternative:** Refactor `lib/mpu6050.py` to accept either `i2c_id` params or a pre-built `I2C` object. Slightly cleaner API but touches the library. Lower risk to leave the library as-is.

**Confidence:** HIGH — both the defect and the injection pattern are directly observed in code.

---

### Defect 3: Legacy gate8_wifi_telemetry.py References Removed Constants

**Location:** `gates/gate8_wifi_telemetry.py`

**Current broken import (line 27-29):**
```python
from config import (
    I2C_ID, I2C_SDA, I2C_SCL, I2C_FREQ,
    WIFI_AP_SSID, WIFI_AP_PASSWORD, WIFI_AP_IP, HTTP_PORT,
)
```

**`WIFI_AP_SSID` does not exist in config.py.** Phase 2 replaced it with `WIFI_AP_SSID_PREFIX = "RoboPico"` (with MAC suffix appended at runtime). Running this gate script standalone would cause:
```
ImportError: cannot import name 'WIFI_AP_SSID' from 'config'
```

**Context:** `gate8_wifi_telemetry.py` is a legacy standalone verification script (pre-Phase 2). It is NOT in `gates/run_all.py` — confirmed by reading run_all.py which only lists gates 1-7. So there is no production impact, but the file is broken.

**Fix options:**

Option A (recommended): Update the gate to use current config constants and derive a fixed test SSID:
```python
from config import (
    I2C_ID, I2C_SDA, I2C_SCL, I2C_FREQ,
    WIFI_AP_SSID_PREFIX, WIFI_AP_PASSWORD, WIFI_AP_IP, HTTP_PORT,
)
WIFI_AP_SSID = WIFI_AP_SSID_PREFIX + "-TEST"  # standalone gate uses fixed SSID
```
And update `ap.config(essid=WIFI_AP_SSID, ...)` to use the local variable. This makes the gate runnable again as a standalone manual test.

Option B: Delete gate8_wifi_telemetry.py — it is superseded by the Phase 2 Microdot-based server in wifi_task.py and gate7_exec_sandbox.py. Deletion eliminates the maintenance burden.

Option C: Add a comment at the top noting the file is broken/legacy and requires manual update before use.

**Recommendation:** Option A — keep the gate runnable. It tests a useful flow (WiFi AP + HTTP) and the fix is two lines. Deletion would remove useful manual test infrastructure.

**Confidence:** HIGH — direct inspection confirms the missing constant and the fix pattern.

---

## Standard Stack

### Core (all MicroPython built-ins — no installation needed)

| Component | Purpose | Notes |
|-----------|---------|-------|
| `machine.I2C` | I2C bus hardware | Already used in main.py and sensor_task; fix unifies to one instance |
| YAML/frontmatter editing | Fix 01-04-SUMMARY.md | Plain text edit — no tooling required |
| Python `import` | gate8 fix | Replace removed constant reference |

### No New Libraries

This phase introduces no new libraries. All fixes are code-level changes to existing files using already-imported modules.

---

## Architecture Patterns

### Pattern: Dependency Injection via Setter (already established)

The project uses a consistent pattern for cross-module wiring set up during the main.py boot sequence:

```python
# Established pattern (sensor_task.py)
_heading_tracker = None

def set_heading_tracker(tracker: HeadingTracker):
    global _heading_tracker
    _heading_tracker = tracker
```

```python
# Established pattern (motor_task.py)
_watchdog = None

def set_watchdog(wdg):
    global _watchdog
    _watchdog = wdg
```

The I2C fix follows the identical pattern:
```python
# New addition to sensor_task.py
_shared_i2c = None
_color_sensor = None  # initialized lazily in set_i2c()

def set_i2c(i2c):
    """Wire in the shared I2C bus from main.py. Call before starting event loop."""
    global _shared_i2c, _color_sensor
    _shared_i2c = i2c
    _color_sensor = ColorSensor(i2c=_shared_i2c)
```

And in main.py's boot sequence (Step 3, after IMU init):
```python
# After: imu = MPU6050(i2c_id=config.I2C_ID, ...)
import tasks.sensor_task as sensor_task
sensor_task.set_i2c(imu._i2c)   # share the bus MPU6050 already opened
sensor_task.set_heading_tracker(heading_tracker)
```

### Pattern: Module-Level Sensor Construction Must Handle None I2C

The current sensor_task.py constructs `_color_sensor` at module level. After the fix, construction is deferred to `set_i2c()`. The `sensor_poll_loop()` must guard against `_color_sensor` being `None` (same as the existing `_heading_tracker` guard):

```python
if _color_sensor is not None:
    _sensor_state["color"] = await _color_sensor.read()
```

### Anti-Patterns to Avoid

- **Creating machine.I2C() more than once for the same bus:** RP2040 I2C peripheral is a hardware resource. Multiple software handles for the same hardware bus risk bus state corruption.
- **Module-level hardware init that bypasses injection:** Any hardware object created at module import time cannot receive injected dependencies. Lazy initialization (inside a setter) is the correct pattern.
- **Hardcoding removed config constants:** Gate scripts must reference current config.py names. Legacy constants (`WIFI_AP_SSID`) must be mapped to current equivalents (`WIFI_AP_SSID_PREFIX`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| I2C sharing | Custom bus arbitration or locking | Single shared I2C instance via injection | MicroPython I2C is synchronous and cooperative-task-safe when there is a single owner; no locking needed |
| SSID generation in gate8 | Dynamic MAC-derived SSID | Fixed test SSID string for standalone gate | Gate8 is a manual test; it doesn't need dynamic SSID — simplest fix wins |

---

## Common Pitfalls

### Pitfall 1: Removing `_color_sensor` Construction Without Guarding sensor_poll_loop

**What goes wrong:** After removing the module-level `I2C()` and `ColorSensor()` construction, `sensor_poll_loop()` will call `await _color_sensor.read()` on `None` and crash with `AttributeError`.

**How to avoid:** Add `if _color_sensor is not None:` guard around the color read in `sensor_poll_loop()`. This mirrors the existing `if _heading_tracker is not None:` pattern at line 121.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'read'` on first sensor_poll_loop iteration.

### Pitfall 2: Touching 01-03-SUMMARY.md When Fixing 01-04-SUMMARY.md

**What goes wrong:** FW-05 and FW-06 appear in `01-04-SUMMARY.md`'s `requirements-completed`. They were correctly completed in plan 01-03. The fix is to remove `[FW-05, FW-06]` from 01-04 and set it to `[FW-07]`. Do NOT add FW-05/FW-06 back to 01-03-SUMMARY.md — they are already there.

**How to avoid:** Read both SUMMARY files before editing. Only edit 01-04-SUMMARY.md's frontmatter field.

### Pitfall 3: Using `imu._i2c` (Private Attribute Access)

**What goes wrong:** `imu._i2c` is a private attribute of MPU6050. Accessing it with `._i2c` is technically valid in Python/MicroPython but fragile — if `lib/mpu6050.py` is ever refactored, this breaks silently.

**How to avoid:** If time permits, add a read-only `i2c` property to MPU6050 that exposes `self._i2c`. This makes the contract explicit. However, for a pure audit fix phase, using `imu._i2c` directly is acceptable with a comment noting the dependency.

### Pitfall 4: gate8 SSID Name Collision in Classroom

**What goes wrong:** If gate8 uses `WIFI_AP_SSID_PREFIX + "-TEST"` as a hardcoded SSID, multiple rovers running gate8 simultaneously in a classroom would broadcast the same SSID ("RoboPico-TEST"), causing connection confusion.

**How to avoid:** Gate8 is a manual standalone test (not in run_all.py) and should only be run one rover at a time. Document this in a comment. If stricter isolation is needed, derive the suffix from the MAC address using the same pattern as wifi_task.py's `start_ap()`.

---

## Code Examples

### Fix 1: Corrected 01-04-SUMMARY.md frontmatter

```yaml
# Before (incorrect):
requirements-completed: [FW-05, FW-06]

# After (correct):
requirements-completed: [FW-07]
```

### Fix 2: REQUIREMENTS.md checkbox update

```markdown
# Before:
- [ ] **FW-07**: Hardware watchdog for exec() safety (prevent runaway student code)

# After:
- [x] **FW-07**: Hardware watchdog for exec() safety (prevent runaway student code) *(completed 01-04, verified in v1.0 audit — code correct, tracking error fixed)*
```

### Fix 3: sensor_task.py I2C injection (sensor_task.py diff)

Remove the existing module-level I2C block (lines 59-65):
```python
# REMOVE this block:
else:
    _shared_i2c = I2C(
        config.I2C_ID,
        sda=Pin(config.I2C_SDA),
        scl=Pin(config.I2C_SCL),
        freq=config.I2C_FREQ,
    )
    _color_sensor = ColorSensor(i2c=_shared_i2c)
```

Replace with lazy initialization via setter (add after `_heading_tracker = None`):
```python
# I2C bus shared with IMU — injected from main.py via set_i2c()
_shared_i2c = None
_color_sensor: ColorSensor = None  # initialized in set_i2c()

def set_i2c(i2c):
    """
    Wire in the shared I2C bus from main.py after IMU init.

    Call this from main.py after MPU6050 init and before starting
    the event loop. sensor_poll_loop() will then use the shared bus
    for ColorSensor reads — avoiding a second I2C(0) instantiation.
    """
    global _shared_i2c, _color_sensor
    _shared_i2c = i2c
    _color_sensor = ColorSensor(i2c=_shared_i2c)
```

Update color sensor initialization in the `else` branch of module-level code to skip I2C construction:
```python
# Color sensor: use analog pin if configured, otherwise I2C TCS34725
if config.COLOR_ANALOG_PIN is not None:
    _color_sensor = ColorSensor(analog_pin=config.COLOR_ANALOG_PIN)
# else: _color_sensor will be set in set_i2c() — called from main.py
```

Add null guard in sensor_poll_loop():
```python
# Color / light — dict with RGBC or lux key
if _color_sensor is not None:
    _sensor_state["color"] = await _color_sensor.read()
```

### Fix 4: main.py I2C injection call (addition to Step 3)

```python
# ── Step 3: Wrap IMU in HAL + HeadingTracker + Share I2C ──────────────────────
from hal.imu import IMUHAL, HeadingTracker
import tasks.sensor_task as sensor_task

imu_hal = IMUHAL(imu)
heading_tracker = HeadingTracker(imu_hal)
sensor_task.set_i2c(imu._i2c)              # share I2C bus — avoids dual I2C(0)
sensor_task.set_heading_tracker(heading_tracker)
print("HeadingTracker and shared I2C wired into sensor_task")
```

### Fix 5: gate8_wifi_telemetry.py import fix

```python
# Before (broken):
from config import (
    I2C_ID, I2C_SDA, I2C_SCL, I2C_FREQ,
    WIFI_AP_SSID, WIFI_AP_PASSWORD, WIFI_AP_IP, HTTP_PORT,
)

# After (fixed):
from config import (
    I2C_ID, I2C_SDA, I2C_SCL, I2C_FREQ,
    WIFI_AP_SSID_PREFIX, WIFI_AP_PASSWORD, WIFI_AP_IP, HTTP_PORT,
)
# Standalone gate uses a fixed test SSID (run only one rover at a time)
WIFI_AP_SSID = WIFI_AP_SSID_PREFIX + "-TEST"
```

No other changes needed — `WIFI_AP_SSID` is used as a local variable in `start_ap()` and print statements, which still work.

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `.planning/phases/01-firmware-foundation/01-04-SUMMARY.md` | YAML frontmatter edit | `requirements-completed: [FW-05, FW-06]` → `[FW-07]` |
| `.planning/REQUIREMENTS.md` | Checkbox + annotation | `[ ] FW-07` → `[x] FW-07` with completion note |
| `tasks/sensor_task.py` | Refactor | Add `set_i2c()` setter, remove duplicate `I2C()` construction, add null guard |
| `main.py` | Addition | Call `sensor_task.set_i2c(imu._i2c)` in Step 3 of boot sequence |
| `gates/gate8_wifi_telemetry.py` | Import fix | Replace `WIFI_AP_SSID` import with `WIFI_AP_SSID_PREFIX`; derive local `WIFI_AP_SSID` variable |

No new files need to be created.

---

## Open Questions

1. **Should `lib/mpu6050.py` be refactored to accept an existing I2C object?**
   - What we know: MPU6050 always creates its own I2C internally; accessing `imu._i2c` works but is fragile
   - What's unclear: Whether future phases (Phase 3+) will need to pass I2C to more components
   - Recommendation: For this audit-fix phase, use `imu._i2c` with a comment. Add a public `i2c` property to MPU6050 only if the planner decides it's worth the minor library change.

2. **Should gate8_wifi_telemetry.py remain or be deleted?**
   - What we know: It is not in run_all.py; it is a legacy pre-Phase-2 manual test; fixing the import restores functionality
   - What's unclear: Whether anyone will actually use it for manual testing now that Microdot-based HTTP is the production path
   - Recommendation: Fix the import (Option A). Preservation is lower effort than deletion-plus-documentation, and keeps the manual test tool available.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `.planning/v1.0-MILESTONE-AUDIT.md` — Authoritative defect list with exact line references and root causes
- `tasks/sensor_task.py` (lines 59-65) — Confirmed duplicate I2C construction
- `main.py` (lines 38-44, 62) — Confirmed I2C initialization via MPU6050 and sensor_task wiring pattern
- `lib/mpu6050.py` (line 48) — Confirmed MPU6050 creates its own I2C internally
- `.planning/phases/01-firmware-foundation/01-04-SUMMARY.md` (line 44) — Confirmed `requirements-completed: [FW-05, FW-06]`
- `gates/gate8_wifi_telemetry.py` (lines 27-29) — Confirmed import of removed `WIFI_AP_SSID`
- `config.py` — Confirmed `WIFI_AP_SSID_PREFIX` exists; `WIFI_AP_SSID` does not

### No External Research Required

This phase has no external library dependencies. All research is codebase-internal.

---

## Metadata

**Confidence breakdown:**
- Defect identification: HIGH — all three defects verified by direct file inspection and cross-referenced with audit report
- Fix approach: HIGH — injection pattern is already established in the codebase; no novel patterns needed
- Scope: HIGH — changes are contained to 5 files; no cross-phase implications

**Research date:** 2026-03-05
**Valid until:** N/A — fixes reference stable internal code, no external API dependency
