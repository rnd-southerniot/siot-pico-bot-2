# Project Research Summary

**Project:** SIOT Pico Bot 2 — K-8 STEM Robotics Kit
**Domain:** Embedded firmware (MicroPython/RP2040) + WiFi + custom web block-coding editor + progressive lesson curriculum
**Researched:** 2026-03-03
**Confidence:** MEDIUM-HIGH (firmware layer: HIGH from direct v1 codebase analysis; web stack and competitive landscape: MEDIUM from training data)

## Executive Summary

SIOT Pico Bot 2 is a WiFi-connected K-8 robotics kit where a Raspberry Pi Pico W serves as the rover brain and a browser-based custom block editor serves as the programming interface. The product's core differentiator in a crowded market is its zero-install, WiFi AP-mode approach: the rover creates its own hotspot, students connect a phone, tablet, or Chromebook directly to it, and the full block editor is served from the Pico W's flash storage. Every major competitor (LEGO SPIKE, VEX, mBot, Sphero) uses Bluetooth and a proprietary app — SIOT's approach eliminates the classroom IT friction that teachers consistently cite as their top pain point. This is a genuine and defensible market gap.

The recommended technical approach layers a MicroPython asyncio firmware stack on the Pico W against a React/TypeScript/Vite single-page application. The central architectural leap from v1 to v2 is replacing the blocking HTTP server loop with an asyncio event loop that concurrently handles WiFi serving, motor PID control, and sensor polling. The v1 prototype proves the hardware works; v2's job is to make it work reliably as a product. The block editor is a fully custom React implementation (no Blockly) with dnd-kit drag-and-drop, a TypeScript block-AST-to-MicroPython code generator, and a JSON-driven lesson system that lives in the browser. The entire product must work offline — no CDN, no backend, no school internet required.

The dominant risks are not hardware risks but architecture risks that compound if not addressed from day one: the monolithic firmware pattern from v1 will block WiFi + motor concurrency unless asyncio is adopted as the foundation (not bolted on later); the custom block editor has well-documented scope-creep failure modes and must be bounded by the lesson plan before a line of editor code is written; and the MicroPython exec() execution sandbox requires a safety layer (watchdog timer, exec globals whitelist, stop-command preemption) or a runaway robot in a classroom will end the product's school market. Each of these is a rewrite-level mistake if caught late.

## Key Findings

### Recommended Stack

The firmware runs MicroPython 1.23.x (latest stable for RP2040-W) on the Pico W. The v1 codebase validates that the core hardware modules work: `machine.PWM` for MX1515H motor control, `machine.Pin.irq()` for Hall encoder counting, `machine.I2C` for MPU6050 communication, and `network` + `socket` for WiFi AP mode. The critical v2 addition is `asyncio` (uasyncio, built-in since MicroPython 1.19), which replaces the blocking socket accept loop with cooperative multitasking — this is the single most important firmware decision for v2.

The web application is React 18 + TypeScript 5 + Vite 5, with Zustand for local state (block workspace, lesson progress, connection status), dnd-kit for drag-and-drop block interactions (touch-compatible, unlike HTML5 drag API), and Tailwind CSS for styling. React Query manages WebSocket/HTTP connection lifecycle. The block editor is custom — no Blockly — which is the correct call for branding control, but it concentrates risk in a single high-complexity component. Lessons are static JSON files bundled with the app and progress persists in localStorage; no backend or database is required.

**Core technologies:**
- `uasyncio` (MicroPython built-in): concurrent firmware event loop — the architectural foundation for v2
- `network.WLAN(AP_IF)`: rover-hosted WiFi hotspot — proven in v1, classroom-safe, no school IT dependency
- WebSocket over TCP port 81: bidirectional real-time command/telemetry — replaces v1's 1-second HTTP polling
- React 18 + TypeScript 5 + Vite 5: SPA build — Vite produces small bundles suitable for serving from Pico W flash
- dnd-kit 6.x: block editor drag-and-drop — touch-compatible for classroom tablets, actively maintained
- Zustand 4.x: state management — sufficient for block workspace and lesson state without Redux ceremony
- Custom TypeScript code generator: block AST to MicroPython string — recursive tree-walk, no external AST library needed
- JSON lesson definitions + localStorage: curriculum system — offline-first, no backend required

### Expected Features

**Must have (table stakes):**
- Block coding environment with drag-and-drop — all K-8 competitors use blocks; text coding is age-inappropriate
- Motor control blocks (forward, backward, turn) — lesson 1 in every competitor; requires encoder feedback for precision
- Sensor reading blocks (line follow, obstacle, distance) — abstracts GPIO; kids get values without hardware knowledge
- Run/Stop with instant feedback — latency above 1 second kills engagement and feels broken
- At least 5-8 progressive lessons with difficulty arc — schools will not buy a robot with no curriculum
- Kid-readable error messages — raw Python tracebacks for a 7-year-old is a product-killer
- WiFi AP-mode setup that works in under 60 seconds — the core product promise; must be teacher-operable
- Block-to-Python code view — table stakes expectation in the education technology market

**Should have (competitive differentiators):**
- IMU-based turn blocks ("turn exactly 90 degrees") — mBot has this; budget kits don't; hardware already on BOM
- Encoder-based precise distance blocks ("move 30 cm") — differentiates from simple timed-movement robots
- Code execution block trace (which block is running) — helps debugging; uncommon in budget kits
- Graceful WiFi auto-reconnection — huge classroom quality-of-life; prevents "refresh and re-run" frustration
- Per-unit unique SSID (e.g., RoboPico-A3F2) — essential for 30-rover classrooms
- Save/load programs to browser localStorage — students return to their work
- Progressive lesson unlock sequencing — "Mars mission" narrative arc builds retention over purchased Blockly curriculum

**Defer to v2+:**
- Teacher dashboard / LMS integration (Canvas, Google Classroom)
- Cloud program storage (COPPA compliance complexity, backend ops cost)
- Mobile native app (App Store approval delays; browser-on-tablet solves it for classroom)
- Multi-robot coordination (fleet management complexity)
- AI lesson suggestions (backend dependency, hallucination risk in K-8 context)
- Open-ended sandbox/challenge mode (validate structured lessons first)

### Architecture Approach

The system is two physical devices communicating over a local WiFi network. The Pico W is the hardware authority — it owns all physical I/O and exposes a clean `Robot` facade API that generated code calls. The React browser app is the user authority — it owns the block editor, lesson viewer, and connection UI. They communicate via HTTP REST for the MVP (GET /telemetry, POST /exec, POST /stop) with WebSocket as the v1 upgrade path for real-time telemetry. The firmware is structured in three layers: HAL (motor.py, encoder.py, imu.py, sensors.py), Control (pid.py, drive.py, robot.py facade), and Server (HTTP/WebSocket router). The web app mirrors this with a Connection Manager, Block Editor + Code Generator, and Lesson Viewer. The lesson content system lives entirely in the browser as JSON data files — the Pico W has no knowledge of lessons.

**Major components:**
1. Firmware HAL (motor, encoder, IMU, sensors, LEDs) — hardware abstraction; mostly built in v1, needs asyncio refactor
2. Robot facade (robot.py) — the stable API surface that block-generated code calls via exec(); must be locked early
3. Firmware async server (server.py + routes) — asyncio HTTP/WebSocket router; replaces v1's blocking socket loop
4. React Connection Manager — WiFi state machine, reconnection, heartbeat, telemetry display
5. Custom block editor + code generator — dnd-kit drag-and-drop, TypeScript AST-to-MicroPython, touch-compatible
6. JSON lesson system + Lesson Viewer — static curriculum bundled with app, localStorage progress, block constraints per step

### Critical Pitfalls

1. **Monolithic blocking firmware (v1's fatal flaw)** — Adopt asyncio as the firmware foundation from day one. Every subsystem (WiFi, motor PID, sensor poll, LED) must be an async coroutine. Never use `time.sleep()` in the main path. Validate with a 3-task async proof-of-concept before building features.

2. **Unsafe code execution via raw exec()** — Student-generated code running via `exec()` without a safety layer can produce a runaway rover. Implement: exec globals whitelist (robot facade only, no `import`/`machine`), watchdog timer (`machine.WDT`) that reboots on 500ms event loop stall, stop-command handler at higher priority than student code, and maximum 60-second program execution timeout.

3. **AP-mode WiFi failing in classrooms** — Hardcoded SSIDs collide across 30 units. School IT blocks ad-hoc networks. HTTPS-only browser policies block `http://192.168.4.1`. Mitigation: per-unit unique SSID using last 4 of MAC address, mDNS for `robopico-xxxx.local`, QR code on robot for connection URL, and document the IT setup checklist for schools.

4. **Custom block editor scope creep** — Custom editors have a well-documented failure mode: the editor becomes the entire product. Freeze the v1 block set to exactly what the defined lesson plan requires before writing editor code. Code generation correctness takes priority over visual polish. Time-box the editor phase and test with real K-8 students within 2 weeks of starting.

5. **MicroPython heap fragmentation causing random crashes** — v1's pattern of building large HTML strings with `.replace()` chains on every HTTP request will exhaust Pico W heap after 60 minutes of classroom use. Mitigation: serve static files from flash in chunks (not RAM), use a minimal JSON API as the communication channel, call `gc.collect()` at safe points, monitor `gc.mem_free()` in telemetry.

## Implications for Roadmap

Research identifies a clear build order driven by two hard dependencies: (1) the Robot facade API must be stable before block types are designed — block names map directly to API methods; and (2) the async firmware architecture must be established before any feature is built on top of it, because adding asyncio after the fact requires rewriting every module. The lesson content system is the last dependency in the chain but should begin in parallel with firmware, not after it.

### Phase 1: Firmware Foundation (Async Architecture + HAL)

**Rationale:** Everything else depends on this. The v1 blocking server architecture is the root cause of concurrency failures. This must be the first thing built, not refactored in later. Encoder ISR overhead, PWM frequency, memory budget, and per-unit configuration all belong here.
**Delivers:** Async event loop with 3 concurrent tasks (WiFi, motor PID, sensor read), clean HAL layer from v1 refactor, per-unit config (unique SSID from MAC address), 20kHz PWM (silent motors)
**Addresses:** Table stakes WiFi AP mode, motor control, sensor reading
**Avoids:** Pitfall 1 (monolithic blocking loop), Pitfall 3 (encoder ISR starvation), Pitfall 4 (heap fragmentation), Pitfall 9 (hardcoded SSID)
**Research flag:** NEEDS RESEARCH — uasyncio WebSocket handshake implementation options (community library vs. minimal custom); RP2040 PIO encoder counting vs. IRQ approach

### Phase 2: Robot Facade + HTTP Server (Stable API Contract)

**Rationale:** The Robot facade API is the contract between firmware and the block editor. Locking it before building the block editor prevents a cascade of synchronized changes. The HTTP server (proven in v1's gate8) provides the communication foundation that the React app can develop against using a mock if needed.
**Delivers:** `robot.py` facade with ~10 stable methods (drive, stop, turn, wait_distance, set_led_color, play_tone, read_line, read_obstacle), HTTP routes (GET /status, GET /telemetry, POST /exec with safety sandbox, POST /stop), and exec() globals whitelist + watchdog timer
**Addresses:** Run/Stop controls, real-time execution feedback
**Avoids:** Pitfall 5 (unsafe exec() without safety layer), Pitfall 2 (monolithic server)
**Research flag:** SKIP — HTTP server pattern confirmed working in v1 gate8; Robot facade API is a design decision, not a research question

### Phase 3: React Connection Layer + Telemetry Display

**Rationale:** The React app can develop against a mock HTTP server while firmware Phase 2 is being built in parallel. The connection state machine and heartbeat mechanism must be designed before the block editor so reconnection logic is baked in from the start, not retrofitted.
**Delivers:** Connection state machine (disconnected → connecting → connected → running → stopped), heartbeat + auto-reconnect, telemetry display (speed, heading, sensor readings), WiFi setup UX (QR code, instructions)
**Addresses:** WiFi reconnection resilience (differentiator), cross-platform browser support (table stakes)
**Avoids:** Pitfall 11 (rover/React state divergence on reconnect)
**Research flag:** SKIP — React state machine patterns are well-documented; TanStack Query for WebSocket management is established

### Phase 4: Block Editor + Code Generator

**Rationale:** Block types must be defined against the stable Robot facade from Phase 2. The code generator is the primary deliverable of this phase — visual polish comes second. The MVP block set must be frozen to the Phase 6 lesson plan before a line of editor code is written.
**Delivers:** dnd-kit drag-and-drop block workspace, TypeScript block AST representation, MicroPython code generator (recursive tree-walk), generated code syntax validation before transmission, kid-readable error translation layer, block-to-Python code view tab
**Addresses:** Block coding environment (table stakes), block-to-code visibility (table stakes), error messages kids can understand (table stakes)
**Avoids:** Pitfall 7 (block editor scope creep), Pitfall 14 (undebuggable code generation errors)
**Research flag:** NEEDS RESEARCH — dnd-kit accessibility patterns for K-8 UX; block AST schema design for lesson-step block restriction (which blocks are allowed per lesson step)

### Phase 5: WebSocket Upgrade + Real-Time Telemetry

**Rationale:** HTTP polling (v1 pattern) produces 1-second command latency, which is unusable for interactive block execution. WebSocket must be in place before lessons are designed around real-time feedback. This phase upgrades the communication layer without changing the block editor or lesson system.
**Delivers:** WebSocket server on firmware (port 81, asyncio-based), WebSocket client in React (replaces HTTP polling for telemetry), push-based sensor updates at 50-100ms, block execution trace (current executing block broadcast over WebSocket)
**Addresses:** Run/Stop with instant feedback (table stakes), code execution block trace (differentiator)
**Avoids:** Pitfall 6 (HTTP polling latency killing interactive control)
**Research flag:** NEEDS RESEARCH — MicroPython uasyncio WebSocket server implementation; memory impact of WebSocket on Pico W heap; evaluate uwebsockets community library vs. minimal custom implementation

### Phase 6: Lesson Content System + Curriculum

**Rationale:** Lessons are the last component in the dependency chain (they constrain which blocks are available, evaluate telemetry pass criteria, and drive lesson progression). However, lesson content authoring should begin in parallel with Phase 1 — the engineering dependency is late, but the content work is long-lead. Educator involvement must start no later than Phase 4.
**Delivers:** JSON lesson schema (stable v1 format supporting future CMS), 5-8 progressive lessons with narrative arc, Lesson Viewer React component (instructions, hints, progress indicator), lesson pass criteria evaluation (telemetry-check and output-match), localStorage progress persistence
**Addresses:** Step-by-step lessons (table stakes), lesson progress tracking (table stakes), progressive lesson unlock (differentiator)
**Avoids:** Pitfall 8 (engineer-written lessons inaccessible to K-8), Pitfall 10 (gyro drift in multi-turn lessons — tolerate ±15 degrees in lesson criteria)
**Research flag:** SKIP (architecture pattern) + NEEDS EDUCATOR — lesson content requires K-8 curriculum consultant, not additional technical research

### Phase 7: Product Quality + Packaging

**Rationale:** All features exist but the product is not shippable without calibration, firmware pre-flash, out-of-box setup flow, and classroom-deployment documentation. This is not polish — it is the difference between a prototype and a product.
**Delivers:** Per-unit hardware calibration routine (stores tuned constants to flash, not firmware source), pre-flashed firmware + UF2 update procedure (no Thonny required for students), QR code connection setup on robot, classroom IT setup guide, 60-minute stress test (memory stability, reconnect recovery), mDNS (robopico-xxxx.local)
**Addresses:** Documentation/getting started (table stakes), WiFi setup flow (table stakes)
**Avoids:** Pitfall 12 (Thonny dependency in student setup), Pitfall 15 (per-unit hardware variation), Pitfall 2 (classroom AP-mode WiFi failures)
**Research flag:** SKIP — packaging and calibration patterns are well-understood; mDNS on MicroPython has established community implementations

### Phase Ordering Rationale

- Phases 1-2 are strictly serial: asyncio foundation before any server, server before any client code
- Phases 3-4 can begin in parallel once the HTTP API contract (Phase 2) is defined — React Connection Manager can develop against a mock server while Phase 2 firmware is being finalized
- Phase 6 lesson content authoring should begin in parallel with Phase 1, despite the engineering dependency being at Phase 6 — content is long-lead and requires an educator collaborator
- Phase 5 WebSocket upgrade sits between the block editor (Phase 4) and lessons (Phase 6) so that lesson pass criteria can be designed knowing the real-time telemetry capability exists
- Phase 7 cannot compress: quality and packaging require all features to be complete and stable before meaningful stress-testing

### Research Flags

Phases needing deeper research during planning:

- **Phase 1:** uasyncio WebSocket handshake (RFC 6455 in MicroPython) — community library vs. minimal implementation; RP2040 PIO for hardware encoder counting vs. IRQ approach
- **Phase 4:** dnd-kit accessibility and touch patterns for K-8 UX; block AST schema design for per-step block restriction in lesson system
- **Phase 5:** MicroPython uasyncio WebSocket server memory budget on Pico W; evaluate `micropython-lib` uwebsockets library before implementation

Phases with standard, well-documented patterns (skip research-phase):

- **Phase 2:** Robot facade + HTTP server — v1 gate8 is a working reference implementation; exec() sandbox pattern is established
- **Phase 3:** React connection state machine + TanStack Query — well-documented patterns
- **Phase 6 (architecture):** JSON lesson schema + localStorage — standard in offline-first education apps
- **Phase 7:** Pre-flash firmware, UF2 update, mDNS — established patterns for MicroPython kit products

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (firmware) | HIGH | Verified directly against v1 codebase; MicroPython module availability confirmed |
| Stack (web) | MEDIUM | React/Vite/Zustand/dnd-kit choices are well-grounded; package versions need npm verification before scaffolding |
| Stack (WebSocket on MicroPython) | LOW-MEDIUM | Community implementations exist but uasyncio WebSocket handshake must be validated before Phase 5 commits |
| Features (table stakes) | HIGH | Stable and consistent across all K-8 competitors through 2025; directly cross-checked with PROJECT.md scope |
| Features (differentiators) | MEDIUM | WiFi/browser advantage well-documented in teacher pain points; specific curriculum reception unverified |
| Features (competitive pricing) | MEDIUM | 2024-2025 era pricing; re-verify before finalizing product positioning |
| Architecture | HIGH | Based on direct v1 codebase analysis; patterns derived from working gate8/gate9 reference implementations |
| Pitfalls (firmware) | HIGH | Identified directly from v1 code artifacts; asyncio, ISR, heap issues are well-established MicroPython failure modes |
| Pitfalls (block editor scope) | HIGH | Directly documented by Scratch, MakeCode, and custom editor teams; well-understood pattern |
| Pitfalls (classroom deployment) | MEDIUM | Classroom WiFi behavior inferred from domain knowledge; needs real-classroom validation during Phase 7 |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **uasyncio WebSocket implementation:** The lowest-confidence decision in the stack. Phase 1 research should evaluate `micropython-lib` uwebsockets, the community `uwebsocket` implementations, and the feasibility of a minimal custom handshake (RFC 6455 is not large). Do not commit to the WebSocket approach in Phase 5 without a working Pico W proof-of-concept.
- **React bundle size in Pico W flash:** The architecture calls for serving the React app from Pico W's limited flash (target under 400KB gzipped). This must be validated with a Vite production build of the full app before Phase 7. If the target is not achievable, fall back to the hybrid model (app hosted externally at `app.siot.io`, connects to rover's AP network).
- **Educator involvement:** No curriculum expert has been identified. Lesson content (Phase 6) requires a K-8 STEM educator as co-author. This is the highest non-technical gap — engineering can build the lesson system, but the content will fail in schools without educator involvement.
- **Classroom WiFi AP-mode validation:** AP-mode behavior has been validated at the desk, not in a real school environment. Phase 7 must include a classroom pilot with 20+ concurrent rovers before claiming classroom readiness.
- **npm package versions:** STACK.md lists package versions as of training data cutoff (August 2025). Verify Zustand, TanStack Query, dnd-kit, Vitest, and Playwright versions against npm before scaffolding.

## Sources

### Primary (HIGH confidence)
- v1 codebase direct analysis — `config.py`, `lib/motor.py`, `lib/encoder.py`, `lib/mpu6050.py`, `lib/pid.py`, `gates/gate8_wifi_telemetry.py`, `gates/gate9_autonomous.py`
- MicroPython documentation (training data, docs.micropython.org) — asyncio, network.WLAN AP_IF, socket, machine.PWM, machine.Pin.irq
- RP2040 datasheet — dual-core execution, PIO state machines for hardware pulse counting

### Secondary (MEDIUM confidence)
- Training data (knowledge cutoff August 2025): LEGO SPIKE Prime, VEX 123/GO, Makeblock mBot/mBot2, Sphero EDU, Edison Robot, micro:bit product documentation and feature specifications
- MicroPython community: uasyncio WebSocket server patterns, heap fragmentation behavior, PIO encoder counting examples
- React ecosystem: dnd-kit adoption vs. react-beautiful-dnd (Atlassian maintenance status), Vite replacing CRA (deprecated 2023)

### Tertiary (LOW confidence — needs validation)
- uasyncio WebSocket handshake community implementations — must be verified against working Pico W code before Phase 5 commitment
- Classroom WiFi AP-mode behavior in school network environments — inferred from domain knowledge, not tested at scale

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
