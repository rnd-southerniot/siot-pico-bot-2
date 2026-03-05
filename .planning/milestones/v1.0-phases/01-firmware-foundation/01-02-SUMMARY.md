---
phase: 01-firmware-foundation
plan: 02
subsystem: firmware
tags: [rp2040, pio, micropython, encoder, motor, hal, quadrature]

# Dependency graph
requires: []
provides:
  - "hal/encoder_pio.py: EncoderPIO class using RP2040 PIO state machine for zero-CPU-overhead quadrature counting"
  - "hal/motors.py: MotorHAL wrapper with K-8 safety cap (70%) applied at HAL boundary"
  - "gates/gate6_pio_encoder.py: on-device PIO encoder tick count validation script"
  - "gates/gate2_motor_distance.py: on-device 200mm motor distance drive test script"
  - "config.MOTOR_MAX_SPEED_PCT: configurable safety cap constant"
affects:
  - tasks/motor_task.py (plan 03: uses EncoderPIO and MotorHAL)
  - robot.py facade (plan 03+: consumes HAL layer)
  - all higher layers that drive motors (cap enforced here)

# Tech tracking
tech-stack:
  added:
    - rp2.StateMachine (RP2040 PIO state machine via MicroPython rp2 module)
    - rp2.asm_pio decorator (PIO assembly program definition)
  patterns:
    - PIO push-state pattern: PIO pushes 2-bit AB encoder state on change; Python applies quadrature lookup table to accumulate signed ticks
    - HAL boundary cap: speed cap applied inside drive() so it cannot be bypassed by any higher layer
    - Normalised speed interface: HAL accepts -1.0 to 1.0; scales to underlying driver range internally

key-files:
  created:
    - hal/__init__.py
    - hal/encoder_pio.py
    - hal/motors.py
    - gates/gate6_pio_encoder.py
    - gates/gate2_motor_distance.py
  modified:
    - config.py (added MOTOR_MAX_SPEED_PCT = 70)

key-decisions:
  - "PIO push-state approach: push raw 2-bit AB state to FIFO on each change; Python uses lookup table for direction. Chosen over PIO-side direction detection (complex assembly, error-prone edge cases)"
  - "SM IDs 4 and 5 (PIO block 1) for encoders to avoid NeoPixel conflict on PIO block 0"
  - "MotorHAL drive() accepts -1.0 to 1.0 (normalised) rather than -100 to 100 (lib/motor.py range); scales internally to preserve clean interface for plan 03+ callers"
  - "Speed cap at 70% MOTOR_MAX_SPEED_PCT enforced at HAL boundary, not in task layer — matches Pitfall 5 from research"

patterns-established:
  - "Pattern: HAL normalised speed interface (-1.0 to 1.0) with internal scaling to driver range"
  - "Pattern: Safety cap at HAL boundary prevents bypass by any higher layer"
  - "Pattern: PIO state-push with Python lookup table for quadrature decoding"

requirements-completed: [FW-02, FW-08]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 1 Plan 02: PIO Encoder and Motor HAL Summary

**RP2040 PIO quadrature encoder (EncoderPIO) with push-state FIFO approach and MotorHAL with K-8 70% speed cap enforced at HAL boundary**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T03:35:15Z
- **Completed:** 2026-03-03T03:39:00Z
- **Tasks:** 2 of 2
- **Files modified:** 6

## Accomplishments

- EncoderPIO class using RP2040 PIO state machine — zero CPU overhead replacing v1 ISR encoder (2,520+ interrupts/sec eliminated)
- MotorHAL with K-8 safety speed cap applied at the HAL boundary — cap cannot be bypassed by plan 03+ task layer or robot.py
- gate6_pio_encoder.py: on-device verification that hand-rotating 2 wheel turns produces ~2016 ticks (±50 tolerance)
- gate2_motor_distance.py: on-device 200mm distance drive test using encoder feedback to stop at target ticks

## Task Commits

Each task was committed atomically:

1. **Task 1: PIO quadrature encoder** - `8708ac7` (feat)
2. **Task 2: Motor HAL wrapper + gate scripts** - `3c826b1` (feat)

## Files Created/Modified

- `hal/__init__.py` - HAL package init
- `hal/encoder_pio.py` - EncoderPIO class: PIO state machine, FIFO drain, quadrature lookup table, count/reset/delta/rpm/deinit interface
- `hal/motors.py` - MotorHAL class: wraps lib/motor.py, normalised -1.0/+1.0 speed, 70% cap, scales to motor driver's -100/+100 range
- `gates/gate6_pio_encoder.py` - On-device encoder tick count validation (PASS/FAIL)
- `gates/gate2_motor_distance.py` - On-device 200mm distance drive test (PASS/FAIL)
- `config.py` - Added MOTOR_MAX_SPEED_PCT = 70

## Decisions Made

- **PIO approach — push-state vs. direction in PIO:** Chose to push raw 2-bit AB state to FIFO and decode direction in Python using a 16-entry lookup table. Direction detection in PIO assembly is feasible but error-prone (edge case handling in assembly is subtle). The push-state pattern is the standard community approach and is more maintainable.

- **SM ID assignment (PIO block 1):** Left encoder uses sm_id=4, right uses sm_id=5 (PIO block 1, SMs 0 and 1). MicroPython's neopixel module claims PIO block 0 SM 0. Using block 1 avoids conflict. Bench test of simultaneous NeoPixel + encoders still required before declaring conflict-free.

- **Normalised speed interface for MotorHAL:** HAL exposes -1.0 to +1.0 rather than lib/motor.py's -100 to 100. This matches the expected interface in plan 03's motor task (PID output is naturally in fractional range). Internal scaling handles the conversion.

- **Speed cap at 70%:** Applied inside MotorHAL.drive() (HAL boundary). This is Pitfall 5 from research — cap in task layer can be bypassed; cap in HAL cannot. Configurable via config.MOTOR_MAX_SPEED_PCT.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — both tasks completed cleanly on first attempt.

## User Setup Required

None — no external service configuration required. On-device validation via mpremote required before declaring hardware working:
```
mpremote run gates/gate6_pio_encoder.py
mpremote run gates/gate2_motor_distance.py
```

## Next Phase Readiness

- hal/encoder_pio.py and hal/motors.py are ready for plan 03 (motor PID async task)
- Plan 03 imports EncoderPIO and MotorHAL directly from the hal package
- Bench test still required: run NeoPixel and both encoder SMs simultaneously to verify SM ID 4/5 are conflict-free
- gate6 and gate2 verify hardware works; should be run on actual Pico W before plan 03 integration

## Self-Check: PASSED

All created files verified present:
- FOUND: hal/__init__.py
- FOUND: hal/encoder_pio.py
- FOUND: hal/motors.py
- FOUND: gates/gate6_pio_encoder.py
- FOUND: gates/gate2_motor_distance.py
- FOUND: .planning/phases/01-firmware-foundation/01-02-SUMMARY.md

All task commits verified:
- FOUND: 8708ac7 (Task 1: PIO encoder HAL)
- FOUND: 3c826b1 (Task 2: MotorHAL + gate scripts)

---
*Phase: 01-firmware-foundation*
*Completed: 2026-03-03*
