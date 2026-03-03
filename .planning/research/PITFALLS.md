# Domain Pitfalls

**Domain:** K-8 STEM Robotics Kit — Pico W firmware, custom block editor, WiFi control, step-by-step lessons
**Researched:** 2026-03-03
**Confidence:** HIGH (primary evidence from v1 codebase analysis + domain knowledge of MicroPython/WebSocket/block coding ecosystems)

---

## Critical Pitfalls

Mistakes that cause rewrites or make the product unsellable.

---

### Pitfall 1: Monolithic Firmware With No Async Event Loop

**What goes wrong:** The v1 architecture (as seen in `gate8_wifi_telemetry.py`) uses a blocking `while True` HTTP accept loop. Once WiFi serving starts, nothing else runs — no motor control, no sensor polling, no button handling. The WiFi gate literally `sys.path.insert` hacks its way around module isolation and then runs an infinite blocking serve loop. When you try to add real-time motor + WiFi, you have two competing infinite loops with no coordination mechanism.

**Why it happens:** It is natural to write sequential MicroPython — it works fine for hardware tests in isolation. The mistake is carrying this pattern into the product firmware where multiple concerns (servo WiFi, motor PID, sensor polling, lesson state) must interleave. MicroPython's `uasyncio` exists precisely for this, but adding it after the fact requires rewriting every module.

**Consequences:**
- Motor control freezes when a browser makes an HTTP request (hundreds of ms blocking)
- Sensor interrupts fire but their results are never consumed while serving
- Firmware becomes impossible to extend without total rewrite (this is what killed v1)
- WiFi dropouts cause the robot to hang in `s.accept()` indefinitely

**Prevention:**
- Design the firmware around a single `asyncio` event loop from day one
- Every subsystem (WiFi server, motor PID, sensor read, LED feedback) runs as an `async` coroutine or uses `asyncio.create_task()`
- HTTP server uses `asyncio.StreamReader/StreamWriter` (MicroPython `uasyncio` has this)
- Never use `time.sleep()` in the main firmware path — use `asyncio.sleep_ms()` exclusively
- Validate the async architecture with a toy 3-task proof-of-concept before building features

**Warning signs:**
- Any firmware file that imports `socket` and runs `while True: s.accept()` at the top level
- Motor or sensor functions that use `time.sleep()` inside a loop meant to run alongside WiFi
- Gate tests passing individually but failing when combined

**Phase:** Firmware foundation phase (must be first, everything else builds on it)

---

### Pitfall 2: WiFi AP Mode Breaking in Classroom Environments

**What goes wrong:** The v1 WiFi design uses AP mode (rover creates its own network, `RoboPico-Lab`). This works on a desk but classrooms have three failure modes: (1) school IT blocks ad-hoc/hotspot networks entirely, (2) students connect 30 rovers and IP collision chaos ensues, (3) browser HTTPS-only policies block `http://192.168.4.1` (Chrome flags non-HTTPS as insecure in some school MDM configurations).

**Why it happens:** AP mode is the easiest demo setup and it works perfectly for a single-device prototype. Nobody tests it in a classroom with 25 students simultaneously.

**Consequences:**
- Product cannot be used in the primary sales channel (schools)
- IT administrators block the product entirely
- Students are stuck at connection step and never reach the lesson

**Prevention:**
- Support both AP mode (default, works at home) and STA mode (join school WiFi, for classroom use)
- Make the SSID configurable — never hardcode it; even `RoboPico-Lab` for 30 rovers creates chaos
- Embed a mDNS/zeroconf responder so students can reach `http://robopico-01.local/` instead of raw IP
- Test connection flow with a 12-year-old operating it with zero instructions — time-to-connected must be under 60 seconds
- Consider a QR code on the robot that encodes the connection URL

**Warning signs:**
- Password hardcoded in `config.py` with no user-facing way to change it
- Single fixed IP `192.168.4.1` with no mDNS fallback
- No documentation for classroom IT setup

**Phase:** WiFi/communication phase; also surfaced in lesson/onboarding phase

---

### Pitfall 3: Blocking Encoder ISRs Corrupting Motor PWM Timing

**What goes wrong:** The Pico W's RP2040 uses software PWM (the MX1515H motor driver takes raw PWM signals). Hall encoder interrupts fire at 252 ticks/rev x 300 RPM = 1,260 interrupts/second per motor (2,520 total). If the ISR body does anything slow (floating point, dictionary operations, function calls), it starves the PWM timer. Result: motors stutter, encoder counts drop pulses, PID loops get wrong velocity estimates, and the robot drives erratically.

**Why it happens:** Easy to write an ISR that does too much. Even incrementing a Python counter in an ISR is slow compared to C — MicroPython ISRs are much heavier than C ISRs. The existing `encoder.py` uses IRQ-based counting which is correct in principle but must be kept absolutely minimal.

**Consequences:**
- Encoder counts are unreliable at high motor speeds
- PID controller gets incorrect velocity feedback and destabilizes
- Motor behavior is inconsistent between identical robots (timing-sensitive)

**Prevention:**
- ISR body must be a single atomic integer increment — nothing else
- Use `micropython.schedule()` for any processing that needs to happen in response to encoder events
- Consider using PIO (Programmable I/O) state machines for encoder counting — the RP2040 has 8 PIO state machines that count pulses in hardware without ISR overhead
- Profile ISR execution time early: use a GPIO toggle to measure ISR duration on an oscilloscope or logic analyzer
- Run encoder IRQ tests at full motor speed before declaring them working

**Warning signs:**
- Encoder counts that decrease or are non-monotonic at high speeds
- PID loop oscillation that disappears when motor speed is reduced
- `gc.collect()` or any allocation inside an ISR

**Phase:** Firmware foundation / motor+encoder subsystem phase

---

### Pitfall 4: MicroPython Memory Fragmentation Causing Random Crashes

**What goes wrong:** The Pico W has ~240KB of usable heap for MicroPython. String concatenation, large JSON objects, HTML template substitution (as seen in `gate8_wifi_telemetry.py` with `html.replace()` chains), and repeated allocation/deallocation cause heap fragmentation. The garbage collector cannot compact memory. After hours of operation (or in a classroom lesson that runs 60+ minutes), the firmware crashes with `MemoryError` or silent hangs. This is catastrophic for a sellable product.

**Why it happens:** The v1 gate architecture builds large HTML strings (the full telemetry dashboard is embedded as a Python string) and rebuilds it on every HTTP request using repeated `.replace()` calls — each one allocates a new string. In a school session, 30 browser refreshes means 30 × (5 string allocations per request) = 150 heap objects that must be GC'd. Eventually fragmentation wins.

**Consequences:**
- Random crashes during lessons with no clear error message shown to student
- Crashes are non-reproducible (depend on exact allocation history)
- Support nightmare: "my robot stopped working" with no log

**Prevention:**
- Never build large strings with concatenation in a loop — use pre-allocated `bytearray` buffers or `io.BytesIO`
- Move all HTML/static content to files on the Pico W's flash filesystem; serve them by reading file chunks rather than loading the whole string into RAM
- Use a minimal JSON API (not HTML) as the primary communication channel; serve the UI from the React web app, not from the Pico W
- Call `gc.collect()` explicitly at safe points (between requests, between lessons)
- Monitor `gc.mem_free()` in telemetry; log and alert if below a threshold (e.g., < 50KB)
- Test with a 60-minute simulated lesson session before shipping

**Warning signs:**
- HTML templates embedded as Python string literals
- String `.replace()` chains on every request
- No `gc.collect()` calls in long-running loops
- `gc.mem_free()` trending downward over time during a session

**Phase:** Firmware foundation phase; validation in product-quality phase

---

### Pitfall 5: Block-to-Code Generation Without an Execution Safety Layer

**What goes wrong:** The block editor generates MicroPython code and sends it to the rover for execution. A student creates a block program that runs the motors forever with no stop condition. Or they create an infinite `repeat` block that never yields to the WiFi coroutine. Or they generate syntactically valid but semantically dangerous code (`motor.drive(100)` with no timeout). The robot escapes across the classroom. This is a liability issue and a product-killer for school sales.

**Why it happens:** Code generation tools optimize for "does the code run?" not "is it safe to run on hardware that physically moves?" It's easy to generate correct Python but miss safety semantics.

**Consequences:**
- Robot runs off a desk or injures a student
- School refuses to purchase after first incident
- Generated code blocks the async event loop, making the stop button unresponsive

**Prevention:**
- The firmware must run all student code inside a managed execution context — not raw `exec()`
- Implement a hardware watchdog that the firmware pings periodically; if student code blocks the event loop for >500ms, the watchdog resets the Pico (MicroPython has `machine.WDT`)
- The WiFi stop-command handler must run in a higher-priority coroutine or interrupt, not at the same level as student code
- Enforce a maximum execution time for any generated program (e.g., 60 seconds) — inject a timeout check into the generated code at regular intervals
- The block editor must prevent users from creating programs with no termination condition unless they explicitly add a "forever" block, which is visually distinct
- Test: generate the most dangerous possible program a student could create, verify it cannot cause physical harm

**Warning signs:**
- `exec(generated_code)` called directly in the main loop
- No watchdog timer in firmware
- WiFi stop handler runs as a regular coroutine at the same priority as student code
- Block editor allows unbounded `repeat` blocks with motor commands

**Phase:** Block editor + firmware execution engine phase (must be designed together, not separately)

---

### Pitfall 6: WiFi HTTP Polling Instead of WebSocket for Real-Time Control

**What goes wrong:** The v1 telemetry dashboard uses `<meta http-equiv="refresh" content="1">` — page refresh every second. This is not interactive control; it is one-way telemetry with 1-second latency. For a block coding kit where students run programs and watch the robot respond, 1-second latency makes the experience feel broken. If the team extends this pattern to command sending (polling GET/POST every N milliseconds), they will discover that MicroPython's HTTP server cannot handle rapid polling without dropping connections, and the browser becomes unresponsive.

**Why it happens:** HTTP is simpler to implement than WebSocket, and it works fine for the telemetry prototype. The mistake is treating the prototype as production architecture.

**Consequences:**
- Students issue a "turn left" command, robot turns left 1 second later
- Rapid button presses in the block editor queue up commands that arrive out of order
- HTTP connection overhead (TCP handshake per request) at 10 req/s overwhelms the Pico W's networking stack

**Prevention:**
- Use WebSocket for bidirectional real-time communication between the React app and the rover
- MicroPython has `uwebsocket` or build a simple WebSocket upgrade on top of `uasyncio`; alternatively, use a simple binary protocol over raw TCP sockets
- Design a message protocol early: `{"type": "run", "code": "..."}` / `{"type": "stop"}` / `{"type": "telemetry", "data": {...}}`
- Latency target: command receipt within 100ms of user action
- Validate WebSocket + asyncio motor control works under load before building the block editor UI

**Warning signs:**
- `fetch()` polling in the React app at fixed intervals
- `<meta http-equiv="refresh">` in any production UI
- HTTP server handling motor commands (REST for commands is the wrong tool)

**Phase:** Communication protocol phase (must be decided before UI and firmware are built)

---

## Moderate Pitfalls

---

### Pitfall 7: Custom Block Editor Scope Creep Making It Incompletable

**What goes wrong:** Building a custom block editor (instead of Blockly) gives full control over branding but dramatically increases scope. Teams building custom editors consistently underestimate: drag-and-drop with snapping, undo/redo, block nesting validation, keyboard accessibility, mobile touch support, code generation from a block AST, visual error highlighting, and block library management. Each one is a non-trivial engineering effort. The block editor becomes the entire project and the robot firmware lags behind.

**Why it happens:** The block editor is the most visible UX component, so it attracts disproportionate attention. "Just a few more block types" compounds until the editor is a full-time product.

**Prevention:**
- Define MVP block set before writing a line of editor code: exactly which blocks exist in v1 (e.g., move forward, turn, wait, repeat, if obstacle, if line detected). Do not add blocks not required for the defined lesson plan.
- Use a proven drag-and-drop foundation (React DnD Kit or similar) rather than building drag-and-drop from scratch
- Treat code generation as the primary deliverable; visual polish comes after generation works correctly
- Time-box the block editor to a fixed phase duration and ship whatever block types are complete, not what was planned
- Test with actual K-8 students within 2 weeks of starting the editor — their interaction patterns reveal blockers early

**Warning signs:**
- Block editor has more than 20 block types planned for v1
- Team discussing custom drag-and-drop physics or animation before code generation is complete
- No student usability test in the first 4 weeks of block editor development

**Phase:** Block editor phase; scope defined in roadmap phase

---

### Pitfall 8: Lesson Content Written by Engineers, Not Teachers

**What goes wrong:** Engineers write lessons optimized for technical correctness. They explain how the encoder works before teaching the student to make the robot move. They use terms like "PWM," "I2C," "callback," and "interrupt." K-8 students (especially K-5) cannot engage with this content, and teachers cannot deliver it. Schools reject the kit after trialing it.

**Why it happens:** The people building the kit are the worst possible people to write the lessons — they cannot un-know what they know. The "curse of knowledge" is acute in robotics education.

**Prevention:**
- Hire or consult with a K-8 STEM educator before writing a single lesson
- Map lessons to specific grade bands (K-2, 3-5, 6-8) with explicitly different vocabulary, complexity, and time estimates
- Lesson structure: goal first ("Make the robot drive in a square"), concepts second, connection to the real world third — never explain the hardware before the student cares about the goal
- Validate every lesson with at least 5 students in the target age band before shipping
- Measure success by completion rate and time-to-completion, not by technical accuracy of the explanation

**Warning signs:**
- Lesson 1 contains the word "firmware," "microcontroller," or "protocol"
- Lessons are written after the hardware and software are complete
- No teacher or educator has reviewed the lesson content

**Phase:** Curriculum/lesson design phase (should begin in parallel with firmware, not after)

---

### Pitfall 9: Hardcoded WiFi Credentials and Pin Assignments Creating Kit-to-Kit Inconsistency

**What goes wrong:** The current `config.py` has `WIFI_AP_SSID = "RoboPico-Lab"` and `WIFI_AP_PASSWORD = "robopico1"` hardcoded. In a classroom with 30 kits, all 30 rovers broadcast the same SSID. Students accidentally connect to the wrong robot. Commands go to the wrong rover. Chaos. Additionally, if the hardware ever changes (different chassis, different pin for a sensor), every shipped unit in the field is on the wrong config.

**Why it happens:** Hardcoded constants are the path of least resistance during prototyping. Nobody thinks about multi-unit deployment during development.

**Prevention:**
- Each unit must have a unique identifier (serial number, last 4 of MAC address) baked into its configuration
- SSID must include the unique identifier: `RoboPico-A3F2`
- Configuration must be readable from a file on flash (`/config.json`) that can be updated without reflashing firmware
- Document the configuration update procedure so schools can manage a fleet of robots
- Consider a first-run setup flow: robot announces its ID over serial/REPL during setup

**Warning signs:**
- `WIFI_AP_SSID` is a string literal in source code
- No mechanism for per-unit configuration
- README does not address "how to set up 30 kits for a classroom"

**Phase:** Firmware foundation phase (configuration architecture); product-quality phase (documentation)

---

### Pitfall 10: Gyro Drift Making IMU-Based Navigation Unreliable for Lessons

**What goes wrong:** The MPU6050 gyro drifts at roughly 1-5 degrees/second at room temperature, and more if the chip warms up. A lesson that asks the student to make the robot "turn exactly 90 degrees" will fail consistently after the first turn. A 4-turn square mission accumulates up to 20 degrees of error even with calibration. Students conclude the robot is broken, not that gyro drift is a fundamental physics problem.

**Why it happens:** The MPU6050 is a low-cost MEMS gyro chosen for price. Its drift characteristics are well-known in the robotics community but easy to miss if you only test once after cold-start calibration. The existing `calibrate_gyro_z()` helps but only compensates for static offset, not temperature-dependent drift during operation.

**Consequences:**
- "Turn 90 degrees" block produces inconsistent results across lesson runs
- Students blame themselves for "doing it wrong"
- Teachers report unreliable robot behavior and stop using the kit

**Prevention:**
- Use encoder-based odometry as the primary navigation method for straight-line motion; use IMU only for turns and only short-duration turns (< 5 seconds)
- Implement complementary filter combining gyro + accelerometer for heading (reduces drift significantly)
- Recalibrate at the start of every program run, not just once at boot
- Design lessons to tolerate ±15 degrees of turn error — frame it as "approximately right" in the curriculum, not "exactly right"
- Include physical landmarks in early lessons (drive to the wall, drive along a line) that do not require precise IMU-based navigation

**Warning signs:**
- Lessons requiring repeated precise turns without re-calibration between turns
- IMU calibration only called at boot, not before each lesson run
- Lesson success criteria require < 5-degree turn accuracy

**Phase:** Sensor/motor integration phase; also lesson design phase

---

### Pitfall 11: React Block Editor State Management Getting Out of Sync With Rover State

**What goes wrong:** The React app maintains a model of what the robot is doing (running, stopped, connected, error). The rover maintains its own state. When the WebSocket connection drops and reconnects (common in a school WiFi environment), these states diverge. The UI shows "running" but the robot is stopped. Or the UI shows "connected" but the robot is mid-reset. Students press "Run" again and get unexpected behavior.

**Why it happens:** State synchronization across a network connection with reconnection logic is one of the hardest problems in networked UI. Teams prototype the happy path (stable connection) and discover reconnection failures only during classroom testing.

**Prevention:**
- Design a state machine for the connection: `disconnected → connecting → connected → running → stopped`
- On reconnect, the rover must immediately broadcast its current state as the first message
- The UI must treat the rover state as ground truth on reconnect — never assume the rover state matches the last UI state
- Implement a heartbeat: if the rover does not send a heartbeat every 2 seconds, the UI transitions to `disconnected` state visually and stops issuing commands
- Test disconnection/reconnection explicitly: unplug the rover's power mid-run, reconnect, verify UI recovers correctly

**Warning signs:**
- No explicit connection state machine in the React app
- No heartbeat mechanism
- UI state updated optimistically (before confirmation from rover)
- No reconnection logic — just "connection failed" error

**Phase:** Communication + UI integration phase

---

## Minor Pitfalls

---

### Pitfall 12: Thonny Dependency for Student Firmware Flashing

**What goes wrong:** The current setup requires Thonny IDE and manual file uploads to the Pico W. This is fine for a development workflow but catastrophic for a packaged product. A K-8 student (or their teacher) should not need to install a Python IDE, understand MicroPython file systems, or manually transfer files. The setup friction will cause most kits to be returned.

**Prevention:**
- Ship the Pico W with firmware pre-flashed
- Provide a one-click firmware updater (UF2 drag-and-drop or a simple web-based flasher tool)
- The out-of-box experience must be: power on, connect to WiFi, open browser — done

**Warning signs:**
- Any step in the getting started guide that mentions "open Thonny"

**Phase:** Product-quality / packaging phase

---

### Pitfall 13: PWM Frequency Causing Audible Motor Whine at Educational Noise Levels

**What goes wrong:** The current `MOTOR_PWM_FREQ = 1000` (1kHz) is in the audible range. At low PWM duty cycles (slow movement), TT motors with MX1515H emit a high-pitched whine that is prominent in a quiet classroom. Teachers and students find it distracting, and schools with noise-sensitive environments (libraries, inclusion classrooms) flag it as a problem.

**Prevention:**
- Set PWM frequency to ≥ 20kHz (above human hearing range) — the MX1515H supports up to 20kHz
- Test at the full range of duty cycles (10%–100%) and listen for audible tones at each frequency
- Document the PWM frequency decision in config with rationale

**Warning signs:**
- `MOTOR_PWM_FREQ = 1000` in shipped firmware

**Phase:** Firmware foundation / motor driver phase

---

### Pitfall 14: Block Editor Code Generation Producing Undebuggable Errors for Students

**What goes wrong:** Generated MicroPython code fails on the rover. The error is a Python traceback (e.g., `IndentationError: unexpected indent`) that the student sees in the UI. This is meaningless to a 9-year-old. Or worse, the code silently fails (motor command sent but rover is in an error state), and the student thinks the block editor is broken.

**Prevention:**
- The code generator must produce syntactically valid Python — add a validation step before sending
- Runtime errors from the rover must be translated into student-facing language ("The robot couldn't complete that step — check that it has enough room to move")
- Design a visual error state in the block editor that highlights which block caused the problem
- Never expose raw Python tracebacks in the student UI

**Warning signs:**
- Raw Python exceptions visible in the UI
- No error translation layer between rover error messages and UI display

**Phase:** Block editor + communication phase

---

### Pitfall 15: Selling a Kit With Per-Unit Hardware Variation

**What goes wrong:** TT motor gear ratios vary by manufacturer batch. Wheel diameters vary ±2mm depending on rubber thickness. IR sensor thresholds vary with ambient light. If the firmware has hardcoded constants (`TICKS_PER_REV`, `WHEEL_DIAMETER_MM`, `MM_PER_TICK`), each robot will behave slightly differently. Lessons designed around precise distances ("drive 50cm") will succeed on 70% of units and fail on 30%, creating inconsistent student experiences.

**Prevention:**
- Design a per-unit calibration routine that students run as the first lesson step
- Calibration stores tuned constants in a config file on flash, not in firmware source
- Design lesson success criteria to tolerate ±20% hardware variation
- Source hardware from a single supplier and batch-test incoming components

**Warning signs:**
- All distance/timing constants in `config.py` with no calibration mechanism
- Lessons requiring sub-5% precision

**Phase:** Firmware foundation phase (calibration architecture); lesson design phase (tolerance design)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Firmware architecture | Blocking HTTP server, no asyncio | Design async event loop before any feature work |
| Motor + encoder integration | ISR overhead dropping pulses at speed | Use PIO state machines for encoder counting |
| WiFi / communication protocol | HTTP polling latency, AP mode blocking in schools | WebSocket + asyncio; dual AP/STA mode |
| Block editor scope | Infinite block types, no code generation shipped | Freeze block set to lesson plan; code gen first |
| Execution engine | Unsafe student code running directly via exec() | Managed exec context + watchdog timer |
| Lesson content | Engineer-written, inaccessible to K-8 | Educator co-author; student testing within 2 weeks |
| Product packaging | Thonny setup friction | Pre-flash firmware; QR code to connect |
| Classroom deployment | Identical SSIDs for all units | Per-unit unique ID in SSID; mDNS |
| UI state management | Rover/React state divergence on disconnect | Heartbeat + state machine + reconnect sync |
| IMU navigation | Gyro drift in multi-turn lessons | Encoder-primary nav; IMU only for short turns |

---

## Sources

**Primary (HIGH confidence — direct code analysis):**
- `gate8_wifi_telemetry.py`: Blocking HTTP serve loop identified as architectural failure mode
- `config.py`: Hardcoded SSID/password, single PWM frequency, all constants non-calibratable
- `gate9_autonomous.py`: IMU drift accumulation in multi-turn mission, `time.sleep_ms()` blocking
- `gate6_pid_speed.py`: PID loop timing with `time.sleep_us()` — blocking, not async
- `gate4_encoders.py`: IRQ-based encoder counting — correct approach, but ISR body weight matters
- `mpu6050.py`: Full I2C read on every `accel()` call — 14 bytes per request, synchronous

**Domain knowledge (MEDIUM confidence — well-established patterns in embedded/educational robotics):**
- MicroPython `uasyncio` cooperative multitasking limitations and WDT integration
- RP2040 PIO capability for hardware encoder counting (documented in RP2040 datasheet)
- MPU6050 gyro drift characteristics (well-known in robotics community, documented in datasheets)
- MicroPython heap fragmentation behavior with repeated string allocation
- Classroom WiFi deployment patterns for IoT educational kits
- Block coding editor scope complexity (Scratch, MakeCode, custom editors all document this)
- K-8 educational content design principles (curse of knowledge, grade-band vocabulary)
