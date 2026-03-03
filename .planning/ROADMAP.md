# Roadmap: SIOT Pico Bot 2

## Overview

Seven phases build from the ground up: async firmware foundation first, then the robot API contract that binds firmware to the browser, then the React connection layer, then the block editor on top of a stable API, then WebSocket for real-time execution trace, then the lesson curriculum that makes it a product, and finally packaging and quality hardening that makes it sellable. Each phase delivers one complete, verifiable capability. Phases 1-2 are strictly serial; Phases 3-4 can run in parallel once the HTTP API contract is defined; Phase 5 sits between the editor and lessons so lesson pass criteria can rely on real-time telemetry.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Firmware Foundation** - Async MicroPython architecture with full HAL layer covering all sensors and motors
- [ ] **Phase 2: Robot API + HTTP Server** - Stable robot facade API, HTTP server, and exec() safety sandbox
- [ ] **Phase 3: React Connection Layer** - WiFi connection state machine, reconnection, and mDNS discovery
- [ ] **Phase 4: Block Editor + Code Generator** - Custom drag-and-drop block editor with MicroPython code generation
- [ ] **Phase 5: WebSocket + Real-Time Execution** - WebSocket upgrade for sub-100ms telemetry and block execution trace
- [ ] **Phase 6: Lesson System + Curriculum** - JSON-driven lesson system with 5-8 progressive lessons and narrative arc
- [ ] **Phase 7: Product Quality + Packaging** - Sellable product hardening: pre-flash, QR setup, documentation, cross-platform validation

## Phase Details

### Phase 1: Firmware Foundation
**Goal**: The rover runs a stable async MicroPython firmware with complete hardware abstraction for all sensors, motors, and safety systems
**Depends on**: Nothing (first phase)
**Requirements**: FW-01, FW-02, FW-03, FW-04, FW-05, FW-06, FW-07, FW-08
**Success Criteria** (what must be TRUE):
  1. The rover boots and runs three concurrent async tasks (WiFi, motor PID, sensor poll) without blocking
  2. A motor command causes the rover to move a precise distance using encoder feedback
  3. A turn command uses the IMU-6050 to rotate an accurate angle (within ±5 degrees)
  4. All sensors (IR line, obstacle, light/color) return readings on demand without crashing the event loop
  5. Student-runaway code triggers the hardware watchdog and the rover stops safely within 500ms
**Plans**: TBD

### Phase 2: Robot API + HTTP Server
**Goal**: A stable, documented robot facade API is locked and the HTTP server accepts exec() commands with a safety sandbox — the contract that all browser code will be written against
**Depends on**: Phase 1
**Requirements**: WIFI-01, WIFI-02, WIFI-03
**Success Criteria** (what must be TRUE):
  1. The rover creates its own WiFi hotspot with a unique SSID derived from its MAC address
  2. A browser can reach the rover at a fixed IP and receive a JSON status response
  3. A POST /exec request runs a robot.py facade method and the rover responds
  4. Injecting `import machine` into exec() is rejected and the rover does not crash
**Plans**: TBD

### Phase 3: React Connection Layer
**Goal**: The React app reliably connects to the rover, survives disconnects, and can be discovered by name instead of IP address
**Depends on**: Phase 2
**Requirements**: WIFI-05, WIFI-06
**Success Criteria** (what must be TRUE):
  1. After a rover WiFi dropout, the browser reconnects automatically without a page refresh
  2. The user can reach the rover by typing a name (e.g., robopico-a3f2.local) instead of an IP address
  3. Connection state (disconnected, connecting, connected) is visible to the user at all times
**Plans**: TBD

### Phase 4: Block Editor + Code Generator
**Goal**: A student can build a program by dragging blocks, see the equivalent MicroPython code, run it on the rover, and receive a kid-readable error if something goes wrong
**Depends on**: Phase 2
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-09, EDIT-10
**Success Criteria** (what must be TRUE):
  1. A student drags blocks onto a workspace and the blocks snap together to form a program
  2. The generated MicroPython code panel updates live as blocks are added or rearranged
  3. Clicking Run sends the program to the rover and the rover responds within 1 second
  4. A block program that causes a Python error shows a plain-English message, not a traceback
  5. A student's block program persists in the browser after closing and reopening the tab
**Plans**: TBD

### Phase 5: WebSocket + Real-Time Execution
**Goal**: Commands and telemetry flow over WebSocket so the rover feels instantly responsive and the currently-running block is highlighted in real time
**Depends on**: Phase 4
**Requirements**: WIFI-04, EDIT-08
**Success Criteria** (what must be TRUE):
  1. Sensor telemetry values update in the browser within 100ms of changing on the rover
  2. While a program runs, the block currently executing is visually highlighted in the editor
  3. Clicking Stop halts the rover within 200ms from any connection quality the classroom WiFi allows
**Plans**: TBD

### Phase 6: Lesson System + Curriculum
**Goal**: A student can open the app, find a lesson, follow step-by-step instructions with only the relevant blocks available, complete the lesson, and have their progress saved
**Depends on**: Phase 5
**Requirements**: LESS-01, LESS-02, LESS-03, LESS-04, LESS-05, LESS-06
**Success Criteria** (what must be TRUE):
  1. The app presents at least 5 structured lessons with step-by-step instructions visible alongside the block editor
  2. Completing a lesson unlocks the next one; a student cannot skip ahead
  3. Only the blocks relevant to the current lesson step appear in the block palette
  4. A student's completed lessons are remembered after closing and reopening the app
  5. All lessons follow a connected narrative theme that gives the student a reason to keep going
**Plans**: TBD

### Phase 7: Product Quality + Packaging
**Goal**: A teacher can unbox a rover, have a student connect in under 60 seconds using the QR code, and complete the first lesson on a Chromebook, Windows laptop, or Mac without installing anything
**Depends on**: Phase 6
**Requirements**: PROD-01, PROD-02, PROD-03, PROD-04, PROD-05
**Success Criteria** (what must be TRUE):
  1. The rover ships with firmware already flashed — no Thonny, no terminal, no setup steps for the student
  2. Scanning the QR code on the rover connects the browser to the block editor without typing an IP address
  3. The LED on the rover changes color to show running vs. stopped state without any app configuration
  4. The block editor works identically on Chromebook, Windows, and Mac in Chrome/Firefox/Edge
  5. A printed or digital Getting Started guide lets a teacher run the first lesson without prior robotics knowledge
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

Note: Phases 3 and 4 both depend on Phase 2 and can execute in parallel.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Firmware Foundation | 0/TBD | Not started | - |
| 2. Robot API + HTTP Server | 0/TBD | Not started | - |
| 3. React Connection Layer | 0/TBD | Not started | - |
| 4. Block Editor + Code Generator | 0/TBD | Not started | - |
| 5. WebSocket + Real-Time Execution | 0/TBD | Not started | - |
| 6. Lesson System + Curriculum | 0/TBD | Not started | - |
| 7. Product Quality + Packaging | 0/TBD | Not started | - |
