"""Transactional learning records; legacy JSON is a read-only migration source."""
from contextlib import contextmanager,closing
from pathlib import Path
from types import SimpleNamespace
import fcntl
import json
import os
import sqlite3
import tempfile

from allma_model.utils.persistence import StateRecoveryRequired,sync_directory

MAPS={'unit_topic','state','counter','variants','user'}
LISTS={'unit','feedback','recent'}
SETS={'sources','state_areas','user_topics','user_areas'}


def _dump(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))
def _read(raw):return json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite learning value')))


class LearningStore:
    VERSION=1

    def __init__(self,path,legacy,normalize):
        self.path=Path(path);self.legacy=Path(legacy) if legacy is not None else None
        self.normalize=normalize;self.generation=None;self._decoder=None

    @contextmanager
    def connect(self,readonly=False):
        uri=self.path.resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw')
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
            db.execute('PRAGMA synchronous=FULL');yield db

    @staticmethod
    def _meta(db):
        if db.execute('PRAGMA user_version').fetchone()!=(1,):raise ValueError('Unsupported learning database version')
        meta=dict(db.execute('SELECT key,value FROM learning_meta'))
        if (set(meta)!={'generation','delivery_checkpoint'} or type(meta['generation']) is not int
                or meta['generation']<0 or type(meta['delivery_checkpoint']) is not int
                or not 0<=meta['delivery_checkpoint']<2**53):
            raise ValueError('Invalid learning database checkpoint')
        return meta

    @classmethod
    def _snapshot(cls,db):
        meta=cls._meta(db)
        data={'schema_version':2,'delivery_checkpoint':meta['delivery_checkpoint'],
            'knowledge_base':{},'knowledge_states':{},'success_counters':{},'responses_pool':{},'user_progress':{}}
        for kind,key,raw in db.execute('SELECT kind,key,data FROM learning_maps'):
            if kind not in MAPS or not isinstance(key,str):raise ValueError('Invalid learning map')
            row=_read(raw)
            if kind=='unit_topic':
                if row!={}:raise ValueError('Invalid unit topic')
                data['knowledge_base'][key]=[]
            elif kind=='state':
                if not isinstance(row,dict) or set(row)!={'topic','content','confidence','last_updated','metadata'}:
                    raise ValueError('Invalid knowledge header')
                data['knowledge_states'][key]=dict(row,sources=[],feedback_history=[],improvement_areas=[])
            elif kind=='counter':data['success_counters'][key]=row
            elif kind=='variants':data['responses_pool'][key]=row
            elif kind=='user':
                if not isinstance(row,dict) or set(row)!={'confidence_levels'}:raise ValueError('Invalid progress header')
                data['user_progress'][key]=dict(row,topics=[],recent_learning=[],improvement_areas=[])
        for kind,key,position,raw in db.execute('SELECT kind,key,position,data FROM learning_lists ORDER BY kind,key,position'):
            if kind not in LISTS:raise ValueError('Unknown learning sequence')
            if kind=='unit':target=data['knowledge_base'].get(key)
            elif kind=='feedback':target=data['knowledge_states'].get(key,{}).get('feedback_history')
            else:target=data['user_progress'].get(key,{}).get('recent_learning')
            if target is None or type(position) is not int or position!=len(target):raise ValueError('Invalid learning sequence order or owner')
            target.append(_read(raw))
        for kind,key,value in db.execute('SELECT kind,key,value FROM learning_sets ORDER BY kind,key,value'):
            if kind not in SETS or not isinstance(value,str):raise ValueError('Invalid learning set')
            if kind in ('sources','state_areas'):
                row=data['knowledge_states'].get(key);field='sources' if kind=='sources' else 'improvement_areas'
            else:
                row=data['user_progress'].get(key);field='topics' if kind=='user_topics' else 'improvement_areas'
            if row is None:raise ValueError('Orphan learning set')
            row[field].append(value)
        return data,meta['generation']

    @classmethod
    def validate_database(cls,path):
        from .incremental_learning import IncrementalLearner
        with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.execute('BEGIN')
            if db.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Invalid learning database integrity')
            data,_=cls._snapshot(db)
            IncrementalLearner()._decode_snapshot(data)

    def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(str(self.path)+'.init.lock',os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(descriptor,'r+b') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                if not self.path.exists():
                    if lock.read(32):raise StateRecoveryRequired('Learning database missing after migration; restore a verified backup')
                    self._initialize_locked()
                lock.seek(0);lock.write(b'initialized\n');lock.flush();os.fsync(lock.fileno())
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def _initialize_locked(self):
        data={'schema_version':2,'knowledge_states':{},'knowledge_base':{}}
        if self.legacy is not None and self.legacy.exists():data=_read(self.legacy.read_text(encoding='utf-8'))
        data=self.normalize(data)
        descriptor,name=tempfile.mkstemp(prefix=self.path.name+'.migration-',dir=self.path.parent)
        os.close(descriptor);temporary=Path(name)
        try:
            with closing(sqlite3.connect(temporary)) as db:
                db.execute('PRAGMA synchronous=FULL')
                db.executescript('''
                    CREATE TABLE learning_meta(key TEXT PRIMARY KEY NOT NULL,value INTEGER NOT NULL);
                    CREATE TABLE learning_maps(kind TEXT NOT NULL,key TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(kind,key));
                    CREATE TABLE learning_lists(kind TEXT NOT NULL,key TEXT NOT NULL,position INTEGER NOT NULL CHECK(position>=0),data TEXT NOT NULL,PRIMARY KEY(kind,key,position));
                    CREATE TABLE learning_sets(kind TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,PRIMARY KEY(kind,key,value));
                    PRAGMA user_version=1;
                ''')
                with db:
                    db.executemany('INSERT INTO learning_meta VALUES(?,?)',[('generation',0),('delivery_checkpoint',data['delivery_checkpoint'])])
                    self._full(db,data)
            self.validate_database(temporary)
            with temporary.open('rb') as reader:os.fsync(reader.fileno())
            os.replace(temporary,self.path);sync_directory(self.path.parent)
        finally:temporary.unlink(missing_ok=True)

    def load(self):
        self.initialize()
        with self.connect(readonly=True) as db:
            db.execute('BEGIN')
            if db.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Invalid learning database integrity')
            data,generation=self._snapshot(db)
        self.generation=generation
        return data

    def check_current_generation(self):
        with self.connect(readonly=True) as db:
            if self._meta(db)['generation']!=self.generation:
                raise StateRecoveryRequired('Learning changed in another writer; reload before continuing')

    @staticmethod
    def _map(db,kind,key,value):
        db.execute('INSERT INTO learning_maps VALUES(?,?,?) ON CONFLICT(kind,key) DO UPDATE SET data=excluded.data '
            'WHERE learning_maps.data!=excluded.data',(kind,key,_dump(value)))

    @staticmethod
    def _append(db,kind,key,start,values):
        db.executemany('INSERT INTO learning_lists VALUES(?,?,?,?)',((kind,key,i,_dump(value)) for i,value in enumerate(values,start)))

    @staticmethod
    def _sets(db,kind,key,previous,current):
        db.executemany('DELETE FROM learning_sets WHERE kind=? AND key=? AND value=?',((kind,key,v) for v in previous-current))
        db.executemany('INSERT INTO learning_sets VALUES(?,?,?)',((kind,key,v) for v in current-previous))

    @classmethod
    def _full(cls,db,data):
        for topic,units in data['knowledge_base'].items():
            cls._map(db,'unit_topic',topic,{});cls._append(db,'unit',topic,0,units)
        for topic,row in data['knowledge_states'].items():
            cls._map(db,'state',topic,{k:v for k,v in row.items() if k not in ('sources','feedback_history','improvement_areas')})
            cls._append(db,'feedback',topic,0,row['feedback_history'])
            cls._sets(db,'sources',topic,set(),set(row['sources']));cls._sets(db,'state_areas',topic,set(),set(row['improvement_areas']))
        for topic,count in data['success_counters'].items():cls._map(db,'counter',topic,count)
        for topic,pool in data['responses_pool'].items():cls._map(db,'variants',topic,pool)
        for user,row in data['user_progress'].items():
            cls._map(db,'user',user,{'confidence_levels':row['confidence_levels']})
            cls._append(db,'recent',user,0,row['recent_learning'])
            cls._sets(db,'user_topics',user,set(),set(row['topics']));cls._sets(db,'user_areas',user,set(),set(row['improvement_areas']))

    def _commit(self,checkpoint,update):
        with self.connect() as db:
            try:
                db.execute('BEGIN IMMEDIATE');meta=self._meta(db)
                if self.generation is None or meta['generation']!=self.generation:
                    raise StateRecoveryRequired('Learning changed in another writer; reload before saving')
                if checkpoint<meta['delivery_checkpoint']:raise ValueError('Learning checkpoint cannot move backwards')
                update(db)
                db.execute("UPDATE learning_meta SET value=? WHERE key='delivery_checkpoint'",(checkpoint,))
                db.execute("UPDATE learning_meta SET value=value+1 WHERE key='generation'")
                db.commit()
            except BaseException:
                db.rollback();raise
        self.generation+=1

    def replace(self,data):
        data=self.normalize(data)
        def update(db):
            for table in ('learning_lists','learning_sets','learning_maps'):db.execute('DELETE FROM '+table)
            self._full(db,data)
        self._commit(data['delivery_checkpoint'],update)

    def apply(self,learner,transaction):
        """Serialize tails and changed headers only; checkpoint shares their commit."""
        topic,user,old=transaction
        prior_units=old['knowledge_base'].get(topic,[]);units=learner.knowledge_base.get(topic,[])
        prior_state=old['knowledge_states'].get(topic);state=learner.knowledge_states.get(topic)
        prior_progress=old['user_progress'].get(user) if user is not None else None
        progress=learner.user_progress.get(user) if user is not None else None
        from .learning_views import PagedHistory
        histories = [prior_units]
        if prior_state:histories.append(prior_state.feedback_history)
        if prior_progress:histories.append(prior_progress['recent_learning'])
        manual_units = topic in getattr(old['knowledge_base'], 'pending', {})
        if manual_units or any((isinstance(h, PagedHistory) and h.edits) or
                (not isinstance(h, PagedHistory) and h) for h in histories):
            raise StateRecoveryRequired('Save manual historical edits explicitly before appending learning')
        history_start=len(prior_state.feedback_history) if prior_state else 0
        recent_start=len(prior_progress['recent_learning']) if prior_progress else 0
        if len(units)<len(prior_units) or (state and len(state.feedback_history)<history_start) or (progress and len(progress['recent_learning'])<recent_start):
            raise ValueError('Learning APIs may only append historical sequences')
        # Reuse the existing codec on a bounded projection. Historical list
        # prefixes are not encoded or validated again for a normal mutation.
        projection=SimpleNamespace(knowledge_base={topic:units[len(prior_units):]} if topic in learner.knowledge_base else {},
            knowledge_states={},success_counters={topic:learner.success_counters[topic]} if topic in learner.success_counters else {},
            responses_pool={topic:learner.responses_pool[topic]} if topic in learner.responses_pool else {},
            user_progress={},delivery_checkpoint=learner.delivery_checkpoint)
        if state:
            from copy import copy
            tail=copy(state);tail.feedback_history=state.feedback_history[history_start:];projection.knowledge_states[topic]=tail
        if progress:
            projection.user_progress[user]=dict(progress,recent_learning=progress['recent_learning'][recent_start:],
                topics=progress['topics']-(prior_progress['topics'] if prior_progress else set()),
                improvement_areas=progress['improvement_areas']-(prior_progress['improvement_areas'] if prior_progress else set()))
        data=self.normalize(type(learner)._snapshot(projection))
        def update(db):
            if topic in learner.knowledge_base:
                self._map(db,'unit_topic',topic,{})
                self._append(db,'unit',topic,len(prior_units),data['knowledge_base'][topic])
            if state:
                row=data['knowledge_states'][topic]
                self._map(db,'state',topic,{k:v for k,v in row.items() if k not in ('sources','feedback_history','improvement_areas')})
                self._append(db,'feedback',topic,history_start,row['feedback_history'])
                self._sets(db,'sources',topic,prior_state.sources if prior_state else set(),state.sources)
                self._sets(db,'state_areas',topic,prior_state.improvement_areas if prior_state else set(),state.improvement_areas)
            if topic in data['success_counters']:self._map(db,'counter',topic,data['success_counters'][topic])
            if topic in data['responses_pool']:self._map(db,'variants',topic,data['responses_pool'][topic])
            if progress:
                row=data['user_progress'][user]
                self._map(db,'user',user,{'confidence_levels':row['confidence_levels']})
                self._append(db,'recent',user,recent_start,row['recent_learning'])
                self._sets(db,'user_topics',user,prior_progress['topics'] if prior_progress else set(),progress['topics'])
                self._sets(db,'user_areas',user,prior_progress['improvement_areas'] if prior_progress else set(),progress['improvement_areas'])
        self._commit(data['delivery_checkpoint'],update)

    def _piece(self, kind, key, raw):
        """Use the public codec on one record, including during integrity scans."""
        from .incremental_learning import IncrementalLearner, decode_learning_unit, decode_learning_feedback
        row = _read(raw)
        if kind == 'unit':
            return decode_learning_unit(key, row)
        if kind == 'feedback':
            return decode_learning_feedback(row)
        if kind == 'recent':
            if not isinstance(row, dict) or not all(k in row for k in ('topic','confidence','timestamp')):
                raise ValueError('Invalid recent learning')
            return row
        payload = {'schema_version': 2, 'knowledge_states': {}, 'knowledge_base': {}}
        if kind == 'unit_topic':
            if not key or row != {}:
                raise ValueError('Invalid unit topic')
            return None
        if kind == 'state':
            if not isinstance(row, dict) or set(row) != {'topic','content','confidence','last_updated','metadata'}:
                raise ValueError('Invalid knowledge header')
            payload['knowledge_states'][key] = dict(row, sources=[], feedback_history=[], improvement_areas=[])
        elif kind == 'unit':
            payload['knowledge_base'][key] = [row]
        elif kind == 'counter':
            payload['success_counters'] = {key: row}
        elif kind == 'variants':
            payload['responses_pool'] = {key: row}
        elif kind == 'user':
            if not isinstance(row, dict) or set(row) != {'confidence_levels'}:
                raise ValueError('Invalid progress header')
            payload['user_progress'] = {key: row}
        elif kind == 'recent':
            payload['user_progress'] = {key: {'recent_learning': [row]}}
        elif kind == 'feedback':
            payload['knowledge_states'][key] = {'topic': key, 'content': '', 'confidence': 1,
                'last_updated': '2000-01-01T00:00:00', 'feedback_history': [row]}
        else:
            raise ValueError('Unknown learning record')
        if self._decoder is None:self._decoder = IncrementalLearner()._decode_snapshot
        states, base, progress, counters, pools, _ = self._decoder(payload)
        return {'state': lambda: states[key], 'unit': lambda: base[key][0],
            'counter': lambda: counters[key], 'variants': lambda: pools[key],
            'user': lambda: progress[key], 'recent': lambda: progress[key]['recent_learning'][0],
            'feedback': lambda: states[key].feedback_history[0]}[kind]()

    def load_paged(self):
        """Validate the whole archive with bounded payload memory, then expose views.

        This still scans for corruption. It does not pretend that a complete
        integrity check has constant execution time as the archive grows.
        """
        self.initialize()
        with self.connect(readonly=True) as db:
            db.execute('BEGIN')
            meta = self._meta(db)
            if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise ValueError('Invalid learning database integrity')
            for kind, key, raw in db.execute('SELECT kind,key,data FROM learning_maps'):
                if kind not in MAPS or not isinstance(key, str):
                    raise ValueError('Invalid learning map')
                self._piece(kind, key, raw)
            owners = {'unit': 'unit_topic', 'feedback': 'state', 'recent': 'user'}
            for kind, key, count, first, last, integers in db.execute(
                    "SELECT kind,key,COUNT(*),MIN(position),MAX(position),SUM(typeof(position)='integer') "
                    'FROM learning_lists GROUP BY kind,key'):
                if (kind not in owners or first != 0 or last != count - 1 or integers != count or
                        db.execute('SELECT 1 FROM learning_maps WHERE kind=? AND key=?', (owners[kind], key)).fetchone() is None):
                    raise ValueError('Invalid learning sequence order or owner')
            for kind, key, raw in db.execute('SELECT kind,key,data FROM learning_lists'):
                self._piece(kind, key, raw)
            owners = {'sources': 'state', 'state_areas': 'state', 'user_topics': 'user', 'user_areas': 'user'}
            for kind, key, value, owner in db.execute(
                    "SELECT s.kind,s.key,s.value,m.key FROM learning_sets s LEFT JOIN learning_maps m ON m.key=s.key AND "
                    "m.kind=CASE WHEN s.kind IN ('sources','state_areas') THEN 'state' ELSE 'user' END"):
                if kind not in owners or not isinstance(value, str) or owner is None:
                    raise ValueError('Invalid learning set owner')
        self.generation = meta['generation']
        return self.paged_views(), meta['delivery_checkpoint']

    def paged_views(self):
        from .learning_views import LearningMap, PagedHistory
        from .incremental_learning import IncrementalLearner
        with self.connect(readonly=True) as db:
            db.execute('BEGIN')
            if self._meta(db)['generation'] != self.generation:
                raise StateRecoveryRequired('Learning changed; reload required')
            keys = {kind: [] for kind in MAPS}
            for kind, key in db.execute('SELECT kind,key FROM learning_maps'):
                keys[kind].append(key)

        def history(kind, key, db):
            count = db.execute('SELECT COUNT(*) FROM learning_lists WHERE kind=? AND key=?', (kind, key)).fetchone()[0]
            def read(start, limit):
                with self.connect(readonly=True) as source:
                    source.execute('BEGIN')
                    if self._meta(source)['generation'] != self.generation:
                        raise StateRecoveryRequired('Learning changed; reload required')
                    rows = source.execute('SELECT data FROM learning_lists WHERE kind=? AND key=? AND position>=? '
                        'AND position<? ORDER BY position', (kind, key, start, start + limit)).fetchall()
                return [self._piece(kind, key, row[0]) for row in rows], sum(len(row[0].encode()) for row in rows)
            return PagedHistory(read, count)

        def reader(kind):
            def read(key):
                with self.connect(readonly=True) as db:
                    db.execute('BEGIN')
                    if self._meta(db)['generation'] != self.generation:
                        raise StateRecoveryRequired('Learning changed; reload required')
                    raw = db.execute('SELECT data FROM learning_maps WHERE kind=? AND key=?', (kind, key)).fetchone()[0]
                    value = self._piece(kind, key, raw)
                    cost = len(raw.encode())
                    if kind == 'unit_topic':
                        value = history('unit', key, db)
                    elif kind in ('state', 'user'):
                        set_kinds = ('sources', 'state_areas') if kind == 'state' else ('user_topics', 'user_areas')
                        sets = []
                        for set_kind in set_kinds:
                            entries = {r[0] for r in db.execute('SELECT value FROM learning_sets WHERE kind=? AND key=?', (set_kind, key))}
                            cost += sum(len(v.encode()) for v in entries)
                            sets.append(entries)
                        if kind == 'state':
                            value.sources, value.improvement_areas = sets
                            value.feedback_history = history('feedback', key, db)
                        else:
                            value['topics'], value['improvement_areas'] = sets
                            value['recent_learning'] = history('recent', key, db)
                return value, cost
            return read
        return (LearningMap(keys['state'], reader('state')),
            LearningMap(keys['unit_topic'], reader('unit_topic')),
            LearningMap(keys['user'], reader('user'), IncrementalLearner._progress_factory),
            LearningMap(keys['counter'], reader('counter')), LearningMap(keys['variants'], reader('variants')))

    def related_units(self, query, threshold, user_id, limit=24):
        """Bounded lexical retrieval; semantic memory remains the vector engine.

        Inspect the latest declaration for this owner in each topic, rather than
        combining obsolete and foreign declarations into a global TF-IDF index.
        Scanning is streaming; the retained shortlist has a fixed maximum.
        """
        import heapq
        import math
        import re
        from collections import Counter
        from .incremental_learning import IncrementalLearner
        tokens = lambda text: Counter(re.findall(r'[^\W_]+', text.casefold(), re.UNICODE))
        q = tokens(query)
        qnorm = math.sqrt(sum(v*v for v in q.values()))
        if not qnorm:
            return []
        candidates, current, found = [], None, False
        with self.connect(readonly=True) as db:
            db.execute('BEGIN')
            if self._meta(db)['generation'] != self.generation:
                raise StateRecoveryRequired('Learning changed; reload required')
            for key, raw in db.execute("SELECT key,data FROM learning_lists WHERE kind='unit' ORDER BY key,position DESC"):
                if key != current:
                    current, found = key, False
                if found:
                    continue
                unit = self._piece('unit', key, raw)
                if not IncrementalLearner._belongs_to_user(unit, user_id):
                    continue
                found = True
                counts = tokens(key + ' ' + unit.content)
                norm = math.sqrt(sum(v*v for v in counts.values()))
                score = sum(v*counts[k] for k,v in q.items()) / (qnorm*norm) if norm else 0
                if score >= threshold or set(q).intersection(tokens(key)):
                    entry = (score, key, unit)
                    if len(candidates) < limit:
                        heapq.heappush(candidates, entry)
                    elif entry[:2] > candidates[0][:2]:
                        heapq.heapreplace(candidates, entry)
        return [entry[2] for entry in sorted(candidates, key=lambda row: (-row[0],row[1]))]
