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
        self.battery_manager = None
        
        if self.is_android:
            try:
                from jnius import autoclass, cast
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                BatteryManager = autoclass('android.os.BatteryManager')
                
                activity = PythonActivity.mActivity
                self.battery_manager = cast(
                    BatteryManager,
                    activity.getSystemService(Context.BATTERY_SERVICE)
                )
                logging.info("✅ TemperatureMonitor initialized (Android)")
            except Exception as e:
                logging.error(f"❌ Failed to initialize TemperatureMonitor: {e}")
                self.battery_manager = None
    
    def get_temperatures(self):
        """
        Get current device temperatures
        
        Returns:
            dict: {'cpu': float, 'battery': float} in Celsius
        """
        if not self.is_android or not self.battery_manager:
            # Fallback for desktop testing
            import random
            return {
                'cpu': round(random.uniform(35, 55), 1),
                'battery': round(random.uniform(30, 40), 1)
            }
        
        try:
            # Battery temperature (in 0.1 degrees C, need to divide by 10)
            battery_temp = self.battery_manager.getIntProperty(
                self.battery_manager.BATTERY_PROPERTY_TEMPERATURE
            ) / 10.0
            
            # CPU temperature: Try reading from thermal zones
            cpu_temp = self._get_cpu_temperature()
            
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
    
    def _get_cpu_temperature(self):
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
            ]
            
            for path in thermal_paths:
                try:
                    with open(path, 'r') as f:
                        temp_raw = int(f.read().strip())
                        # Temperature is in millidegrees, convert to Celsius
                        temp_celsius = temp_raw / 1000.0
                        
                        # Sanity check (20-100°C range)
                        if 20 <= temp_celsius <= 100:
                            return temp_celsius
                except (FileNotFoundError, ValueError, PermissionError):
                    continue
            
            # Fallback: estimate from battery temp + offset
            from jnius import autoclass
            battery_temp = self.battery_manager.getIntProperty(
                self.battery_manager.BATTERY_PROPERTY_TEMPERATURE
            ) / 10.0
            
            # CPU usually 5-15°C hotter than battery during processing
            return battery_temp + 10.0
            
        except Exception as e:
            logging.warning(f"Could not read CPU temperature: {e}")
            # Use battery temp as fallback
            try:
                battery_temp = self.battery_manager.getIntProperty(
                    self.battery_manager.BATTERY_PROPERTY_TEMPERATURE
                ) / 10.0
                return battery_temp + 8.0
            except:
                return 45.0  # Safe default
