"""Real monitor code with synthetic JNI sensors and a controlled clock."""
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from allma_model.core.system_monitor import SystemMonitor
from allma_model.utils.background_work import power_allows_background


@pytest.fixture
def android_sensors(monkeypatch):
    values = {'level': 90, 'scale': 100, 'status': 2, 'temperature': 350}
    intent = NS(getIntExtra=lambda name, default: values.get(name, default))
    power = NS(isPowerSaveMode=Mock(return_value=False),getCurrentThermalStatus=Mock(return_value=0))
    memory = NS(getMemoryInfo=Mock(side_effect=lambda info: setattr(info, 'availMem', 2*1024**3)))
    activity = NS(registerReceiver=Mock(return_value=intent),
                  getSystemService=lambda name: {'power': power, 'activity': memory}[name])
    classes = {
        'org.kivy.android.PythonActivity': NS(mActivity=activity),
        'android.content.Intent': NS(ACTION_BATTERY_CHANGED='battery'),
        'android.content.IntentFilter': lambda action: action,
        'android.os.BatteryManager': NS(EXTRA_LEVEL='level', EXTRA_SCALE='scale', EXTRA_STATUS='status',
            EXTRA_TEMPERATURE='temperature', BATTERY_STATUS_CHARGING=2, BATTERY_STATUS_FULL=5,
            BATTERY_STATUS_DISCHARGING=3, BATTERY_STATUS_NOT_CHARGING=4, BATTERY_STATUS_UNKNOWN=1),
        'android.content.Context': NS(ACTIVITY_SERVICE='activity', POWER_SERVICE='power'),
        'android.app.ActivityManager': object,
        'android.app.ActivityManager$MemoryInfo': lambda: NS(availMem=0),
        'android.os.PowerManager': object,
        'android.os.Build$VERSION': NS(SDK_INT=34),
    }
    monkeypatch.setitem(sys.modules, 'jnius', NS(autoclass=lambda name: classes[name], cast=lambda cls, value: value))
    return NS(monitor=SystemMonitor(is_android=True), activity=activity, power=power, memory=memory, values=values)


def test_stale_success_cannot_authorize_background_after_sensor_error(android_sensors):
    sensors = android_sensors
    assert power_allows_background(sensors.monitor)
    sensors.activity.registerReceiver.side_effect = RuntimeError('JNI unavailable')
    assert not power_allows_background(sensors.monitor)
    assert sensors.monitor.last_state.is_valid is False
    assert sensors.monitor.last_state.error


def test_missing_battery_broadcast_invalidates_previous_success(android_sensors):
    sensors = android_sensors
    assert power_allows_background(sensors.monitor)
    sensors.activity.registerReceiver.return_value = None
    assert not power_allows_background(sensors.monitor)


def test_power_save_blocks_background_and_clears_on_fresh_read(android_sensors):
    sensors = android_sensors
    assert power_allows_background(sensors.monitor)
    sensors.power.isPowerSaveMode.return_value = True
    assert not power_allows_background(sensors.monitor)
    sensors.power.isPowerSaveMode.return_value = False
    assert power_allows_background(sensors.monitor)


@pytest.mark.parametrize('field,value', [('scale',0), ('level',-1), ('level',110),
    ('status',1), ('temperature',-1), ('temperature',float('nan'))])
def test_invalid_sensor_values_fail_closed(android_sensors, field, value):
    android_sensors.values[field] = value
    assert not power_allows_background(android_sensors.monitor)


def test_ram_failure_does_not_invalidate_a_valid_power_sample(android_sensors):
    sensors = android_sensors
    sensors.memory.getMemoryInfo.side_effect = RuntimeError('RAM unavailable')
    assert power_allows_background(sensors.monitor)
    assert sensors.monitor.get_metrics()['ram_free'] is None


def test_unavailable_power_save_status_cannot_authorize_work(android_sensors):
    sensors = android_sensors
    assert power_allows_background(sensors.monitor)
    sensors.power.isPowerSaveMode.side_effect = RuntimeError('Power service unavailable')
    assert not power_allows_background(sensors.monitor)


def test_old_sample_and_clock_rollback_are_rejected(android_sensors, monkeypatch):
    sensors = android_sensors
    state = sensors.monitor.get_metabolic_state()
    monitor = NS(get_metabolic_state=lambda: state)
    from allma_model.core import system_monitor
    clock = state.observed_at
    monkeypatch.setattr(system_monitor.time, 'monotonic', lambda: clock+11)
    assert not power_allows_background(monitor)
    monkeypatch.setattr(system_monitor.time, 'monotonic', lambda: clock-1)
    assert not power_allows_background(monitor)


def test_unknown_hardware_is_not_reported_as_low_battery():
    from allma_model.core.system_monitor import MetabolicState
    import time
    unknown = MetabolicState(energy_level=0., is_charging=False)
    assert not unknown.is_tired
    known = MetabolicState(energy_level=.1, is_charging=False,
        is_valid=True, source='synthetic', observed_at=time.monotonic())
    assert known.is_tired


def test_stale_temperature_is_not_reported_as_current(android_sensors):
    from allma_model.utils.resource_diagnostics import ResourceDiagnostics
    sensors = android_sensors
    assert ResourceDiagnostics().read(sensors.monitor)['temp'] == 35.
    sensors.activity.registerReceiver.return_value = None
    assert ResourceDiagnostics().read(sensors.monitor)['temp'] is None


def test_all_optional_consumers_reject_failed_or_power_save_readings(android_sensors):
    from allma_model.utils.background_work import power_allows_backup, power_allows_initiative
    sensors = android_sensors
    for allow in (power_allows_background, power_allows_backup, power_allows_initiative):
        assert allow(sensors.monitor)
    sensors.power.isPowerSaveMode.return_value = True
    for allow in (power_allows_background, power_allows_backup, power_allows_initiative):
        assert not allow(sensors.monitor)
    sensors.power.isPowerSaveMode.return_value = False
    sensors.activity.registerReceiver.side_effect = RuntimeError('Sensors unavailable')
    for allow in (power_allows_background, power_allows_backup, power_allows_initiative):
        assert not allow(sensors.monitor)


def test_background_cancellation_rechecks_power(android_sensors, monkeypatch):
    from threading import Event
    from allma_model.utils.background_work import BackgroundCancellation
    from allma_model.core import system_monitor
    clock = [100.]
    monkeypatch.setattr(system_monitor.time, 'monotonic', lambda: clock[0])
    token = BackgroundCancellation(Event(), Event(), android_sensors.monitor)
    assert token.is_set() is False
    android_sensors.activity.registerReceiver.return_value = None
    clock[0] += 1.1
    assert token.is_set() is True


@pytest.mark.parametrize('status',[2,3,4,5,6,None,True,-1,7])
def test_os_thermal_stress_blocks_optional_work_despite_cool_battery(android_sensors,status):
    from allma_model.utils.background_work import power_allows_initiative,power_allows_backup,power_allows_decision
    sensors=android_sensors;sensors.values['temperature']=350
    sensors.power.getCurrentThermalStatus.return_value=status
    state=sensors.monitor.get_metabolic_state()
    assert state.is_valid and state.battery_temp_celsius==35
    for allow in (power_allows_background,power_allows_initiative,power_allows_backup,power_allows_decision):
        assert not allow(sensors.monitor)
    sensors.power.getCurrentThermalStatus.return_value=0
    assert power_allows_background(sensors.monitor)


def test_thermal_api_failure_does_not_fabricate_or_invalidate_battery(android_sensors):
    sensors=android_sensors;sensors.power.getCurrentThermalStatus.side_effect=RuntimeError('synthetic thermal failure')
    state=sensors.monitor.get_metabolic_state()
    assert state.is_valid and state.battery_temp_celsius==35 and state.thermal_status is None
    assert state.thermal_api_available is True and not power_allows_background(sensors.monitor)


def test_pre_29_thermal_api_absence_has_an_explicit_battery_fallback(android_sensors,monkeypatch):
    sensors=android_sensors
    import jnius
    original=jnius.autoclass
    monkeypatch.setattr(jnius,'autoclass',lambda name:NS(SDK_INT=28) if name=='android.os.Build$VERSION' else original(name))
    state=sensors.monitor.get_metabolic_state()
    assert state.thermal_api_available is False and state.thermal_status is None
    assert power_allows_background(sensors.monitor)
    sensors.power.getCurrentThermalStatus.assert_not_called()
