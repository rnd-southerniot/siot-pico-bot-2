"""
app.runtime — async runtime entrypoint extracted from main.py
"""

import uasyncio


async def main_async(ctx):
    """
    Start all task coroutines and the WDT feed loop concurrently.

    Coroutines:
      motor_pid_loop()              — 20Hz motor PID with real encoder feedback
      sensor_poll_loop()            — 10Hz sensor reads (IR, ultrasonic, color)
      heading_tracker.update_loop() — 100Hz gyro-Z heading integration
      wifi_server_task()            — Microdot HTTP server on port 80 (AP already up)
      watchdog.feed_loop()          — feeds hardware WDT every 4s (MUST keep running)
    """
    from tasks.motor_task import motor_pid_loop
    from tasks.sensor_task import sensor_poll_loop
    from tasks.wifi_task import wifi_server_task

    print("Starting event loop: motor | sensor | heading | wifi/http | watchdog")
    await uasyncio.gather(
        motor_pid_loop(),
        sensor_poll_loop(),
        ctx.heading_tracker.update_loop(),
        wifi_server_task(),  # HTTP server — AP started in boot() above
        ctx.watchdog.feed_loop(),
    )
