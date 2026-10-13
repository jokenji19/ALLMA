"""Fail-closed admission and cooperative cancellation for background model work."""
import math


def power_allows_background(monitor):
    if monitor is None:
        return False
    try:
        state = monitor.get_metabolic_state()
        energy, temperature = float(state.energy_level), float(state.battery_temp_celsius)
        return (state.is_charging is True and math.isfinite(energy) and energy >= .72
                and math.isfinite(temperature) and 0 < temperature <= 40)
    except Exception:
        return False


class BackgroundCancellation:
    def __init__(self, shutdown, active, monitor):
        self.shutdown, self.active, self.monitor = shutdown, active, monitor
        self._last_power_check = 0
        self._power_allowed = False

    def is_set(self):
        if self.shutdown.is_set() or self.active.is_set():
            return True
        import time
        now = time.monotonic()
        if now - self._last_power_check >= 1:
            self._power_allowed = power_allows_background(self.monitor)
            self._last_power_check = now
        return not self._power_allowed
