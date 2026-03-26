Student API
===========

Current public API surface
--------------------------

The student-facing API in this repository is the ``RobotAPI`` class in
``robot.py``. This is the current public surface used by sandboxed code.

Motion methods
--------------

``robot.forward(rpm=60.0)``
   Drive both wheels forward at the requested target RPM.

``robot.backward(rpm=60.0)``
   Drive both wheels backward at the requested target RPM.

``robot.turn_left(rpm=40.0)``
   Pivot left by driving the left wheel backward and the right wheel forward.

``robot.turn_right(rpm=40.0)``
   Pivot right by driving the left wheel forward and the right wheel backward.

``robot.stop()``
   Stop both wheels by setting both target RPM values to zero.

Status method
-------------

``robot.status()``
   Return a JSON-serializable dictionary with the current runtime snapshot.

Current keys returned by ``status()``
-------------------------------------

- ``rpm_left``
- ``rpm_right``
- ``ir``
- ``distance_cm``
- ``color``
- ``heading``
- ``tick``

Usage boundary
--------------

This first pass documents only the current facade in ``robot.py``. It does not
promise any direct access to task globals, HAL objects, or lower-level drivers.
