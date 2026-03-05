# Phase 1: Firmware Foundation - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an async MicroPython firmware with complete hardware abstraction for all sensors, motors, and safety systems on the Cytron Robo Pico W platform. This is the foundation every subsequent phase builds on. No HTTP server, no WiFi communication protocol, no block editor concerns — just the hardware layer and asyncio architecture.

Requirements: FW-01, FW-02, FW-03, FW-04, FW-05, FW-06, FW-07, FW-08

</domain>

<decisions>
## Implementation Decisions

### Asyncio architecture (FW-01)
- Replace v1's blocking `time.sleep` patterns with `uasyncio` cooperative tasks
- Core event loop manages: motor PID control, sensor polling, and a placeholder coroutine for the future WiFi server
- Validate with a 3-coroutine proof-of-concept before building feature drivers
- V1 library classes (Motor, MPU6050, PID) are clean and reusable — wrap/adapt for async, don't rewrite from scratch

### Motor control with encoders (FW-02, FW-08)
- Reuse v1 Motor class (`lib/motor.py`) — drive/brake/coast interface is solid
- Replace Python ISR-based encoder (`lib/encoder.py`) with RP2040 PIO state machines for hardware encoder counting — eliminates the 2,520+ interrupts/second overhead documented in pitfalls research
- Reuse v1 PID controller (`lib/pid.py`) — proven working with anti-windup
- PID loop runs as an async task at 20Hz (matching v1's PID_LOOP_HZ)

### IMU integration (FW-03)
- Reuse v1 MPU6050 driver (`lib/mpu6050.py`) — already has calibration, gyro Z optimization for heading
- Gyro Z integration for heading runs in the PID/motor task or its own coroutine
- Calibration happens at boot (robot must be stationary)

### Sensor drivers (FW-04, FW-05, FW-06)
- **Line following:** IR reflective sensors — driver needs to support multi-channel array (3-5 channels typical)
- **Obstacle detection:** Ultrasonic distance sensor (HC-SR04 style trigger/echo) or I2C ToF
- **Color/light:** RGB color sensor (I2C, e.g., TCS34725) or simpler analog light sensor
- Pin assignments: Use available GPIO from Robo Pico — GP2-GP5 and Grove/servo ports (GP12-GP15) are free
- Each sensor gets an async-compatible read method that doesn't block the event loop

### Safety / watchdog (FW-07)
- Hardware watchdog (`machine.WDT`) as last resort — resets entire device if firmware hangs
- Software timeout for student code execution — auto-stop motors after configurable timeout (default 30s)
- Motor speed cap in the HAL layer for K-8 safety
- If student code crashes, motors stop immediately but firmware stays running (no full reboot)

### LED/buzzer feedback
- 2 NeoPixels (GP18): Color-coded state indication (green=ready, blue=running, red=error, pulsing=connecting)
- Buzzer (GP22): Available for both system feedback (boot chime, error tone) and student block programs (play_tone)
- Buzzer has a mute switch on the Robo Pico — documented in Getting Started guide

### Claude's Discretion
- Exact asyncio task structure and inter-task communication patterns
- PIO assembly for encoder counting (implementation detail)
- Specific sensor pin assignments within available GPIO
- Motor speed cap percentage (research best practices for K-8 robotics)
- Boot sequence and calibration flow
- Whether to keep v1 gate scripts as test suite or build new verification tests

</decisions>

<specifics>
## Specific Ideas

- V1 `config.py` has the complete pin map for the Cytron Robo Pico platform — this is ground truth for hardware
- Cytron Robo Pico uses MX1515H motor driver — v1 Motor class already handles the truth table correctly
- Encoder constants: 6 magnetic pulses × 42:1 gearbox = 252 ticks/rev (1008 in quadrature)
- Wheel geometry: 65mm diameter, 150mm track width — already computed in config.py
- V1 gate9 demonstrates working drive_straight() and turn_angle() functions that integrate motors + encoders + IMU — good reference for the v2 movement API
- V1 gate6 PID tuning (kp=0.8, ki=0.3, kd=0.05) is a known-good starting point

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/motor.py`: Motor class with drive(speed), brake(), coast(), deinit() — clean, reuse directly
- `lib/mpu6050.py`: MPU6050 class with accel(), gyro(), gyro_z_calibrated(), calibrate_gyro_z() — solid, reuse directly
- `lib/pid.py`: PID class with compute(), reset(), set_gains() — proven, reuse directly
- `lib/encoder.py`: Encoder class — interface is good but ISR implementation needs PIO rewrite
- `config.py`: Complete hardware pin definitions, encoder constants, wheel geometry, PID defaults

### Established Patterns
- All v1 drivers use a consistent pattern: `__init__` configures hardware, methods return values, `deinit` cleans up
- Config constants are centralized in `config.py` — continue this pattern
- Gate scripts demonstrate the integration sequence: init → calibrate → run → cleanup

### Integration Points
- Phase 2 (Robot API) will consume the HAL drivers via a `robot.py` facade
- The async event loop started here will be extended by Phase 2's HTTP server coroutine
- Sensor read methods must return values without blocking, suitable for JSON serialization in Phase 2

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-firmware-foundation*
*Context gathered: 2026-03-03*
