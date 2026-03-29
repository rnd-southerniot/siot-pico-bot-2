"""
Gate 10: runtime smoke check for boot + AP + HTTP server wiring

On-device only.
Verifies:
  1. boot() completes
  2. AP activates
  3. watchdog feeding stays active during the gate
  4. wifi_server_task() binds a Microdot server
  5. GET /status returns 200 with required keys
  6. POST /exec accepts a minimal valid payload
"""

import json
import uasyncio

import config
from app.boot import boot
from microdot import Request
import tasks.wifi_task as wifi_task


async def dispatch(method, path, body=None):
    headers = {"Host": "127.0.0.1"}
    payload = b""
    if body is not None:
        payload = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(payload))
    req = Request(wifi_task.app, ("127.0.0.1", 0), method, path, "1.1", headers, body=payload)
    return await wifi_task.app.dispatch_request(req)


async def cancel_task(task):
    if task is None:
        return
    task.cancel()
    try:
        await task
    except BaseException as exc:
        if exc.__class__.__name__ != "CancelledError":
            raise


async def main():
    print("=" * 40)
    print("GATE 10: Runtime Smoke")
    print("=" * 40)

    ctx = boot()
    watchdog_task = uasyncio.create_task(ctx.watchdog.feed_loop())
    server_task = None

    try:
        assert ctx.ap.active(), "AP should be active after boot()"
        assert ctx.ssid.startswith(config.WIFI_AP_SSID_PREFIX + "-"), "SSID prefix mismatch"
        print("PASS: boot() completed and AP is active:", ctx.ssid)

        server_task = uasyncio.create_task(wifi_task.wifi_server_task())
        for _ in range(20):
            if wifi_task.app is not None and wifi_task.app.server is not None:
                break
            await uasyncio.sleep_ms(100)

        assert wifi_task.app is not None, "wifi_task.app not initialized"
        assert wifi_task.app.server is not None, "HTTP server did not start"
        print("PASS: wifi_server_task() started HTTP server")

        status_res = await dispatch("GET", "/status")
        assert status_res.status_code == 200, "GET /status should return 200"
        status_data = json.loads(status_res.body.decode())
        required_keys = (
            "rpm_left",
            "rpm_right",
            "ir",
            "distance_cm",
            "color",
            "heading",
            "tick",
        )
        for key in required_keys:
            assert key in status_data, "Missing /status key: " + key
        print("PASS: GET /status returned required keys")

        exec_res = await dispatch("POST", "/exec", {"code": "robot.stop()"})
        assert exec_res.status_code == 200, "POST /exec should return 200"
        exec_data = json.loads(exec_res.body.decode())
        assert exec_data["ok"] == True, "POST /exec should succeed: " + str(exec_data)
        print("PASS: POST /exec accepted minimal robot command")

        print()
        print("PASS: Runtime smoke gate passed")
    finally:
        if wifi_task.app is not None and wifi_task.app.server is not None:
            wifi_task.app.shutdown()
        await cancel_task(server_task)
        await cancel_task(watchdog_task)
        ctx.ap.active(False)


uasyncio.run(main())
