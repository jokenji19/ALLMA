"""Measured-profile selection, CPU isolation and crash recovery contracts."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from allma_model.llm import native_backend as backend
from allma_model.llm.model_catalog import MODELS


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    backend._handles.clear()
    backend._cpu_registries.clear()
    backend._gpu_registries.clear()
    directory = tmp_path / 'llama_cpp'
    directory.mkdir()
    metadata = {'python_version': '0.3.36', 'qwen35': True, 'backends': ['CPU', 'OpenCL'],
                'dynamic_backends': True, 'source_sha256': 'source'}
    (directory / 'allma_runtime.json').write_text(json.dumps(metadata))
    for name in ['libggml-base.so', 'libggml-cpu.so', 'libggml.so', 'libggml-opencl.so']:
        (directory / name).touch()
    register = Mock(return_value=1)
    library = SimpleNamespace(ggml_backend_load=register)
    load = Mock(return_value=library)
    verify = Mock(return_value=True)
    driver = Mock(return_value=('QUALCOMM Adreno(TM) 830', backend.TESTED_DRIVER))
    model = tmp_path / MODELS['qwen35_2b']['filename']
    def prepare(**overrides):
        args = dict(verify_model=verify, cache_root=tmp_path/'cache', soc='SM8750',
                    driver_reader=driver, load=load)
        args.update(overrides)
        return backend.prepare_runtime(directory, model, **args)
    return SimpleNamespace(directory=directory, prepare=prepare, metadata=metadata,
                           register=register, load=load, verify=verify, driver=driver)


def test_measured_profile_loads_cpu_first_and_enables_gpu(runtime):
    choice = runtime.prepare()
    assert choice.kind == 'opencl'
    assert choice.kwargs == {'n_gpu_layers': -1, 'offload_kqv': True, 'op_offload': True,
                             'n_ubatch': 256, 'n_threads_batch': 4}
    names = [Path(call.args[0].decode()).name for call in runtime.register.call_args_list]
    assert names == ['libggml-cpu.so', 'libggml-opencl.so']
    assert not choice.guard.path.exists()
    runtime.prepare()
    assert runtime.register.call_count == 2


def test_explicit_cpu_diagnostic_does_not_probe_or_register_gpu(runtime):
    runtime.metadata['explicit_devices'] = True
    (runtime.directory/'allma_runtime.json').write_text(json.dumps(runtime.metadata))
    choice = runtime.prepare(force_cpu=True)
    assert choice.kind == 'cpu' and choice.reason == 'diagnostic_cpu'
    assert choice.kwargs == {'n_gpu_layers': 0, 'offload_kqv': False, 'op_offload': False, 'devices': []}
    runtime.driver.assert_not_called();runtime.verify.assert_not_called()
    assert runtime.register.call_count == 1


def test_cpu_diagnostic_rejects_runtime_without_explicit_device_isolation(runtime):
    with pytest.raises(RuntimeError, match='Explicit CPU isolation'):
        runtime.prepare(force_cpu=True)


def test_cpu_diagnostic_keeps_gpu_unselected_when_plugin_is_already_registered(runtime):
    assert runtime.prepare().kind == 'opencl'
    runtime.metadata['explicit_devices'] = True
    (runtime.directory/'allma_runtime.json').write_text(json.dumps(runtime.metadata))
    choice = runtime.prepare(force_cpu=True)
    assert choice.kwargs['devices'] == [] and choice.kwargs['op_offload'] is False
    assert runtime.register.call_count == 2


@pytest.mark.parametrize('soc', ['SM8650', 'SM8550', None, 'unknown'])
def test_unmeasured_hardware_keeps_cpu_without_driver_probe(runtime, soc, monkeypatch):
    monkeypatch.setattr(backend, 'android_soc', lambda: soc)
    choice = runtime.prepare(soc=soc)
    assert choice.kind == 'cpu'
    runtime.driver.assert_not_called()
    runtime.verify.assert_not_called()
    assert runtime.register.call_count == 1


@pytest.mark.parametrize('device,driver', [
    ('Different GPU', backend.TESTED_DRIVER), ('QUALCOMM Adreno(TM) 830', 'new driver'),
])
def test_driver_change_does_not_inherit_gpu_approval(runtime, device, driver):
    runtime.driver.return_value = (device, driver)
    assert runtime.prepare().reason == 'unmeasured_driver'
    assert runtime.register.call_count == 1


def test_unverified_model_stays_on_cpu(runtime):
    runtime.verify.return_value = False
    assert runtime.prepare().reason == 'unverified_or_unmeasured_model'
    runtime.driver.assert_not_called()


def test_older_cpu_runtime_does_not_load_plugins(runtime):
    runtime.metadata.update(backends=['CPU'], dynamic_backends=False)
    (runtime.directory/'allma_runtime.json').write_text(json.dumps(runtime.metadata))
    assert runtime.prepare().reason == 'cpu_runtime'
    runtime.register.assert_not_called()
    runtime.driver.assert_not_called()


def test_missing_optional_plugin_keeps_cpu(runtime):
    (runtime.directory/'libggml-opencl.so').unlink()
    assert runtime.prepare().reason == 'gpu_plugin_missing'
    assert runtime.register.call_count == 1


def test_gpu_registration_failure_keeps_cpu(runtime):
    runtime.register.side_effect = [1, None]
    assert runtime.prepare().reason == 'gpu_unavailable'


def test_vendor_library_access_failure_keeps_cpu(runtime):
    runtime.driver.side_effect = OSError('not accessible')
    assert runtime.prepare().reason == 'gpu_unavailable'
    assert runtime.register.call_count == 1


def test_cpu_registration_failure_is_not_silently_ignored(runtime):
    runtime.register.return_value = None
    with pytest.raises(RuntimeError, match='registration failed'):
        runtime.prepare()


def test_pending_native_operation_quarantines_gpu(runtime):
    choice = runtime.prepare()
    choice.guard.path.parent.mkdir(exist_ok=True)
    choice.guard.path.write_text(json.dumps({'profile': choice.guard.key}))
    assert runtime.prepare().reason == 'previous_gpu_operation_incomplete'


def test_malformed_pending_operation_is_fail_closed(runtime):
    choice = runtime.prepare()
    choice.guard.path.parent.mkdir(exist_ok=True)
    choice.guard.path.write_text('{bad')
    assert runtime.prepare().kind == 'cpu'


def test_native_process_death_leaves_recovery_marker(tmp_path):
    script = "from allma_model.llm.native_backend import NativeGuard; import os,sys\nwith NativeGuard(sys.argv[1],'test').operation(): os._exit(17)"
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)],
                            cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 17
    assert backend.NativeGuard(tmp_path, 'test').blocked()
    assert not backend.NativeGuard(tmp_path, 'different-profile').blocked()


def test_normal_exception_and_nested_operations_clear_only_at_outer_exit(tmp_path):
    one = backend.NativeGuard(tmp_path, 'test')
    two = backend.NativeGuard(tmp_path, 'test')
    with pytest.raises(ValueError):
        with one.operation():
            with two.operation():
                assert one.path.exists()
            assert one.path.exists()
            raise ValueError('ordinary Python failure')
    assert not one.path.exists()


def test_concurrent_guards_share_one_operation_lock(tmp_path):
    def operation(_):
        guard = backend.NativeGuard(tmp_path, 'test')
        with guard.operation():
            assert json.loads(guard.path.read_text())['profile'] == 'test'
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(operation, range(16)))
    assert not backend.NativeGuard(tmp_path, 'test').path.exists()


@pytest.mark.parametrize('gpu_fails', [False, True])
def test_wrapper_constructs_once_or_retries_cpu_after_gpu_failure(tmp_path, monkeypatch, gpu_fails):
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    module = SimpleNamespace()
    calls = []
    class FakeLlama:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            if gpu_fails and kwargs['n_gpu_layers'] == -1:
                raise RuntimeError('GPU allocation failed')
    module.Llama = FakeLlama
    monkeypatch.setitem(sys.modules, 'llama_cpp', module)
    monkeypatch.delitem(sys.modules, 'llama_cpp.llama_cpp', raising=False)
    choice = backend.BackendChoice('opencl', 'test', 'driver', backend.NativeGuard(tmp_path, 'test'))
    monkeypatch.setattr(backend, 'prepare_android_backend', lambda _: choice)
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.model_path = '/data/model.gguf'
    wrapper.n_ctx = 2048
    wrapper.system_monitor = None
    wrapper._load()
    assert wrapper.llm is not None
    assert len(calls) == (2 if gpu_fails else 1)
    assert calls[0]['n_gpu_layers'] == -1
    if gpu_fails:
        assert calls[-1]['n_gpu_layers'] == 0
        assert calls[-1]['op_offload'] is False
    assert wrapper.backend_info['kind'] == ('cpu' if gpu_fails else 'opencl')
    assert not choice.guard.path.exists()


def test_cpu_generation_does_not_write_a_gpu_marker(tmp_path):
    class Wrapper:
        @backend.native_operation
        def generate(self): return 'response'
    assert Wrapper().generate() == 'response'
    assert not list(tmp_path.iterdir())


def test_interactive_scheduling_is_configured_before_plugin_registration(runtime, monkeypatch):
    runtime.metadata['interactive_scheduling'] = True
    (runtime.directory/'allma_runtime.json').write_text(json.dumps(runtime.metadata))
    monkeypatch.delenv('ALLMA_OPENCL_SCHEDULING', raising=False)
    observed = []
    original = backend._register
    def register(ggml, path):
        if path.name == 'libggml-opencl.so':
            observed.append(backend.os.environ.get('ALLMA_OPENCL_SCHEDULING'))
        return original(ggml, path)
    monkeypatch.setattr(backend, '_register', register)
    choice = runtime.prepare()
    assert choice.kind == 'opencl'
    assert observed == ['interactive']
    assert backend.BackendChoice().kwargs == {
        'n_gpu_layers': 0, 'offload_kqv': False, 'op_offload': False}


@pytest.fixture
def npu_runtime(runtime, tmp_path):
    import hashlib
    from allma_model.llm import decision_backend as npu
    npu._registries.clear()
    data={'libggml-hexagon.so':b'host fixture','libggml-htp-v79.so.bin':b'DSP fixture'}
    manifest={'source_commit':npu.SOURCE_COMMIT,'architecture':'v79','role':'decider',
              'files':{name:hashlib.sha256(value).hexdigest() for name,value in data.items()}}
    runtime.metadata.update(runtime_id='allma-cpu-opencl-hexagon-v3',explicit_devices=True,
                            backends=['CPU','OpenCL','Hexagon'],hexagon=manifest)
    (runtime.directory/'allma_runtime.json').write_text(json.dumps(runtime.metadata))
    for name,value in data.items():(runtime.directory/name).write_bytes(value)
    library=runtime.load.return_value
    library.ggml_backend_dev_by_name=Mock(side_effect=lambda name:111 if name==b'GPUOpenCL' else 222)
    library.ggml_backend_hexagon_reg=Mock(return_value=333)
    library.ggml_backend_register=Mock()
    def prepare(**kwargs):
        params=dict(soc='SM8750',driver_reader=lambda:npu.RPC_SHA256,thermal_reader=lambda:0,load=runtime.load)
        params.update(kwargs)
        return npu.prepare_runtime(runtime.directory,tmp_path/'cache',**params)
    return SimpleNamespace(runtime=runtime,prepare=prepare,npu=npu,library=library,cache=tmp_path/'cache')


def test_npu_decider_and_gpu_chat_keep_explicit_independent_devices(npu_runtime):
    fixture=npu_runtime
    chat=fixture.runtime.prepare()
    decision=fixture.prepare()
    assert chat.kind=='opencl' and chat.kwargs['devices']==[111]
    assert decision.kind=='hexagon' and decision.kwargs['devices']==[222]
    assert decision.kwargs['n_threads_batch']==2
    assert (fixture.cache/'hexagon-v79/libggml-htp-v79.so').read_bytes()==b'DSP fixture'
    fixture.prepare()
    fixture.library.ggml_backend_register.assert_called_once_with(333)
    assert decision.cpu_fallback('test').kwargs['devices']==[]


@pytest.mark.parametrize('overrides,reason',[
    ({'soc':'SM8650'},'npu_unmeasured_soc'),
    ({'driver_reader':lambda:'different'},'npu_unmeasured_driver'),
    ({'thermal_reader':lambda:None},'npu_thermal_unavailable'),
    ({'thermal_reader':lambda:2},'npu_thermal_unavailable'),
])
def test_unmeasured_or_hot_npu_preserves_cpu_decider(npu_runtime,overrides,reason):
    choice=npu_runtime.prepare(**overrides)
    assert choice.kind=='cpu' and choice.reason==reason and choice.kwargs['devices']==[]
    npu_runtime.library.ggml_backend_register.assert_not_called()


def test_corrupt_npu_component_is_not_loaded(npu_runtime):
    (npu_runtime.runtime.directory/'libggml-hexagon.so').write_bytes(b'corrupt')
    choice=npu_runtime.prepare()
    assert choice.kind=='cpu' and choice.reason=='npu_unavailable'
    npu_runtime.library.ggml_backend_hexagon_reg.assert_not_called()


def test_incomplete_npu_operation_does_not_quarantine_gpu(npu_runtime):
    choice=npu_runtime.prepare()
    choice.guard.path.parent.mkdir(exist_ok=True)
    choice.guard.path.write_text(json.dumps({'profile':choice.guard.key}))
    assert npu_runtime.prepare().reason=='previous_npu_operation_incomplete'
    assert npu_runtime.runtime.prepare().kind=='opencl'
    assert choice.guard.path.name=='npu-decision-pending.json'


def test_native_access_failure_keeps_decider_cpu_and_clears_python_error_marker(npu_runtime):
    def load(path,**kwargs):
        if Path(path).name=='libggml-hexagon.so':raise OSError('FastRPC unavailable')
        return npu_runtime.library
    npu_runtime.runtime.load.side_effect=load
    choice=npu_runtime.prepare()
    assert choice.kind=='cpu' and choice.kwargs['devices']==[]
    assert not (npu_runtime.cache/'npu-decision-pending.json').exists()
