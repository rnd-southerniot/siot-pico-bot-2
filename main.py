"""
siot-pico-bot — Main Entry Point (v2 async architecture)

Boot sequence (safe WDT order per Pitfall 1 from research):
  1. Initialize I2C and MPU6050
  2. Calibrate gyro Z (blocks ~1s — WDT must NOT be running yet)
  3. Start WDT after calibration completes
  4. Launch uasyncio event loop with all coroutines gathered

Usage:
  Flash to Pico W as main.py (via Thonny or mpremote).
  The rover will calibrate the IMU on boot (keep still for ~1 second),
  then start the async event loop running motor PID, sensor polling,
  and the WiFi placeholder coroutines concurrently.
"""

import machine
from machine import I2C, Pin, WDT
import uasyncio
import config
from lib.mpu6050 import MPU6050

# ── Boot Banner ───────────────────────────────────────────────────────────────

print()
print("=========================================")
print("  siot-pico-bot Learning Kit  v2.0")
print("  Async firmware — uasyncio architecture")
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

# ── Step 3: Start WDT AFTER calibration ──────────────────────────────────────

# WDT range on RP2040: 1000-8388 ms; feed every 4000ms to stay well within limit
wdt = WDT(timeout=8000)
wdt.feed()
print("Watchdog armed (8s timeout, fed every 4s)")


# ── Inline WDT feed coroutine (Plan 04 replaces with safety/watchdog.py) ─────

async def _wdt_feed_loop():
    """Feed the hardware watchdog every 4000ms.

    If this coroutine stops running (firmware hang), the WDT will reset
    the device within 8 seconds. Plan 04 refactors this into
    safety/watchdog.py WatchdogKeeper.feed_loop().
    """
    while True:
        wdt.feed()
        await uasyncio.sleep_ms(4000)


# ── Async main: gather all coroutines ────────────────────────────────────────

async def main_async():
    """Start the three task coroutines and the WDT feed loop concurrently."""
    from tasks.motor_task import motor_pid_loop
    from tasks.sensor_task import sensor_poll_loop
    from tasks.wifi_task import wifi_placeholder

    print("Starting event loop: motor | sensor | wifi | watchdog")
    await uasyncio.gather(
        motor_pid_loop(),
        sensor_poll_loop(),
        wifi_placeholder(),
        _wdt_feed_loop(),
    )


# ── Entry point ───────────────────────────────────────────────────────────────

uasyncio.run(main_async())
