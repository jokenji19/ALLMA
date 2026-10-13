"""Non-blocking resource readings. Missing sensors remain unknown, never simulated."""
import math
import sys
import time


class ResourceDiagnostics:
    def __init__(self):
        self._sample = None

    def read(self, monitor=None):
        result = {'cpu': None, 'ram': None, 'temp': None,
                  'cpu_source': 'process_cpu_one_core_percent',
                  'ram_source': 'process_peak_rss_mb', 'temp_source': 'battery_celsius'}
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            now = time.monotonic()
            cpu_seconds = usage.ru_utime + usage.ru_stime
            if self._sample is not None:
                previous_time, previous_cpu = self._sample
                if now > previous_time:
                    result['cpu'] = max(0., (cpu_seconds - previous_cpu) / (now - previous_time) * 100)
            self._sample = (now, cpu_seconds)
            divisor = 1024 * 1024 if sys.platform == 'darwin' else 1024
            result['ram'] = usage.ru_maxrss / divisor
        except (ImportError, OSError, AttributeError):
            pass
        try:
            temperature = monitor.get_metabolic_state().battery_temp_celsius
            if isinstance(temperature, (int, float)) and math.isfinite(temperature) and temperature > 0:
                result['temp'] = temperature
        except Exception:
            pass
        return result
