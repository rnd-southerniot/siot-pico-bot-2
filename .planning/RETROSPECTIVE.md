# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Firmware Foundation + Robot API

**Shipped:** 2026-03-05
**Phases:** 3 | **Plans:** 7 | **Sessions:** ~3

### What Was Built
- Async MicroPython firmware with 5-task uasyncio event loop (motor PID, sensor poll, WiFi server, IMU heading, watchdog)
- Complete hardware abstraction layer: PIO encoders, motors, IMU, IR/ultrasonic/color sensors, NeoPixel LED
- Robot API facade with exec() sandbox blocking all imports — safe student code execution
- WiFi AP with MAC-derived unique SSID + Microdot HTTP server with CORS
- Two-layer safety system: hardware WDT (8s) + software motor timeout (30s)
- 7 verification gates for on-device and static testing

### What Worked
- Phase-by-phase bottom-up build order — firmware first, then API on top — meant each layer had a stable foundation
- Dependency injection pattern (HeadingTracker, I2C bus) avoided circular init problems cleanly
- Audit + Phase 8 gap closure cycle caught 3 real defects (FW-07 tracking, dual I2C, stale import) before they compounded
- Fast execution: ~3 min/plan average, 7 plans in ~21 min total

### What Was Inefficient
- ROADMAP.md initially marked Phase 8 as `[ ] 0/1 Not started` even after completion — state sync between STATE.md and ROADMAP.md requires manual attention
- First audit found gaps that required creating Phase 8 and re-auditing — could have caught dual I2C and gate8 import issues during Phase 2 execution with tighter cross-phase integration checks

### Patterns Established
- `set_*(dependency)` injection pattern for shared resources (HeadingTracker, I2C bus)
- gate scripts as verification contracts — each plan delivers runnable proof
- Two-layer safety: hardware WDT as backstop, software timeout as first line
- `run_student_code()` always returns dict, never raises — safe for HTTP response encoding

### Key Lessons
1. Audit-then-fix is worth the cost — Phase 8 caught 3 real defects that would have cascaded into Phase 3+ work
2. PIO state machines are powerful but SM ID conflicts are subtle — document block allocation early (block 0 = NeoPixel, block 1 = encoders)
3. exec() sandbox must block ALL imports, not allow-list — any module can reach `machine` indirectly

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet (balanced profile)
- Sessions: ~3
- Notable: 3 min/plan average — firmware plans executed efficiently due to clear gate-based verification

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 3 | Established audit-fix cycle, dependency injection pattern |

### Cumulative Quality

| Milestone | Gates | Coverage | Tech Debt Items |
|-----------|-------|----------|-----------------|
| v1.0 | 7 | 11/11 reqs | 6 (all low severity) |

### Top Lessons (Verified Across Milestones)

1. Bottom-up build order with gate verification at each layer prevents integration surprises
2. Audit-then-fix cycles are worth the overhead — catches defects before they compound
