---
phase: 01-firmware-foundation
plan: 01
subsystem: firmware
tags: [micropython, uasyncio, raspberry-pi-pico-w, async, watchdog, motor, pid, imu]

# Dependency graph
requires: []
provides:
  - uasyncio event loop entry point in main.py with safe WDT boot sequence
  - tasks/motor_task.py: motor_pid_loop() coroutine at 20Hz with PID stubs
  - tasks/sensor_task.py: sensor_poll_loop() coroutine at 10Hz
  - tasks/wifi_task.py: wifi_placeholder() coroutine for Phase 2 HTTP server slot
  - gates/gate1_async_skeleton.py: 3-coroutine interleave proof-of-concept
  - gates/run_all.py: sequential gate runner for v2 verification suite
affects:
  - 01-firmware-foundation (plans 02-04 build on this async skeleton)
  - Phase 2 WiFi/HTTP server slots into wifi_placeholder() coroutine slot

# Tech tracking
tech-stack:
  added:
    - uasyncio (MicroPython built-in cooperative scheduler)
    - machine.WDT (hardware watchdog, 8000ms timeout)
  patterns:
    - uasyncio.gather() for concurrent coroutines (motor + sensor + wifi + wdt)
    - Module-level hardware instances in task modules (one Motor/PID per file)
    - try/except Exception in every coroutine body to prevent gather() cascade failure
    - Actual dt measurement with utime.ticks_diff() instead of nominal interval
    - WDT armed AFTER IMU calibration completes (Pitfall 1 avoidance)

key-files:
  created:
    - tasks/__init__.py
    - tasks/motor_task.py
    - tasks/sensor_task.py
    - tasks/wifi_task.py
    - gates/gate1_async_skeleton.py
    - gates/run_all.py
  modified:
    - main.py (full rewrite as async entry point)

key-decisions:
  - "Inline wdt_feed_loop in main.py for now — Plan 04 refactors into safety/watchdog.py WatchdogKeeper"
  - "Motor stubs use measured=0.0 for PID input — Phase 2 replaces with real encoder RPM"
  - "sensor_poll_loop catches and continues on exception — sensor failure must not kill motor task"
  - "WDT timeout=8000ms with 4s feed interval — 2x safety margin against RP2040 WDT max of 8388ms"

patterns-established:
  - "Pitfall 1 pattern: calibrate IMU before arming WDT in boot sequence"
  - "Pitfall 2 pattern: each coroutine wraps body in try/except; motor brakes before re-raise"
  - "Pitfall 4 pattern: actual dt via utime.ticks_diff(), not nominal sleep interval"
  - "gate1_async_skeleton.py is standalone (no tasks/ imports) — proves scheduler, not hardware"

requirements-completed: [FW-01]

# Metrics
duration: 2min
completed: 2026-03-03
---

# Phase 1 Plan 01: Async Skeleton Summary

**Three concurrent uasyncio coroutines (motor PID at 20Hz, sensor poll at 10Hz, WiFi placeholder) launched from a safe-boot main.py with WDT armed after IMU calibration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-03T03:34:51Z
- **Completed:** 2026-03-03T03:36:56Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created tasks/ module with three stub coroutines proving cooperative scheduling works without hardware drivers
- Rewrote main.py as async entry point with correct boot sequence: I2C init, IMU calibrate_gyro_z(200), then WDT arm
- Created gate1_async_skeleton.py standalone 3-coroutine interleave proof-of-concept and run_all.py gate runner

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tasks/ module with three stub coroutines** - `4ca6003` (feat)
2. **Task 2: Rewrite main.py as async entry point + create gate1 + run_all** - `eb63608` (feat)

**Plan metadata:** (added in final commit)

## Files Created/Modified

- `tasks/__init__.py` - Package marker for tasks module
- `tasks/motor_task.py` - motor_pid_loop() at 20Hz; Motor + PID instances; actual dt measurement; brakes on exception
- `tasks/sensor_task.py` - sensor_poll_loop() at 10Hz; shared _sensor_state dict; continues on exception (safe for gather)
- `tasks/wifi_task.py` - wifi_placeholder() every 1s; slot reserved for Phase 2 HTTP server
- `main.py` - Full rewrite: banner, I2C+IMU init, calibrate_gyro_z(200), WDT(8000ms), uasyncio.run(main_async())
- `gates/gate1_async_skeleton.py` - Standalone 3-coroutine interleave test; task_a(100ms)+task_b(150ms)+task_c(200ms); outputs PASS
- `gates/run_all.py` - Sequential gate runner with exec() per gate and PASS/FAIL summary

## Decisions Made

- **Inline wdt_feed_loop:** Plan 04 introduces safety/watchdog.py WatchdogKeeper; this plan uses a simpler inline coroutine to avoid forward dependencies
- **Stub PID measured=0.0:** Motor task computes PID against zero measured RPM since no encoder exists yet — demonstrates architecture without requiring hardware
- **Sensor exception continues:** sensor_poll_loop() catches and continues rather than re-raising, since sensor failure must never propagate to gather() and cancel the motor task

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all files parsed without syntax errors on the first attempt. The MPU6050 constructor takes `(i2c_id, sda, scl, freq, addr)` keyword args as confirmed from lib/mpu6050.py inspection before writing main.py.

## User Setup Required

None - no external service configuration required. On-device verification requires physical Pico W connected via USB:

```
mpremote run gates/gate1_async_skeleton.py
```

Expected output: interleaved A/B/C lines ending with "PASS: All 3 tasks completed without blocking"

## Next Phase Readiness

- Async skeleton complete — Phase 1 Plan 02 (encoder PIO) and Plan 03 (sensor drivers) can build on this architecture
- All three task coroutine files are in place; replacing stub bodies with real drivers requires no architectural changes
- The gather() call in main.py is the single integration point — adding a fifth coroutine (e.g., Phase 2 HTTP server) is a one-line addition

---
*Phase: 01-firmware-foundation*
*Completed: 2026-03-03*

## Self-Check: PASSED

- FOUND: tasks/__init__.py
- FOUND: tasks/motor_task.py
- FOUND: tasks/sensor_task.py
- FOUND: tasks/wifi_task.py
- FOUND: main.py
- FOUND: gates/gate1_async_skeleton.py
- FOUND: gates/run_all.py
- FOUND commit: 4ca6003 (Task 1)
- FOUND commit: eb63608 (Task 2)
