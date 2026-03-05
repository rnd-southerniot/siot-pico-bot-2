# Milestones

## v1.0 Firmware Foundation + Robot API (Shipped: 2026-03-05)

**Phases completed:** 3 phases, 7 plans, 0 tasks

**Key accomplishments:**
- Async MicroPython firmware with uasyncio event loop running 5 concurrent tasks (motor PID, sensor poll, WiFi server, IMU heading, watchdog)
- PIO-based hardware encoder counting + MotorHAL with K-8 safety cap (70%)
- Full sensor suite — IMU heading tracker (100Hz), IR line following, ultrasonic obstacle, color sensor, NeoPixel status LED
- Two-layer safety: hardware WDT (8s reset) + software motor timeout (30s brake) with closed-loop PID
- Robot API facade + exec() sandbox blocking all student imports — safe student code execution
- WiFi AP with MAC-derived unique SSID (RoboPico-XXXX) + Microdot HTTP server with CORS

**Stats:**
- Lines of code: 5,705 MicroPython
- Timeline: 3 days (2026-03-03 → 2026-03-05)
- Commits: 43
- Tech debt: 6 low-severity items (see v1.0-MILESTONE-AUDIT.md)

---

