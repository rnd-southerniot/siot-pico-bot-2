# robot.py — facade API (robot-as-object pattern)
import tasks.motor_task as _motor_task
import tasks.sensor_task as _sensor_task


class RobotAPI:
    """
    Stable robot facade API.
    This is the contract between firmware and all browser-generated code.
    All public methods here are the complete API surface for exec() commands.
    Never expose HAL or task internals below this layer.
    """

    def forward(self, rpm=60.0):
        """Drive both wheels forward at rpm."""
        _motor_task.set_drive_targets(rpm, rpm)

    def backward(self, rpm=60.0):
        """Drive both wheels backward at rpm."""
        _motor_task.set_drive_targets(-rpm, -rpm)

    def turn_left(self, rpm=40.0):
        """Pivot left: right wheel forward, left wheel backward."""
        _motor_task.set_drive_targets(-rpm, rpm)

    def turn_right(self, rpm=40.0):
        """Pivot right: left wheel forward, right wheel backward."""
        _motor_task.set_drive_targets(rpm, -rpm)

    def turn_degrees(self, angle_deg, rpm=30.0, tolerance_deg=3.0, timeout_s=5.0):
        """
        Submit a non-blocking relative heading turn goal.

        Positive angle turns clockwise/right, negative angle turns
        counterclockwise/left. This method returns immediately; the async motor
        PID loop owns goal completion, timeout handling, and stop-on-exit behavior.
        """
        if rpm <= 0:
            raise ValueError("rpm must be > 0")
        if tolerance_deg <= 0:
            raise ValueError("tolerance_deg must be > 0")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        if angle_deg == 0:
            self.stop()
            return
        _motor_task.submit_turn_goal(angle_deg, rpm, tolerance_deg, timeout_s)

    def drive_distance_cm(self, distance_cm, rpm=40.0, tolerance_cm=1.0, timeout_s=5.0):
        """
        Submit a non-blocking encoder-distance goal.

        Positive distance drives forward, negative distance drives backward.
        This method returns immediately; the async motor PID loop owns goal
        completion, timeout handling, and motor stop-on-exit behavior.
        """
        if rpm <= 0:
            raise ValueError("rpm must be > 0")
        if tolerance_cm <= 0:
            raise ValueError("tolerance_cm must be > 0")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        if distance_cm == 0:
            self.stop()
            return
        _motor_task.submit_distance_goal(distance_cm, rpm, tolerance_cm, timeout_s)

    def stop(self):
        """Stop both wheels."""
        _motor_task.stop_motion()

    def status(self):
        """Return current robot state as JSON-serializable dict."""
        state = _sensor_task.get_sensor_state()
        return {
            "rpm_left":    _motor_task.get_actual_rpm("left"),
            "rpm_right":   _motor_task.get_actual_rpm("right"),
            "ir":          state["ir"],
            "distance_cm": state["distance_cm"],
            "color":       state["color"],
            "heading":     state["heading"],
            "tick":        state["tick"],
        }
