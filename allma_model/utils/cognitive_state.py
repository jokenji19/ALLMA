"""Small persistent cognitive sections, independent of model weights and transient mood."""
import json
import logging
import math
import threading
from pathlib import Path
from allma_model.utils.persistence import atomic_write_json, preserve_invalid_file, StateRecoveryRequired


def unit_number(value, default):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        return default
    return float(value)


class CognitiveStateStore:
    _guard = threading.Lock()
    _locks = {}

    def __init__(self, db_path):
        self.path = Path(db_path).resolve().parent / 'cognitive_state.json' if db_path else None
        self.load_error = None
        with self._guard:
            self.lock = self._locks.setdefault(str(self.path), threading.RLock())

    def _read(self, *, for_write=False):
        if self.path is None or not self.path.exists():
            if for_write and self.load_error is not None:
                raise StateRecoveryRequired('Archivio cognitivo da recuperare prima di salvare') from self.load_error
            return {'version': 1, 'sections': {}}
        try:
            state = json.loads(self.path.read_text(encoding='utf-8'))
            if (not isinstance(state, dict) or type(state.get('version')) is not int
                    or state['version'] != 1 or not isinstance(state.get('sections'), dict)
                    or any(not isinstance(v, dict) for v in state['sections'].values())):
                raise ValueError('Invalid cognitive schema')
            self.load_error = None
            return state
        except (OSError, ValueError) as error:
            self.load_error = error
            try:
                preserve_invalid_file(self.path)
            except OSError:
                pass
            logging.warning('Cognitive state unreadable; original preserved when possible')
            if for_write:
                raise StateRecoveryRequired('Archivio cognitivo da recuperare prima di salvare') from error
            return {'version': 1, 'sections': {}}

    def get(self, section):
        with self.lock:
            value = self._read()['sections'].get(section, {})
            return value if isinstance(value, dict) else {}

    def put(self, section, value):
        if not isinstance(section, str) or not section or not isinstance(value, dict):
            raise ValueError('A named cognitive section and dictionary are required')
        if self.path is None:
            return
        with self.lock:
            state = self._read(for_write=True)
            state['sections'][section] = value
            atomic_write_json(self.path, state)
