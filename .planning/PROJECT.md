# SIOT Pico Bot 2

## What This Is

A sellable STEM robotics kit for K-8 students. The kit includes a wheeled rover powered by a Raspberry Pi Pico W running async MicroPython firmware, a custom block coding editor (React web app connected over WiFi), and step-by-step lessons that teach robotics and programming concepts progressively. Sold to schools and direct consumers.

## Core Value

A kid can unbox the kit, connect to the rover over WiFi, and complete guided lessons using block coding — learning robotics concepts while having fun.

## Requirements

### Validated

- MicroPython async firmware architecture with 5-task event loop — v1.0
- Motor control with PIO encoder feedback and closed-loop PID — v1.0
- IMU-6050 heading tracker for accurate turning — v1.0
- Full sensor suite (IR line, ultrasonic obstacle, color, NeoPixel LED) — v1.0
- Hardware watchdog + software motor timeout safety layer — v1.0
- WiFi AP with MAC-derived unique SSID (RoboPico-XXXX) — v1.0
- JSON command/telemetry protocol via HTTP — v1.0
- exec() sandbox blocking all student imports — v1.0

### Active

- [ ] Custom block coding editor in React with SIOT branding
- [ ] Block-to-MicroPython code generation and execution on rover
- [ ] WiFi reconnection and mDNS discovery
- [ ] WebSocket for real-time telemetry and block execution trace
- [ ] Step-by-step lesson system with progressive difficulty
- [ ] Sellable product quality (polished UX, documentation, packaging-ready)

### Out of Scope

- Mobile native app — web-first approach, mobile later
- Real-time video streaming — adds hardware cost and complexity
- Multi-robot coordination — single robot per kit for v1
- Bluetooth connectivity — WiFi chosen for reliability and range
- Account/login system — COPPA complexity; LocalStorage sufficient
- AI-generated lesson suggestions — hallucination risk in educational context

## Context

Shipped v1.0 with 5,705 LOC MicroPython across 54 files.
Tech stack: MicroPython (async), Microdot HTTP, React (frontend).
Firmware covers all hardware: motors (PIO encoders, PID), IMU (heading tracker), sensors (IR, ultrasonic, color), NeoPixel LED, WiFi AP.
Robot API facade provides clean contract for browser-generated code.
6 low-severity tech debt items from v1.0 audit (pin placeholders, old gate scripts, cosmetic docstring).

V1 was a prototype that proved the concept but had firmware architecture problems — v2 firmware (shipped in v1.0) replaced the blocking loop with async architecture.

## Constraints

- **Hardware**: Raspberry Pi Pico W — limited memory and processing, MicroPython runtime
- **Connectivity**: WiFi only — must work in classroom environments with potential network restrictions
- **Audience**: K-8 students — UI must be dead simple, error-tolerant, visually engaging
- **Firmware language**: MicroPython — chosen for readability and educational value
- **Frontend**: React — existing codebase to build on
- **Product quality**: Must be sellable — polished enough for schools and consumers to purchase

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MicroPython over C/C++ | Readability for educational context, faster iteration | Good — clean async architecture |
| Custom block editor over Blockly | Full branding and UX control for sellable product | — Pending |
| WiFi over Bluetooth | Better range, works with web browser, classroom-friendly | Good — AP mode with unique SSID works well |
| React for frontend | Existing codebase from v1, rich ecosystem for UI components | — Pending |
| Clean firmware rewrite (async) | V1 blocking loop was fatal flaw | Good — 5-task gather() architecture stable |
| PIO for encoder counting | Zero-CPU-overhead quadrature counting on RP2040 | Good — hardware counting with SM IDs 4/5 |
| Two-layer safety (WDT + motor timeout) | Student runaway code in classroom is a product-killer | Good — 8s hardware reset + 30s software brake |
| exec() sandbox blocks ALL imports | No allow-list by module name; strictest possible | Good — prevents all student code escapes |
| Microdot HTTP server | Lightweight async HTTP for Pico W | Good — CORS + JSON endpoints working |
| MAC-derived SSID (RoboPico-XXXX) | Each rover uniquely identifiable in classroom | Good — no conflicts with 30+ rovers |
| Dependency injection (HeadingTracker, I2C) | Avoids circular init and duplicate bus construction | Good — clean wiring pattern |

---
*Last updated: 2026-03-05 after v1.0 milestone*
