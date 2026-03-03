"""
motor_task.py — Async motor PID control coroutine (20Hz)

Runs as one of the three concurrent coroutines under uasyncio.
This stub prints tick messages to prove scheduling without requiring
real encoder hardware — Phase 2 replaces the stub body with full PID.

Exports:
  motor_pid_loop()   — coroutine, schedule with uasyncio.gather()
  get_target_rpm(side) — returns current target RPM for 'left' or 'right'
  set_target_rpm(side, rpm) — sets target RPM
"""

import uasyncio
import utime
from lib.motor import Motor
from lib.pid import PID
import config

# ── Module-level hardware instances ──────────────────────────────────────────
# Motor instances (safe to construct at import time — no PWM until drive() called)
_left_motor  = Motor(config.MOTOR_LEFT_A,  config.MOTOR_LEFT_B)
_right_motor = Motor(config.MOTOR_RIGHT_A, config.MOTOR_RIGHT_B)

# PID controllers — one per wheel
_left_pid  = PID(config.PID_KP, config.PID_KI, config.PID_KD)
_right_pid = PID(config.PID_KP, config.PID_KI, config.PID_KD)

# Shared target RPM state — written by external commands, read by PID loop
_target_rpm = {"left": 0.0, "right": 0.0}

# ── Public accessors ──────────────────────────────────────────────────────────

def get_target_rpm(side: str) -> float:
    """Return current target RPM for 'left' or 'right' motor."""
    return _target_rpm[side]


def set_target_rpm(side: str, rpm: float):
    """Set target RPM for 'left' or 'right' motor."""
    _target_rpm[side] = rpm


# ── Coroutine ─────────────────────────────────────────────────────────────────

async def motor_pid_loop():
    """
    Motor PID loop coroutine — runs at 20Hz (every 50ms).

    Stub behaviour: measures actual dt with utime.ticks_diff (Pitfall 4
    avoidance — actual elapsed time, not nominal interval) and prints
    'motor tick' every 5 iterations to show interleaving.

    Exception handling (Pitfall 2 avoidance): on any exception,
    brake both motors then re-raise so the caller gets the error.
    """
    interval_ms = 1000 // config.PID_LOOP_HZ  # 50 ms at 20Hz
    iteration   = 0
    last_tick   = utime.ticks_ms()

    while True:
        try:
            # Measure actual elapsed time (avoids RPM error if loop ran late)
            now = utime.ticks_ms()
            dt  = utime.ticks_diff(now, last_tick) / 1000.0  # seconds
            last_tick = now

            iteration += 1
            if iteration % 5 == 0:
                print("motor tick", iteration)

            # Stub: no encoder yet — PID computes against measured=0.0
            # Phase 2 replaces 0.0 with actual encoder RPM readings
            left_out  = _left_pid.compute(_target_rpm["left"],  0.0, dt if dt > 0 else 0.05)
            right_out = _right_pid.compute(_target_rpm["right"], 0.0, dt if dt > 0 else 0.05)

            # Only drive if non-zero target (stub: targets start at 0)
            if _target_rpm["left"] != 0.0:
                _left_motor.drive(left_out)
            if _target_rpm["right"] != 0.0:
                _right_motor.drive(right_out)

        except Exception as e:
            # Brake both motors before propagating — never leave motors running
            _left_motor.brake()
            _right_motor.brake()
            print("motor_task ERROR:", e)
            raise

        await uasyncio.sleep_ms(interval_ms)
