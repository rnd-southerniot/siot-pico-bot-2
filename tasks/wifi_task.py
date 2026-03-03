"""
wifi_task.py — WiFi placeholder coroutine

Holds the WiFi/HTTP server slot in the uasyncio.gather() call.
Phase 2 replaces this entire coroutine with the HTTP server task.

Exports:
  wifi_placeholder()  — coroutine, schedule with uasyncio.gather()
"""

import uasyncio

# ── Coroutine ─────────────────────────────────────────────────────────────────

async def wifi_placeholder():
    """
    WiFi placeholder — loops every 1000ms, prints once per 10 iterations.

    Phase 2 replaces this coroutine with the HTTP server:
      - Starts WiFi AP (config.WIFI_AP_SSID / WIFI_AP_PASSWORD)
      - Binds HTTP server on config.HTTP_PORT
      - Handles block-code execution requests
    """
    iteration = 0

    while True:
        try:
            iteration += 1

            if iteration % 10 == 0:
                print("wifi placeholder", iteration)

        except Exception as e:
            print("wifi_task ERROR (continuing):", e)

        await uasyncio.sleep_ms(1000)
