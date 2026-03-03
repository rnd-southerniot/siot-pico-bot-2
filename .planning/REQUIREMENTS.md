# Requirements: SIOT Pico Bot 2

**Defined:** 2026-03-03
**Core Value:** A kid can unbox the kit, connect to the rover over WiFi, and complete guided lessons using block coding — learning robotics concepts while having fun.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Firmware

- [ ] **FW-01**: Asyncio-based firmware architecture replacing v1 blocking loop
- [ ] **FW-02**: Motor control with encoder feedback for precise distance movement
- [ ] **FW-03**: IMU-6050 integration for accurate turning (e.g., "turn exactly 90 degrees")
- [ ] **FW-04**: Line following sensor support via IR sensors
- [ ] **FW-05**: Obstacle detection sensor support
- [ ] **FW-06**: Light/color sensor support
- [ ] **FW-07**: Hardware watchdog for exec() safety (prevent runaway student code)
- [ ] **FW-08**: PIO state machines for hardware encoder counting

### WiFi & Communication

- [ ] **WIFI-01**: WiFi AP mode — rover creates its own hotspot
- [ ] **WIFI-02**: Per-unit unique SSID to avoid classroom conflicts
- [ ] **WIFI-03**: JSON-based command/telemetry protocol
- [ ] **WIFI-04**: WebSocket for real-time bidirectional communication
- [ ] **WIFI-05**: Graceful WiFi reconnection without page refresh
- [ ] **WIFI-06**: mDNS discovery — connect by name instead of IP

### Block Editor

- [ ] **EDIT-01**: Custom drag-and-drop block coding editor in React
- [ ] **EDIT-02**: Motor control blocks (forward, backward, turn, precise distance/angle)
- [ ] **EDIT-03**: Sensor reading blocks (line, distance, color, IMU values)
- [ ] **EDIT-04**: Block-to-MicroPython code generation
- [ ] **EDIT-05**: Run/Stop controls with <1s feedback latency
- [ ] **EDIT-06**: Kid-readable error messages (intercept Python tracebacks)
- [ ] **EDIT-07**: Block-to-Python code view panel
- [ ] **EDIT-08**: Code execution trace — highlight currently running block
- [ ] **EDIT-09**: Save/load programs via LocalStorage
- [ ] **EDIT-10**: SIOT branded look and feel throughout

### Lessons

- [ ] **LESS-01**: At least 5-8 step-by-step structured lessons
- [ ] **LESS-02**: Progressive difficulty with sequential lesson unlocking
- [ ] **LESS-03**: Lesson completion tracking (completed/not completed per lesson)
- [ ] **LESS-04**: Student-facing lesson UI embedded in the block editor
- [ ] **LESS-05**: Narrative curriculum arc (themed mission story)
- [ ] **LESS-06**: Lesson-specific block restrictions (only relevant blocks shown)

### Product Quality

- [ ] **PROD-01**: Getting Started guide (digital, printable)
- [ ] **PROD-02**: Cross-platform browser support (Chromebook, Windows, Mac)
- [ ] **PROD-03**: Visual robot feedback via LED (running/stopped indicator)
- [ ] **PROD-04**: QR code on rover for instant WiFi setup
- [ ] **PROD-05**: Pre-flash firmware — robots ship ready to use

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Teacher Tools

- **TEACH-01**: Teacher dashboard for class management
- **TEACH-02**: LMS integration (Canvas, Google Classroom)
- **TEACH-03**: CSV/PDF export for lesson completion reports

### Advanced Features

- **ADV-01**: Multi-robot coordination
- **ADV-02**: Open-ended challenge/sandbox mode
- **ADV-03**: Cloud program storage with account system
- **ADV-04**: PWM frequency above audible range (20kHz+)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Mobile native app (iOS/Android) | Web-first approach; responsive design handles tablets; app store delays |
| Real-time video streaming | Adds hardware cost (camera), Pico W lacks processing headroom |
| Bluetooth connectivity | WiFi AP chosen for classroom reliability; BT pairing with 30 devices is chaos |
| Account/login system | COPPA compliance complexity; LocalStorage sufficient for v1 |
| AI-generated lesson suggestions | Backend dependency, hallucination risk in educational context |
| C/C++ firmware exposure | MicroPython chosen for readability; exposing C defeats educational goal |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| — | — | — |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 0
- Unmapped: 30 ⚠️

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after initial definition*
