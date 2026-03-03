# Technology Stack

**Project:** SIOT Pico Bot 2 — STEM Robotics Kit
**Researched:** 2026-03-03
**Confidence note:** WebSearch and WebFetch were unavailable during research. Firmware layer assessed from v1 codebase (HIGH confidence). Web stack assessed from training data (MEDIUM confidence, flagged where version verification is needed).

---

## Recommended Stack

### Firmware — Raspberry Pi Pico W

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| MicroPython | 1.23.x (latest stable for RP2040) | Runtime on Pico W | Mandated by project; readable, educational, fast-iteration — matches v1 pattern; `network`, `socket`, `machine`, `struct`, `json` all built-in |
| `machine.PWM` | built-in | Motor control (MX1515H H-bridge) | Already proven in v1 `motor.py`; PWM freq 1000 Hz works well with MX1515H up to 20kHz |
| `machine.Pin.irq()` | built-in | Quadrature encoder tick counting | ISR-based counting is the correct pattern for Pico; proven in v1 `encoder.py` |
| `machine.I2C` | built-in | MPU6050 / GY-521 communication | 400kHz fast mode; register-level reads with `struct.unpack` proven in v1 |
| `machine.Pin` | built-in | IR line sensors, obstacle detection, buttons, NeoPixel control | Standard GPIO; v1 uses GP20/GP21 for buttons |
| `network` + `socket` | built-in | WiFi AP mode + HTTP/WebSocket server | Pico W ships with CYW43 WiFi; `network.WLAN(network.AP_IF)` is standard AP pattern |
| `asyncio` (uasyncio) | built-in since MicroPython 1.19 | Concurrent WiFi serving + sensor polling | Critical for v2: v1's blocking `socket.accept()` loop cannot do WiFi and PID simultaneously; `asyncio` is the standard fix |
| `json` | built-in | Serialise sensor telemetry and command messages | Already used in v1 Gate 8 |
| `neopixel` | built-in | WS2812 NeoPixel control (GP18, 2 LEDs) | Built-in driver; proven in v1 |

**Confidence:** HIGH — verified against v1 codebase and MicroPython built-in module list (training data, MicroPython 1.20+ stable).

**Version note:** Verify current stable UF2 at https://micropython.org/download/RPI_PICO_W/ before shipping. As of knowledge cutoff (August 2025) v1.23 was the stable series for RP2040-W.

---

### Communication Protocol — Pico W ↔ Browser

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| WiFi AP mode (`network.AP_IF`) | MicroPython built-in | Rover creates its own hotspot | Classroom-safe: no dependency on school WiFi infrastructure; student connects phone/laptop directly to rover AP |
| WebSocket over TCP port 81 | MicroPython socket API | Bidirectional command/telemetry | Replaces v1's HTTP polling; real-time block execution commands need push semantics, not request/response; WebSocket fits within MicroPython's raw socket API without external libs |
| HTTP on port 80 | MicroPython socket API | Serve the React app bundle | Pico W serves a single-page app from flash storage; eliminates need for a separate CDN or server for classroom use |
| JSON message protocol | built-in | Command messages and sensor telemetry | Simple, human-readable, easy to debug; fits within Pico W RAM budget |

**Confidence:** MEDIUM — WebSocket via raw sockets on MicroPython is well-documented community practice; the specific approach of serving the React bundle from Pico flash is a design decision with tradeoffs (see Pitfalls). Verify MicroPython WebSocket handshake implementations before committing.

**Alternative considered — HTTP REST polling:** v1 uses blocking HTTP with 1s auto-refresh. Works for telemetry dashboards but is unusable for block command execution (commands need <100ms round trip, not 1s poll cycles). Do not use for v2.

**Alternative considered — MQTT over WiFi:** Requires a broker process (mosquitto), adds infrastructure complexity in classrooms. Ruled out.

---

### Frontend — React Web Application

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.x | UI component framework | Mandated — existing v1 codebase; React 18 concurrent features improve drag-and-drop responsiveness |
| TypeScript | 5.x | Type safety across block schema, code generator, and API layer | Block editor has complex data structures (block types, workspace state, generated code); TypeScript prevents category of bugs that are hard to catch at runtime |
| Vite | 5.x | Build tool and dev server | Replaces CRA (dead); fast HMR; produces small bundles suitable for serving from Pico W flash; no server-side rendering needed |
| Tailwind CSS | 3.x | Styling | Utility-first; works well for custom UI without fighting a component library's opinions; keeps bundle small; kid-friendly theming via CSS variables |
| Zustand | 4.x | State management for block workspace + lesson state | Simpler than Redux for this use case; block workspace state, lesson progress, WiFi connection status all fit in a few Zustand slices |
| React Query (TanStack Query) | 5.x | WebSocket connection management and sensor data | Manages connection lifecycle, reconnection, error states; removes boilerplate from WiFi communication layer |
| react-dnd or dnd-kit | dnd-kit 6.x | Drag-and-drop for block editor | dnd-kit is the current (2024-2025) standard for React DnD: accessible, no HTML5 drag API quirks, works on touch (tablets in classrooms) |

**Confidence:** MEDIUM — React 18, TypeScript 5, Vite 5 are well-established. Package versions should be verified against npm before scaffolding. dnd-kit is the recommended choice over react-beautiful-dnd (maintenance mode since 2023) and react-dnd (less active).

---

### Custom Block Editor (No Blockly)

The project explicitly chose NOT to use Blockly. This is the right call for a sellable product — Blockly requires significant custom theming to avoid looking like Scratch clone, and its API surface creates friction for custom block types.

| Technology | Purpose | Why |
|------------|---------|-----|
| Custom block editor built on React + dnd-kit | Drag-and-drop block workspace | Full SIOT branding, no Blockly licensing concerns, custom block shapes |
| Custom code generator (TypeScript AST → MicroPython string) | Transform block graph to MicroPython | Blocks map 1:1 to MicroPython constructs; simple recursive tree-walk generator is sufficient — no full AST library needed |
| Monaco Editor (optional, hidden) | Show generated MicroPython code to curious students | Familiar (VS Code engine), syntax highlighting for Python, read-only view only |

**Confidence on custom editor approach:** MEDIUM — custom block editors are non-trivial. The main risk is scope creep. The key architectural constraint is to design the block schema as a pure data structure first (independent of rendering), then build the renderer and code generator separately. This makes testing tractable.

**Alternatives explicitly ruled out:**
- **Blockly (Google):** Full-featured but heavy, default Scratch aesthetic requires major theming investment, Google-dependency. Not chosen — correct decision.
- **Scratch 3.0 blocks component:** MIT licensed, but the component is designed specifically for Scratch's architecture and is not extraction-friendly.
- **Snap!:** Education-focused but not embeddable as a library.

---

### Lesson / Curriculum System

| Technology | Purpose | Why |
|------------|---------|-----|
| JSON/YAML lesson definitions (bundled with app) | Define lesson steps, objectives, hints, unlock conditions | Static content; no database needed for v1; lessons are authored by SIOT, not user-generated |
| React component tree for lesson renderer | Display step instructions, media, progress | Leverages existing React investment; lesson UI is a sidebar alongside the block editor |
| localStorage (browser) | Persist lesson progress across sessions | No backend needed; students return to where they left off; works offline (Pico AP mode) |

**Confidence:** HIGH — this pattern (static JSON lessons + browser localStorage) is standard in education web apps and matches the offline-first constraint of the Pico AP mode deployment.

**Alternative ruled out — Markdown files for lessons:** MDX is attractive but adds build complexity for dynamic elements (hint reveals, progress gates). Use JSON with embedded metadata.

**Alternative ruled out — Backend database for progress:** Adds a server requirement that breaks the classroom model (no school server, no internet required).

---

### Development Tooling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Thonny IDE | 4.x | Flash firmware, REPL, file upload to Pico W | Standard MicroPython IDE; what the README already prescribes for students; the friction-free path for firmware development |
| mpremote | 0.6.x | Scripted file sync from CI / Makefile | CLI tool for bulk file upload; useful for dev iteration without Thonny GUI |
| pytest + pytest-micropython (or unittest on device) | latest | Firmware unit tests | Custom pure-Python modules (PID, encoder math, code generator) can be unit-tested; hardware-dependent modules tested via gate runs |
| Vitest | 1.x | Frontend unit tests | Pairs with Vite; fast; good TypeScript support; test the block-to-code generator exhaustively |
| Playwright | 1.x | Frontend E2E / integration tests | Test lesson flows, block editor interactions; can mock the WebSocket layer |

**Confidence:** MEDIUM — Thonny and mpremote are established tools. pytest on host for pure MicroPython modules is a proven pattern. Vitest/Playwright versions should be verified.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Firmware runtime | MicroPython | CircuitPython | MicroPython has better `asyncio` support and more mature networking for Pico W; CircuitPython is strong on Adafruit boards but not the target here |
| Firmware runtime | MicroPython | C/C++ SDK | Project constraint: MicroPython chosen for readability and educational value |
| WiFi comm protocol | WebSocket | HTTP polling | HTTP polling (v1 approach) cannot support real-time command execution; 1s round-trip unacceptable |
| WiFi comm protocol | WebSocket | BLE | Project explicitly ruled out Bluetooth |
| WiFi comm protocol | WebSocket | MQTT | Requires broker infrastructure; impractical in classroom AP mode |
| WiFi deployment | AP mode (rover is AP) | Station mode (connect to school WiFi) | School network restrictions (captive portals, device isolation) make station mode unreliable; AP mode works everywhere |
| Frontend build | Vite | Create React App | CRA is deprecated and unmaintained since 2023 |
| Frontend build | Vite | Next.js | No SSR needed; Next.js adds complexity and a server requirement incompatible with Pico-served SPA model |
| State management | Zustand | Redux Toolkit | Redux adds ceremony; block editor state is local and not shared across network — Zustand is sufficient |
| Drag-and-drop | dnd-kit | react-beautiful-dnd | react-beautiful-dnd is in maintenance mode (Atlassian), no active development |
| Drag-and-drop | dnd-kit | react-dnd | Less active, weaker touch support — problematic for tablet use in classrooms |
| Block editor | Custom | Blockly | Project decision: full branding control, no Blockly theming debt |
| Lesson storage | localStorage | Backend database | No server in classroom AP-mode deployment |

---

## Installation

### Firmware (on Pico W)

```bash
# 1. Download latest MicroPython UF2 for Pico W from:
#    https://micropython.org/download/RPI_PICO_W/
# 2. Hold BOOTSEL, connect USB → drag UF2 to RPI-RP2 volume
# 3. Use mpremote or Thonny to upload project files:
mpremote connect /dev/tty.usbmodem* cp -r lib/ :lib/
mpremote connect /dev/tty.usbmodem* cp config.py main.py :
```

### Frontend

```bash
# Scaffold (if starting fresh from v1 React code)
npm create vite@latest siot-editor -- --template react-ts

# Core dependencies
npm install zustand @tanstack/react-query @dnd-kit/core @dnd-kit/sortable

# Styling
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Optional: Monaco for code view
npm install @monaco-editor/react

# Dev dependencies
npm install -D vitest @vitest/ui @playwright/test
```

---

## Critical Architecture Constraints

These constraints shape every technology decision:

1. **Pico W RAM budget (~200KB free for user code):** Avoid large MicroPython libraries. Do not use third-party HTTP frameworks (picoweb, microdot) — raw socket server with asyncio is sufficient and keeps RAM overhead low. Serving the React bundle from Pico flash requires the bundle to be under ~1MB (Vite + tree-shaking achieves this).

2. **No internet in classroom:** The React app must work fully offline once loaded from the Pico. No CDN imports, no external API calls, no Google Fonts with online URLs. Bundle everything.

3. **Concurrent firmware tasks:** WiFi server + PID loop + sensor reads must run concurrently. This is the primary reason to adopt `asyncio` (uasyncio) for v2. The v1 blocking socket loop cannot do this.

4. **Touch support for block editor:** Classroom tablets are common. dnd-kit handles pointer events correctly; HTML5 drag API does not work on touch.

5. **MicroPython asyncio WebSocket:** Implementing WebSocket handshake (RFC 6455) in MicroPython asyncio requires care. Community implementations exist (e.g., `uwebsockets`). Evaluate whether to use a lightweight third-party library or implement the minimal handshake needed. Keep it minimal — the protocol payload is simple JSON commands, not binary streams.

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| MicroPython module availability (asyncio, network, socket, machine) | v1 codebase + MicroPython docs (training data, docs.micropython.org) | HIGH |
| Pico W AP mode via `network.WLAN(network.AP_IF)` | v1 `gate8_wifi_telemetry.py` (direct inspection) | HIGH |
| Hardware pin assignments | v1 `config.py` (direct inspection) | HIGH |
| Cytron Robo Pico / MX1515H details | v1 `config.py`, `motor.py`, `README.md` | HIGH |
| react-beautiful-dnd maintenance status | Training data (Atlassian archived repo ~2023) | MEDIUM — verify |
| dnd-kit as current standard | Training data (community adoption 2023-2025) | MEDIUM — verify current npm weekly downloads |
| Vite replacing CRA | Training data (CRA deprecated 2023) | HIGH |
| MicroPython version 1.23 | Training data (knowledge cutoff Aug 2025) | MEDIUM — verify at micropython.org/download |
| Zustand v4 / React Query v5 | Training data | MEDIUM — verify npm |
| uasyncio WebSocket community implementations | Training data | LOW — must verify before implementation phase |
