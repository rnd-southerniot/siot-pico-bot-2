import asyncio
import importlib.util
import itertools
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
ROBOT_PATH = REPO_ROOT / "robot.py"
MOTOR_TASK_PATH = REPO_ROOT / "tasks" / "motor_task.py"
_MODULE_COUNTER = itertools.count()


class LoopBreak(BaseException):
    """Raised by fake uasyncio.sleep_ms to stop a single loop iteration."""


class FakeMotor:
    def __init__(self, *args, **kwargs):
        self.drive_calls = []
        self.brake_calls = 0

    def drive(self, value):
        self.drive_calls.append(value)

    def brake(self):
        self.brake_calls += 1


class FakePID:
    def __init__(self, *args, **kwargs):
        self.reset_calls = 0

    def compute(self, setpoint, measured, dt):
        return 0.0

    def reset(self):
        self.reset_calls += 1


class FakeEncoder:
    def __init__(self, *args, counts=None, rpm_values=None, **kwargs):
        self._counts = list(counts or [0])
        self._rpm_values = list(rpm_values or [0.0])
        self._last_count = self._counts[-1]
        self._last_rpm = self._rpm_values[-1]

    def count(self):
        if self._counts:
            self._last_count = self._counts.pop(0)
        return self._last_count

    def rpm(self, dt):
        if self._rpm_values:
            self._last_rpm = self._rpm_values.pop(0)
        return self._last_rpm


class FakeWatchdog:
    def __init__(self):
        self.arm_calls = 0
        self.disarm_calls = 0

    def arm_motor_timeout(self):
        self.arm_calls += 1

    def disarm_motor_timeout(self):
        self.disarm_calls += 1

    def check_motor_timeout(self, stop_fn):
        return None


def load_module(module_path, module_name, injected_modules):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with mock.patch.dict(sys.modules, injected_modules, clear=False):
        spec.loader.exec_module(module)
    return module


def make_robot_module():
    fake_tasks = types.ModuleType("tasks")
    fake_tasks.__path__ = []

    fake_motor_task = types.ModuleType("tasks.motor_task")
    fake_motor_task.submit_distance_goal = mock.Mock()
    fake_motor_task.submit_turn_goal = mock.Mock()
    fake_motor_task.stop_motion = mock.Mock()
    fake_motor_task.set_drive_targets = mock.Mock()
    fake_motor_task.get_actual_rpm = mock.Mock(return_value=0.0)

    fake_sensor_task = types.ModuleType("tasks.sensor_task")
    fake_sensor_task.get_sensor_state = mock.Mock(
        return_value={
            "ir": [],
            "distance_cm": -1.0,
            "color": {},
            "heading": 0.0,
            "tick": 0,
        }
    )

    module_name = "robot_under_test_{}".format(next(_MODULE_COUNTER))
    robot_module = load_module(
        ROBOT_PATH,
        module_name,
        {
            "tasks": fake_tasks,
            "tasks.motor_task": fake_motor_task,
            "tasks.sensor_task": fake_sensor_task,
        },
    )
    return robot_module, fake_motor_task


def make_motor_task_module():
    fake_uasyncio = types.ModuleType("uasyncio")

    async def sleep_ms(_ms):
        raise LoopBreak()

    fake_uasyncio.sleep_ms = sleep_ms

    class FakeUtime(types.ModuleType):
        def __init__(self):
            super().__init__("utime")
            self.now = 1000

        def ticks_ms(self):
            return self.now

        def ticks_add(self, base, delta):
            return base + delta

        def ticks_diff(self, a, b):
            return a - b

    fake_utime = FakeUtime()

    fake_config = types.ModuleType("config")
    fake_config.MOTOR_LEFT_A = 1
    fake_config.MOTOR_LEFT_B = 2
    fake_config.MOTOR_RIGHT_A = 3
    fake_config.MOTOR_RIGHT_B = 4
    fake_config.ENC_LEFT_A = 5
    fake_config.ENC_LEFT_B = 6
    fake_config.ENC_RIGHT_A = 7
    fake_config.ENC_RIGHT_B = 8
    fake_config.ENC_LEFT_INVERT = False
    fake_config.ENC_RIGHT_INVERT = False
    fake_config.PID_KP = 0.8
    fake_config.PID_KI = 0.3
    fake_config.PID_KD = 0.05
    fake_config.PID_LOOP_HZ = 20
    fake_config.MM_PER_TICK = 1.0

    fake_hal = types.ModuleType("hal")
    fake_hal.__path__ = []
    fake_hal_motors = types.ModuleType("hal.motors")
    fake_hal_motors.MotorHAL = FakeMotor
    fake_hal_encoder = types.ModuleType("hal.encoder_pio")
    fake_hal_encoder.EncoderPIO = FakeEncoder

    fake_lib = types.ModuleType("lib")
    fake_lib.__path__ = []
    fake_lib_pid = types.ModuleType("lib.pid")
    fake_lib_pid.PID = FakePID

    fake_tasks = types.ModuleType("tasks")
    fake_tasks.__path__ = []
    fake_sensor_state = {"heading": 0.0}
    fake_sensor_task = types.ModuleType("tasks.sensor_task")
    fake_sensor_task.get_sensor_state = mock.Mock(return_value=fake_sensor_state)
    sys.modules["tasks"] = fake_tasks
    sys.modules["tasks.sensor_task"] = fake_sensor_task

    module_name = "motor_task_under_test_{}".format(next(_MODULE_COUNTER))
    motor_task = load_module(
        MOTOR_TASK_PATH,
        module_name,
        {
            "uasyncio": fake_uasyncio,
            "utime": fake_utime,
            "config": fake_config,
            "hal": fake_hal,
            "hal.motors": fake_hal_motors,
            "hal.encoder_pio": fake_hal_encoder,
            "lib": fake_lib,
            "lib.pid": fake_lib_pid,
            "tasks": fake_tasks,
            "tasks.sensor_task": fake_sensor_task,
        },
    )
    motor_task._fake_utime = fake_utime
    motor_task._fake_sensor_state = fake_sensor_state
    motor_task._fake_sensor_task = fake_sensor_task
    return motor_task


class RobotAPIRoutingTests(unittest.TestCase):
    def test_forward_routes_to_set_drive_targets(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().forward(25)
        fake_motor_task.set_drive_targets.assert_called_once_with(25, 25)

    def test_backward_routes_to_set_drive_targets(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().backward(25)
        fake_motor_task.set_drive_targets.assert_called_once_with(-25, -25)

    def test_turn_left_routes_to_set_drive_targets(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().turn_left(25)
        fake_motor_task.set_drive_targets.assert_called_once_with(-25, 25)

    def test_turn_right_routes_to_set_drive_targets(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().turn_right(25)
        fake_motor_task.set_drive_targets.assert_called_once_with(25, -25)

    def test_stop_routes_to_stop_motion(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().stop()
        fake_motor_task.stop_motion.assert_called_once_with()


class RobotAPIMotionGoalTests(unittest.TestCase):
    def test_turn_degrees_positive_submits_turn_goal(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().turn_degrees(90, rpm=30, tolerance_deg=4.0, timeout_s=6.0)
        fake_motor_task.submit_turn_goal.assert_called_once_with(90, 30, 4.0, 6.0)

    def test_turn_degrees_negative_submits_turn_goal(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().turn_degrees(-90, rpm=30, tolerance_deg=4.0, timeout_s=6.0)
        fake_motor_task.submit_turn_goal.assert_called_once_with(-90, 30, 4.0, 6.0)

    def test_turn_degrees_zero_maps_to_stop(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().turn_degrees(0)
        fake_motor_task.stop_motion.assert_called_once_with()
        fake_motor_task.submit_turn_goal.assert_not_called()

    def test_invalid_turn_degrees_args_raise_value_error(self):
        robot_module, _fake_motor_task = make_robot_module()
        robot = robot_module.RobotAPI()

        with self.assertRaises(ValueError):
            robot.turn_degrees(90, rpm=0)
        with self.assertRaises(ValueError):
            robot.turn_degrees(90, tolerance_deg=0)
        with self.assertRaises(ValueError):
            robot.turn_degrees(90, timeout_s=0)

    def test_drive_distance_positive_submits_forward_goal(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().drive_distance_cm(20, rpm=35, tolerance_cm=1.5, timeout_s=4.0)
        fake_motor_task.submit_distance_goal.assert_called_once_with(20, 35, 1.5, 4.0)

    def test_drive_distance_negative_submits_backward_goal(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().drive_distance_cm(-20, rpm=35, tolerance_cm=1.5, timeout_s=4.0)
        fake_motor_task.submit_distance_goal.assert_called_once_with(-20, 35, 1.5, 4.0)

    def test_drive_distance_zero_maps_to_stop(self):
        robot_module, fake_motor_task = make_robot_module()
        robot_module.RobotAPI().drive_distance_cm(0)
        fake_motor_task.stop_motion.assert_called_once_with()
        fake_motor_task.submit_distance_goal.assert_not_called()

    def test_invalid_drive_distance_args_raise_value_error(self):
        robot_module, _fake_motor_task = make_robot_module()
        robot = robot_module.RobotAPI()

        with self.assertRaises(ValueError):
            robot.drive_distance_cm(10, rpm=0)
        with self.assertRaises(ValueError):
            robot.drive_distance_cm(10, tolerance_cm=0)
        with self.assertRaises(ValueError):
            robot.drive_distance_cm(10, timeout_s=0)


class MotorTaskDistanceGoalTests(unittest.TestCase):
    def test_submit_distance_goal_sets_signed_direction_state(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_enc = FakeEncoder(counts=[10])
        motor_task._right_enc = FakeEncoder(counts=[20])
        motor_task._watchdog = FakeWatchdog()

        motor_task.submit_distance_goal(-20, rpm=35, tolerance_cm=1.0, timeout_s=5.0)

        self.assertEqual(motor_task._distance_goal["direction"], -1.0)
        self.assertEqual(motor_task._distance_goal["left_start_ticks"], 10)
        self.assertEqual(motor_task._distance_goal["right_start_ticks"], 20)
        self.assertEqual(motor_task._distance_goal["target_ticks"], 200.0)
        self.assertEqual(motor_task._target_rpm, {"left": -35, "right": -35})

    def test_set_drive_targets_clears_active_distance_goal(self):
        motor_task = make_motor_task_module()
        motor_task._distance_goal = {"direction": 1.0}
        motor_task._turn_goal = {"direction": -1.0}

        motor_task.set_drive_targets(10.0, 20.0)

        self.assertIsNone(motor_task._distance_goal)
        self.assertIsNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 10.0, "right": 20.0})

    def test_stop_motion_clears_active_goal_and_stops(self):
        motor_task = make_motor_task_module()
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._distance_goal = {"direction": 1.0}
        motor_task._turn_goal = {"direction": -1.0}
        motor_task._target_rpm = {"left": 12.0, "right": 12.0}

        motor_task.stop_motion()

        self.assertIsNone(motor_task._distance_goal)
        self.assertIsNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 1)
        self.assertEqual(motor_task._right_pid.reset_calls, 1)
        self.assertEqual(motor_task._left_motor.brake_calls, 1)
        self.assertEqual(motor_task._right_motor.brake_calls, 1)

    def test_submit_distance_goal_cancels_active_turn_goal(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_enc = FakeEncoder(counts=[10])
        motor_task._right_enc = FakeEncoder(counts=[20])
        motor_task._turn_goal = {"direction": 1.0}

        motor_task.submit_distance_goal(20, rpm=35, tolerance_cm=1.0, timeout_s=5.0)

        self.assertIsNone(motor_task._turn_goal)
        self.assertIsNotNone(motor_task._distance_goal)

    def test_motor_pid_loop_success_clears_goal_and_stops(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[60], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[60], rpm_values=[0.0])
        motor_task._distance_goal = {
            "direction": 1.0,
            "left_start_ticks": 0,
            "right_start_ticks": 0,
            "target_ticks": 50.0,
            "tolerance_ticks": 0.0,
            "deadline_ms": 2000,
        }
        motor_task._target_rpm = {"left": 35.0, "right": 35.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNone(motor_task._distance_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 1)
        self.assertEqual(motor_task._right_pid.reset_calls, 1)
        self.assertEqual(motor_task._left_motor.brake_calls, 1)
        self.assertEqual(motor_task._right_motor.brake_calls, 1)
        self.assertEqual(motor_task._left_motor.drive_calls[-1], 0.0)
        self.assertEqual(motor_task._right_motor.drive_calls[-1], 0.0)

    def test_motor_pid_loop_timeout_clears_goal_and_stops(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._fake_utime.now = 3000
        motor_task._distance_goal = {
            "direction": 1.0,
            "left_start_ticks": 0,
            "right_start_ticks": 0,
            "target_ticks": 50.0,
            "tolerance_ticks": 0.0,
            "deadline_ms": 2000,
        }
        motor_task._target_rpm = {"left": 35.0, "right": 35.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNone(motor_task._distance_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 1)
        self.assertEqual(motor_task._right_pid.reset_calls, 1)
        self.assertEqual(motor_task._left_motor.brake_calls, 1)
        self.assertEqual(motor_task._right_motor.brake_calls, 1)
        self.assertEqual(motor_task._left_motor.drive_calls[-1], 0.0)
        self.assertEqual(motor_task._right_motor.drive_calls[-1], 0.0)

    def test_wrong_direction_progress_does_not_complete_backward_goal(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[120], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[120], rpm_values=[0.0])
        motor_task._distance_goal = {
            "direction": -1.0,
            "left_start_ticks": 0,
            "right_start_ticks": 0,
            "target_ticks": 50.0,
            "tolerance_ticks": 0.0,
            "deadline_ms": 5000,
        }
        motor_task._target_rpm = {"left": -35.0, "right": -35.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNotNone(motor_task._distance_goal)
        self.assertEqual(motor_task._target_rpm, {"left": -35.0, "right": -35.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 0)
        self.assertEqual(motor_task._right_pid.reset_calls, 0)
        self.assertEqual(motor_task._left_motor.brake_calls, 0)
        self.assertEqual(motor_task._right_motor.brake_calls, 0)


class MotorTaskTurnGoalTests(unittest.TestCase):
    def test_submit_turn_goal_positive_sets_right_turn_targets(self):
        motor_task = make_motor_task_module()
        motor_task._fake_sensor_state["heading"] = 12.5
        motor_task._distance_goal = {"direction": 1.0}

        motor_task.submit_turn_goal(90, rpm=30, tolerance_deg=4.0, timeout_s=6.0)

        self.assertIsNone(motor_task._distance_goal)
        self.assertEqual(motor_task._turn_goal["direction"], 1.0)
        self.assertEqual(motor_task._turn_goal["start_heading"], 12.5)
        self.assertEqual(motor_task._turn_goal["target_degrees"], 90)
        self.assertEqual(motor_task._target_rpm, {"left": 30, "right": -30})

    def test_submit_turn_goal_negative_sets_left_turn_targets(self):
        motor_task = make_motor_task_module()
        motor_task._fake_sensor_state["heading"] = -3.0

        motor_task.submit_turn_goal(-90, rpm=30, tolerance_deg=4.0, timeout_s=6.0)

        self.assertEqual(motor_task._turn_goal["direction"], -1.0)
        self.assertEqual(motor_task._turn_goal["start_heading"], -3.0)
        self.assertEqual(motor_task._target_rpm, {"left": -30, "right": 30})

    def test_submit_turn_goal_rejects_missing_heading(self):
        motor_task = make_motor_task_module()
        motor_task._fake_sensor_state["heading"] = None

        with self.assertRaises(RuntimeError):
            motor_task.submit_turn_goal(90, rpm=30, tolerance_deg=4.0, timeout_s=6.0)

        self.assertIsNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})

    def test_motor_pid_loop_turn_success_clears_goal_and_stops(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._fake_sensor_state["heading"] = 46.0
        motor_task._turn_goal = {
            "direction": 1.0,
            "start_heading": 0.0,
            "target_degrees": 45.0,
            "tolerance_deg": 1.0,
            "deadline_ms": 2000,
        }
        motor_task._target_rpm = {"left": 30.0, "right": -30.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 1)
        self.assertEqual(motor_task._right_pid.reset_calls, 1)
        self.assertEqual(motor_task._left_motor.brake_calls, 1)
        self.assertEqual(motor_task._right_motor.brake_calls, 1)
        self.assertEqual(motor_task._left_motor.drive_calls[-1], 0.0)
        self.assertEqual(motor_task._right_motor.drive_calls[-1], 0.0)

    def test_motor_pid_loop_turn_timeout_clears_goal_and_stops(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._fake_sensor_state["heading"] = 0.0
        motor_task._fake_utime.now = 3000
        motor_task._turn_goal = {
            "direction": 1.0,
            "start_heading": 0.0,
            "target_degrees": 45.0,
            "tolerance_deg": 1.0,
            "deadline_ms": 2000,
        }
        motor_task._target_rpm = {"left": 30.0, "right": -30.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": 0.0, "right": 0.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 1)
        self.assertEqual(motor_task._right_pid.reset_calls, 1)
        self.assertEqual(motor_task._left_motor.brake_calls, 1)
        self.assertEqual(motor_task._right_motor.brake_calls, 1)
        self.assertEqual(motor_task._left_motor.drive_calls[-1], 0.0)
        self.assertEqual(motor_task._right_motor.drive_calls[-1], 0.0)

    def test_wrong_direction_heading_progress_does_not_complete_turn_goal(self):
        motor_task = make_motor_task_module()
        motor_task._ensure_initialized = lambda: None
        motor_task._left_motor = FakeMotor()
        motor_task._right_motor = FakeMotor()
        motor_task._left_pid = FakePID()
        motor_task._right_pid = FakePID()
        motor_task._left_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._right_enc = FakeEncoder(counts=[0], rpm_values=[0.0])
        motor_task._fake_sensor_state["heading"] = 30.0
        motor_task._turn_goal = {
            "direction": -1.0,
            "start_heading": 0.0,
            "target_degrees": 45.0,
            "tolerance_deg": 1.0,
            "deadline_ms": 5000,
        }
        motor_task._target_rpm = {"left": -30.0, "right": 30.0}

        with self.assertRaises(LoopBreak):
            asyncio.run(motor_task.motor_pid_loop())

        self.assertIsNotNone(motor_task._turn_goal)
        self.assertEqual(motor_task._target_rpm, {"left": -30.0, "right": 30.0})
        self.assertEqual(motor_task._left_pid.reset_calls, 0)
        self.assertEqual(motor_task._right_pid.reset_calls, 0)
        self.assertEqual(motor_task._left_motor.brake_calls, 0)
        self.assertEqual(motor_task._right_motor.brake_calls, 0)


if __name__ == "__main__":
    unittest.main()
