Sensors and Motion
==================

Motion stack
------------

The current motion stack combines:

- motor output through ``hal/motors.py``
- encoder feedback through ``hal/encoder_pio.py``
- wheel-speed PID control in ``tasks/motor_task.py``
- a watchdog-backed timeout layer in ``safety/watchdog.py``

Motor output is intentionally safety-capped in the HAL. The control loop reads
actual RPM from the encoders and updates motor drive continuously.

Current sensors
---------------

The tracked repository currently includes support for:

- wheel encoders
- MPU6050 IMU and heading tracking
- IR line sensing
- ultrasonic distance sensing
- color or light sensing

Runtime sensor model
--------------------

``tasks/sensor_task.py`` polls the sensor set and updates shared sensor state.
That state is then surfaced through ``robot.status()`` and the ``/status``
HTTP endpoint.

Important current details
-------------------------

- encoder counting uses RP2040 PIO state machines
- heading comes from integrated gyro Z updates
- sensor reads are coordinated by the async runtime
- pin assignments and constants live in ``config.py``

This page documents the current firmware behavior only; it does not assume
extra sensors, richer telemetry, or future front-end features.
