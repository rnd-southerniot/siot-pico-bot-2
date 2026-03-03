# Architecture Patterns

**Domain:** STEM robotics kit — embedded firmware + WiFi + web block-coding editor + curriculum
**Researched:** 2026-03-03
**Confidence:** HIGH (based on direct codebase analysis of v1 prototype + established embedded/web patterns)

---

## System Overview

The system spans two physical devices connected over WiFi. The Pico W is the hardware authority — it owns all hardware I/O. The React web app is the user authority — it owns the block editor, lesson viewer, and connection UI. They communicate over HTTP (command-response) and optionally WebSocket (telemetry push).

```
┌─────────────────────────────────────────────────────────┐
│  BROWSER (React Web App)                                 │
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────┐  │
│  │  Block Editor  │  │  Lesson Viewer │  │Connection │  │
│  │  (code gen)    │  │  (curriculum)  │  │  Manager  │  │
│  └───────┬────────┘  └────────────────┘  └─────┬─────┘  │
│          │ generated MicroPython                │        │
│          └───────────────┬───────────────────────┘       │
│                          │ HTTP POST /exec                │
│                          │ HTTP GET  /telemetry           │
└──────────────────────────┼──────────────────────────────┘
                           │ WiFi (AP mode: 192.168.4.1)
┌──────────────────────────┼──────────────────────────────┐
│  PICO W FIRMWARE (MicroPython)                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  WiFi Server Layer                                │   │
│  │  AP mode (SSID: RoboPico-Lab) + HTTP on :80      │   │
│  └──────────┬─────────────────────────┬─────────────┘   │
│             │                         │                  │
│  ┌──────────▼──────────┐  ┌───────────▼──────────────┐  │
│  │  Command Executor   │  │  Telemetry Collector     │  │
│  │  (exec MicroPython  │  │  (sensor state snapshot) │  │
│  │   code strings)     │  └───────────┬──────────────┘  │
│  └──────────┬──────────┘              │                  │
│             │                         │                  │
│  ┌──────────▼─────────────────────────▼──────────────┐  │
│  │  Hardware Abstraction Layer (HAL)                  │  │
│  │  motor.py  encoder.py  mpu6050.py  pid.py          │  │
│  └──────────┬─────────────────────────────────────────┘  │
│             │                                             │
│  ┌──────────▼─────────────────────────────────────────┐  │
│  │  Physical Hardware                                  │  │
│  │  MX1515H motors, Hall encoders, MPU6050, NeoPixel, │  │
│  │  buzzer, IR sensors, servo ports                   │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Firmware Components (on Pico W)

| Component | Responsibility | Communicates With | Files (v1) |
|-----------|---------------|-------------------|------------|
| **WiFi Server** | AP mode management, HTTP request routing, socket lifecycle | Browser (inbound), HAL (outbound) | `gate8_wifi_telemetry.py` (prototype) |
| **Command Executor** | Receives code strings from browser, executes them in MicroPython sandbox | WiFi Server (receives), HAL (calls) | To be built in v2 |
| **Telemetry Collector** | Reads sensor state, packages as JSON | HAL (reads), WiFi Server (returns data) | `gate8` serve() loop |
| **Motor Driver (HAL)** | PWM signals to MX1515H H-bridge for each motor channel | Encoders (feedback), PID controller | `lib/motor.py` |
| **Encoder Driver (HAL)** | IRQ-based quadrature tick counting, RPM calculation | Motor Driver (speed feedback), PID | `lib/encoder.py` |
| **IMU Driver (HAL)** | I2C reads from MPU6050 — accel, gyro, temp, calibration | Telemetry Collector, heading control | `lib/mpu6050.py` |
| **PID Controller** | Closed-loop speed/heading control with anti-windup | Motor Driver (output), Encoders (input) | `lib/pid.py` |
| **Config** | Central pin definitions and hardware constants | All components | `config.py` |

### Web App Components (in browser)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Block Editor** | Drag-and-drop block coding UI with SIOT branding | Code Generator (outbound), Lesson Viewer (inbound context) |
| **Code Generator** | Converts block AST to MicroPython code strings | Block Editor (receives AST), Robot Connection (sends code) |
| **Robot Connection Manager** | WiFi connection state, HTTP request queue, error handling | Code Generator (receives code), Telemetry Display (pushes data) |
| **Telemetry Display** | Live sensor data visualization (speed, heading, sensor readings) | Robot Connection Manager (receives JSON) |
| **Lesson Viewer** | Step-by-step lesson content, progress tracking, hints | Block Editor (constrains available blocks), local storage (progress) |
| **Lesson Content System** | Structured lesson definitions (JSON/MDX), ordered progression | Lesson Viewer (consumed by) |

---

## Data Flow

### Flow 1: User writes block code and runs it

```
Student drags blocks
    → Block Editor builds block AST
    → Code Generator converts AST to MicroPython string
    → Robot Connection Manager POSTs code string to http://192.168.4.1/exec
    → Pico W Command Executor receives code string
    → Executor runs code in MicroPython context (exec() or safe sandbox)
    → Robot performs physical action (motors move, LEDs change, etc.)
    → Executor returns JSON result { "ok": true, "output": "..." }
    → Browser displays result / advances lesson step
```

### Flow 2: Telemetry (sensor data to browser)

```
Browser polls GET http://192.168.4.1/telemetry
    → Pico W Telemetry Collector reads HAL:
        imu.accel(), imu.gyro(), enc_l.rpm(), enc_r.rpm()
    → Packages as JSON { "accel": {...}, "gyro": {...}, "speed": {...} }
    → Returns HTTP 200 JSON
    → Browser Telemetry Display renders live values
```

Alternative (preferred at v2): WebSocket push from Pico W on sensor change, eliminates polling latency. MicroPython's `uasyncio` supports WebSocket servers. Assess memory impact on Pico W before committing.

### Flow 3: Connection establishment

```
Student powers rover → Pico W boots, starts AP "RoboPico-Lab" (192.168.4.1)
Student connects laptop/tablet WiFi to "RoboPico-Lab"
Student opens browser to http://192.168.4.1/ OR opens React app (served separately)
Robot Connection Manager pings GET /status
    → success: shows "Connected" indicator
    → failure: shows "Not connected" with setup instructions
```

### Flow 4: Lesson progression

```
Lesson Viewer loads lesson definition (JSON)
    → Presents objective, allowed blocks, instructions
    → Student completes block program for step
    → Code runs on rover
    → If pass criteria met (telemetry check or output match): advance step
    → Lesson Viewer updates progress (local storage), shows next step
```

---

## WiFi Architecture Decision

The Pico W runs in **Access Point (AP) mode**. This is the correct choice for a classroom product because:

- No dependency on school WiFi infrastructure (which is often locked down)
- No internet required
- Fixed IP (192.168.4.1) means no discovery needed — URL is always the same
- Simple setup: student connects device WiFi to "RoboPico-Lab" network

**Alternative considered: Station mode** (Pico W joins school network). Rejected because it requires school IT credentials, introduces DHCP variability, and breaks in offline environments.

**React app delivery:** Two options, each with tradeoffs.

| Option | How | Pros | Cons |
|--------|-----|------|------|
| Served from Pico W | Pico W serves static HTML/JS/CSS from flash | Single connection step, fully self-contained | Pico W flash is 2MB total, MicroPython takes ~500KB, React bundle must be tiny (<500KB) |
| Served from internet/CDN | Hosted web app, browser connects to rover | Full React bundle size OK, standard dev workflow | Requires internet to load app (not suitable for classroom-offline use) |
| Served from local file | `file://` React app, packaged with kit setup | No internet needed, no size constraint | Requires initial OS-level setup, harder UX |

**Recommendation:** Serve a minimal, production-optimized React bundle from Pico W flash for the MVP kit. Size budget: target <400KB gzipped. Use Vite + aggressive tree-shaking. Validate this size constraint early. If it fails, fall back to a separate hosted app that connects to the rover over the AP network (student connects WiFi, then opens `app.siot.io` which talks to `192.168.4.1`).

---

## Communication Protocol

### HTTP REST (baseline — confirmed working in v1)

```
GET  /status      → { "ok": true, "uptime_s": 42 }
GET  /telemetry   → { "accel": {...}, "gyro": {...}, "speed": {...}, "encoders": {...} }
POST /exec        → body: { "code": "motor_left.drive(50)" }
                  ← { "ok": true, "output": "..." } or { "ok": false, "error": "..." }
POST /stop        → emergency stop all motors
GET  /config      → current PID gains, wheel constants
POST /config      → update PID gains
```

**Confidence:** HIGH — v1 prototype (gate8) confirms HTTP server works on Pico W with `socket` module. Pattern is simple and reliable on constrained hardware.

### WebSocket (telemetry streaming — optional enhancement)

MicroPython's `uasyncio` library supports async TCP, and the community `micropython-lib` provides WebSocket support. This enables push-based telemetry (Pico W pushes sensor data every 50–100ms) rather than browser polling.

**Trade-off:** WebSocket adds async complexity to firmware. Given Pico W single-core RP2040 and MicroPython memory limits, this needs careful implementation. Recommend: ship v1 with HTTP polling, measure latency, add WebSocket in v2 if needed for lesson experiences that require real-time feedback.

---

## Firmware Architecture Pattern: HAL + Service Layer

The v1 prototype uses a flat module pattern (each gate is standalone). For v2, use a two-layer firmware architecture:

```
main.py (boot + service loop)
    ├── server.py (WiFi AP + HTTP routing)
    │       ├── routes/exec.py    (code execution endpoint)
    │       ├── routes/telemetry.py
    │       └── routes/status.py
    ├── hal/
    │   ├── motors.py      (Motor class — already clean in v1)
    │   ├── encoders.py    (Encoder class — already clean in v1)
    │   ├── imu.py         (MPU6050 class — already clean in v1)
    │   ├── sensors.py     (IR line follow, obstacle, light/color)
    │   └── leds.py        (NeoPixel + buzzer)
    ├── control/
    │   ├── pid.py         (already clean in v1)
    │   ├── drive.py       (drive_straight, turn_angle — from gate9)
    │   └── robot.py       (top-level Robot facade)
    └── config.py          (hardware pin constants)
```

**Key principle:** The HTTP server receives code strings from the browser, which it executes using Python's `exec()` with a controlled globals dict exposing only the `robot` facade. Students' block-generated code cannot access OS-level APIs — only the robot API.

Example block-generated code that arrives via POST /exec:
```python
robot.drive(50)
robot.wait_distance(200)  # mm
robot.turn(90)            # degrees
robot.stop()
```

---

## Code Execution Safety Model

Block coding → code generation → exec() on Pico W is a deliberate educational architecture choice. The safety model is:

1. **Block editor constrains what code can be generated** — students can only build programs from predefined block types. The generated code is a predictable subset of the Robot API.
2. **exec() globals whitelist** — the Pico W executor exposes only `robot`, `time`, and math builtins. No `import`, no `open`, no `machine` directly.
3. **Timeout enforcement** — every exec() call runs with a watchdog timer. If code hangs (infinite loop), the watchdog reboots or kills the execution context.
4. **Emergency stop** — the HTTP server continues accepting `/stop` requests even during code execution (requires async or thread-based server).

**Constraint:** MicroPython on RP2040 does not support true threading. Concurrent HTTP serving + code execution requires either `uasyncio` (cooperative multitasking) or running the HTTP server on one core and execution on the other (`_thread` module — RP2040 is dual-core). The dual-core approach is simpler to reason about for this use case.

---

## Lesson Content System Architecture

Lessons are structured data, not code. Each lesson is a JSON definition:

```json
{
  "id": "lesson-03-turn",
  "title": "Making Turns",
  "prerequisite": "lesson-02-forward",
  "steps": [
    {
      "id": "step-1",
      "instruction": "Make your robot turn right 90 degrees",
      "hint": "Use the Turn block and set it to 90",
      "allowed_blocks": ["drive_forward", "turn_right", "stop"],
      "pass_criteria": {
        "type": "telemetry_check",
        "field": "heading_delta",
        "expected": 90,
        "tolerance": 15
      }
    }
  ]
}
```

Lessons live in the React app (browser-side). They do not need to be on the Pico W. The web app reads lesson JSON, configures the block editor (restricts available block types per step), and evaluates pass criteria by checking telemetry after code runs.

**Lesson storage options:**
- Bundled JSON files in the React app (recommended for offline kit use)
- Remote CMS/API (recommended for over-the-air curriculum updates post-launch)
- Start with bundled JSON, add remote CMS hook in v2

---

## Build Order (Dependencies)

This order reflects what each component requires to exist before it can be built or tested:

```
Phase 1: Firmware HAL (no dependencies — pure hardware)
    motor.py, encoder.py, imu.py, sensors.py, leds.py, config.py
    → Already substantially built in v1, needs refactor/clean

Phase 2: Firmware Control Layer (depends on Phase 1 HAL)
    pid.py, drive.py, robot.py facade
    → robot.py is the API that block-generated code calls
    → gate9_autonomous.py contains the reference implementation to port

Phase 3: Firmware Server Layer (depends on Phase 2 Robot facade)
    server.py, routes/exec.py, routes/telemetry.py, routes/status.py
    → exec() sandbox requires robot facade to be stable
    → gate8_wifi_telemetry.py is the reference HTTP server pattern

Phase 4: React Connection Layer (depends on Phase 3 server contract)
    RobotConnectionManager, useRobotStatus hook, telemetry display
    → Can develop with a mock server before real Pico W is ready

Phase 5: Block Editor (depends on Phase 4 connection, Phase 2 robot API)
    Custom block types must map to robot.py API methods
    → Block design is driven by what the robot can actually do

Phase 6: Lesson System (depends on Phase 5 block editor)
    Lesson JSON definitions, Lesson Viewer component, progress tracking
    → Lessons constrain which blocks are available per step

Phase 7: Polish & Integration (depends on all above)
    UX refinement, error handling, setup flow, packaging
```

**Critical dependency:** The `robot.py` facade API must be stable before block types are designed. Block names and parameters directly mirror robot API methods. If the API changes after block types are built, both the code generator and block editor must be updated in sync. Lock the robot API early.

---

## Patterns to Follow

### Pattern 1: Robot Facade (Gateway to Hardware)

All user-generated code routes through a single `Robot` class. This decouples the block-generated code from HAL internals and makes the API stable and teachable.

```python
# robot.py — The stable public API
class Robot:
    def drive(self, speed_pct: float): ...
    def stop(self): ...
    def turn(self, degrees: float): ...
    def wait_distance(self, mm: float): ...
    def set_led_color(self, r, g, b): ...
    def play_tone(self, freq_hz, duration_ms): ...
    def read_line(self) -> bool: ...
    def read_obstacle(self) -> bool: ...
```

### Pattern 2: HTTP Request-Response (Simple, Reliable)

Keep the Pico W HTTP server stateless and synchronous for the MVP. Each request reads current state, handles the request, returns response, closes socket. This is what gate8 does — it works.

```python
# Confirmed working pattern from gate8_wifi_telemetry.py
while True:
    cl, _ = s.accept()
    request = cl.recv(1024).decode()
    path = parse_path(request)
    body = parse_body(request)
    response = handle(path, body)
    cl.send(response)
    cl.close()
```

### Pattern 3: Block-to-Code Generation (AST → string)

The block editor maintains a tree of block nodes. The code generator does a depth-first traversal to emit MicroPython strings. Each block type has a corresponding code template.

```typescript
// Code generator pattern
function generateCode(blockTree: BlockNode[]): string {
  return blockTree.map(block => {
    switch (block.type) {
      case 'drive_forward':
        return `robot.drive(${block.params.speed})\nrobot.wait_distance(${block.params.distance})`;
      case 'turn_right':
        return `robot.turn(${block.params.degrees})`;
      // ...
    }
  }).join('\n');
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Hardware Access in Generated Code

**What goes wrong:** Block editor generates code that calls `machine.PWM()` or `motor._pwm_a.duty_u16()` directly.
**Why bad:** Bypasses safety model, allows malformed code to damage hardware state, breaks if HAL internals change.
**Instead:** Generated code only calls `robot.*` methods. The exec() sandbox exposes only the `robot` object.

### Anti-Pattern 2: Monolithic Server Loop (v1 Problem)

**What goes wrong:** The HTTP server loop, sensor reading, and code execution all happen in one synchronous while loop. A slow command (drive 1 meter) blocks the server — no stop command can interrupt it.
**Why bad:** Students can't stop a runaway robot. Lessons requiring real-time feedback won't work.
**Instead:** Use dual-core execution: Core 0 runs the HTTP server, Core 1 runs the robot execution context. Or use `uasyncio` with cooperative yields in long-running robot commands.

### Anti-Pattern 3: Lesson Content Hardcoded in React Components

**What goes wrong:** Lesson text, block restrictions, and pass criteria written directly in React component JSX.
**Why bad:** Adding a lesson requires a code deploy. Translating lessons requires code changes. Product team can't edit curriculum without engineering.
**Instead:** Lessons as JSON data files. React components are pure renderers that consume lesson JSON. Curriculum can be updated independently.

### Anti-Pattern 4: WiFi Station Mode for Classroom

**What goes wrong:** Pico W configured to join school WiFi. Robot works in lab, fails on first day in school.
**Why bad:** School networks use WPA Enterprise, block client isolation, assign different IPs each boot. Teacher can't troubleshoot.
**Instead:** AP mode with fixed SSID and IP (192.168.4.1) — confirmed working in v1 prototype. Zero network dependency.

### Anti-Pattern 5: Serving Uncompressed React Bundle from Pico W Flash

**What goes wrong:** Standard Create React App build is 500KB–2MB+ JS. Pico W has 2MB flash total with MicroPython taking ~500KB.
**Why bad:** Pico W flash fills up, can't store firmware and web app simultaneously.
**Instead:** Use Vite with aggressive code splitting, minimal dependencies, production optimization. Target <400KB total. Validate early. If not achievable, use the hybrid model: app hosted externally, connects to rover over the AP network.

---

## Scalability Considerations

This is a single-robot, single-user product. "Scale" means supporting more lesson complexity and more robust hardware interaction, not more users.

| Concern | MVP | v2 | Notes |
|---------|-----|-----|-------|
| Lesson count | 10 lessons bundled | 30+ lessons, CMS-managed | JSON schema must be stable from day 1 |
| Robot API surface | ~10 methods | ~20 methods (sensors, servos) | Freeze core API early, add methods via new blocks |
| Telemetry frequency | HTTP poll 1s | WebSocket 100ms push | Start with polling, profile if lesson UX needs faster |
| Error recovery | Show error message | Auto-reconnect, retry | AP connection drops if student moves out of range |
| Multi-robot (future) | Out of scope | Out of scope | Architecture supports it but not planned |

---

## Sources

- Direct analysis of v1 prototype codebase (confidence: HIGH — first-party source)
  - `config.py` — hardware pin layout, WiFi AP constants
  - `lib/motor.py` — Motor PWM driver
  - `lib/encoder.py` — Quadrature encoder IRQ driver
  - `lib/mpu6050.py` — I2C IMU driver
  - `lib/pid.py` — PID controller
  - `gates/gate8_wifi_telemetry.py` — HTTP server + AP mode pattern (confirmed working)
  - `gates/gate9_autonomous.py` — Motor + encoder + IMU integration (confirmed working)
- MicroPython documentation: `network.WLAN` AP_IF mode, `socket`, `uasyncio`, `_thread` (confidence: HIGH — well-established MicroPython APIs, stable since 2021)
- RP2040 dual-core execution via `_thread` module: established MicroPython pattern (confidence: HIGH)
- STEM robotics kit AP-mode WiFi pattern: used by WPILib XRP (referenced in project README), micro:bit classroom tools, and similar products (confidence: HIGH — industry standard for offline-capable kits)
