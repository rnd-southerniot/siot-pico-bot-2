"""
sensor_task.py — Async sensor poll coroutine (10Hz)

Runs as one of the three concurrent coroutines under uasyncio.
Stub writes a counter into the shared _sensor_state dict so other
tasks can read it. Phase 2 replaces with real sensor reads.

Exports:
  sensor_poll_loop()  — coroutine, schedule with uasyncio.gather()
  get_sensor_state()  — returns the shared state dict
"""

import uasyncio

# Shared sensor state — written by this task, read by motor / wifi tasks
_sensor_state = {}

# ── Public accessor ───────────────────────────────────────────────────────────

def get_sensor_state() -> dict:
    """Return a reference to the shared sensor state dict."""
    return _sensor_state


# ── Coroutine ─────────────────────────────────────────────────────────────────

async def sensor_poll_loop():
    """
    Sensor poll loop coroutine — runs at 10Hz (every 100ms).

    Stub behaviour: increments a tick counter and prints 'sensor tick'
    every 10 iterations to show interleaving with the motor task.

    Exception handling: sensor failures must NOT propagate to gather()
    and kill the motor task (Pitfall 2). Log and continue.
    """
    iteration = 0

    while True:
        try:
            iteration += 1
            _sensor_state["tick"] = iteration

            if iteration % 10 == 0:
                print("sensor tick", iteration)

            # Phase 2: replace with real reads, e.g.:
            #   _sensor_state["ir"]  = await ir_sensor.read_all()
            #   _sensor_state["dist"] = await ultrasonic.read_cm()

        except Exception as e:
            # Log but continue — a sensor failure must not kill motor task
            print("sensor_task ERROR (continuing):", e)

        await uasyncio.sleep_ms(100)
