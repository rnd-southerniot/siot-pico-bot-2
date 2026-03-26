Gates and Validation
====================

What gates are in this repo
---------------------------

The ``gates/`` directory contains on-device verification scripts for the robot.
These are hardware-backed checks, not host-side unit tests.

The tracked repository currently shows two visible groups of gates:

- early hardware bring-up and milestone gates such as board, peripherals,
  motors, encoders, IMU, heading, Wi-Fi telemetry, and autonomous motion
- async/runtime-oriented gates such as async scheduling, motor distance,
  watchdog behavior, sensor polling, PIO encoder validation, and exec sandboxing

How to use them
---------------

Gates are intended to be run on the Pico, usually through ``mpremote``.
Because the production ``main.py`` auto-boots the runtime, some gate workflows
may require temporarily preventing the normal boot path before running a gate.

What they validate
------------------

Current gates cover areas such as:

- MicroPython environment and board responsiveness
- motors and encoder feedback
- IMU behavior and heading control
- PID motion control
- Wi-Fi telemetry
- sandbox behavior for ``/exec``
- autonomous mission behavior

Current limitation
------------------

Treat the gates as practical on-device checks. They are useful for bring-up and
debugging, but they are not a substitute for a host-side automated test suite.
