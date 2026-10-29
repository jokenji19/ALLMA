"""Optional native GPU backend, restricted to a measured model/driver profile."""
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from functools import wraps
import ctypes
import hashlib
import json
import logging
import os
from pathlib import Path
import threading

from allma_model.utils.persistence import atomic_write_json


PROFILE = 'adreno830-qwen35-q4km-interactive-60hz-20261024'
TESTED_DRIVER = 'OpenCL 3.0 QUALCOMM build: 0800.64.8 Compiler E031.47.18.56'
_lock = threading.RLock()
_handles = {}
_cpu_registries = set()
_gpu_registries = set()
_guard_locks = {}
_guard_depth = {}
_activity_lock = threading.RLock()
_active_operations = 0
_update_pending = False


class NativeUpdatePending(RuntimeError):
    """The installer has reserved an idle runtime; no new inference may start."""


@contextmanager
def native_activity():
    global _active_operations
    with _activity_lock:
        if _update_pending:
            raise NativeUpdatePending('Aggiornamento in preparazione')
        _active_operations += 1
    try:
        yield
    finally:
        with _activity_lock:
            _active_operations -= 1


def update_status(*, reserve=False, resume=False):
    global _update_pending
    with _activity_lock:
        if resume:
            _update_pending = False
        if reserve and not _active_operations:
            _update_pending = True
        return {'ready': _update_pending and not _active_operations,
                'reserved': _update_pending, 'active_operations': _active_operations}


class NativeGuard:
    """Unexplained death stays quarantined; a verified APK update may recover."""
    def __init__(self, root, key, *, filename='gpu-pending.json'):
        if filename not in {'gpu-pending.json','npu-decision-pending.json'}:
            raise ValueError('Unknown native operation marker')
        self.path = Path(root) / filename
        self.key = key
        self.recovery = None
        with _lock:
            self.lock = _guard_locks.setdefault(str(self.path), threading.RLock())

    def blocked(self):
        with self.lock:
            if _guard_depth.get(str(self.path), 0) or not self.path.exists():
                return False
            try:
                raw = self.path.read_bytes()
                marker = json.loads(raw)
                profile = marker['profile']
                if not isinstance(profile, str):
                    return True
                if profile != self.key:
                    return False
                from .native_health import exit_records, update_recovery_proof
                owner = marker.get('owner', {})
                if not isinstance(owner, dict) or type(owner.get('pid')) is not int or owner['pid'] == os.getpid():
                    return True
                proof = update_recovery_proof(marker, exit_records(owner['pid']))
                if proof is None or self.path.read_bytes() != raw:
                    return True
                # One bounded audit per backend; preserve the old marker before
                # removing it. A failed retry writes its own new process token.
                audit = self.path.with_name(self.path.stem.replace('-pending', '-recovery') + '.json')
                atomic_write_json(audit, {'previous_marker': marker, 'proof': proof,
                    'marker_sha256': hashlib.sha256(raw).hexdigest()})
                self.path.unlink()
                self.recovery = proof
                logging.info('[NativeBackend] Verified package update; previous pid=%s', owner['pid'])
                return False
            except (OSError, ValueError, KeyError, TypeError):
                return True
            except Exception:
                logging.warning('[NativeBackend] Exit history unavailable; keeping quarantine')
                return True

    @contextmanager
    def operation(self, stage='native_operation'):
        with native_activity(), self.lock:
            name = str(self.path)
            depth = _guard_depth.get(name, 0)
            if not depth:
                from .native_health import operation_marker
                atomic_write_json(self.path, operation_marker(self.key, stage))
            _guard_depth[name] = depth + 1
            try:
                yield
            finally:
                _guard_depth[name] -= 1
                if not _guard_depth[name]:
                    try:
                        self.path.unlink(missing_ok=True)
                    except OSError:
                        logging.warning('[NativeBackend] Could not clear GPU operation marker')


@dataclass(frozen=True)
class BackendChoice:
    kind: str = 'cpu'
    reason: str = 'portable_cpu'
    driver: str | None = None
    guard: NativeGuard | None = None
    device_ids: tuple[int, ...] | None = None
    batch_threads: int = 4

    @property
    def kwargs(self):
        gpu = self.kind in {'opencl', 'hexagon'}
        result = {'n_gpu_layers': -1 if gpu else 0,
                  'offload_kqv': gpu, 'op_offload': gpu}
        if gpu:
            # Keep the logical batch/context and reasoning budgets unchanged.
            # Smaller physical batches bound GPU dispatches; batch CPU helpers
            # no longer default to all cores while Android is drawing.
            result.update(n_ubatch=256, n_threads_batch=self.batch_threads)
        if self.device_ids is not None:
            result['devices'] = list(self.device_ids)
        return result

    def cpu_fallback(self, reason):
        return BackendChoice(reason=reason, device_ids=() if self.device_ids is not None else None)


def native_operation(function):
    @wraps(function)
    def guarded(self, *args, **kwargs):
        guard = getattr(self, '_native_guard', None)
        with native_activity(), guard.operation(function.__name__) if guard else nullcontext():
            return function(self, *args, **kwargs)
    return guarded


def native_work(function):
    """Count a motor's work without changing its existing model/guard lock order."""
    @wraps(function)
    def counted(self, *args, **kwargs):
        with native_activity():
            return function(self, *args, **kwargs)
    return counted


def android_soc():
    try:
        from jnius import autoclass
        return str(autoclass('android.os.Build').SOC_MODEL)
    except Exception:
        return None


def opencl_driver(load=ctypes.CDLL):
    library = load('libOpenCL.so')
    platforms = library.clGetPlatformIDs
    platforms.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    platforms.restype = ctypes.c_int
    devices = library.clGetDeviceIDs
    devices.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint,
                       ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    devices.restype = ctypes.c_int
    info = library.clGetDeviceInfo
    info.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_size_t)]
    info.restype = ctypes.c_int
    platform = ctypes.c_void_p()
    count = ctypes.c_uint()
    if platforms(1, ctypes.byref(platform), ctypes.byref(count)) != 0 or not count.value:
        raise RuntimeError('No OpenCL platform')
    device = ctypes.c_void_p()
    if devices(platform, 4, 1, ctypes.byref(device), ctypes.byref(count)) != 0 or not count.value:
        raise RuntimeError('No OpenCL GPU')
    values = []
    for field in (0x102B, 0x102D):  # CL_DEVICE_NAME, CL_DRIVER_VERSION
        buffer = ctypes.create_string_buffer(2048)
        if info(device, field, len(buffer), buffer, None) != 0:
            raise RuntimeError('OpenCL device information unavailable')
        values.append(buffer.value.decode('utf-8'))
    return tuple(values)


def _load(path, load, *, global_symbols=True):
    key = str(path)
    if key not in _handles:
        _handles[key] = load(key, mode=ctypes.RTLD_GLOBAL if global_symbols else ctypes.RTLD_LOCAL)
    return _handles[key]


def _register(ggml, path):
    function = ggml.ggml_backend_load
    function.argtypes = [ctypes.c_char_p]
    function.restype = ctypes.c_void_p
    if not function(os.fsencode(path)):
        raise RuntimeError('Native backend registration failed: ' + path.name)


def device_ids(ggml, names):
    select = ggml.ggml_backend_dev_by_name
    select.argtypes = [ctypes.c_char_p]
    select.restype = ctypes.c_void_p
    result = tuple(select(name.encode('ascii')) for name in names)
    if any(not pointer for pointer in result):
        raise RuntimeError('Requested native device unavailable')
    return tuple(int(pointer) for pointer in result)


def prepare_runtime(directory, model_path, *, verify_model, cache_root,
                    soc=None, driver_reader=opencl_driver, load=ctypes.CDLL, force_cpu=False):
    """CPU is always loaded first; only the measured profile may add OpenCL."""
    directory = Path(directory)
    with _lock:
        metadata = json.loads((directory / 'allma_runtime.json').read_text())
        def cpu(reason, driver=None):
            return BackendChoice(reason=reason, driver=driver,
                                 device_ids=() if metadata.get('explicit_devices') is True else None)
        if metadata.get('python_version') != '0.3.36' or not metadata.get('qwen35'):
            raise RuntimeError('Unsupported bundled native runtime')
        _load(directory / 'libggml-base.so', load)
        _load(directory / 'libggml-cpu.so', load)
        ggml = _load(directory / 'libggml.so', load)
        dynamic = metadata.get('dynamic_backends') is True
        if dynamic and str(directory) not in _cpu_registries:
            _register(ggml, directory / 'libggml-cpu.so')
            _cpu_registries.add(str(directory))
        if force_cpu:
            if metadata.get('explicit_devices') is not True:
                raise RuntimeError('Explicit CPU isolation is required for this diagnostic')
            return cpu('diagnostic_cpu')
        if not dynamic or 'OpenCL' not in metadata.get('backends', []):
            return cpu('cpu_runtime')
        if (soc if soc is not None else android_soc()) != 'SM8750':
            return cpu('unmeasured_soc')
        from .model_catalog import MODELS
        model = MODELS['qwen35_2b']
        if Path(model_path).name != model['filename'] or not verify_model(model_path, model):
            return cpu('unverified_or_unmeasured_model')
        try:
            name, driver = driver_reader()
            if name != 'QUALCOMM Adreno(TM) 830' or driver != TESTED_DRIVER:
                return cpu('unmeasured_driver', driver)
            key = hashlib.sha256((PROFILE + metadata['source_sha256'] + model['sha256'] + driver).encode()).hexdigest()
            guard = NativeGuard(cache_root, key)
            if guard.blocked():
                return cpu('previous_gpu_operation_incomplete', driver)
            gpu_path = directory / 'libggml-opencl.so'
            if not gpu_path.is_file():
                return cpu('gpu_plugin_missing', driver)
            if str(directory) not in _gpu_registries:
                if metadata.get('interactive_scheduling') is True:
                    os.environ['ALLMA_OPENCL_SCHEDULING'] = 'interactive'
                with guard.operation('register'):
                    _register(ggml, gpu_path)
                _gpu_registries.add(str(directory))
            os.environ['GGML_OPENCL_KERNEL_CACHE_DIR'] = str(Path(cache_root) / 'opencl')
            with guard.operation('device_selection'):
                selected=device_ids(ggml, ['GPUOpenCL']) if metadata.get('explicit_devices') is True else None
            return BackendChoice('opencl', 'package_update_recovered' if guard.recovery else 'measured_profile', driver, guard, selected)
        except Exception as error:
            logging.warning('[NativeBackend] OpenCL unavailable; keeping CPU: %s', error)
            return cpu('gpu_unavailable')


def prepare_android_backend(model_path, *, force_cpu=False):
    """Resolve only the APK package selected by main.py, never debug libraries."""
    if 'ANDROID_PRIVATE' not in os.environ:
        return BackendChoice()
    library = os.environ.get('LLAMA_CPP_LIB')
    if not library or not Path(library).is_file():
        raise RuntimeError('Bundled llama library unavailable')
    private = Path(os.environ['ANDROID_PRIVATE'])
    if private.name == 'app':
        private = private.parent
    from allma_model.utils.model_downloader import ModelDownloader
    downloader = ModelDownloader(str(Path(model_path).parent))
    return prepare_runtime(Path(library).parent, model_path, verify_model=downloader._valid,
                           cache_root=private / 'allma_native_cache', force_cpu=force_cpu)
