import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "deploy_runtime.py"

spec = importlib.util.spec_from_file_location("deploy_runtime", MODULE_PATH)
deploy_runtime = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deploy_runtime)


class FailureMessageMixin:
    def assert_failure_message(self, func, *args, contains):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as excinfo:
                func(*args)
        self.assertEqual(excinfo.exception.code, 1)
        self.assertIn(contains, stderr.getvalue())
        return stdout.getvalue(), stderr.getvalue()


class FindMpremoteTests(FailureMessageMixin, unittest.TestCase):
    def test_find_mpremote_returns_path(self):
        with mock.patch.object(deploy_runtime.shutil, "which", return_value="/tmp/mpremote"):
            self.assertEqual(deploy_runtime.find_mpremote(), "/tmp/mpremote")

    def test_find_mpremote_exits_with_human_readable_error_when_missing(self):
        with mock.patch.object(deploy_runtime.shutil, "which", return_value=None):
            self.assert_failure_message(
                deploy_runtime.find_mpremote,
                contains="mpremote not found on PATH. Install mpremote and retry.",
            )


class DiscoverPortTests(FailureMessageMixin, unittest.TestCase):
    def test_discover_port_returns_single_plausible_device(self):
        output = (
            "/dev/cu.debug serial adapter\n"
            "/dev/cu.usbmodem1401 serial MicroPython Board\n"
        )
        with mock.patch.object(deploy_runtime, "capture_cmd", return_value=output):
            self.assertEqual(
                deploy_runtime.discover_port("mpremote"),
                "/dev/cu.usbmodem1401",
            )

    def test_discover_port_exits_with_human_readable_error_when_none_found(self):
        with mock.patch.object(
            deploy_runtime,
            "capture_cmd",
            return_value="/dev/cu.debug serial adapter\n",
        ):
            stdout, _stderr = self.assert_failure_message(
                deploy_runtime.discover_port,
                "mpremote",
                contains=(
                    "Expected exactly one plausible MicroPython USB device when --port "
                    "is omitted; found 0."
                ),
            )
        self.assertIn("/dev/cu.debug serial adapter", stdout)

    def test_discover_port_exits_with_human_readable_error_when_multiple_found(self):
        output = (
            "/dev/cu.usbmodem1401 serial MicroPython Board\n"
            "/dev/cu.usbmodem1402 serial 2e8a:0005\n"
        )
        with mock.patch.object(deploy_runtime, "capture_cmd", return_value=output):
            stdout, _stderr = self.assert_failure_message(
                deploy_runtime.discover_port,
                "mpremote",
                contains=(
                    "Expected exactly one plausible MicroPython USB device when --port "
                    "is omitted; found 2."
                ),
            )
        self.assertIn("/dev/cu.usbmodem1401", stdout)
        self.assertIn("/dev/cu.usbmodem1402", stdout)


class EnsureRemoteDirsTests(unittest.TestCase):
    def test_ensure_remote_dirs_includes_runtime_dirs_without_gates(self):
        with mock.patch.object(deploy_runtime, "run_cmd") as run_cmd:
            deploy_runtime.ensure_remote_dirs("mpremote", "/dev/ttyUSB0", include_gates=False)

        run_cmd.assert_called_once()
        cmd = run_cmd.call_args.args[0]
        self.assertEqual(cmd[:4], ["mpremote", "connect", "/dev/ttyUSB0", "exec"])
        code = cmd[4]
        self.assertIn("paths = ('app', 'hal', 'tasks', 'safety', 'lib', 'lib/microdot')", code)
        self.assertNotIn("'gates'", code)
        self.assertIn("os.mkdir(current)", code)

    def test_ensure_remote_dirs_adds_gates_for_smoke(self):
        with mock.patch.object(deploy_runtime, "run_cmd") as run_cmd:
            deploy_runtime.ensure_remote_dirs("mpremote", "/dev/ttyUSB0", include_gates=True)

        run_cmd.assert_called_once()
        code = run_cmd.call_args.args[0][4]
        self.assertIn(
            "paths = ('app', 'hal', 'tasks', 'safety', 'lib', 'lib/microdot', 'gates')",
            code,
        )


class CopyCommandTests(unittest.TestCase):
    def test_run_batched_fs_cp_builds_chained_mpremote_command(self):
        copies = [
            (Path("/tmp/config.py"), ":config.py"),
            (Path("/tmp/main.py"), ":main.py"),
        ]
        with mock.patch.object(deploy_runtime, "run_cmd") as run_cmd:
            deploy_runtime.run_batched_fs_cp("mpremote", "/dev/ttyUSB0", copies)

        run_cmd.assert_called_once_with(
            [
                "mpremote",
                "connect",
                "/dev/ttyUSB0",
                "fs",
                "cp",
                "/tmp/config.py",
                ":config.py",
                "+",
                "fs",
                "cp",
                "/tmp/main.py",
                ":main.py",
            ]
        )

    def test_copy_top_level_files_uses_expected_targets(self):
        with mock.patch.object(deploy_runtime, "run_batched_fs_cp") as batched:
            deploy_runtime.copy_top_level_files("mpremote", "/dev/ttyUSB0")

        batched.assert_called_once_with(
            "mpremote",
            "/dev/ttyUSB0",
            [
                (deploy_runtime.ROOT / "config.py", ":config.py"),
                (deploy_runtime.ROOT / "main.py", ":main.py"),
                (deploy_runtime.ROOT / "robot.py", ":robot.py"),
            ],
        )

    def test_copy_group_builds_explicit_sorted_remote_targets(self):
        fake_files = [
            deploy_runtime.ROOT / "lib" / "pid.py",
            deploy_runtime.ROOT / "lib" / "encoder.py",
        ]
        with mock.patch.object(Path, "glob", return_value=fake_files):
            with mock.patch.object(deploy_runtime, "run_batched_fs_cp") as batched:
                deploy_runtime.copy_group("mpremote", "/dev/ttyUSB0", "lib", ":/lib/")

        batched.assert_called_once_with(
            "mpremote",
            "/dev/ttyUSB0",
            [
                (deploy_runtime.ROOT / "lib" / "encoder.py", ":/lib/encoder.py"),
                (deploy_runtime.ROOT / "lib" / "pid.py", ":/lib/pid.py"),
            ],
        )


class MainFlowTests(unittest.TestCase):
    def test_main_uses_explicit_port_without_discovery(self):
        with mock.patch.object(sys, "argv", ["deploy_runtime.py", "--port", "/dev/ttyUSB9"]):
            with mock.patch.object(deploy_runtime, "find_mpremote", return_value="mpremote"):
                with mock.patch.object(deploy_runtime, "discover_port") as discover_port:
                    with mock.patch.object(deploy_runtime, "ensure_remote_dirs") as ensure_dirs:
                        with mock.patch.object(deploy_runtime, "copy_top_level_files") as top_level:
                            with mock.patch.object(deploy_runtime, "copy_group") as copy_group:
                                with mock.patch.object(deploy_runtime, "run_cmd") as run_cmd:
                                    rc = deploy_runtime.main()

        self.assertEqual(rc, 0)
        discover_port.assert_not_called()
        ensure_dirs.assert_called_once_with("mpremote", "/dev/ttyUSB9", include_gates=False)
        top_level.assert_called_once_with("mpremote", "/dev/ttyUSB9")
        self.assertEqual(
            [call.args for call in copy_group.call_args_list],
            [
                ("mpremote", "/dev/ttyUSB9", relative_dir, remote_dir)
                for relative_dir, remote_dir in deploy_runtime.COPY_GROUPS
            ],
        )
        self.assertEqual(
            run_cmd.call_args_list,
            [
                mock.call(["mpremote", "connect", "/dev/ttyUSB9", "fs", "ls", ":"]),
                mock.call(["mpremote", "connect", "/dev/ttyUSB9", "fs", "ls", ":/app"]),
            ],
        )

    def test_main_with_smoke_stages_and_runs_only_gate10(self):
        with mock.patch.object(sys, "argv", ["deploy_runtime.py", "--smoke"]):
            with mock.patch.object(deploy_runtime, "find_mpremote", return_value="mpremote"):
                with mock.patch.object(deploy_runtime, "discover_port", return_value="/dev/ttyUSB0"):
                    with mock.patch.object(deploy_runtime, "ensure_remote_dirs") as ensure_dirs:
                        with mock.patch.object(deploy_runtime, "copy_top_level_files"):
                            with mock.patch.object(deploy_runtime, "copy_group") as copy_group:
                                with mock.patch.object(deploy_runtime, "run_cmd") as run_cmd:
                                    rc = deploy_runtime.main()

        self.assertEqual(rc, 0)
        ensure_dirs.assert_called_once_with("mpremote", "/dev/ttyUSB0", include_gates=True)
        self.assertEqual(
            [call.args[2] for call in copy_group.call_args_list],
            [relative_dir for relative_dir, _remote_dir in deploy_runtime.COPY_GROUPS],
        )
        self.assertNotIn("gates", [call.args[2] for call in copy_group.call_args_list])

        smoke_cmds = [call.args[0] for call in run_cmd.call_args_list if "gate10_runtime_smoke.py" in " ".join(call.args[0])]
        self.assertEqual(
            smoke_cmds,
            [
                [
                    "mpremote",
                    "connect",
                    "/dev/ttyUSB0",
                    "fs",
                    "cp",
                    str(deploy_runtime.SMOKE_GATE),
                    ":/gates/",
                ],
                [
                    "mpremote",
                    "connect",
                    "/dev/ttyUSB0",
                    "run",
                    str(deploy_runtime.SMOKE_GATE),
                ],
            ],
        )


if __name__ == "__main__":
    unittest.main()
