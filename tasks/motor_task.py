"""
motor_task.py — Async motor PID control coroutine (20Hz)

Runs as one of the three concurrent coroutines under uasyncio.
Uses PIO quadrature encoders (EncoderPIO) as the measured RPM for PID
feedback — closing the control loop with real encoder data (FW-02).

Exports:
  motor_pid_loop()      — coroutine, schedule with uasyncio.gather()
  get_target_rpm(side)  — returns current target RPM for 'left' or 'right'
  set_target_rpm(side, rpm) — sets target RPM
  set_drive_targets(left, right) — sets both target RPMs together
  stop_motion()         — clears distance goals and stops both motors
  submit_distance_goal(distance_cm, rpm, tolerance_cm, timeout_s)
                        — non-blocking encoder-distance goal submission
  submit_turn_goal(angle_deg, rpm, tolerance_deg, timeout_s)
                        — non-blocking heading-turn goal submission
  set_watchdog(wdg)     — injects WatchdogKeeper after creation in main.py
"""

import uasyncio
import utime
from hal.motors import MotorHAL
from lib.pid import PID
from hal.encoder_pio import EncoderPIO
import config

# ── Module-level hardware instances ──────────────────────────────────────────
# MotorHAL wraps lib/motor.py with normalised -1.0..1.0 interface and 70% speed cap.
_left_motor = None
_right_motor = None

# PIO quadrature encoders — PIO block 1 (SM IDs 4 & 5) to avoid NeoPixel conflict.
# Pins must be consecutive: ENC_LEFT_A/B = GP6/GP7, ENC_RIGHT_A/B = GP26/GP27.
# SM IDs 4/5 = PIO block 1; NeoPixel on PIO block 0 SM 0 (no conflict).
_left_enc = None
_right_enc = None

# PID controllers — one per wheel
_left_pid = None
_right_pid = None

# Shared target RPM state — written by external commands, read by PID loop
_target_rpm = {"left": 0.0, "right": 0.0}

# Measured RPM state — written by PID loop, read by status endpoint
_actual_rpm = {"left": 0.0, "right": 0.0}

# Internal encoder-distance goal state. This remains private to motor_task so
# the student-facing API and HTTP status schema do not grow new motion fields.
_distance_goal = None
_turn_goal = None

# WatchdogKeeper — injected by main.py via set_watchdog() after WDT creation.
# None until set; check_motor_timeout / emergency_stop are no-ops when None.
_watchdog = None

# Tick tracking for actual dt measurement (Pitfall 4: use measured dt, not nominal)
_last_tick_ms = utime.ticks_ms()


def initialize_motors():
    """
    Explicitly construct motor hardware and PID controllers after boot wiring.

    Idempotent and all-or-nothing: module globals are only published after all
    constructors succeed.
    """
    global _left_motor, _right_motor, _left_enc, _right_enc
    global _left_pid, _right_pid, _last_tick_ms

    if (
        _left_motor is not None
        and _right_motor is not None
        and _left_enc is not None
        and _right_enc is not None
        and _left_pid is not None
        and _right_pid is not None
    ):
        return

    left_motor = MotorHAL(config.MOTOR_LEFT_A, config.MOTOR_LEFT_B)
    right_motor = MotorHAL(config.MOTOR_RIGHT_A, config.MOTOR_RIGHT_B)
    left_enc = EncoderPIO(
        config.ENC_LEFT_A,
        config.ENC_LEFT_B,
        sm_id=4,
        invert=getattr(config, "ENC_LEFT_INVERT", False),
    )
    right_enc = EncoderPIO(
        config.ENC_RIGHT_A,
        config.ENC_RIGHT_B,
        sm_id=5,
        invert=getattr(config, "ENC_RIGHT_INVERT", False),
    )
    left_pid = PID(config.PID_KP, config.PID_KI, config.PID_KD)
    right_pid = PID(config.PID_KP, config.PID_KI, config.PID_KD)

    _left_motor = left_motor
    _right_motor = right_motor
    _left_enc = left_enc
    _right_enc = right_enc
    _left_pid = left_pid
    _right_pid = right_pid
    _last_tick_ms = utime.ticks_ms()


def _ensure_initialized():
    initialize_motors()


def _reset_pid_if_ready():
    """Reset PID integrators when actively stopping the drivetrain."""
    if _left_pid is not None:
        _left_pid.reset()
    if _right_pid is not None:
        _right_pid.reset()


def _brake_if_ready():
    """Brake motors immediately when hardware is already initialized."""
    if _left_motor is not None:
        _left_motor.brake()
    if _right_motor is not None:
        _right_motor.brake()


def _update_watchdog_for_targets():
    """Arm motor timeout when targets are non-zero; disarm when both are zero."""
    if _watchdog is None:
        return
    if _target_rpm["left"] != 0.0 or _target_rpm["right"] != 0.0:
        _watchdog.arm_motor_timeout()
    else:
        _watchdog.disarm_motor_timeout()


def _set_target_rpm_raw(side: str, rpm: float):
    """Update a single target RPM without distance-goal preemption."""
    _target_rpm[side] = rpm
    _update_watchdog_for_targets()


def _set_drive_targets_raw(left_rpm: float, right_rpm: float):
    """Update both target RPMs without distance-goal preemption."""
    _target_rpm["left"] = left_rpm
    _target_rpm["right"] = right_rpm
    _update_watchdog_for_targets()


def _clear_motion_goals(stop_motors: bool = False, clear_distance: bool = True, clear_turn: bool = True):
    """Drop active motion goals and optionally stop immediately."""
    global _distance_goal, _turn_goal
    if clear_distance:
        _distance_goal = None
    if clear_turn:
        _turn_goal = None
    if stop_motors:
        _set_drive_targets_raw(0.0, 0.0)
        _reset_pid_if_ready()
        _brake_if_ready()


def _read_heading_snapshot(require_numeric: bool = False):
    """
    Read the current heading from sensor_task without a top-level import.

    Returns the numeric heading when available. If require_numeric is False and
    heading is unavailable/non-numeric, returns None so the caller can defer to
    timeout handling.
    """
    import tasks.sensor_task as sensor_task

    state = sensor_task.get_sensor_state()
    heading = state.get("heading")
    if isinstance(heading, bool) or not isinstance(heading, (int, float)):
        if require_numeric:
            raise RuntimeError("Heading unavailable for turn control")
        return None
    return float(heading)

# ── Public accessors ──────────────────────────────────────────────────────────

def get_target_rpm(side: str) -> float:
    """Return current target RPM for 'left' or 'right' motor."""
    return _target_rpm[side]


def get_actual_rpm(side: str) -> float:
    """Return measured RPM for 'left' or 'right' motor."""
    return _actual_rpm[side]


def set_target_rpm(side: str, rpm: float):
    """Set target RPM for 'left' or 'right' motor.

    Arms the software motor timeout when any wheel has a non-zero target,
    and disarms it when both wheels return to zero.
    """
    _clear_motion_goals()
    _set_target_rpm_raw(side, rpm)


def set_drive_targets(left_rpm: float, right_rpm: float):
    """Set both wheel targets together and cancel any active distance goal."""
    _clear_motion_goals()
    _set_drive_targets_raw(left_rpm, right_rpm)


def stop_motion():
    """Stop both wheels immediately and cancel any active distance goal."""
    _clear_motion_goals(stop_motors=True)


def cancel_distance_goal(stop_motors: bool = False):
    """Cancel the current distance goal without exposing goal state publicly."""
    _clear_motion_goals(stop_motors=stop_motors, clear_turn=False)


def cancel_turn_goal(stop_motors: bool = False):
    """Cancel the current turn goal without exposing goal state publicly."""
    _clear_motion_goals(stop_motors=stop_motors, clear_distance=False)


def submit_distance_goal(distance_cm: float, rpm: float, tolerance_cm: float, timeout_s: float):
    """
    Submit a non-blocking encoder-distance goal.

    Positive distance drives forward; negative distance drives backward.
    The PID loop owns completion/timeout handling and will stop the motors and
    clear the goal on success or timeout.
    """
    global _distance_goal

    if distance_cm == 0:
        _clear_motion_goals(stop_motors=True)
        return

    try:
        _ensure_initialized()
    except Exception as exc:
        raise RuntimeError("Encoder distance control unavailable") from exc

    _clear_motion_goals()
    direction = 1.0 if distance_cm > 0 else -1.0
    ticks_per_cm = 10.0 / config.MM_PER_TICK
    target_ticks = abs(distance_cm) * ticks_per_cm
    tolerance_ticks = tolerance_cm * ticks_per_cm

    _distance_goal = {
        "direction": direction,
        "left_start_ticks": _left_enc.count(),
        "right_start_ticks": _right_enc.count(),
        "target_ticks": target_ticks,
        "tolerance_ticks": tolerance_ticks,
        "deadline_ms": utime.ticks_add(utime.ticks_ms(), int(timeout_s * 1000)),
    }
    _set_drive_targets_raw(direction * rpm, direction * rpm)


def submit_turn_goal(angle_deg: float, rpm: float, tolerance_deg: float, timeout_s: float):
    """
    Submit a non-blocking heading-turn goal.

    Positive angle turns clockwise/right; negative angle turns counterclockwise/left.
    The PID loop owns completion/timeout handling and will stop the motors and
    clear the goal on success or timeout.
    """
    global _turn_goal

    if angle_deg == 0:
        _clear_motion_goals(stop_motors=True)
        return

    start_heading = _read_heading_snapshot(require_numeric=True)
    _clear_motion_goals()

    direction = 1.0 if angle_deg > 0 else -1.0
    _turn_goal = {
        "direction": direction,
        "start_heading": start_heading,
        "target_degrees": abs(angle_deg),
        "tolerance_deg": tolerance_deg,
        "deadline_ms": utime.ticks_add(utime.ticks_ms(), int(timeout_s * 1000)),
    }
    _set_drive_targets_raw(direction * rpm, -direction * rpm)


def set_watchdog(wdg):
    """
    Inject the WatchdogKeeper instance created in main.py.

    Called once during boot after WatchdogKeeper construction and before
    the async event loop starts. Allows main.py to control WDT lifecycle
    (create after IMU calibration) while motor_task uses it for safety.

    Args:
        wdg: WatchdogKeeper instance, or None to clear.
    """
    global _watchdog
    _watchdog = wdg


# ── Coroutine ─────────────────────────────────────────────────────────────────

async def motor_pid_loop():
    """
    Motor PID loop coroutine — runs at 20Hz (every 50ms).

    Each iteration:
      1. Measures actual dt using utime.ticks_diff (Pitfall 4 avoidance —
         actual elapsed time, not nominal interval, avoids RPM overshoot).
      2. Reads actual RPM from PIO quadrature encoders (_left_enc, _right_enc).
      3. Computes PID correction using measured RPM as feedback (FW-02).
      4. Drives motors with PID output.
      5. Checks software motor timeout via WatchdogKeeper.

    Exception handling (Pitfall 2 avoidance): on any exception, brakes both
    motors and calls emergency_stop() before breaking the loop. gather() will
    propagate the exception; WDT will eventually reset if nothing else runs.
    """
    global _last_tick_ms

    _ensure_initialized()
    interval_ms = 1000 // config.PID_LOOP_HZ  # 50 ms at 20Hz
    iteration   = 0
    _last_tick_ms = utime.ticks_ms()

    while True:
        try:
            # ── Step 1: Measure actual elapsed time ───────────────────────────
            now = utime.ticks_ms()
            dt  = utime.ticks_diff(now, _last_tick_ms) / 1000.0  # seconds
            _last_tick_ms = now

            iteration += 1
            if iteration % 5 == 0:
                print("motor tick", iteration)

            # ── Step 2: Read actual RPM from PIO encoders ─────────────────────
            # Use measured dt (not nominal) to avoid RPM calculation error
            # when the event loop runs late (Pitfall 4 from research).
            left_rpm_actual  = _left_enc.rpm(dt)  if dt > 0 else 0.0
            right_rpm_actual = _right_enc.rpm(dt) if dt > 0 else 0.0
            _actual_rpm["left"]  = left_rpm_actual
            _actual_rpm["right"] = right_rpm_actual

            force_stop = False
            if _distance_goal is not None:
                direction = _distance_goal["direction"]
                left_progress = direction * (
                    _left_enc.count() - _distance_goal["left_start_ticks"]
                )
                right_progress = direction * (
                    _right_enc.count() - _distance_goal["right_start_ticks"]
                )
                avg_progress = (left_progress + right_progress) / 2.0
                success_ticks = max(
                    0.0, _distance_goal["target_ticks"] - _distance_goal["tolerance_ticks"]
                )

                if avg_progress >= success_ticks:
                    _clear_motion_goals(stop_motors=True)
                    force_stop = True
                elif utime.ticks_diff(_distance_goal["deadline_ms"], now) <= 0:
                    _clear_motion_goals(stop_motors=True)
                    force_stop = True
            elif _turn_goal is not None:
                current_heading = _read_heading_snapshot(require_numeric=False)
                if current_heading is not None:
                    direction = _turn_goal["direction"]
                    progress_deg = direction * (current_heading - _turn_goal["start_heading"])
                    success_deg = max(
                        0.0, _turn_goal["target_degrees"] - _turn_goal["tolerance_deg"]
                    )
                    if progress_deg >= success_deg:
                        _clear_motion_goals(stop_motors=True)
                        force_stop = True

                if not force_stop and utime.ticks_diff(_turn_goal["deadline_ms"], now) <= 0:
                    _clear_motion_goals(stop_motors=True)
                    force_stop = True

            # ── Step 3: Compute PID correction using real encoder feedback ─────
            if force_stop:
                left_out = 0.0
                right_out = 0.0
            else:
                left_out  = _left_pid.compute(_target_rpm["left"],  left_rpm_actual,  dt if dt > 0 else 0.05)
                right_out = _right_pid.compute(_target_rpm["right"], right_rpm_actual, dt if dt > 0 else 0.05)

            # ── Step 4: Drive motors with PID output ──────────────────────────
            _left_motor.drive(left_out)
            _right_motor.drive(right_out)

            # ── Step 5: Check software motor timeout ──────────────────────────
            if _watchdog is not None:
                stop_fn = lambda: (_left_motor.brake(), _right_motor.brake())
                _watchdog.check_motor_timeout(stop_fn)

        except Exception as e:
            # Brake both motors and call emergency_stop before propagating.
            # Never leave motors running when firmware has an error.
            stop_fn = lambda: (_left_motor.brake(), _right_motor.brake())
            _left_motor.brake()
            _right_motor.brake()
            if _watchdog is not None:
                _watchdog.emergency_stop(stop_fn)
            print("motor_task ERROR:", e)
            break  # Exit loop; gather() propagates exception; WDT resets if stuck

        await uasyncio.sleep_ms(interval_ms)
