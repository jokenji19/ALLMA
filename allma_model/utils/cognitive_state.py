"""Small persistent cognitive sections, independent of model weights and transient mood."""
import json
import logging
import math
import shutil
import threading
from pathlib import Path
from allma_model.utils.persistence import atomic_write_json


def unit_number(value, default):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        return default
    return float(value)


class CognitiveStateStore:
    _guard = threading.Lock()
    _locks = {}

    def __init__(self, db_path):
        self.path = Path(db_path).resolve().parent / 'cognitive_state.json' if db_path else None
        with self._guard:
            self.lock = self._locks.setdefault(str(self.path), threading.RLock())

    def _read(self):
        if self.path is None or not self.path.exists():
            return {'version': 1, 'sections': {}}
        try:
            state = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(state, dict) or state.get('version') != 1 or not isinstance(state.get('sections'), dict):
                raise ValueError('Invalid cognitive schema')
            return state
        except (OSError, ValueError):
            backup = self.path.with_name(self.path.name + '.invalid.bak')
            try:
                if not backup.exists():
                    shutil.copy2(self.path, backup)
            except OSError:
                pass
            logging.warning('Cognitive state unreadable; original preserved when possible')
            return {'version': 1, 'sections': {}}

    def get(self, section):
        with self.lock:
            value = self._read()['sections'].get(section, {})
            return value if isinstance(value, dict) else {}

    def put(self, section, value):
        if self.path is None:
            return
        with self.lock:
            state = self._read()
            state['sections'][section] = value
            atomic_write_json(self.path, state)
