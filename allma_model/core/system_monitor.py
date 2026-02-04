
"""SystemMonitor - Interfaccia sensoriale hardware per ALLMA (Brain v2)."""

import platform
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class MetabolicState:
    """Stato metabolico del sistema."""
    energy_level: float = 1.0       # 0.0 - 1.0 (Battery)
    cognitive_load: float = 0.0     # 0.0 - 1.0 (RAM/CPU)
    is_charging: bool = False       # Crucial for Dream Mode
    is_power_save: bool = False     # If OS is in power save
    
    @property
    def is_tired(self) -> bool:
        return self.energy_level < 0.15 and not self.is_charging

class SystemMonitor:
    def __init__(self, is_android: bool = False):
        self.is_android = is_android
        self.last_state = MetabolicState()
        
    def get_metabolic_state(self) -> MetabolicState:
        """Legge i sensori hardware e restituisce lo stato metabolico."""
        if self.is_android:
            return self._read_android_sensors()
        else:
            return self._read_desktop_sensors()

    def _read_android_sensors(self) -> MetabolicState:
        """Legge batteria e memoria tramite PyJnius."""
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
                return self.last_state
                
            level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
            status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            
            if level == -1 or scale == -1:
                energy = 0.5
            else:
                energy = level / float(scale)
                
            is_charging = (status == BatteryManager.BATTERY_STATUS_CHARGING or
                         status == BatteryManager.BATTERY_STATUS_FULL)
            
            # MEMORY
            ActivityManager = autoclass('android.app.ActivityManager')
            Context = autoclass('android.content.Context')
            act_mgr = cast(ActivityManager, context.getSystemService(Context.ACTIVITY_SERVICE))
            mem_info = autoclass('android.app.ActivityManager$MemoryInfo')()
            act_mgr.getMemoryInfo(mem_info)
            
            # total = mem_info.totalMem
            avail = mem_info.availMem
            # Load roughly inverted avail
            # (Simple approximation as totalMem access might vary by API level)
            # Defaulting to a safe heuristic if total unavailable in older APIs
            # Assuming 4GB average device for heuristic if needed, but try total first
            
            # For simplicity and safety on PyJnius:
            # High load if available < 500MB
            load = 0.0
            if avail < 500 * 1024 * 1024:
                load = 0.8
            elif avail < 1024 * 1024 * 1024:
                load = 0.5
            else:
                load = 0.2
                
            self.last_state = MetabolicState(
                energy_level=energy,
                cognitive_load=load,
                is_charging=is_charging
            )
            return self.last_state
            
        except Exception as e:
            print(f"[SystemMonitor] Error reading sensors: {e}")
            return self.last_state

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
        """Mock per desktop/macOS."""
        # Su Mac potremmo usare psutil, ma per ora mockiamo per test
        return MetabolicState(
            energy_level=0.45,  # Mock value
            cognitive_load=0.20,
            is_charging=True
        )
