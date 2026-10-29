
"""SystemMonitor - Interfaccia sensoriale hardware per ALLMA (Brain v2)."""

from dataclasses import dataclass, replace
from typing import Optional
import math
import threading
import time

@dataclass
class MetabolicState:
    """Stato metabolico del sistema."""
    energy_level: float = 1.0       # 0.0 - 1.0 (Battery)
    cognitive_load: float = 0.0     # 0.0 - 1.0 (RAM/CPU)
    is_charging: bool = False       # Crucial for Dream Mode
    is_power_save: bool = False     # If OS is in power save
    battery_temp_celsius: float = 0.0  # Temperatura batteria (proxy CPU)
    observed_at: Optional[float] = None  # Monotonic, never a persisted wall clock.
    source: str = 'unavailable'
    is_valid: bool = False
    error: Optional[str] = None
    thermal_status: Optional[int] = None
    thermal_api_available: Optional[bool] = None
    
    @property
    def is_tired(self) -> bool:
        # Unknown hardware is not evidence of an exhausted battery. Foreground
        # answers keep their normal budget; optional work has stricter gates.
        return current_power_reading(self) and self.energy_level < 0.15 and not self.is_charging


def current_power_reading(state, max_age=10.0):
    """Optional work requires a successful, recent and attributable sample."""
    try:
        observed = state.observed_at
        age = time.monotonic()-observed
        return (state.is_valid is True and isinstance(state.source, str)
                and bool(state.source) and state.source != 'unavailable'
                and type(observed) in (int, float) and math.isfinite(observed)
                and 0 <= age <= max_age)
    except (AttributeError, TypeError, ValueError):
        return False


def thermal_allows_optional(state):
    """Use the OS severity as well as battery temperature for optional work.

    Pre-29 devices explicitly fall back to the battery gates. A supported API
    that failed is unknown, and cannot admit extra work. Synthetic adapters and
    desktops retain their existing contract.
    """
    available = getattr(state, 'thermal_api_available', None)
    if available is False:
        return True
    if available is None and getattr(state, 'source', '') != 'android':
        return True
    status = getattr(state, 'thermal_status', None)
    return available is True and type(status) is int and 0 <= status < 2


class SystemMonitor:
    def __init__(self, is_android: bool = False):
        self.is_android = is_android
        self.last_state = MetabolicState()
        self._ram_free_mb = None
        self._sensor_lock = threading.RLock()
        self.wakelock = None
        
    def get_metrics(self):
        """Available RAM in MB, or unavailable; never a guessed capacity."""
        with self._sensor_lock:
            self._ram_free_mb = None
            if self.is_android:
                self.get_metabolic_state()
            else:
                try:
                    import os
                    self._ram_free_mb = os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / (1024 * 1024)
                except (ValueError, OSError, AttributeError):
                    pass
            return {'ram_free': self._ram_free_mb,
                    'ram_source': 'os' if self._ram_free_mb is not None else 'unavailable'}

    def get_metabolic_state(self) -> MetabolicState:
        """Legge i sensori hardware e restituisce lo stato metabolico."""
        with self._sensor_lock:
            if self.is_android:
                return self._read_android_sensors()
            return self._read_desktop_sensors()

    def _invalidate_power(self, reason):
        # Retain the last values for diagnostics, with their original age.
        # A failed refresh never turns them into a fresh valid sample.
        self.last_state = replace(self.last_state, is_valid=False, error=reason)
        return self.last_state

    def _read_android_sensors(self) -> MetabolicState:
        """Legge batteria e memoria tramite PyJnius."""
        observed_at = time.monotonic()
        self._ram_free_mb = None
        try:
            from jnius import autoclass, cast
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            
            # BATTERY INTENT
            Intent = autoclass('android.content.Intent')
            IntentFilter = autoclass('android.content.IntentFilter')
            BatteryManager = autoclass('android.os.BatteryManager')
            
            ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            batteryStatus = context.registerReceiver(None, ifilter)
            
            if not batteryStatus:
                return self._invalidate_power('battery_broadcast_unavailable')
                
            level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
            status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            # Temperatura in decimi di grado (es. 370 = 37.0°C)
            raw_temp = batteryStatus.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
            if (not all(type(v) in (int, float) and math.isfinite(v) for v in (level, scale, raw_temp))
                    or scale <= 0 or not 0 <= level <= scale or raw_temp < 0
                    or status not in (BatteryManager.BATTERY_STATUS_CHARGING,
                                      BatteryManager.BATTERY_STATUS_FULL,
                                      BatteryManager.BATTERY_STATUS_DISCHARGING,
                                      BatteryManager.BATTERY_STATUS_NOT_CHARGING)):
                return self._invalidate_power('invalid_battery_reading')
            batt_temp = raw_temp / 10.0
            energy = level / float(scale)
                
            is_charging = (status == BatteryManager.BATTERY_STATUS_CHARGING or
                         status == BatteryManager.BATTERY_STATUS_FULL)
            
            Context = autoclass('android.content.Context')
            PowerManager = autoclass('android.os.PowerManager')
            power = cast(PowerManager, context.getSystemService(Context.POWER_SERVICE))
            power_save = power.isPowerSaveMode()
            if type(power_save) is not bool:
                return self._invalidate_power('power_save_unavailable')
            thermal_status, thermal_available = None, None
            try:
                sdk = int(autoclass('android.os.Build$VERSION').SDK_INT)
                thermal_available = sdk >= 29
                if thermal_available:
                    value = power.getCurrentThermalStatus()
                    if type(value) is int and 0 <= value <= 6:
                        thermal_status = value
            except Exception:
                # Thermal and battery evidence remain separate. Failure of the
                # newer API cannot make a good battery reading stale or invented.
                pass
            # RAM is independent: a missing memory service must not turn a
            # successful power reading into a fabricated or stale one.
            load = 0.0
            try:
                ActivityManager = autoclass('android.app.ActivityManager')
                act_mgr = cast(ActivityManager, context.getSystemService(Context.ACTIVITY_SERVICE))
                mem_info = autoclass('android.app.ActivityManager$MemoryInfo')()
                act_mgr.getMemoryInfo(mem_info)
                avail = mem_info.availMem
                if type(avail) is int and avail >= 0:
                    self._ram_free_mb = avail / (1024 * 1024)
                    load = .8 if avail < 500*1024**2 else .5 if avail < 1024**3 else .2
            except Exception:
                pass
            self.last_state = MetabolicState(
                energy_level=energy,
                cognitive_load=load,
                is_charging=is_charging,
                battery_temp_celsius=batt_temp, is_power_save=power_save,
                observed_at=observed_at, source='android', is_valid=True,
                thermal_status=thermal_status, thermal_api_available=thermal_available
            )
            return self.last_state
            
        except Exception as e:
            return self._invalidate_power('android_read_failed:'+type(e).__name__)

    def acquire_wake_lock(self, reason: str = "ALLMA:BackgroundProcessing"):
        """Acquisisce un Partial WakeLock per mantenere la CPU attiva."""
        if not self.is_android:
            print(f"[SystemMonitor] WakeLock simulato acquisito: {reason}")
            return

        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            PowerManager = autoclass('android.os.PowerManager')
            
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            
            # PARTIAL_WAKE_LOCK = 1
            # Ensures CPU is on, screen can be off.
            self.wakelock = pm.newWakeLock(1, reason)
            self.wakelock.acquire()
            print(f"[SystemMonitor] ✅ WAKE_LOCK ACQUIRED: {reason}")
            
        except Exception as e:
            print(f"[SystemMonitor] ❌ Failed to acquire WakeLock: {e}")

    def release_wake_lock(self):
        """Rilascia il WakeLock se esistente."""
        if not self.is_android:
            print("[SystemMonitor] WakeLock simulato rilasciato.")
            return

        try:
            if self.wakelock and self.wakelock.isHeld():
                self.wakelock.release()
                self.wakelock = None
                print("[SystemMonitor] 🌙 WAKE_LOCK RELEASED.")
        except Exception as e:
            print(f"[SystemMonitor] Error releasing WakeLock: {e}")

    def _read_desktop_sensors(self) -> MetabolicState:
        """No desktop battery provider is implemented; do not simulate one."""
        return MetabolicState(energy_level=0., source='desktop_unavailable', error='not_implemented')
