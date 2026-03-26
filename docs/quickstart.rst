Quick Start
===========

What you need
-------------

- Python 3 with ``mpremote`` available
- a MicroPython UF2 for Raspberry Pi Pico W
- the robot hardware fully assembled
- a battery connected for motor operation

Flash MicroPython
-----------------

#. Hold **BOOTSEL** on the Pico W and connect it over USB.
#. Copy the correct MicroPython UF2 onto the ``RPI-RP2`` drive.
#. Let the board reboot into MicroPython.

Upload the firmware files
-------------------------

The tracked repo upload flow is:

.. code-block:: bash

   mpremote connect auto mkdir :lib :lib/microdot :hal :tasks :safety :gates
   mpremote connect auto cp config.py main.py robot.py :/
   mpremote connect auto cp lib/*.py :/lib/
   mpremote connect auto cp lib/microdot/*.py :/lib/microdot/
   mpremote connect auto cp hal/*.py :/hal/
   mpremote connect auto cp tasks/*.py :/tasks/
   mpremote connect auto cp safety/*.py :/safety/
   mpremote connect auto cp gates/*.py :/gates/

What happens on boot
--------------------

The current ``main.py`` boot path:

#. initializes the IMU over I2C
#. calibrates gyro Z while the robot is still
#. wires heading tracking and shared I2C into the sensor task
#. arms the watchdog
#. starts the Wi-Fi access point
#. launches the async runtime

Use the browser dashboard
-------------------------

The repository includes ``tools/test-dashboard.html`` for browser-based
interaction. The current firmware exposes HTTP endpoints over the Pico W access
point, including ``/status`` and ``/exec``.

Current Wi-Fi access point details are defined in tracked code and configuration:

- SSID format: ``RoboPico-XXXX``
- password: ``robopico1``
- default AP IP: ``192.168.4.1``

Current safety notes
--------------------

- keep the robot still during IMU calibration at startup
- keep wheels clear on first power-up
- use battery power for motor testing; USB alone is not enough for reliable motion
- treat gates as on-device checks, not host-side unit tests
