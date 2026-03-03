# SIOT Pico Bot 2

## What This Is

A sellable STEM robotics kit for K-8 students. The kit includes a wheeled rover powered by a Raspberry Pi Pico W, a custom block coding editor (React web app connected over WiFi), and step-by-step lessons that teach robotics and programming concepts progressively. Sold to schools and direct consumers.

## Core Value

A kid can unbox the kit, connect to the rover over WiFi, and complete guided lessons using block coding — learning robotics concepts while having fun.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Clean, modular MicroPython firmware for Pico W (fixing v1 architecture issues)
- [ ] WiFi connectivity between rover and web interface
- [ ] Custom block coding editor in React with SIOT branding
- [ ] Block-to-MicroPython code generation and execution on rover
- [ ] Motor control with encoder feedback and IMU-6050 integration
- [ ] Line following sensor support (IR)
- [ ] Obstacle detection sensor support
- [ ] Light/color sensor support
- [ ] Step-by-step lesson system with progressive difficulty
- [ ] Sellable product quality (polished UX, documentation, packaging-ready)

### Out of Scope

- Mobile native app — web-first approach, mobile later
- Real-time video streaming — adds hardware cost and complexity
- Multi-robot coordination — single robot per kit for v1
- Bluetooth connectivity — WiFi chosen for reliability and range

## Context

- V1 was a prototype that proved the concept but had firmware architecture problems — messy, hard to extend
- Existing repo contains MicroPython firmware and a React web frontend from prototype work
- SIOT is the company/brand name
- Target age range (K-8) means the interface must be extremely intuitive — no text coding, minimal setup friction
- The rover has a rich sensor suite: line following (IR), obstacle detection, light/color, wheel encoders, and MPU-6050 IMU
- WiFi connection means the Pico W hosts or connects to a network; the React app communicates over HTTP/WebSocket
- Custom block editor chosen over Blockly for full control over branding and UX
- Curriculum is structured as step-by-step lessons (not open-ended challenges)

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
| MicroPython over C/C++ | Readability for educational context, faster iteration | — Pending |
| Custom block editor over Blockly | Full branding and UX control for sellable product | — Pending |
| WiFi over Bluetooth | Better range, works with web browser, classroom-friendly | — Pending |
| React for frontend | Existing codebase from v1, rich ecosystem for UI components | — Pending |
| Clean firmware rewrite | V1 architecture was hard to extend, starting fresh | — Pending |

---
*Last updated: 2026-03-03 after initialization*
