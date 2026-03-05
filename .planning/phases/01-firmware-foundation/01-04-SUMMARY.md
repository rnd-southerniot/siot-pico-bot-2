---
phase: 01-firmware-foundation
plan: 04
subsystem: firmware
tags: [watchdog, wdt, safety, pid, encoder, rp2040]

requires:
  - phase: 01-firmware-foundation/01
    provides: "tasks/ module with motor_pid_loop, sensor_poll_loop stubs, main.py async entry"
  - phase: 01-firmware-foundation/02
    provides: "EncoderPIO (PIO quadrature), MotorHAL (70% speed cap)"
  - phase: 01-firmware-foundation/03
    provides: "IMUHAL, HeadingTracker, sensor drivers, StatusLED"
provides:
  - WatchdogKeeper with hardware WDT (8s) and software motor timeout (30s)
  - Closed-loop PID with real encoder RPM feedback
  - Fully-wired main.py boot sequence (calibrate → WDT → LED → gather)
  - Complete gate suite (6 gates via run_all.py)
affects: [02-robot-api, safety, motor-control]

tech-stack:
  added: [machine.WDT]
  patterns: [dependency-injection-for-safety, two-layer-watchdog]

key-files:
  created:
    - safety/watchdog.py
    - safety/__init__.py
    - gates/gate5_watchdog.py
  modified:
    - tasks/motor_task.py
    - main.py
    - gates/run_all.py

key-decisions:
  - "Two-layer safety: hardware WDT (8s hard reset) + software motor timeout (30s graceful brake)"
  - "Dependency injection for watchdog via set_watchdog() — avoids circular init, WDT created after IMU calibration"
  - "30-second motor timeout configurable per-unit via MOTOR_TIMEOUT_S class constant"

patterns-established:
  - "Safety injection: main.py creates WatchdogKeeper, injects into motor_task via setter — not constructor"
  - "Emergency stop pattern: brake motors first, then disarm timeout, then log"

requirements-completed: [FW-07]

duration: 4min
completed: 2026-03-03
---

# Plan 01-04: Safety Layer + Final Integration Summary

**WatchdogKeeper two-layer safety (hardware WDT 8s + software motor timeout 30s), PIO encoder closed-loop PID, fully-wired main.py boot sequence**

## Performance

- **Duration:** 4 min
- **Completed:** 2026-03-03
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- WatchdogKeeper with hardware WDT (8s device reset) and software motor timeout (30s graceful brake)
- motor_pid_loop wired to real PIO encoder RPM feedback — closed control loop
- main.py fully integrated: IMU calibrate → WatchdogKeeper → LED ready → gather(motor, sensor, wifi, wdt_feed)
- gate5_watchdog verifies software timeout trigger, WDT feed, and emergency stop

## Task Commits

1. **Task 1: WatchdogKeeper safety module** - `91c8dc5` (feat)
2. **Task 2: Wire encoders + watchdog into motor_task, main.py, gate5, run_all** - `66c8091` (feat)

## Files Created/Modified
- `safety/watchdog.py` - WatchdogKeeper: hardware WDT feed_loop + software motor timeout + emergency_stop
- `safety/__init__.py` - Package init
- `tasks/motor_task.py` - Real EncoderPIO RPM feedback in PID loop, set_watchdog() injection, emergency_stop on error
- `main.py` - Full boot sequence: I2C → IMU calibrate → WatchdogKeeper → set_watchdog → LED green → gather 4 coroutines
- `gates/gate5_watchdog.py` - 3 tests: software timeout trigger, WDT feed alive, emergency stop
- `gates/run_all.py` - Updated with all 6 gates in dependency order

## Decisions Made
- Two-layer safety: hardware WDT for full event-loop hangs, software timeout for runaway student motor code
- Dependency injection (set_watchdog) rather than constructor parameter to avoid circular init and allow WDT creation after IMU calibration
- 30-second motor timeout as class constant — configurable per deployment

## Deviations from Plan
None - plan executed as written

## Issues Encountered
- Subagent Bash permissions were denied — commits completed by orchestrator

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 firmware foundation complete: async architecture, HAL layer, safety system all wired
- Phase 2 (Robot API + HTTP Server) can build on this: WiFi AP, HTTP server slots into wifi_placeholder task
- All 6 gates ready for on-device verification via `mpremote run gates/run_all.py`

---
*Phase: 01-firmware-foundation*
*Completed: 2026-03-03*
