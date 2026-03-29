class RuntimeContext:
    """
    Tiny runtime container for boot outputs needed by the async runtime.
    """

    def __init__(self, heading_tracker, watchdog, ap, ssid):
        self.heading_tracker = heading_tracker
        self.watchdog = watchdog
        self.ap = ap
        self.ssid = ssid
