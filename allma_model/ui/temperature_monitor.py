"""
Device temperature monitoring for Android
Reads CPU and battery temperature sensors
"""

from kivy.utils import platform
import logging

class TemperatureMonitor:
    """Monitor device temperature on Android"""
    
    def __init__(self):
        self.is_android = platform == 'android'
        
        if self.is_android:
            logging.info("✅ TemperatureMonitor initialized (Android)")
    
    def get_temperatures(self):
        """
        Get current device temperatures
        
        Returns:
            dict: {'cpu': float, 'battery': float} in Celsius
        """
        if not self.is_android:
            # Fallback for desktop testing
            import random
            return {
                'cpu': round(random.uniform(35, 55), 1),
                'battery': round(random.uniform(30, 40), 1)
            }
        
        try:
            # ROBUST METHOD: Use Sticky Intent for Battery
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            IntentFilter = autoclass('android.content.IntentFilter')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            activity = PythonActivity.mActivity
            filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            battery_status = activity.registerReceiver(None, filter)
            
            if battery_status:
                raw_temp = battery_status.getIntExtra("temperature", 0)
                battery_temp = raw_temp / 10.0
            else:
                battery_temp = 25.0 # Fallback
            
            # CPU temperature: Try reading from thermal zones or estimate
            cpu_temp = self._get_cpu_temperature(battery_temp)
            
            return {
                'cpu': round(cpu_temp, 1),
                'battery': round(battery_temp, 1)
            }
            
        except Exception as e:
            logging.error(f"Error getting temperature: {e}")
            return {
                'cpu': 0.0,
                'battery': 0.0
            }
    
    def _get_cpu_temperature(self, battery_temp):
        """
        Read CPU temperature from thermal zone files
        Android exposes these in /sys/class/thermal/
        """
        try:
            # Common thermal zone paths for CPU
            thermal_paths = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/class/thermal/thermal_zone1/temp',
                '/sys/devices/virtual/thermal/thermal_zone0/temp',
                # Some Samsung specific
                '/sys/class/thermal/thermal_zone7/temp', # Often CPU on newer SOCs
            ]
            
            for path in thermal_paths:
                try:
                    import os
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            content = f.read().strip()
                            if content:
                                temp_raw = int(content)
                                # Temperature is in millidegrees, convert to Celsius
                                temp_celsius = temp_raw / 1000.0
                                
                                # Sanity check (20-100°C range)
                                if 20 <= temp_celsius <= 100:
                                    return temp_celsius
                except (FileNotFoundError, ValueError, PermissionError):
                    continue
            
            # Fallback: CPU usually 5-15°C hotter than battery during processing
            return battery_temp + 10.0
            
        except Exception as e:
            logging.warning(f"Could not read CPU temperature: {e}")
            return battery_temp + 8.0
