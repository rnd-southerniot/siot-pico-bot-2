Troubleshooting
===============

Robot does not move
-------------------

- confirm the battery is connected; USB alone is not enough for reliable motor operation
- verify motor wiring and power
- use the gate scripts to isolate whether the issue is motors, encoders, or safety logic

Robot does not appear on Wi-Fi
------------------------------

- reboot the robot and wait for normal startup to finish
- check the access point name and password from the current configuration
- confirm the firmware was uploaded successfully before troubleshooting the dashboard

Heading or turns are unstable
-----------------------------

- keep the robot still during startup IMU calibration
- verify the IMU is mounted securely
- run the IMU and heading-related gates on-device

Sensor readings look wrong
--------------------------

- verify the actual hardware matches the pin assignments in ``config.py``
- check each sensor with the relevant gate before assuming a runtime bug
- remember that this repo is using on-device checks, not host simulation

REPL or gate workflow is awkward
--------------------------------

The production runtime auto-starts from ``main.py``. The repository README
documents a gate workflow that temporarily prevents the normal boot path so an
individual gate can be run through ``mpremote``.
