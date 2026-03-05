---
phase: 01-firmware-foundation
plan: 03
subsystem: firmware
tags: [micropython, uasyncio, imu, sensors, neopixel, hc-sr04, ir-sensor, tcs34725, raspberry-pi-pico-w]

# Dependency graph
requires:
  - 01-01 (uasyncio skeleton, sensor_task stub, main.py boot sequence)
  - 01-02 (hal/motors.py, hal/encoder_pio.py — motor HAL for gate3)
provides:
  - hal/imu.py: IMUHAL wrapper + HeadingTracker async 100Hz integration loop
  - hal/sensors.py: IRLineSensor, UltrasonicSensor, ColorSensor — all async-safe
  - hal/leds.py: StatusLED NeoPixel controller (ready/running/error/off/pulse)
  - tasks/sensor_task.py: Updated — real sensor reads at 10Hz, shared _sensor_state
  - gates/gate3_turn_angle.py: On-device 90-degree IMU heading accuracy test
  - gates/gate4_sensors.py: On-device all-sensor reads smoke test
affects:
  - Phase 2 (robot.py facade reads from _sensor_state dict; no direct hardware access)
  - main.py (wire HeadingTracker via set_heading_tracker() after IMU calibration)

# Tech tracking
tech-stack:
  added:
    - neopixel (MicroPython built-in WS2812 driver via PIO block 0)
    - machine.ADC (analog IR line sensor reads)
    - machine.PWM (buzzer blocking beep — boot-time only)
  patterns:
    - HeadingTracker.update_loop() as separate uasyncio task at 100Hz
    - Echo wait loops use await uasyncio.sleep_ms(0) per iteration (Pitfall 6 avoidance)
    - Actual dt measurement in HeadingTracker via utime.ticks_diff() (Pitfall 4 avoidance)
    - ColorSensor dual-mode: I2C TCS34725 (addr 0x29) or analog ADC fallback
    - Sensor instances at module level in sensor_task.py — created once, not per loop
    - set_heading_tracker() injection pattern — avoids circular init dependency

key-files:
  created:
    - hal/imu.py
    - hal/leds.py
    - hal/sensors.py
    - gates/gate3_turn_angle.py
    - gates/gate4_sensors.py
  modified:
    - tasks/sensor_task.py (stub replaced with real sensor reads)
    - config.py (added IR_PINS, ULTRASONIC_TRIG, ULTRASONIC_ECHO, COLOR_ANALOG_PIN)

key-decisions:
  - "config.NEOPIXEL_PIN used in leds.py (not LED_PIN) — NEOPIXEL_PIN is the actual config.py constant"
  - "Sensor pin defaults are placeholders — IR_PINS=[28], ULTRASONIC_TRIG=2, ULTRASONIC_ECHO=3; verify against hardware wiring before deploy"
  - "Only GP28 is free for ADC (GP26/27 are encoder pins) — single-channel IR default; 3-channel requires I2C expander or digital-output IR sensors"
  - "HeadingTracker injected into sensor_task via set_heading_tracker() — avoids circular init between main.py and sensor_task module-level init"
  - "ColorSensor defaults to I2C TCS34725 (COLOR_ANALOG_PIN=None); shares I2C0 with IMU (no address conflict: IMU=0x68, TCS34725=0x29)"

requirements-completed: [FW-03, FW-04, FW-05, FW-06]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 1 Plan 03: Sensor HAL + LED Controller Summary

**IMUHAL wrapper with HeadingTracker (100Hz gyro Z integration), async-safe IR/ultrasonic/color sensor drivers, NeoPixel state LED controller, and updated sensor_poll_loop wired to real hardware**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T04:02:16Z
- **Completed:** 2026-03-03T04:06:21Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created hal/imu.py with IMUHAL (thin MPU6050 wrapper) and HeadingTracker (async 100Hz gyro Z integration with actual dt measurement)
- Created hal/leds.py with StatusLED: set_ready/set_running/set_error/set_off state methods, async pulse_loop() animation, and buzzer_beep() boot-time tone
- Created hal/sensors.py with three async-safe sensor classes — IRLineSensor (multi-channel ADC), UltrasonicSensor (HC-SR04 with await in echo wait loops), ColorSensor (TCS34725 I2C or analog fallback)
- Updated tasks/sensor_task.py to instantiate real sensors and populate _sensor_state with ir/distance_cm/color/heading keys at 10Hz
- Added sensor pin constants to config.py (IR_PINS, ULTRASONIC_TRIG, ULTRASONIC_ECHO, COLOR_ANALOG_PIN)
- Created gate3_turn_angle.py: async on-device test for IMU 90-degree turn accuracy (±5 degrees)
- Created gate4_sensors.py: async on-device smoke test verifying all three sensors return valid data types

## Task Commits

Each task was committed atomically:

1. **Task 1: IMU HAL + heading tracker + LED controller** — `e02d70d` (feat)
2. **Task 2: Sensor drivers + wire sensor_task + gate scripts** — `c8de8f3` (feat)

**Plan metadata:** (added in final commit)

## Files Created/Modified

- `hal/imu.py` — IMUHAL wraps lib/mpu6050.py; HeadingTracker integrates gyro Z at 100Hz with ticks_diff() dt measurement
- `hal/leds.py` — StatusLED with state colours (green/blue/red), async pulse_loop(), buzzer_beep() blocking boot tone
- `hal/sensors.py` — IRLineSensor (ADC multi-channel), UltrasonicSensor (HC-SR04 async echo), ColorSensor (I2C TCS34725 + analog fallback)
- `tasks/sensor_task.py` — Full rewrite: real sensor instances, _sensor_state populated with ir/distance_cm/color/heading, set_heading_tracker() injection
- `config.py` — Added IR_PINS=[28], ULTRASONIC_TRIG=2, ULTRASONIC_ECHO=3, COLOR_ANALOG_PIN=None (with hardware notes)
- `gates/gate3_turn_angle.py` — Async 90-degree turn test; PASS if heading within ±5 degrees of 90
- `gates/gate4_sensors.py` — All-sensor smoke test; PASS if each sensor returns expected data type

## Decisions Made

- **NEOPIXEL_PIN not LED_PIN:** The plan spec referenced `config.LED_PIN` but config.py uses `config.NEOPIXEL_PIN`. Used the actual constant. Not a deviation — the plan noted to use whatever config.py has.
- **Single IR channel default:** Only GP28 is ADC-capable and free (GP26/27 used by encoders). Set `IR_PINS=[28]` as default with a comment explaining the constraint. For 3-channel line following, hardware with I2C multiplexer or digital comparator outputs will be needed.
- **HeadingTracker injection pattern:** sensor_task.py imports HeadingTracker but receives an instance via `set_heading_tracker()` rather than creating one — this avoids circular init dependencies since main.py is responsible for I2C init and IMU calibration before the event loop starts.
- **ColorSensor defaults to I2C mode:** `COLOR_ANALOG_PIN=None` in config.py means ColorSensor uses TCS34725 I2C by default. The sensor_task creates a new I2C instance for this (separate from main.py's I2C); on MicroPython, two I2C instances on the same bus/pins may need consolidation — noted as a wiring concern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Config] Added sensor pin constants to config.py**
- **Found during:** Task 2
- **Issue:** sensor_task.py and gate scripts need IR_PINS, ULTRASONIC_TRIG, ULTRASONIC_ECHO, COLOR_ANALOG_PIN from config.py — these did not exist
- **Fix:** Added sensor pin section to config.py with placeholder defaults and hardware notes
- **Files modified:** config.py
- **Commit:** c8de8f3

**2. [Rule 2 - Missing Critical Functionality] Added set_heading_tracker() injection**
- **Found during:** Task 2
- **Issue:** sensor_task.py needs a HeadingTracker instance but cannot create one at module load time (I2C init hasn't happened yet when the module is imported)
- **Fix:** Added `set_heading_tracker()` function — main.py calls this after IMU calibration, before starting the event loop
- **Files modified:** tasks/sensor_task.py
- **Commit:** c8de8f3

## Verification

Syntax check (all files pass):
```
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['hal/imu.py','hal/sensors.py','hal/leds.py','tasks/sensor_task.py','gates/gate3_turn_angle.py','gates/gate4_sensors.py']]"
```
Result: ALL SYNTAX OK

On-device verification (requires Pico W connected via USB):
```
mpremote run gates/gate4_sensors.py
mpremote run gates/gate3_turn_angle.py
```

## Next Phase Readiness

- Complete HAL layer: main.py and robot.py (Phase 2) can now access all hardware through clean async interfaces
- sensor_poll_loop() ready for Phase 2 — _sensor_state dict is the integration point
- HeadingTracker ready for Phase 2 movement API — wire via set_heading_tracker() in main.py
- gate4_sensors.py verifies sensor drivers are wired correctly before Phase 2 builds on them

---
*Phase: 01-firmware-foundation*
*Completed: 2026-03-03*

## Self-Check: PASSED

- FOUND: hal/imu.py
- FOUND: hal/leds.py
- FOUND: hal/sensors.py
- FOUND: tasks/sensor_task.py
- FOUND: config.py
- FOUND: gates/gate3_turn_angle.py
- FOUND: gates/gate4_sensors.py
- FOUND: .planning/phases/01-firmware-foundation/01-03-SUMMARY.md
- FOUND commit: e02d70d (Task 1)
- FOUND commit: c8de8f3 (Task 2)
- SYNTAX: ALL 6 files parse without errors (verified via python3 ast.parse)
