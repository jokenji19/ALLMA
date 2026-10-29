"""Technical process identity and narrowly verified recovery after APK updates."""
from functools import lru_cache
import json
import os
import re
import logging
import threading
import time

_owner = None

@lru_cache(maxsize=1)
def android_process_helper():
    # Like BackupCipher: JNI FindClass on a Python-created worker uses the
    # system classloader. Resolve the app class on Android's UI thread once.
    from android.runnable import run_on_ui_thread
    ready, results, errors = threading.Event(), [], []
    @run_on_ui_thread
    def load():
        try:
            from jnius import autoclass
            results.append(autoclass('org.allma.runtime.NativeProcessHealth'))
        except Exception as error:
            errors.append(error)
        finally:
            ready.set()
    load()
    if not ready.wait(10):
        raise RuntimeError('Android native health class not ready')
    if errors:
        raise RuntimeError('Android native health class unavailable') from errors[0]
    return results[0]


def process_owner(*, fresh=False):
    global _owner
    fallback = {'pid': os.getpid(), 'token': None}
    if 'ANDROID_PRIVATE' not in os.environ:
        return fallback
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        helper = android_process_helper()
        value = json.loads(str(helper.ownerForOperation(activity, fresh)))
        if _owner is not None and value.get('token') != _owner.get('token'):
            raise RuntimeError('Native process identity changed unexpectedly')
        if value.get('token'):
            _owner = value
        return value
    except Exception as error:
        # Unsupported Android/API/JNI must never permit automatic recovery.
        # A transient classloader failure must not be cached for the process.
        fallback['unavailable_reason'] = type(error).__name__ + ': ' + str(error)[:180]
        logging.warning('[NativeHealth] Process identity unavailable: %s', fallback['unavailable_reason'])
        return fallback


def exit_records(pid):
    if 'ANDROID_PRIVATE' not in os.environ:
        return []
    from jnius import autoclass
    activity = autoclass('org.kivy.android.PythonActivity').mActivity
    helper = android_process_helper()
    return json.loads(str(helper.exits(activity, int(pid))))


def operation_marker(profile, stage):
    return {'version': 2, 'profile': profile, 'stage': stage,
            'started_at_ms': int(time.time() * 1000),
            'owner': process_owner(fresh=stage in {'load', 'generate', 'synthetic_update_probe'})}


def recovery_probe(mode):
    """Synthetic marker only, for checking a real package-update exit record."""
    from pathlib import Path
    from .native_backend import NativeGuard
    from allma_model.utils.persistence import atomic_write_json
    private = Path(os.environ['ANDROID_PRIVATE'])
    if private.name == 'app':
        private = private.parent
    root = private / 'allma_native_cache' / 'synthetic_update_probe'
    guard = NativeGuard(root, 'diagnostic-only')
    if mode == 'arm':
        if guard.path.exists():
            raise ValueError('Esiste già una prova da verificare')
        marker = operation_marker('diagnostic-only', 'synthetic_update_probe')
        owner = marker['owner']
        if not owner.get('token'):
            raise RuntimeError('Identificatore Android non disponibile: ' + str(owner.get('unavailable_reason', 'API unavailable')))
        atomic_write_json(guard.path, marker)
        return {'armed': True, 'owner': owner, 'synthetic': True}
    if mode != 'verify' or not guard.path.exists():
        raise ValueError('Nessuna prova valida da verificare')
    blocked = guard.blocked()
    owner = json.loads(guard.path.read_text()).get('owner', {}) if guard.path.exists() else {}
    try:
        records = exit_records(owner['pid']) if type(owner.get('pid')) is int else []
    except Exception as error:
        records = []
        evidence_error = type(error).__name__
    else:
        evidence_error = None
    evidence = [{'pid': r.get('pid'), 'reason': r.get('reason'), 'timestamp_ms': r.get('timestamp_ms'),
                 'token_matches': r.get('token') == owner.get('token'),
                 'token_kind': 'allma' if str(r.get('token', '')).startswith('allma-native-v2-') else 'other_or_missing'}
                for r in records if isinstance(r, dict)]
    return {'blocked': blocked, 'proof': guard.recovery, 'exit_evidence': evidence,
            'exit_history_error': evidence_error,
            'marker_exists': guard.path.exists(), 'synthetic': True}


def update_recovery_proof(marker, records, *, now_ms=None):
    """An exact process token plus Android's PACKAGE_UPDATED reason is required.

    PID/time proximity alone is insufficient: Android can reuse process IDs.
    Old markers, force-stops, native crashes, ANRs and unavailable history stay
    quarantined. The token is random technical data, never conversation data.
    """
    if not isinstance(marker, dict) or marker.get('version') != 2:
        return None
    owner = marker.get('owner')
    start = marker.get('started_at_ms')
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    if (not isinstance(owner, dict) or type(owner.get('pid')) is not int
            or owner['pid'] <= 0 or type(start) is not int or not 0 < start <= now_ms
            or not isinstance(owner.get('token'), str)
            or not re.fullmatch(r'allma-native-v2-[0-9a-f]{32}', owner['token'])
            or owner.get('package') != 'org.allma.allma_prime'
            or owner.get('process') != owner['package']
            or not isinstance(records, list)):
        return None
    matching = [record for record in records if isinstance(record, dict)
                and record.get('pid') == owner['pid']
                and record.get('process') == owner['process']
                and record.get('token') == owner['token']]
    if len(matching) != 1:
        return None
    record = matching[0]
    stamp = record.get('timestamp_ms')
    if (type(record.get('reason')) is not int or record['reason'] != 16
            or type(stamp) is not int or not start <= stamp <= now_ms):
        return None
    return {'source': 'android_application_exit_info', 'reason': 'package_updated',
            'pid': owner['pid'], 'exit_timestamp_ms': stamp}


def backend_status(core):
    """Read existing state only; never load or probe an inference motor."""
    wrapper = getattr(core, '_llm', None)
    info = getattr(wrapper, 'backend_info', None)
    qwen = dict(info) if isinstance(info, dict) else {'kind': 'not_loaded', 'reason': 'not_loaded'}
    runtime = getattr(core, 'decision_runtime', None)
    engine = getattr(runtime, '_engine', None)
    info = getattr(engine, 'backend_info', None)
    decider = dict(info) if isinstance(info, dict) else {'kind': 'not_loaded', 'reason': 'not_loaded'}
    return {'qwen': qwen, 'decider': decider}
