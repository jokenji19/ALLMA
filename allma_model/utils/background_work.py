"""Fail-closed admission and cooperative cancellation for background model work."""
import math
from allma_model.core.system_monitor import current_power_reading, thermal_allows_optional


def _power_state(monitor, minimum_energy, maximum_temperature, charging=False):
    if monitor is None:
        return False
    try:
        state = monitor.get_metabolic_state()
        energy, temperature = state.energy_level, state.battery_temp_celsius
        return (current_power_reading(state) and thermal_allows_optional(state) and state.is_power_save is False
                and type(energy) in (int, float) and math.isfinite(energy) and minimum_energy <= energy <= 1
                and type(temperature) in (int, float) and math.isfinite(temperature)
                and 0 < temperature <= maximum_temperature
                and (not charging or state.is_charging is True))
    except Exception:
        return False


def power_allows_background(monitor):
    return _power_state(monitor, .72, 40, charging=True)


def power_allows_initiative(monitor):
    return _power_state(monitor, .2, 38.9)


def power_allows_backup(monitor):
    return _power_state(monitor, .2, 40)


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


def power_allows_decision(monitor):
    return _power_state(monitor, .15, 40)
