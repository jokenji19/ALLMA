"""Update recovery needs Android's exact process token, not merely a stale PID."""
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from allma_model.llm import native_backend as backend, native_health as health


@pytest.fixture
def previous():
    marker = {'version': 2, 'profile': 'profile', 'stage': 'generate', 'started_at_ms': 1000,
              'owner': {'pid': 999999, 'package': 'org.allma.allma_prime',
                        'process': 'org.allma.allma_prime', 'token': 'allma-native-v2-' + 'a' * 32}}
    record = {'pid': 999999, 'process': 'org.allma.allma_prime',
              'token': marker['owner']['token'], 'timestamp_ms': 2000, 'reason': 16}
    return marker, record


def test_package_update_requires_the_exact_process(previous):
    marker, record = previous
    assert health.update_recovery_proof(marker, [record], now_ms=3000)['reason'] == 'package_updated'


@pytest.mark.parametrize('reason', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, True, '16'])
def test_native_crash_anr_force_stop_or_unknown_never_reenables_acceleration(previous, reason):
    marker, record = previous
    record['reason'] = reason
    assert health.update_recovery_proof(marker, [record], now_ms=3000) is None


@pytest.mark.parametrize('field,value', [('pid', 123), ('token', 'another-owner'),
    ('process', 'org.allma.allma_prime:service'), ('timestamp_ms', 999), ('timestamp_ms', 3001)])
def test_pid_reuse_wrong_process_or_unrelated_update_is_insufficient(previous, field, value):
    marker, record = previous
    record[field] = value
    assert health.update_recovery_proof(marker, [record], now_ms=3000) is None


@pytest.mark.parametrize('records', [[], None, {}, 'missing'])
def test_unavailable_exit_history_keeps_quarantine(previous, records):
    assert health.update_recovery_proof(previous[0], records, now_ms=3000) is None


def test_ambiguous_records_do_not_recover(previous):
    marker, record = previous
    assert health.update_recovery_proof(marker, [record, dict(record, reason=5)], now_ms=3000) is None


@pytest.mark.parametrize('marker', [{}, {'profile': 'profile'}, {'version': 2, 'owner': None}, []])
def test_legacy_or_corrupt_markers_are_not_automatically_reset(marker):
    assert health.update_recovery_proof(marker, [], now_ms=3000) is None


def test_real_guard_preserves_audit_then_clears_only_verified_marker(previous, tmp_path, monkeypatch):
    marker, record = previous
    guard = backend.NativeGuard(tmp_path, 'profile')
    raw = json.dumps(marker)
    guard.path.write_text(raw)
    monkeypatch.setattr(health, 'exit_records', lambda pid: [record])
    assert not guard.blocked()
    assert guard.recovery['reason'] == 'package_updated'
    assert not guard.path.exists()
    audit = json.loads((tmp_path / 'gpu-recovery.json').read_text())
    assert audit['previous_marker'] == marker
    assert audit['proof'] == guard.recovery
    # The retry has a NEW owner. If it crashes, the old update record is no
    # longer a reason to unblock it a second time.
    retry = dict(marker, owner=dict(marker['owner'], token='allma-native-v2-' + 'b' * 32))
    guard.path.write_text(json.dumps(retry))
    assert backend.NativeGuard(tmp_path, 'profile').blocked()


def test_corrupt_or_failed_history_does_not_delete_marker(previous, tmp_path, monkeypatch):
    marker, _ = previous
    guard = backend.NativeGuard(tmp_path, 'profile')
    guard.path.write_text(json.dumps(marker))
    monkeypatch.setattr(health, 'exit_records', Mock(side_effect=RuntimeError('API unavailable')))
    assert guard.blocked() and guard.path.exists()


def test_marker_replaced_during_check_is_not_deleted(previous, tmp_path, monkeypatch):
    marker, record = previous
    guard = backend.NativeGuard(tmp_path, 'profile')
    guard.path.write_text(json.dumps(marker))
    def records(pid):
        guard.path.write_text('{"profile":"new-operation"}')
        return [record]
    monkeypatch.setattr(health, 'exit_records', records)
    assert guard.blocked()
    assert json.loads(guard.path.read_text())['profile'] == 'new-operation'


def test_current_owner_is_not_recovered_while_running(previous, tmp_path, monkeypatch):
    marker, record = previous
    marker['owner']['pid'] = os.getpid()
    record['pid'] = os.getpid()
    guard = backend.NativeGuard(tmp_path, 'profile')
    guard.path.write_text(json.dumps(marker))
    read = Mock(return_value=[record])
    monkeypatch.setattr(health, 'exit_records', read)
    assert guard.blocked()
    read.assert_not_called()


def test_markers_contain_only_technical_owner_data(tmp_path):
    guard = backend.NativeGuard(tmp_path, 'test')
    with guard.operation('load'):
        marker = json.loads(guard.path.read_text())
        assert marker['version'] == 2 and marker['owner']['pid'] == os.getpid()
        assert marker['started_at_ms'] > 0 and marker['stage'] == 'load'
    assert not guard.path.exists()


def test_update_waits_for_cpu_gpu_and_nested_work_then_blocks_new_work(tmp_path):
    try:
        with backend.native_activity():
            with backend.NativeGuard(tmp_path, 'test').operation():
                status = backend.update_status(reserve=True)
                assert not status['ready'] and not status['reserved']
        status = backend.update_status(reserve=True)
        assert status['ready'] and status['active_operations'] == 0
        with pytest.raises(backend.NativeUpdatePending):
            with backend.native_activity():
                pytest.fail('Native work started during install')
        with pytest.raises(backend.NativeUpdatePending):
            with backend.NativeGuard(tmp_path, 'test').operation():
                pytest.fail('GPU started during install')
        assert not (tmp_path / 'gpu-pending.json').exists()
    finally:
        backend.update_status(resume=True)
    with backend.native_activity():
        assert backend.update_status()['active_operations'] == 1


@pytest.mark.parametrize('motor', ['conversation', 'decider'])
def test_reserved_update_cannot_start_native_teardown_or_discard_live_motor(motor):
    import threading
    native = Mock()
    if motor == 'conversation':
        from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
        engine = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
        engine.inference_lock = threading.RLock()
        engine.llm = native
        attribute = 'llm'
    else:
        from allma_model.agency_system.decision_engine import LocalDecisionEngine
        engine = LocalDecisionEngine('synthetic.gguf')
        engine._native = native
        attribute = '_native'
    try:
        assert backend.update_status(reserve=True)['ready']
        with pytest.raises(backend.NativeUpdatePending):
            engine.close()
        assert getattr(engine, attribute) is native
        native.close.assert_not_called()
    finally:
        backend.update_status(resume=True)
    engine.close()
    native.close.assert_called_once()
    assert getattr(engine, attribute) is None


def test_diagnostics_read_actual_backends_without_loading_engines():
    core = SimpleNamespace(_llm=SimpleNamespace(backend_info={'kind': 'cpu', 'reason': 'previous_gpu_operation_incomplete'}),
        decision_runtime=SimpleNamespace(_engine=SimpleNamespace(backend_info={'kind': 'hexagon', 'reason': 'measured_decider_profile'})))
    data = health.backend_status(core)
    assert data['qwen']['kind'] == 'cpu' and data['decider']['kind'] == 'hexagon'
    data['qwen']['kind'] = 'changed'
    assert core._llm.backend_info['kind'] == 'cpu'
    assert health.backend_status(SimpleNamespace())['qwen']['kind'] == 'not_loaded'


def test_transient_android_classloader_failure_does_not_poison_process_identity(monkeypatch):
    monkeypatch.setenv('ANDROID_PRIVATE', '/synthetic/app')
    monkeypatch.setattr(health, '_owner', None)
    monkeypatch.setitem(sys.modules, 'jnius', SimpleNamespace(autoclass=lambda _: SimpleNamespace(mActivity=object())))
    helper = SimpleNamespace(ownerForOperation=Mock(return_value=json.dumps({'pid': os.getpid(), 'token': 'allma-native-v2-' + 'c' * 32})))
    load = Mock(side_effect=[RuntimeError('not on app classloader'), helper, helper])
    monkeypatch.setattr(health, 'android_process_helper', load)
    assert health.process_owner()['token'] is None
    assert health.process_owner()['token'] == 'allma-native-v2-' + 'c' * 32
    assert health.process_owner()['token'] == 'allma-native-v2-' + 'c' * 32
    assert load.call_count == 3 and helper.ownerForOperation.call_count == 2


def test_native_operation_refreshes_summary_even_when_owner_metadata_is_cached(monkeypatch):
    owner = {'pid': os.getpid(), 'token': 'allma-native-v2-' + 'd' * 32}
    monkeypatch.setenv('ANDROID_PRIVATE', '/synthetic/app')
    monkeypatch.setattr(health, '_owner', owner)
    monkeypatch.setitem(sys.modules, 'jnius', SimpleNamespace(autoclass=lambda _: SimpleNamespace(mActivity=object())))
    helper = SimpleNamespace(ownerForOperation=Mock(return_value=json.dumps(owner)))
    monkeypatch.setattr(health, 'android_process_helper', lambda: helper)
    assert health.operation_marker('test', 'register')['owner'] == owner
    assert health.operation_marker('test', 'generate')['owner'] == owner
    assert [call.args[1] for call in helper.ownerForOperation.call_args_list] == [False, True]


def test_failed_summary_refresh_can_retry_without_changing_owner_metadata(monkeypatch):
    owner = {'pid': os.getpid(), 'token': 'allma-native-v2-' + 'e' * 32}
    monkeypatch.setenv('ANDROID_PRIVATE', '/synthetic/app')
    monkeypatch.setattr(health, '_owner', owner)
    monkeypatch.setitem(sys.modules, 'jnius', SimpleNamespace(autoclass=lambda _: SimpleNamespace(mActivity=object())))
    helper = SimpleNamespace(ownerForOperation=Mock(side_effect=[RuntimeError('API not ready'), json.dumps(owner)]))
    monkeypatch.setattr(health, 'android_process_helper', lambda: helper)
    assert health.process_owner(fresh=True)['token'] is None
    assert health._owner == owner
    assert health.process_owner(fresh=True) == owner


def test_webview_or_other_library_version_is_never_an_owner_token(previous):
    marker, record = previous
    record['token'] = '155.0.8059.43'
    assert health.update_recovery_proof(marker, [record], now_ms=3000) is None


def installer():
    path = Path(__file__).resolve().parents[2] / 'tools/install_android_safe.py'
    spec = importlib.util.spec_from_file_location('safe_install', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_waits_for_gate_before_install_and_never_force_stops():
    device = Mock()
    device.js.return_value = True
    device.request.return_value = {'reserved': True, 'ready': True, 'busy': False, 'active_operations': 0}
    device.adb.return_value = 'Success'
    installer().install(Path('app.apk'), device)
    assert device.method_calls.index(('request', ('prepare_native_update',), {})) < device.method_calls.index(('adb', ('install', '-r', 'app.apk'), {'timeout': 120}))
    assert 'force-stop' not in str(device.adb.call_args_list)
    device.disconnect.assert_called_once()
    device.launch_after_install.assert_called_once()


def test_delayed_package_stop_is_retried_without_forcing_a_running_motor(monkeypatch):
    module = installer()
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    device = module.Device('synthetic')
    device.adb = Mock(side_effect=['Status: ok', '', 'Status: ok', '321', '321'])
    device.launch_after_install()
    starts = [c for c in device.adb.call_args_list if 'start' in c.args]
    assert len(starts) == 2 and all('-W' in c.args for c in starts)
    assert 'force-stop' not in str(device.adb.call_args_list)


def test_unchanged_package_process_does_not_keep_maintenance_gate_reserved(monkeypatch):
    module = installer()
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    device = module.Device('synthetic')
    device.pid = '321'
    device.adb = Mock(side_effect=['Status: ok', '321', '321'])
    device.request = Mock()
    device.launch_after_install()
    device.request.assert_called_once_with('resume_native_update')


@pytest.mark.parametrize('failure', ['busy', 'install', 'ack_lost'])
def test_failed_installation_releases_gate_without_killing_app(failure):
    device = Mock()
    device.js.return_value = True
    status = {'reserved': True, 'ready': True, 'busy': False, 'active_operations': 0}
    if failure == 'busy':
        status.update(reserved=False, ready=False, busy=True, active_operations=1)
    device.request.side_effect = [RuntimeError('lost') if failure == 'ack_lost' else status, {}]
    device.adb.side_effect = RuntimeError('installation failed')
    with pytest.raises(RuntimeError):
        installer().install(Path('app.apk'), device)
    assert device.request.call_args.args == ('resume_native_update',)
    if failure != 'install':
        device.adb.assert_not_called()
    device.disconnect.assert_called_once()
