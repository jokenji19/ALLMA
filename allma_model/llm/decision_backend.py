"""Optional Hexagon for Decider's bounded prefill; the chat keeps its own device."""
import ctypes
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile

from . import native_backend as native

SOURCE_COMMIT='0c1e57098bba43ac29e6e3b677cdceebdd22334f'
RPC_SHA256='60f7d28f535a3bb589e44073d1c092015682b73cbe994cdbcc132d2624a5c00a'
PROFILE='sm8750-hexagon-v79-decider-q4km-20261024'
_registries=set()

def android_thermal_status():
    try:
        from jnius import autoclass
        activity=autoclass('org.kivy.android.PythonActivity').mActivity
        return int(activity.getSystemService('power').getCurrentThermalStatus())
    except Exception:
        return None

def rpc_digest():
    with Path('/vendor/lib64/libcdsprpc.so').open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def _component(path, digest):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:
        raise RuntimeError('Optional Hexagon component checksum mismatch')
    return data

def prepare_runtime(directory, cache_root, *, soc=None, driver_reader=rpc_digest,
                    thermal_reader=android_thermal_status, load=ctypes.CDLL):
    directory=Path(directory)
    with native._lock:
        metadata=json.loads((directory/'allma_runtime.json').read_text())
        cpu=native.BackendChoice(reason='decision_cpu',
                                device_ids=() if metadata.get('explicit_devices') is True else None)
        if (metadata.get('runtime_id')!='allma-cpu-opencl-hexagon-v3'
                or metadata.get('python_version')!='0.3.36'
                or metadata.get('explicit_devices') is not True):
            return cpu
        if (soc if soc is not None else native.android_soc())!='SM8750':
            return cpu.cpu_fallback('npu_unmeasured_soc')
        try:
            if thermal_reader() not in (0,1):
                return cpu.cpu_fallback('npu_thermal_unavailable')
            if driver_reader()!=RPC_SHA256:
                return cpu.cpu_fallback('npu_unmeasured_driver')
            manifest=metadata['hexagon']
            if (manifest['source_commit']!=SOURCE_COMMIT or manifest['role']!='decider'
                    or manifest['architecture']!='v79'
                    or set(manifest['files'])!={'libggml-hexagon.so','libggml-htp-v79.so.bin'}):
                return cpu.cpu_fallback('npu_incompatible_component')
            key=hashlib.sha256((PROFILE+SOURCE_COMMIT+RPC_SHA256+
                               manifest['files']['libggml-hexagon.so']).encode()).hexdigest()
            guard=native.NativeGuard(cache_root,key,filename='npu-decision-pending.json')
            if guard.blocked():
                return cpu.cpu_fallback('previous_npu_operation_incomplete')
            host=directory/'libggml-hexagon.so'
            _component(host,manifest['files'][host.name])
            skeleton=_component(directory/'libggml-htp-v79.so.bin',manifest['files']['libggml-htp-v79.so.bin'])
            target=Path(cache_root)/'hexagon-v79';target.mkdir(parents=True,exist_ok=True)
            path=target/'libggml-htp-v79.so'
            if not path.is_file() or path.read_bytes()!=skeleton:
                fd,temporary=tempfile.mkstemp(dir=target,prefix='htp-',suffix='.tmp')
                try:
                    with os.fdopen(fd,'wb') as writer:
                        writer.write(skeleton);writer.flush();os.fsync(writer.fileno())
                    os.replace(temporary,path)
                finally:
                    if os.path.exists(temporary):os.unlink(temporary)
            os.environ['ADSP_LIBRARY_PATH']=str(target)
            os.environ['GGML_HEXAGON_DEVICES']='HTP0'
            os.environ['GGML_HEXAGON_VERBOSE']='0'
            os.environ['GGML_HEXAGON_PROFILE']='0'
            with guard.operation('register'):
                native._load(directory/'libggml-base.so',load)
                native._load(directory/'libggml-cpu.so',load)
                ggml=native._load(directory/'libggml.so',load)
                if str(directory) not in native._cpu_registries:
                    native._register(ggml,directory/'libggml-cpu.so')
                    native._cpu_registries.add(str(directory))
                if str(host) not in _registries:
                    library=native._load(host,load,global_symbols=False)
                    initialize=library.ggml_backend_hexagon_reg
                    initialize.argtypes=[];initialize.restype=ctypes.c_void_p
                    registry=initialize()
                    if not registry:raise RuntimeError('Hexagon registry unavailable')
                    register=ggml.ggml_backend_register
                    register.argtypes=[ctypes.c_void_p];register.restype=None
                    register(registry);_registries.add(str(host))
                selected=native.device_ids(ggml,['HTP0'])
            return native.BackendChoice('hexagon','package_update_recovered' if guard.recovery else 'measured_decider_profile',RPC_SHA256,guard,selected,2)
        except Exception as error:
            logging.warning('[DeciderBackend] Optional NPU unavailable: %s',type(error).__name__)
            return cpu.cpu_fallback('npu_unavailable')

def prepare_android_backend():
    if 'ANDROID_PRIVATE' not in os.environ:
        return native.BackendChoice(reason='decision_cpu')
    library=os.environ.get('LLAMA_CPP_LIB')
    if not library or not Path(library).is_file():
        return native.BackendChoice(reason='decision_cpu')
    private=Path(os.environ['ANDROID_PRIVATE'])
    if private.name=='app':private=private.parent
    return prepare_runtime(Path(library).parent,private/'allma_native_cache')
