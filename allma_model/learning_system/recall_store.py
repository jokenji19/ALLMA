"""Transactional answer records; the bounded RAM cache is never the archive."""
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import closing, contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from allma_model.utils.persistence import sync_directory


class RecordView(Mapping):
    def __init__(self, store):
        self.store = store

    def __getitem__(self, key):
        value = self.store.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __iter__(self):
        # Iterate keys without loading every answer into RAM.
        with self.store.connect() as db:
            for row in db.execute('SELECT key FROM answers ORDER BY rowid'):
                yield row[0]

    def __len__(self):
        with self.store.connect() as db:
            return db.execute('SELECT COUNT(*) FROM answers').fetchone()[0]

    def __deepcopy__(self, memo):
        return {key: self[key] for key in self}


class RecallStore:
    VERSION = 1
    CACHE_SIZE = 500

    def __init__(self, path, valid_record, valid_snapshot, legacy_path=None):
        self.path = Path(path)
        self.valid_record = valid_record
        self.valid_snapshot = valid_snapshot
        self.legacy_path = Path(legacy_path) if legacy_path is not None else None
        self.cache = OrderedDict()
        self.generation = None
        self.view = RecordView(self)

    @contextmanager
    def connect(self, readonly=False):
        # Never recreate a removed or damaged live archive by opening it.
        uri = self.path.resolve().as_uri() + ('?mode=ro' if readonly else '?mode=rw')
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db:
            db.execute('PRAGMA synchronous=FULL')
            yield db

    @classmethod
    def validate_database(cls, path, valid_record):
        uri = Path(path).resolve().as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as db:
            if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise ValueError('Invalid recall database integrity')
            if db.execute('PRAGMA user_version').fetchone() != (cls.VERSION,):
                raise ValueError('Unsupported recall database version')
            meta = dict(db.execute('SELECT key,value FROM recall_meta'))
            checkpoint = meta.get('delivery_checkpoint')
            generation = meta.get('generation')
            if (type(checkpoint) is not int or not 0 <= checkpoint < 2**53
                    or type(generation) is not int or generation < 0):
                raise ValueError('Invalid recall database checkpoint')
            for key, raw in db.execute('SELECT key,record FROM answers'):
                if not valid_record(key, json.loads(raw)):
                    raise ValueError('Invalid recall database record')
            return checkpoint

    def initialize(self):
        if self.path.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Android app policy can reject hard links even inside private storage.
        # Serialize openers, then publish using the supported atomic rename.
        # Keep the empty lock file: unlinking it could split waiting openers
        # across different inodes. It is coordination, not backed-up state.
        import fcntl
        lock_path = self.path.with_name(self.path.name+'.init.lock')
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os,'O_NOFOLLOW',0), 0o600)
        with os.fdopen(descriptor,'r+b') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                if not self.path.exists():
                    self._initialize_locked()
            finally:
                fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def _initialize_locked(self):
        records, checkpoint = {}, 0
        if self.legacy_path is not None and self.legacy_path.exists():
            data = json.loads(self.legacy_path.read_text(encoding='utf-8'))
            records, checkpoint = self.valid_snapshot(data)
        fd, name = tempfile.mkstemp(prefix=self.path.name+'.migration-', dir=self.path.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            with closing(sqlite3.connect(temporary)) as db:
                db.execute('PRAGMA synchronous=FULL')
                db.executescript('''
                    CREATE TABLE answers(key TEXT PRIMARY KEY NOT NULL, record TEXT NOT NULL);
                    CREATE TABLE recall_meta(key TEXT PRIMARY KEY NOT NULL, value INTEGER NOT NULL);
                    PRAGMA user_version=1;
                ''')
                with db:
                    db.executemany('INSERT INTO answers VALUES (?,?)',
                        ((key,json.dumps(record,ensure_ascii=False)) for key,record in records.items()))
                    db.executemany('INSERT INTO recall_meta VALUES (?,?)',
                        [('delivery_checkpoint',checkpoint),('generation',0)])
            self.validate_database(temporary, self.valid_record)
            with temporary.open('rb') as reader:
                os.fsync(reader.fileno())
            os.replace(temporary,self.path)
            sync_directory(self.path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def load(self, initialize=False):
        if initialize:
            self.initialize()
        checkpoint = self.validate_database(self.path, self.valid_record)
        self.cache.clear()
        self.generation = None
        return checkpoint

    def _refresh_generation(self, db):
        current = db.execute("SELECT value FROM recall_meta WHERE key='generation'").fetchone()[0]
        if type(current) is not int or current < 0:
            raise ValueError('Invalid recall generation')
        if self.generation != current:
            self.cache.clear()
            self.generation = current

    def _remember(self, key, value):
        self.cache.pop(key, None)
        self.cache[key] = deepcopy(value)
        while len(self.cache) > self.CACHE_SIZE:
            self.cache.popitem(last=False)

    def get(self, key):
        with self.connect(readonly=True) as db:
            self._refresh_generation(db)
            if key in self.cache:
                value = self.cache.pop(key)
                self.cache[key] = value
                return deepcopy(value)
            row = db.execute('SELECT record FROM answers WHERE key=?', (key,)).fetchone()
            if row is None:
                return None
            value = json.loads(row[0])
            if not self.valid_record(key, value):
                raise ValueError('Invalid recall record')
            self._remember(key, value)
            return deepcopy(value)

    def apply(self, key, update, delivery_sequence=None):
        """Read, change record and advance replay checkpoint in one transaction."""
        if delivery_sequence is not None and (type(delivery_sequence) is not int
                or not 0 <= delivery_sequence < 2**53):
            raise ValueError('Invalid recall checkpoint')
        with self.connect() as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                checkpoint = db.execute("SELECT value FROM recall_meta WHERE key='delivery_checkpoint'").fetchone()[0]
                if delivery_sequence is not None and delivery_sequence <= checkpoint:
                    db.rollback()
                    return False, checkpoint
                row = db.execute('SELECT record FROM answers WHERE key=?', (key,)).fetchone()
                previous = json.loads(row[0]) if row is not None else None
                if previous is not None and not self.valid_record(key, previous):
                    raise ValueError('Invalid recall record')
                value = update(previous)
                if value is None:
                    db.rollback()
                    return False, checkpoint
                if not self.valid_record(key, value):
                    raise ValueError('Invalid recall update')
                db.execute('INSERT INTO answers VALUES (?,?) ON CONFLICT(key) DO UPDATE SET record=excluded.record',
                           (key,json.dumps(value,ensure_ascii=False)))
                if delivery_sequence is not None:
                    if type(delivery_sequence) is not int or not 0 <= delivery_sequence < 2**53:
                        raise ValueError('Invalid recall checkpoint')
                    checkpoint = delivery_sequence
                    db.execute("UPDATE recall_meta SET value=? WHERE key='delivery_checkpoint'", (checkpoint,))
                db.execute("UPDATE recall_meta SET value=value+1 WHERE key='generation'")
                db.commit()
            except BaseException:
                db.rollback()
                raise
            # Publish cache only after the durable transaction succeeds.
            self._refresh_generation(db)
            self._remember(key, value)
            return True, checkpoint
