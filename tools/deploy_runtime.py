#!/usr/bin/env python3
"""
Deploy the tracked runtime tree to a Pico/Pico W using mpremote.

Optionally run the on-device runtime smoke gate after deployment.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TOP_LEVEL_FILES = (
    ("config.py", ":config.py"),
    ("main.py", ":main.py"),
    ("robot.py", ":robot.py"),
)

COPY_GROUPS = (
    ("app", ":/app/"),
    ("hal", ":/hal/"),
    ("tasks", ":/tasks/"),
    ("safety", ":/safety/"),
    ("lib", ":/lib/"),
    ("lib/microdot", ":/lib/microdot/"),
)

REMOTE_DIRS = (
    "app",
    "hal",
    "tasks",
    "safety",
    "lib",
    "lib/microdot",
)

SMOKE_GATE = ROOT / "gates" / "gate10_runtime_smoke.py"


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def find_mpremote() -> str:
    executable = shutil.which("mpremote")
    if executable is None:
        fail("mpremote not found on PATH. Install mpremote and retry.")
    return executable


def run_cmd(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def capture_cmd(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def run_batched_fs_cp(
    mpremote: str, port: str, copies: list[tuple[Path, str]]
) -> None:
    if not copies:
        return

    cmd = [mpremote, "connect", port]
    for index, (local_path, remote_target) in enumerate(copies):
        if index:
            cmd.append("+")
        cmd.extend(["fs", "cp", str(local_path), remote_target])
    run_cmd(cmd)


def discover_port(mpremote: str) -> str:
    output = capture_cmd([mpremote, "connect", "list"])
    candidates = []
    for line in output.splitlines():
        if "MicroPython Board" in line or "2e8a:0005" in line:
            candidates.append(line.split()[0])
    if len(candidates) != 1:
        if output:
            print(output, end="")
        fail(
            "Expected exactly one plausible MicroPython USB device when --port "
            f"is omitted; found {len(candidates)}."
        )
    return candidates[0]


def ensure_remote_dirs(mpremote: str, port: str, include_gates: bool = False) -> None:
    paths = list(REMOTE_DIRS)
    if include_gates:
        paths.append("gates")
    code = (
        "import os\n"
        f"paths = {tuple(paths)!r}\n"
        "for path in paths:\n"
        "    current = ''\n"
        "    for part in path.split('/'):\n"
        "        current = part if not current else current + '/' + part\n"
        "        try:\n"
        "            os.stat(current)\n"
        "        except OSError:\n"
        "            os.mkdir(current)\n"
    )
    run_cmd([mpremote, "connect", port, "exec", code])


def copy_top_level_files(mpremote: str, port: str) -> None:
    copies = [(ROOT / relative_path, remote_target) for relative_path, remote_target in TOP_LEVEL_FILES]
    run_batched_fs_cp(mpremote, port, copies)


def copy_group(mpremote: str, port: str, relative_dir: str, remote_dir: str) -> None:
    files = sorted((ROOT / relative_dir).glob("*.py"))
    if not files:
        return
    copies = [(path, f"{remote_dir}{path.name}") for path in files]
    run_batched_fs_cp(mpremote, port, copies)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy the current runtime tree to a Pico/Pico W."
    )
    parser.add_argument(
        "--port",
        help="Explicit serial port, e.g. /dev/cu.usbmodem21101",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run gates/gate10_runtime_smoke.py after deployment",
    )
    args = parser.parse_args()

    mpremote = find_mpremote()
    port = args.port or discover_port(mpremote)

    ensure_remote_dirs(mpremote, port, include_gates=args.smoke)
    copy_top_level_files(mpremote, port)
    for relative_dir, remote_dir in COPY_GROUPS:
        copy_group(mpremote, port, relative_dir, remote_dir)

    run_cmd([mpremote, "connect", port, "fs", "ls", ":"])
    run_cmd([mpremote, "connect", port, "fs", "ls", ":/app"])

    if args.smoke:
        run_cmd([mpremote, "connect", port, "fs", "cp", str(SMOKE_GATE), ":/gates/"])
        run_cmd([mpremote, "connect", port, "run", str(SMOKE_GATE)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
