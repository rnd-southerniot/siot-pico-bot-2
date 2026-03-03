"""
siot-pico-bot — Main Entry Point (v2 async architecture)

Boot sequence (safe WDT order per Pitfall 1 from research):
  1. Initialize I2C and MPU6050
  2. Calibrate gyro Z (blocks ~1s — WDT must NOT be running yet)
  3. Create WatchdogKeeper AFTER calibration (starts hardware WDT)
  4. Inject watchdog into motor_task via set_watchdog()
  5. Set green LED to signal boot complete
  6. Launch uasyncio event loop with all coroutines gathered

Usage:
  Flash to Pico W as main.py (via Thonny or mpremote).
  The rover will calibrate the IMU on boot (keep still for ~1 second),
  then start the async event loop running motor PID, sensor polling,
  WiFi placeholder, and WDT feed loop concurrently.
"""

import machine
from machine import I2C, Pin
import uasyncio
import config
from lib.mpu6050 import MPU6050

# ── Boot Banner ───────────────────────────────────────────────────────────────

print()
print("=========================================")
print("  siot-pico-bot Learning Kit  v2.0")
print("  Async firmware -- uasyncio architecture")
print("=========================================")
print()

# ── Step 1: Hardware Init (NO WDT yet — Pitfall 1) ───────────────────────────

print("Initializing I2C and IMU...")
i2c = I2C(
    config.I2C_ID,
    sda=Pin(config.I2C_SDA),
    scl=Pin(config.I2C_SCL),
    freq=config.I2C_FREQ,
)
imu = MPU6050(
    i2c_id=config.I2C_ID,
    sda=config.I2C_SDA,
    scl=config.I2C_SCL,
    freq=config.I2C_FREQ,
    addr=config.MPU6050_ADDR,
)

# ── Step 2: IMU Calibration (blocking — WDT must NOT be running) ──────────────

print("Calibrating IMU -- keep robot still...")
imu.calibrate_gyro_z(samples=200)
print("Calibration done")

# ── Step 3: Start WDT AFTER calibration via WatchdogKeeper ───────────────────
# WatchdogKeeper wraps machine.WDT and provides the feed_loop coroutine plus
# the software motor timeout layer. Creating it here (after calibration) ensures
# the blocking calibration call cannot trigger a premature WDT reset.

from safety.watchdog import WatchdogKeeper
import tasks.motor_task as motor_task

watchdog = WatchdogKeeper(timeout_ms=8000)
print("Watchdog armed (8s timeout, fed every 4s in feed_loop coroutine)")

# ── Step 4: Inject watchdog into motor task ───────────────────────────────────
# motor_task needs the watchdog for check_motor_timeout() and emergency_stop().
# Injected here so motor_task module-level init (encoders, motors) can run
# at import time without needing the watchdog yet.

motor_task.set_watchdog(watchdog)

# ── Step 5: Signal boot complete (green LED = ready) ─────────────────────────

try:
    from hal.leds import StatusLED
    leds = StatusLED(config.NEOPIXEL_PIN, config.NEOPIXEL_COUNT)
    leds.set_ready()
    print("Status LED: green (ready)")
except Exception as e:
    # LED failure is non-fatal — firmware continues without visual indicator
    print("LED init skipped:", e)


# ── Async main: gather all coroutines ────────────────────────────────────────

async def main_async():
    """
    Start all task coroutines and the WDT feed loop concurrently.

    Coroutines:
      motor_pid_loop()    — 20Hz motor PID with real encoder feedback
      sensor_poll_loop()  — 10Hz sensor reads (IR, ultrasonic, color)
      wifi_placeholder()  — 1Hz placeholder (Phase 5 replaces with WiFi AP)
      watchdog.feed_loop() — feeds hardware WDT every 4s (MUST keep running)
    """
    from tasks.motor_task import motor_pid_loop
    from tasks.sensor_task import sensor_poll_loop
    from tasks.wifi_task import wifi_placeholder

    print("Starting event loop: motor | sensor | wifi | watchdog")
    await uasyncio.gather(
        motor_pid_loop(),
        sensor_poll_loop(),
        wifi_placeholder(),
        watchdog.feed_loop(),
    )


# ── Entry point ───────────────────────────────────────────────────────────────

uasyncio.run(main_async())
