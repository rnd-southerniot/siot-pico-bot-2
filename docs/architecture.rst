Architecture
============

Current repository shape
------------------------

The tracked repository is organized around these main parts:

- ``main.py`` for boot and runtime startup
- ``config.py`` for pins, constants, and deployment settings
- ``robot.py`` for the public student-facing API
- ``hal/`` for hardware abstraction
- ``tasks/`` for async runtime loops
- ``safety/`` for watchdog and sandbox behavior
- ``gates/`` for on-device validation
- ``lib/`` for low-level drivers and vendored Microdot
- ``tools/test-dashboard.html`` for browser-based interaction

Current boot flow
-----------------

The current ``main.py`` performs a boot sequence that:

#. creates the MPU6050 driver
#. calibrates the IMU before the watchdog starts
#. wires heading tracking into the sensor task
#. creates the watchdog keeper
#. starts the Wi-Fi access point
#. runs the async event loop

Current long-running tasks
--------------------------

The runtime gathers these main responsibilities:

- motor PID control
- sensor polling
- heading integration
- HTTP serving over Wi-Fi
- watchdog feeding

Current network boundary
------------------------

The HTTP server lives in ``tasks/wifi_task.py`` and currently exposes:

- ``GET /status``
- ``POST /exec``

The ``/exec`` path runs code through the sandbox in ``safety/sandbox.py`` and
operates on the public robot facade rather than exposing low-level hardware
objects directly.
