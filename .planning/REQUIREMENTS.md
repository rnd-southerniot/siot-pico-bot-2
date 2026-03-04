# Requirements: SIOT Pico Bot 2

**Defined:** 2026-03-03
**Core Value:** A kid can unbox the kit, connect to the rover over WiFi, and complete guided lessons using block coding — learning robotics concepts while having fun.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Firmware

- [x] **FW-01**: Asyncio-based firmware architecture replacing v1 blocking loop *(completed 01-01, 2026-03-03)*
- [x] **FW-02**: Motor control with encoder feedback for precise distance movement
- [x] **FW-03**: IMU-6050 integration for accurate turning (e.g., "turn exactly 90 degrees") *(completed 01-03, 2026-03-03)*
- [x] **FW-04**: Line following sensor support via IR sensors *(completed 01-03, 2026-03-03)*
- [x] **FW-05**: Obstacle detection sensor support *(completed 01-03, 2026-03-03)*
- [x] **FW-06**: Light/color sensor support *(completed 01-03, 2026-03-03)*
- [ ] **FW-07**: Hardware watchdog for exec() safety (prevent runaway student code)
- [x] **FW-08**: PIO state machines for hardware encoder counting

### WiFi & Communication

- [ ] **WIFI-01**: WiFi AP mode — rover creates its own hotspot
- [ ] **WIFI-02**: Per-unit unique SSID to avoid classroom conflicts
- [x] **WIFI-03**: JSON-based command/telemetry protocol
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
| FW-01 | Phase 1 | Pending |
| FW-02 | Phase 1 | Complete |
| FW-03 | Phase 1 | Complete |
| FW-04 | Phase 1 | Complete |
| FW-05 | Phase 1 | Complete |
| FW-06 | Phase 1 | Complete |
| FW-07 | Phase 1 | Pending |
| FW-08 | Phase 1 | Complete |
| WIFI-01 | Phase 2 | Pending |
| WIFI-02 | Phase 2 | Pending |
| WIFI-03 | Phase 2 | Complete |
| WIFI-04 | Phase 5 | Pending |
| WIFI-05 | Phase 3 | Pending |
| WIFI-06 | Phase 3 | Pending |
| EDIT-01 | Phase 4 | Pending |
| EDIT-02 | Phase 4 | Pending |
| EDIT-03 | Phase 4 | Pending |
| EDIT-04 | Phase 4 | Pending |
| EDIT-05 | Phase 4 | Pending |
| EDIT-06 | Phase 4 | Pending |
| EDIT-07 | Phase 4 | Pending |
| EDIT-08 | Phase 5 | Pending |
| EDIT-09 | Phase 4 | Pending |
| EDIT-10 | Phase 4 | Pending |
| LESS-01 | Phase 6 | Pending |
| LESS-02 | Phase 6 | Pending |
| LESS-03 | Phase 6 | Pending |
| LESS-04 | Phase 6 | Pending |
| LESS-05 | Phase 6 | Pending |
| LESS-06 | Phase 6 | Pending |
| PROD-01 | Phase 7 | Pending |
| PROD-02 | Phase 7 | Pending |
| PROD-03 | Phase 7 | Pending |
| PROD-04 | Phase 7 | Pending |
| PROD-05 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation*
