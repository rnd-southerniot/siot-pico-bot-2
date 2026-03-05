# Phase 1: Firmware Foundation - Research

**Researched:** 2026-03-03
**Domain:** MicroPython async firmware on RP2040 (Pico W) with hardware abstraction
**Confidence:** HIGH (codebase is the primary source; v1 drivers are ground truth)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Asyncio architecture (FW-01)**
- Replace v1's blocking `time.sleep` patterns with `uasyncio` cooperative tasks
- Core event loop manages: motor PID control, sensor polling, and a placeholder coroutine for the future WiFi server
- Validate with a 3-coroutine proof-of-concept before building feature drivers
- V1 library classes (Motor, MPU6050, PID) are clean and reusable — wrap/adapt for async, don't rewrite from scratch

**Motor control with encoders (FW-02, FW-08)**
- Reuse v1 Motor class (`lib/motor.py`) — drive/brake/coast interface is solid
- Replace Python ISR-based encoder (`lib/encoder.py`) with RP2040 PIO state machines for hardware encoder counting — eliminates the 2,520+ interrupts/second overhead
- Reuse v1 PID controller (`lib/pid.py`) — proven working with anti-windup
- PID loop runs as an async task at 20Hz (matching v1's PID_LOOP_HZ)

**IMU integration (FW-03)**
- Reuse v1 MPU6050 driver (`lib/mpu6050.py`) — already has calibration, gyro Z optimization for heading
- Gyro Z integration for heading runs in the PID/motor task or its own coroutine
- Calibration happens at boot (robot must be stationary)

**Sensor drivers (FW-04, FW-05, FW-06)**
- Line following: IR reflective sensors, multi-channel array (3-5 channels)
- Obstacle detection: Ultrasonic (HC-SR04 style) or I2C ToF
- Color/light: RGB color sensor (I2C, e.g. TCS34725) or simpler analog
- Pin assignments: GP2-GP5 and Grove/servo ports (GP12-GP15) are free
- Each sensor gets an async-compatible read method that doesn't block the event loop

**Safety / watchdog (FW-07)**
- Hardware watchdog (`machine.WDT`) as last resort — resets entire device if firmware hangs
- Software timeout for student code execution — auto-stop motors after configurable timeout (default 30s)
- Motor speed cap in the HAL layer for K-8 safety
- If student code crashes, motors stop immediately but firmware stays running (no full reboot)

**LED/buzzer feedback**
- 2 NeoPixels (GP18): Color-coded state (green=ready, blue=running, red=error, pulsing=connecting)
- Buzzer (GP22): System feedback and student play_tone blocks
- Buzzer has a mute switch on the Robo Pico

### Claude's Discretion

- Exact asyncio task structure and inter-task communication patterns
- PIO assembly for encoder counting (implementation detail)
- Specific sensor pin assignments within available GPIO
- Motor speed cap percentage (research best practices for K-8 robotics)
- Boot sequence and calibration flow
- Whether to keep v1 gate scripts as test suite or build new verification tests

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FW-01 | Asyncio-based firmware architecture replacing v1 blocking loop | uasyncio task structure, `asyncio.create_task`, coroutine patterns documented below |
| FW-02 | Motor control with encoder feedback for precise distance movement | v1 Motor class reused; PIO encoder replaces ISR; PID async task at 20Hz |
| FW-03 | IMU-6050 integration for accurate turning | v1 mpu6050.py reused; gyro Z integration pattern documented below |
| FW-04 | Line following sensor support via IR sensors | Analog ADC read on MicroPython, async-safe non-blocking reads |
| FW-05 | Obstacle detection sensor support | HC-SR04 pulse timing pattern; async-safe with `uasyncio.sleep_ms` during echo wait |
| FW-06 | Light/color sensor support | I2C async-compatible read; TCS34725 or analog fallback |
| FW-07 | Hardware watchdog for exec() safety | `machine.WDT(timeout=8000)`, feed in main loop, software timeout pattern for motor stop |
| FW-08 | PIO state machines for hardware encoder counting | RP2040 PIO quadrature counter program documented below |
</phase_requirements>

---

## Summary

This phase builds on a solid v1 codebase. The Motor, MPU6050, and PID classes in `lib/` are production-quality and require no rewrite — the work is wrapping them in an async architecture and replacing the Python ISR encoder with a PIO state machine. The v1 gate scripts (`gates/gate0` through `gate9`) serve as an integration test reference and should be adapted into the v2 verification suite rather than discarded.

The most technically demanding task is the PIO quadrature encoder. The RP2040 has two PIO blocks with four state machines each — more than enough for two encoders. A standard PIO quadrature counter program is well-documented in the MicroPython/RP2040 ecosystem and can be ported directly. This eliminates the 4×252×RPM interrupts/second that caused the v1 ISR overhead at speed.

The async architecture uses `uasyncio` (MicroPython's asyncio subset). The critical constraint is that sensor reads and the PID loop must never call blocking `time.sleep()` — use `await uasyncio.sleep_ms()` instead. The WDT watchdog must be fed in the main loop coroutine; if the main loop hangs (runaway student code), the device resets within the WDT timeout.

**Primary recommendation:** Build and validate the 3-coroutine async skeleton first (motor PID task + sensor poll task + placeholder WiFi task), then layer in drivers one by one, running the gate-equivalent verification after each.

---

## Standard Stack

### Core (MicroPython built-ins — no installation needed)

| Library | Module | Purpose | Why Standard |
|---------|--------|---------|--------------|
| uasyncio | `import uasyncio` | Cooperative multitasking event loop | Built into MicroPython ≥1.19; the only async option on bare-metal Pico |
| machine.WDT | `from machine import WDT` | Hardware watchdog timer | RP2040 built-in; resets device on timeout |
| machine.Pin / PWM | `from machine import Pin, PWM` | GPIO and motor PWM | Built-in hardware abstraction |
| machine.I2C | `from machine import I2C` | IMU and I2C sensor bus | Built-in; used by existing MPU6050 driver |
| machine.ADC | `from machine import ADC` | Analog sensor reads | Built-in; for IR line sensors |
| rp2 (PIO) | `import rp2` | PIO state machine for encoders | RP2040-specific; `@rp2.asm_pio` decorator for PIO programs |
| neopixel | `import neopixel` | WS2812 RGB LED control | Built into MicroPython for Pico |

### Reused v1 Drivers (already in `lib/`)

| File | Class | Reuse Strategy |
|------|-------|---------------|
| `lib/motor.py` | `Motor` | Use as-is; `drive()`, `brake()`, `coast()` are blocking-free |
| `lib/mpu6050.py` | `MPU6050` | Use as-is; I2C reads are fast (<1ms); call from async task without await |
| `lib/pid.py` | `PID` | Use as-is; pure computation, no I/O |
| `lib/encoder.py` | `Encoder` | Replace ISR implementation with PIO; keep same public interface (`count()`, `reset()`, `delta()`, `rpm()`, `deinit()`) |
| `config.py` | constants | Use as ground truth for all pin assignments and constants |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PIO quadrature counter | Python ISR (current v1) | ISR works but generates 2,520+ interrupts/sec at speed; PIO offloads entirely to hardware |
| uasyncio cooperative tasks | threading / _thread | _thread exists on Pico but shares GIL constraints; uasyncio is the idiomatic MicroPython async pattern |
| machine.WDT | Software-only timeout | Software timeout only catches infinite loops if the main coroutine keeps running; hardware WDT catches full hangs |
| HC-SR04 ultrasonic | I2C ToF (VL53L0X) | ToF is more accurate but adds I2C address management complexity; HC-SR04 is simpler for K-8 |

---

## Architecture Patterns

### Recommended Project Structure

```
/                          # Pico W root (flashed via mpremote/Thonny)
├── main.py                # Entry point: init hardware, start event loop
├── config.py              # Pin map and constants (reuse v1 as-is)
├── hal/
│   ├── __init__.py
│   ├── encoder_pio.py     # PIO quadrature encoder (replaces lib/encoder.py)
│   ├── motors.py          # Thin async wrapper around v1 Motor class
│   ├── imu.py             # Thin async wrapper around v1 MPU6050 class
│   ├── sensors.py         # IR line, ultrasonic, color — async read methods
│   └── leds.py            # NeoPixel state machine + buzzer
├── tasks/
│   ├── motor_task.py      # Async PID control coroutine (20Hz)
│   ├── sensor_task.py     # Async sensor poll coroutine
│   └── wifi_task.py       # Placeholder coroutine (Phase 2 fills this)
├── safety/
│   └── watchdog.py        # WDT feed, software timeout, motor kill
├── lib/                   # v1 libraries (motor.py, mpu6050.py, pid.py retained)
└── gates/                 # Adapted v2 verification gate scripts
```

### Pattern 1: Async Task Structure

**What:** Three concurrent coroutines sharing state through module-level variables or a simple state object. No threading — cooperative scheduling via `await`.

**When to use:** This IS the architecture. Every feature is a coroutine or called from one.

```python
# main.py skeleton
import uasyncio
from tasks.motor_task import motor_pid_loop
from tasks.sensor_task import sensor_poll_loop
from tasks.wifi_task import wifi_placeholder
from safety.watchdog import WatchdogKeeper

async def main():
    wdt = WatchdogKeeper(timeout_ms=8000)
    await uasyncio.gather(
        motor_pid_loop(),
        sensor_poll_loop(),
        wifi_placeholder(),
        wdt.feed_loop(),
    )

uasyncio.run(main())
```

### Pattern 2: PIO Quadrature Encoder

**What:** RP2040 PIO state machine counts encoder pulses in hardware, zero CPU overhead.

**When to use:** Required — replaces v1 ISR encoder. Same public interface (`count()`, `reset()`).

```python
# hal/encoder_pio.py
import rp2
from machine import Pin

@rp2.asm_pio()
def quadrature_program():
    # Standard RP2040 PIO quadrature counter
    # Reads both channels; increments/decrements X register
    # Pushes count to RX FIFO on request
    wrap_target()
    mov(x, isr)           # load current count
    in_(pins, 2)          # read A and B
    mov(y, isr)           # save new state
    jmp(x_not_y, "count") # changed? count
    jmp("read")           # no change
    label("count")
    # direction logic via jump conditions
    wrap()

class EncoderPIO:
    """PIO quadrature encoder — same interface as v1 Encoder."""
    def __init__(self, pin_a: int, pin_b: int, sm_id: int = 0):
        self._sm = rp2.StateMachine(
            sm_id,
            quadrature_program,
            in_base=Pin(pin_a),
            freq=1_000_000,
        )
        self._sm.active(1)
        self._count = 0

    def count(self) -> int:
        # Drain FIFO and accumulate
        while self._sm.rx_fifo():
            self._count += self._sm.get()
        return self._count

    def reset(self):
        self._count = 0

    def deinit(self):
        self._sm.active(0)
```

NOTE: The PIO assembly above is illustrative. The actual working program from the MicroPython RP2040 examples repository should be used verbatim — see Sources section. The exact assembly matters for correct direction detection.

### Pattern 3: Non-Blocking Sensor Read

**What:** Every sensor read in an async context uses `await uasyncio.sleep_ms(0)` or a timed sleep — never `time.sleep()`.

```python
# hal/sensors.py
import uasyncio
from machine import Pin, ADC

class IRLineSensor:
    def __init__(self, pins: list[int]):
        self._adcs = [ADC(Pin(p)) for p in pins]

    async def read_all(self) -> list[int]:
        """Returns 0-65535 per channel. Non-blocking."""
        await uasyncio.sleep_ms(0)  # yield to event loop
        return [adc.read_u16() for adc in self._adcs]

class UltrasonicSensor:
    def __init__(self, trig_pin: int, echo_pin: int):
        self._trig = Pin(trig_pin, Pin.OUT)
        self._echo = Pin(echo_pin, Pin.IN)

    async def read_cm(self) -> float:
        """Measure distance. Awaits echo — non-blocking."""
        self._trig.value(0)
        await uasyncio.sleep_ms(2)
        self._trig.value(1)
        await uasyncio.sleep_ms(0)  # 10us pulse (yields once)
        self._trig.value(0)
        # Time echo pulse
        start = utime.ticks_us()
        while self._echo.value() == 0:
            await uasyncio.sleep_ms(0)
            if utime.ticks_diff(utime.ticks_us(), start) > 30000:
                return -1.0  # timeout
        pulse_start = utime.ticks_us()
        while self._echo.value() == 1:
            await uasyncio.sleep_ms(0)
            if utime.ticks_diff(utime.ticks_us(), pulse_start) > 30000:
                return -1.0
        duration_us = utime.ticks_diff(utime.ticks_us(), pulse_start)
        return duration_us / 58.0
```

### Pattern 4: Watchdog + Software Motor Kill

**What:** Two-layer safety: hardware WDT resets device if firmware hangs; software timeout stops motors if student code runs too long.

```python
# safety/watchdog.py
from machine import WDT
import uasyncio

class WatchdogKeeper:
    def __init__(self, timeout_ms: int = 8000):
        # WDT timeout must be 1000-8388 ms on RP2040
        self._wdt = WDT(timeout=timeout_ms)
        self._motor_timeout_s = 30
        self._motor_start_time = None

    async def feed_loop(self):
        """Feed WDT every 4s. If this coroutine stops running, device resets."""
        while True:
            self._wdt.feed()
            await uasyncio.sleep_ms(4000)

    def arm_motor_timeout(self):
        import utime
        self._motor_start_time = utime.time()

    def check_motor_timeout(self, stop_fn):
        """Call from motor task. Stops motors after timeout."""
        import utime
        if self._motor_start_time is None:
            return
        if utime.time() - self._motor_start_time > self._motor_timeout_s:
            stop_fn()  # calls motor.brake() on both motors
            self._motor_start_time = None
```

### Pattern 5: Motor PID Async Task

**What:** 20Hz PID loop as a coroutine. Reads encoder, computes PID, drives motor.

```python
# tasks/motor_task.py
import uasyncio
from lib.pid import PID
from hal.encoder_pio import EncoderPIO
from lib.motor import Motor
import config

_left_motor = Motor(config.MOTOR_LEFT_A, config.MOTOR_LEFT_B)
_right_motor = Motor(config.MOTOR_RIGHT_A, config.MOTOR_RIGHT_B)
_left_enc = EncoderPIO(config.ENC_LEFT_A, config.ENC_LEFT_B, sm_id=0)
_right_enc = EncoderPIO(config.ENC_RIGHT_A, config.ENC_RIGHT_B, sm_id=1)
_left_pid = PID(config.PID_KP, config.PID_KI, config.PID_KD)
_right_pid = PID(config.PID_KP, config.PID_KI, config.PID_KD)

_target_rpm = {"left": 0.0, "right": 0.0}

async def motor_pid_loop():
    interval_ms = 1000 // config.PID_LOOP_HZ  # 50ms at 20Hz
    while True:
        dt = interval_ms / 1000.0
        left_rpm = _left_enc.rpm(dt)
        right_rpm = _right_enc.rpm(dt)
        left_out = _left_pid.compute(_target_rpm["left"], left_rpm, dt)
        right_out = _right_pid.compute(_target_rpm["right"], right_rpm, dt)
        _left_motor.drive(left_out)
        _right_motor.drive(right_out)
        await uasyncio.sleep_ms(interval_ms)
```

### Anti-Patterns to Avoid

- **`time.sleep()` in any async context:** Blocks the entire event loop. Every wait must be `await uasyncio.sleep_ms()`.
- **ISR modifying shared data without atomic access:** PIO eliminates this for encoders. For any remaining ISR use (buttons), use a flag, not a list or dict.
- **WDT timeout too short:** MicroPython I2C operations can take 2-5ms; boot calibration takes ~1s. Set WDT to 8000ms (max safe), feed every 4s. Do NOT start the WDT before boot calibration completes.
- **Creating `uasyncio.gather()` inside a loop:** Create all tasks once at startup. Re-creating tasks leaks resources on Pico's constrained heap.
- **Blocking I2C in hot path:** MPU6050 I2C reads are ~0.5ms at 400kHz. At 20Hz they are fine. If polling faster than 50Hz, benchmark first.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PIO quadrature counting | Custom assembly from scratch | Port the official MicroPython RP2040 PIO quadrature example | Direction detection edge cases are subtle; the community example is battle-tested |
| PID control | Custom PID | `lib/pid.py` (v1, already has anti-windup) | Anti-windup integral clamping is the hard part; v1 has it working |
| NeoPixel WS2812 driver | Bit-bang timing | `neopixel` built-in MicroPython module | Timing is hardware-critical; built-in uses PIO |
| Event loop | Custom scheduler | `uasyncio` | uasyncio IS the standard; implementing your own cooperative scheduler is a rewrite of the platform |
| I2C MPU6050 register parsing | Custom byte manipulation | `lib/mpu6050.py` (v1, already calibrated) | Calibration drift math and register sequencing are subtle; v1 works |

**Key insight:** This phase is integration work, not invention. The hard problems (PID math, I2C protocol, motor H-bridge timing) are already solved in v1. The work is wiring them into an async architecture.

---

## Common Pitfalls

### Pitfall 1: WDT Started Before Boot Calibration

**What goes wrong:** MPU6050 gyro calibration takes ~1 second of stationary sampling. If WDT is armed before calibration, it may reset the device mid-calibration (or calibration extends past the feed interval).

**Why it happens:** WDT is often initialized at top of `main.py` before any other setup.

**How to avoid:** Complete all boot-time initialization (I2C scan, MPU6050 calibration, PIO setup) BEFORE calling `WDT(timeout=8000)`. Or: start WDT with a long timeout, feed it once immediately after calibration completes.

**Warning signs:** Device resets ~1s into boot; calibration never completes.

### Pitfall 2: uasyncio `gather()` Stops on First Exception

**What goes wrong:** If `sensor_poll_loop()` raises an unhandled exception, `gather()` cancels ALL tasks including the motor PID loop. Motors freeze in last state (or keep running if not braked).

**Why it happens:** `asyncio.gather()` propagates the first exception and cancels siblings.

**How to avoid:** Wrap each task body in `try/except Exception` and log the error. Ensure motor brake is called in the except block. Use a task restart pattern if needed.

**Warning signs:** Rover drives away when a sensor read fails.

### Pitfall 3: PIO State Machine ID Conflicts

**What goes wrong:** RP2040 has 2 PIO blocks × 4 state machines = 8 total. NeoPixel built-in uses PIO. If encoder PIO programs claim the same SM IDs, conflicts occur at runtime (silent wrong behavior or crash).

**Why it happens:** MicroPython's `neopixel` module claims PIO resources automatically. PIO SM IDs must be assigned carefully.

**How to avoid:** Check which SM IDs MicroPython's neopixel claims (typically PIO block 0, SM 0). Assign encoder SMs to PIO block 1 (SM IDs 4-7 in some MicroPython builds) or non-conflicting IDs. Test NeoPixel and encoder simultaneously on the bench before assuming compatibility.

**Warning signs:** Encoders count wrong or NeoPixels flicker after encoder init.

### Pitfall 4: `rpm()` Called with Wrong `dt` in Async Context

**What goes wrong:** `rpm()` divides tick delta by `dt`. If the task runs late (event loop was busy), `dt` based on expected interval is wrong — RPM appears too low, PID overdrives.

**Why it happens:** `await uasyncio.sleep_ms(50)` sleeps AT LEAST 50ms, not exactly 50ms.

**How to avoid:** Measure actual elapsed time with `utime.ticks_diff(utime.ticks_ms(), last_tick)` rather than using the nominal interval as `dt`.

### Pitfall 5: Motor Speed Cap Placement

**What goes wrong:** Speed cap implemented in the task layer can be bypassed by Phase 2 code that calls Motor directly. Cap provides false safety guarantee.

**Why it happens:** Cap is added as a convenience, not enforced at hardware boundary.

**How to avoid:** Apply speed cap inside `Motor.drive()` itself — the hardware abstraction layer. This makes it impossible to bypass regardless of what calls the motor. For K-8, 70% PWM max is a reasonable starting point (reduces impact energy while keeping responsive movement).

### Pitfall 6: HC-SR04 Echo Timeout Blocks Event Loop

**What goes wrong:** Naive HC-SR04 implementations spin-wait for the echo pin with a `while` loop and no `await`. This blocks the event loop for up to 30ms on each read.

**Why it happens:** Copy-pasted examples from blocking MicroPython tutorials.

**How to avoid:** Echo wait loop must `await uasyncio.sleep_ms(0)` on each iteration. See Pattern 3 above. Limit poll rate to 10Hz max for ultrasonic (HC-SR04 needs 60ms between triggers anyway).

---

## Code Examples

### Gate-Equivalent v2 Verification Pattern

```python
# gates/gate1_async_skeleton.py — Verify 3-coroutine proof-of-concept
import uasyncio

async def task_a():
    for i in range(5):
        print(f"A {i}")
        await uasyncio.sleep_ms(100)

async def task_b():
    for i in range(5):
        print(f"B {i}")
        await uasyncio.sleep_ms(150)

async def task_c():
    for i in range(3):
        print(f"C {i}")
        await uasyncio.sleep_ms(200)

async def main():
    await uasyncio.gather(task_a(), task_b(), task_c())
    print("PASS: All 3 tasks completed without blocking")

uasyncio.run(main())
# Expected: interleaved A/B/C output proving cooperative scheduling
```

### Gyro Z Heading Integration

```python
# From v1 gate7 — adapt into async task
import utime
import uasyncio

class HeadingTracker:
    def __init__(self, imu):
        self._imu = imu
        self._heading = 0.0
        self._last_t = utime.ticks_ms()

    async def update_loop(self):
        while True:
            now = utime.ticks_ms()
            dt = utime.ticks_diff(now, self._last_t) / 1000.0
            self._last_t = now
            gz = self._imu.gyro_z_calibrated()  # deg/s
            self._heading += gz * dt
            await uasyncio.sleep_ms(10)  # 100Hz heading update

    def get_heading(self) -> float:
        return self._heading

    def reset(self):
        self._heading = 0.0
```

### Boot Sequence (Safe WDT Pattern)

```python
# main.py boot sequence
from machine import I2C, Pin
import config
from lib.mpu6050 import MPU6050

# 1. Hardware init (no WDT yet)
i2c = I2C(config.I2C_ID, sda=Pin(config.I2C_SDA), scl=Pin(config.I2C_SCL), freq=config.I2C_FREQ)
imu = MPU6050(i2c)

# 2. Calibration (blocks ~1s — OK, WDT not started)
print("Calibrating IMU — keep robot still...")
imu.calibrate_gyro_z(samples=200)
print("Calibration done")

# 3. NOW start WDT
from machine import WDT
wdt = WDT(timeout=8000)
wdt.feed()

# 4. Start async event loop
import uasyncio
uasyncio.run(main_async())
```

---

## State of the Art

| Old Approach (v1) | Current Approach (v2) | Impact |
|-------------------|-----------------------|--------|
| `time.sleep()` blocking loop in `main.py` | `uasyncio` cooperative tasks | Motor, sensors, WiFi can run concurrently |
| Python ISR encoder (`lib/encoder.py`) | RP2040 PIO state machine | Eliminates ~2,520 interrupts/sec at 60 RPM; zero CPU overhead |
| Single-file `gates/` scripts | Modular `hal/` + `tasks/` + `safety/` | Phase 2 can add HTTP server as a new task without touching hardware code |
| No safety layer | `machine.WDT` + software motor timeout | Runaway student code stops within 500ms instead of requiring power cycle |

**Still valid from v1:**
- Motor drive/brake/coast interface (MX1515H truth table correctly implemented)
- MPU6050 calibration approach (gyro Z drift compensation at boot)
- PID gains (kp=0.8, ki=0.3, kd=0.05) — proven starting point, may need tuning per-unit
- Encoder constants: 252 ticks/rev single-phase, 1008 quadrature

---

## Open Questions

1. **PIO NeoPixel SM ID conflict**
   - What we know: MicroPython's `neopixel` module uses PIO; encoder PIO needs 2 SMs (one per wheel)
   - What's unclear: Exact SM IDs claimed by the MicroPython neopixel implementation in the current Pico W firmware build
   - Recommendation: Test neopixel + 2 encoder SMs on bench as the first integration test in Wave 1. If conflict found, use PIO block 1 for encoders (sm_id 4-7).

2. **Sensor hardware confirmation**
   - What we know: The context specifies IR line, ultrasonic/ToF, and color sensor — but specific hardware SKUs are not confirmed
   - What's unclear: Whether the actual sensors in the kit are HC-SR04 or a different ultrasonic; whether color is TCS34725 or analog
   - Recommendation: The planner should scope sensor driver tasks as "implement driver for [sensor type]" with a note to confirm exact SKU. Drivers should use `config.py` pin constants that can be updated.

3. **Motor speed cap value for K-8**
   - What we know: Cap should be applied in Motor.drive(); purpose is collision safety in classrooms
   - What's unclear: Whether 70% is right or if a lower cap (50-60%) is more appropriate
   - Recommendation: Default to 70% cap (still fast enough to be engaging); make it a `config.py` constant `MOTOR_MAX_SPEED_PCT = 70` so it can be tuned per school environment.

4. **v1 gate scripts: adapt or replace**
   - What we know: Gates 0-9 cover all major hardware components and provide a proven verification sequence
   - What's unclear: Whether to adapt gate scripts directly (quick) or build a formal pytest/unittest suite (better long-term)
   - Recommendation: Adapt gates as v2 scripts for now; they run on-device which is the right test environment for firmware. A host-side test framework would require mocking the entire MicroPython hardware API.

---

## Validation Architecture

> Firmware runs on-device (Pico W). No host-side test runner is viable for hardware validation. Tests are gate scripts run via `mpremote run gates/gateN_name.py`.

### Test Approach

| Property | Value |
|----------|-------|
| Framework | On-device gate scripts (MicroPython) run via `mpremote` |
| Quick run command | `mpremote run gates/gate1_async_skeleton.py` |
| Full suite command | `mpremote run gates/run_all.py` (to be created) |
| Hardware required | Pico W connected via USB |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Gate Script | Notes |
|--------|----------|-----------|-------------|-------|
| FW-01 | 3 concurrent tasks run without blocking | smoke | `gate1_async_skeleton.py` | Interleaved output proves cooperative scheduling |
| FW-02 | Motor drives precise distance via encoder feedback | integration | `gate2_motor_distance.py` | Drive 500mm, measure actual; encoder delta check |
| FW-03 | Turn accurate angle via IMU (±5 deg) | integration | `gate3_turn_angle.py` | 90-degree turn, read final heading |
| FW-04 | IR line sensor returns readings on all channels | smoke | `gate4_sensors.py` | Print ADC values for each channel |
| FW-05 | Ultrasonic distance returns valid reading | smoke | `gate4_sensors.py` | Print distance_cm, check > 0 |
| FW-06 | Color sensor returns RGBC values | smoke | `gate4_sensors.py` | Print color tuple |
| FW-07 | WDT stops rover within 500ms on hang | integration | `gate5_watchdog.py` | Simulate hang, verify reset or motor stop |
| FW-08 | PIO encoder counts match expected ticks | unit | `gate6_pio_encoder.py` | Hand-rotate wheel N turns, count ticks |

### Wave 0 Gaps

- [ ] `gates/gate1_async_skeleton.py` — 3-coroutine proof-of-concept (new)
- [ ] `gates/gate2_motor_distance.py` — async motor+encoder+PID distance test (new)
- [ ] `gates/gate3_turn_angle.py` — async IMU heading turn test (new)
- [ ] `gates/gate4_sensors.py` — all sensor reads in one script (new)
- [ ] `gates/gate5_watchdog.py` — WDT + software timeout verification (new)
- [ ] `gates/gate6_pio_encoder.py` — PIO tick count validation (new)
- [ ] `gates/run_all.py` — sequential runner that stops on first failure (new)

Note: v1 gates (gate3_motors, gate4_encoders, etc.) are reference material, not reusable as-is — they use blocking patterns incompatible with the v2 async architecture.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `config.py` — Ground truth for all pin assignments, encoder constants, wheel geometry, PID gains
- `lib/motor.py` — Motor class implementation; confirmed drive/brake/coast interface
- `lib/encoder.py` — v1 ISR encoder; confirmed interface to preserve for PIO replacement
- `lib/mpu6050.py` — Confirmed calibrate_gyro_z() and gyro_z_calibrated() API
- `lib/pid.py` — Confirmed PID.compute() interface
- `gates/gate6_pid_speed.py`, `gates/gate9_autonomous.py` — Reference for proven integration patterns

### Secondary (MEDIUM confidence)

- RP2040 Datasheet / MicroPython PIO docs — PIO state machine architecture; 2 blocks × 4 SMs; `@rp2.asm_pio` decorator pattern is standard MicroPython
- MicroPython `machine.WDT` docs — timeout range 1000-8388ms on RP2040; `wdt.feed()` pattern
- MicroPython `uasyncio` — `gather()`, `sleep_ms()`, `create_task()` are standard in MicroPython ≥1.19

### Tertiary (LOW confidence — verify during implementation)

- PIO NeoPixel SM ID allocation — community reports suggest PIO0/SM0; needs bench verification
- HC-SR04 async echo pattern — adapted from community MicroPython examples; needs timing validation on actual hardware
- 70% motor speed cap for K-8 — engineering judgment; no published standard found

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — built-in MicroPython modules; v1 code is the source of truth
- Architecture: HIGH — patterns derived directly from v1 codebase and RP2040 constraints
- Pitfalls: HIGH (WDT/calibration, gather exception, speed cap) / MEDIUM (PIO SM conflict, rpm dt drift) — based on known MicroPython constraints
- Validation approach: HIGH — on-device gate scripts are the only viable approach; host mocking not practical for bare-metal firmware

**Research date:** 2026-03-03
**Valid until:** 2026-09-03 (MicroPython API is stable; RP2040 PIO architecture won't change)
