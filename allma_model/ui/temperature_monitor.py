"""Read identified Android thermal sensors; never fabricate temperatures."""
from kivy.utils import platform
import glob
import logging
import math
import os
import time


class TemperatureMonitor:
    def __init__(self):
        self.is_android = platform == 'android'
        self.cpu_source = None

    def get_temperatures(self):
        result = {'cpu': None, 'battery': None,
                  'cpu_source': 'unavailable', 'battery_source': 'unavailable',
                  'sampled_at': time.time()}
        if not self.is_android:
            return result
        try:
            from jnius import autoclass
            intent = autoclass('android.content.Intent')
            intent_filter = autoclass('android.content.IntentFilter')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            status = activity.registerReceiver(None, intent_filter(intent.ACTION_BATTERY_CHANGED))
            if status:
                raw = status.getIntExtra('temperature', -1)
                if 0 < raw <= 1000:
                    result['battery'] = raw / 10.0
                    result['battery_source'] = 'android_battery_intent'
        except Exception as error:
            logging.debug('Battery temperature unavailable: %s', error)
        result['cpu'] = self._get_cpu_temperature(result['battery'])
        if result['cpu'] is not None:
            result['cpu_source'] = self.cpu_source
        return result

    def _get_cpu_temperature(self, battery_temp=None):
        self.cpu_source = None
        for zone in sorted(glob.glob('/sys/class/thermal/thermal_zone*')):
            try:
                with open(os.path.join(zone, 'type')) as stream:
                    sensor_type = stream.read().strip().lower()
                # thermal_zone0 is not necessarily CPU: accept identified SoC sensors.
                if not any(label in sensor_type for label in ('cpu', 'soc', 'ap_therm', 'cluster')):
                    continue
                with open(os.path.join(zone, 'temp')) as stream:
                    value = float(stream.read().strip()) / 1000.0
                if math.isfinite(value) and 0 < value <= 125:
                    self.cpu_source = 'thermal:' + sensor_type
                    return round(value, 1)
            except (OSError, ValueError):
                continue
        return None
