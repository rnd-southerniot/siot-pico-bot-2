"""
siot-pico-bot — Main Entry Point (v2 async architecture)
"""

import uasyncio

from app.boot import boot
from app.runtime import main_async


ctx = boot()
uasyncio.run(main_async(ctx))
