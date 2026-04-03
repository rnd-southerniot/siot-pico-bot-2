Gates and Validation
====================

What gates are in this repo
---------------------------

The ``gates/`` directory contains on-device verification scripts for the robot.
These are hardware-backed checks, not host-side unit tests.

The tracked repository currently has two practical validation paths:

- older/manual bring-up and milestone gates for board, peripherals, motors,
  encoders, IMU, heading, Wi-Fi telemetry, and autonomous motion
- the current runtime smoke path in ``gates/gate10_runtime_smoke.py``

How to use them
---------------

Gates are intended to be run on the Pico, usually through ``mpremote``.
Because the production ``main.py`` auto-boots the runtime, some gate workflows
may require temporarily preventing the normal boot path before running a gate.

For the current runtime-oriented smoke check, use:

.. code-block:: bash

   python3 tools/deploy_runtime.py --smoke

This deploys and runs only ``gates/gate10_runtime_smoke.py``. It validates the
current boot, AP, HTTP ``/status``, and ``/exec`` wiring. It does not prove
external Wi-Fi client reachability.

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
