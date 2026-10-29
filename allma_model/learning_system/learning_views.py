"""Bounded decoded views over the canonical learning database.

The topic directory is small and frozen at load. Historical payloads stay in
SQLite; explicit snapshot/export is deliberately the materialising operation.
Manual edits are retained as dirty overlays, never silently evicted.
"""
from collections import OrderedDict
from collections.abc import MutableMapping, Sequence
from copy import copy, deepcopy
from hashlib import sha256


def stamp(value):
    if isinstance(value, PagedHistory):
        value.collect_edits()
        return ('history', value.count, repr(value.tail), repr(value.edits))
    if isinstance(value, dict):
        return tuple((k, stamp(v)) for k, v in value.items())
    if hasattr(value, '__dataclass_fields__'):
        return stamp(vars(value))
    return sha256(repr(value).encode()).digest()


class PagedHistory(Sequence):
    PAGE = 32
    CACHE_PAGES = 2
    CACHE_BYTES = 256 * 1024

    def __init__(self, reader, count):
        self.reader, self.count = reader, count
        self.tail, self.edits = [], {}
        self.cache = OrderedDict()

    def __len__(self):
        return self.count + len(self.tail)

    def collect_edits(self):
        for page, (rows, original, _) in self.cache.items():
            if stamp(rows) != original:
                for offset, value in enumerate(rows):
                    self.edits[page * self.PAGE + offset] = value

    def _page(self, page):
        if page in self.cache:
            self.cache.move_to_end(page)
            return self.cache[page][0]
        start = page * self.PAGE
        rows, cost = self.reader(start, min(self.PAGE, self.count - start))
        if len(rows) != min(self.PAGE, self.count - start):
            raise ValueError('Learning history changed or is incomplete; reload required')
        # Retain a single large page until the next read so manual edits can be
        # detected. The bound is two pages, with a byte budget for normal rows.
        while self.cache and (len(self.cache) >= self.CACHE_PAGES or
                sum(v[2] for v in self.cache.values()) + cost > self.CACHE_BYTES):
            self.collect_edits()
            self.cache.popitem(last=False)
        self.cache[page] = (rows, stamp(rows), cost)
        return rows

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self))) ]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        if index >= self.count:
            return self.tail[index - self.count]
        if index in self.edits:
            return self.edits[index]
        return self._page(index // self.PAGE)[index % self.PAGE]

    def append(self, value):
        self.tail.append(value)

    def __add__(self, values):
        result = deepcopy(self)
        result.tail.extend(values)
        return result

    def __deepcopy__(self, memo):
        self.collect_edits()
        result = type(self)(self.reader, self.count)
        result.tail, result.edits = deepcopy(self.tail, memo), deepcopy(self.edits, memo)
        return result

    def __eq__(self, other):
        return isinstance(other, Sequence) and len(self) == len(other) and all(a == b for a, b in zip(self, other))


class LearningMap(MutableMapping):
    CACHE_ENTRIES = 24
    CACHE_BYTES = 512 * 1024

    def __init__(self, keys, reader, factory=None):
        self.keys_at_load, self.reader, self.factory = frozenset(keys), reader, factory
        self.pending, self.deleted, self.cache = {}, set(), OrderedDict()

    def _collect_edits(self):
        for key, (value, original, _) in self.cache.items():
            if stamp(value) != original:
                self.pending[key] = value

    def __getitem__(self, key):
        if key in self.deleted:
            raise KeyError(key)
        if key in self.pending:
            return self.pending[key]
        if key not in self.keys_at_load:
            if self.factory is None:
                raise KeyError(key)
            value = self.factory()
            self.pending[key] = value
            return value
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key][0]
        value, cost = self.reader(key)
        while self.cache and (len(self.cache) >= self.CACHE_ENTRIES or
                sum(v[2] for v in self.cache.values()) + cost > self.CACHE_BYTES):
            self._collect_edits()
            self.cache.popitem(last=False)
        self.cache[key] = (value, stamp(value), cost)
        return value

    def get(self, key, default=None):
        return self[key] if key in self else default

    def __contains__(self, key):
        return key not in self.deleted and (key in self.pending or key in self.keys_at_load)

    def __setitem__(self, key, value):
        self.deleted.discard(key)
        self.pending[key] = value
        self.cache.pop(key, None)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        self.deleted.add(key)
        self.pending.pop(key, None)
        self.cache.pop(key, None)

    def __iter__(self):
        return iter(sorted((self.keys_at_load | self.pending.keys()) - self.deleted))

    def __len__(self):
        return len((self.keys_at_load | self.pending.keys()) - self.deleted)

    def __copy__(self):
        self._collect_edits()
        result = type(self)(self.keys_at_load, self.reader, self.factory)
        result.pending, result.deleted, result.cache = copy(self.pending), copy(self.deleted), copy(self.cache)
        return result

    def committed(self, key):
        if key in self.pending:
            self.keys_at_load = self.keys_at_load | {key}
            self.pending.pop(key, None)
            self.cache.pop(key, None)

    def full_committed(self):
        self.keys_at_load = frozenset((self.keys_at_load | self.pending.keys()) - self.deleted)
        self.pending.clear()
        self.deleted.clear()
        self.cache.clear()
