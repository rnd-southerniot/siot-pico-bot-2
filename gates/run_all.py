"""
run_all.py — Sequential gate runner for v2 async firmware

Executes all gate verification scripts in order. Run with:

  mpremote run gates/run_all.py

Each gate is exec()'d in a try/except. A gate PASSES if it runs without
raising an exception AND its output contains the string 'PASS'.
Prints a summary at the end.

Note: Gate scripts that use uasyncio.run() will drive their own event loop.
"""

import uasyncio

# List of gate scripts to run in order.
# Additional gates are appended in later plans as they are created.
GATES = [
    "gates/gate1_async_skeleton.py",
]

passed = 0
failed = 0

for gate_path in GATES:
    print("=" * 40)
    print("Running:", gate_path)
    print("-" * 40)

    try:
        gate_src = open(gate_path).read()
        exec(gate_src, {"__name__": "__main__"})
        print("RESULT: PASS -", gate_path)
        passed += 1
    except Exception as e:
        print("RESULT: FAIL -", gate_path)
        print("  Error:", e)
        failed += 1

print()
print("=" * 40)
total = passed + failed
print("SUMMARY: {}/{} gates passed".format(passed, total))
print("=" * 40)
