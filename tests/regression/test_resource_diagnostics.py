from types import SimpleNamespace
from unittest.mock import Mock
from allma_model.utils.resource_diagnostics import ResourceDiagnostics


def test_cpu_requires_two_samples_temperature_is_sensor_value(monkeypatch):
    import resource
    import time
    import allma_model.utils.resource_diagnostics as source
    times = iter([10., 12.])
    monkeypatch.setattr(source, 'time', SimpleNamespace(monotonic=lambda: next(times)))
    usages = iter([SimpleNamespace(ru_utime=1., ru_stime=1., ru_maxrss=1048576),
                   SimpleNamespace(ru_utime=2., ru_stime=1., ru_maxrss=1048576)])
    monkeypatch.setattr(resource, 'getrusage', lambda _: next(usages))
    monitor = Mock(get_metabolic_state=Mock(return_value=SimpleNamespace(battery_temp_celsius=37.2,
        is_valid=True, observed_at=time.monotonic(), source='synthetic')))
    d = ResourceDiagnostics()
    assert d.read(monitor)['cpu'] is None
    reading = d.read(monitor)
    assert reading['cpu'] == 50
    assert reading['temp'] == 37.2


def test_unavailable_temperature_is_unknown():
    d = ResourceDiagnostics()
    assert d.read()['temp'] is None
    monitor = Mock(get_metabolic_state=Mock(side_effect=OSError('missing sensor')))
    assert d.read(monitor)['temp'] is None
