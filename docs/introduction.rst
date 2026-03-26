Introduction
============

What this project is
--------------------

SIOT Pico Bot 2 is an educational robot kit built around:

- a Cytron Robo Pico carrier board
- a Raspberry Pi Pico W
- TT gear motors with hall encoders
- an MPU6050 IMU
- a small set of classroom-friendly sensors

The tracked repository is primarily a MicroPython firmware codebase. It also
includes gate scripts for on-device verification and a browser dashboard at
``tools/test-dashboard.html``.

Who this documentation is for
-----------------------------

This site is aimed at three audiences:

- students who need the current robot API and safe motion basics
- teachers who need setup, validation, and troubleshooting guidance
- developers who need a concise view of the current firmware structure

What this site covers
---------------------

This first pass documents the current repository as it exists now:

- firmware setup and boot behavior
- the public ``robot.py`` API
- sensors, motion, and runtime responsibilities
- on-device gates and validation workflow
- current architecture and common failure points

It does not document unshipped features such as a React block editor,
WebSockets, lesson content, or multi-stage deployment infrastructure.
