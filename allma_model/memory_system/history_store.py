"""Authoritative incremental conversation storage with a preserved JSON migration."""
from contextlib import closing, contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
from collections import deque

from allma_model.utils.autobiography_validation import validate_history_archive,validate_history_record
from allma_model.utils.persistence import sync_directory,StateRecoveryRequired


class HistoryStore:
    VERSION=1
    FIELDS={
        'messages':('conversation_id','role','content','timestamp','metadata','user_id'),
        'conversations':('id','user_id','timestamp','content','metadata'),
    }

    def __init__(self,path,legacy_path):
        self.path,self.legacy=Path(path),Path(legacy_path)
        self.generation=None
        self.loaded=False
        self.read_error=None

    @contextmanager
    def connect(self,readonly=False):
        uri=self.path.resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw')
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
            db.execute('PRAGMA synchronous=FULL')
            yield db

    @classmethod
    def validate_database(cls,path):
        uri=Path(path).resolve().as_uri()+'?mode=ro'
        with closing(sqlite3.connect(uri,uri=True)) as db:
            db.execute('BEGIN')
            return cls._validate_snapshot(db)[0]

    @classmethod
    def _validate_snapshot(cls,db,consume=None):
        generation,state=cls._validated_state(db)
        for kind,token,position,row,owner in cls._validated_rows(db,state):
            if consume is not None:consume(kind,token,position,row,owner)
        return generation,state

    @classmethod
    def _validated_state(cls,db):
        if db.execute('PRAGMA quick_check').fetchone()!=('ok',):
            raise ValueError('History database integrity check failed')
        if db.execute('PRAGMA user_version').fetchone()!=(cls.VERSION,):
            raise ValueError('Unsupported history database version')
        generation=db.execute('SELECT generation FROM history_meta WHERE singleton=1').fetchone()
        if generation is None or type(generation[0]) is not int or generation[0]<0:
            raise ValueError('Invalid history generation')
        state={name:json.loads(raw) for name,raw in db.execute('SELECT name,data FROM history_state')}
        groups=state.get('conversation_users')
        if (set(state)!={'conversation_users','user_data','trauma_log'} or not isinstance(groups,list)
                or any(not isinstance(uid,str) for uid in groups) or len(groups)!=len(set(groups))):
            raise ValueError('Invalid history state sections')
        validate_history_archive({'user_data':state['user_data'],'trauma_log':state['trauma_log']})
        return generation[0],state

    @classmethod
    def _validated_rows(cls,db,state,order=None):
        groups=set(state['conversation_users'])
        for kind in cls.FIELDS if order is None else order:
            previous={}
            query=('SELECT token,position,data,NULL FROM history_messages ORDER BY position'
                   if kind=='messages' else 'SELECT token,position,data,owner FROM history_conversations ORDER BY owner,position')
            for token,position,raw,owner in db.execute(query):
                if (not isinstance(token,str) or not token or type(position) is not int or position<0
                        or position<=previous.get(owner,-1)):
                    raise ValueError('Invalid history ordering')
                previous[owner]=position
                row=json.loads(raw)
                if kind=='conversations' and owner not in groups:raise ValueError('Unknown history owner')
                validate_history_record(kind,row)
                yield kind,token,position,row,owner
    def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(str(self.path)+'.init.lock',os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(descriptor,'r+b') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                if not self.path.exists():
                    if lock.read(32):
                        raise StateRecoveryRequired('History database missing after migration; restore a verified backup')
                    self._initialize_locked()
                lock.seek(0);lock.write(b'initialized\n');lock.flush();os.fsync(lock.fileno())
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def _initialize_locked(self):
        data={}
        if self.legacy.exists():
            data=json.loads(self.legacy.read_text(encoding='utf-8'))
        validate_history_archive(data)
        descriptor,name=tempfile.mkstemp(prefix=self.path.name+'.migration-',dir=self.path.parent)
        os.close(descriptor);temporary=Path(name)
        try:
            with closing(sqlite3.connect(temporary)) as db:
                db.execute('PRAGMA synchronous=FULL')
                db.executescript('''
                    CREATE TABLE history_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),generation INTEGER NOT NULL);
                    INSERT INTO history_meta VALUES(1,0);
                    CREATE TABLE history_state(name TEXT PRIMARY KEY,data TEXT NOT NULL);
                    CREATE TABLE history_messages(token TEXT PRIMARY KEY,position INTEGER NOT NULL,data TEXT NOT NULL);
                    CREATE TABLE history_conversations(token TEXT PRIMARY KEY,owner TEXT NOT NULL,position INTEGER NOT NULL,data TEXT NOT NULL);
                    CREATE INDEX history_message_order ON history_messages(position);
                    CREATE INDEX history_conversation_order ON history_conversations(owner,position);
                    PRAGMA user_version=1;
                ''')
                with db:
                    db.executemany('INSERT INTO history_messages VALUES(?,?,?)',
                        ((uuid4().hex,i,json.dumps(row,ensure_ascii=False)) for i,row in enumerate(data.get('messages',[]))))
                    db.executemany('INSERT INTO history_conversations VALUES(?,?,?,?)',
                        ((uuid4().hex,uid,i,json.dumps(row,ensure_ascii=False))
                         for uid,rows in data.get('conversations',{}).items() for i,row in enumerate(rows)))
                    db.executemany('INSERT INTO history_state VALUES(?,?)',[
                        ('conversation_users',json.dumps(list(data.get('conversations',{})),ensure_ascii=False)),
                        ('user_data',json.dumps(data.get('user_data',{}),ensure_ascii=False)),
                        ('trauma_log',json.dumps(data.get('trauma_log',[]),ensure_ascii=False))])
            self.validate_database(temporary)
            with temporary.open('rb') as reader:os.fsync(reader.fileno())
            os.replace(temporary,self.path);sync_directory(self.path.parent)
        finally:temporary.unlink(missing_ok=True)

    def load(self,message_type,conversation_type):
        if not self.loaded:self.initialize()
        messages,groups=[],{}
        def consume(kind,token,position,row,owner):
            from datetime import datetime
            row.setdefault('metadata',{})
            row['timestamp']=datetime.fromisoformat(row['timestamp'])
            constructor=message_type if kind=='messages' else conversation_type
            value=constructor(**{key:row.get(key) for key in self.FIELDS[kind]})
            value._archive_key,value._archive_position=token,position
            (messages if kind=='messages' else groups.setdefault(owner,[])).append(value)
        with self.connect(readonly=True) as db:
            db.execute('BEGIN')
            generation,state=self._validate_snapshot(db,consume)
            groups={uid:groups.get(uid,[]) for uid in state['conversation_users']}
        self.generation,self.loaded=generation,True
        self.read_error=None
        return messages,groups,state['user_data'],state['trauma_log']

    def _check_generation(self,db,expected=None):
        expected=self.generation if expected is None else expected
        found=db.execute('SELECT generation FROM history_meta WHERE singleton=1').fetchone()
        if found is None or found[0]!=expected:
            raise StateRecoveryRequired('History changed in another writer; reload before reading another page')

    def _decode_page(self,kind,owner,raw):
        try:
            data=json.loads(raw)
            validate_history_record(kind,data)
            return data
        except Exception as error:
            self.read_error=error
            raise

    def check_current_generation(self):
        with self.connect(readonly=True) as db:self._check_generation(db)

    def stream(self,kind,owner=None,*,reverse=False):
        """Read bounded pages, closing each transaction before yielding to callers.

        A changed archive invalidates the remaining read. It must never mix a
        new generation into an old iterator or hold a writer hostage while idle.
        """
        if kind not in self.FIELDS:raise ValueError('Unknown history collection')
        generation=self.generation
        direction='DESC' if reverse else 'ASC'
        last=None
        while True:
            conditions=['owner=?'] if kind=='conversations' else []
            parameters=[owner] if conditions else []
            if last is not None:
                conditions.append('position'+('<' if reverse else '>')+'?');parameters.append(last)
            where=' WHERE '+' AND '.join(conditions) if conditions else ''
            with self.connect(readonly=True) as db:
                db.execute('BEGIN');self._check_generation(db,generation)
                rows=db.execute(f'SELECT token,position,data FROM history_{kind}{where} '
                    f'ORDER BY position {direction} LIMIT 64',parameters).fetchall()
            if not rows:return
            for token,position,raw in rows:
                if self.generation!=generation:
                    raise StateRecoveryRequired('History changed during iteration; restart the read')
                yield token,position,self._decode_page(kind,owner,raw)
            last=rows[-1][1]
            if len(rows)<64:return

    def page(self,kind,owner,offset,count,total):
        if kind not in self.FIELDS:raise ValueError('Unknown history collection')
        where=' WHERE owner=?' if kind=='conversations' else ''
        parameters=(owner,) if where else ()
        # The tail uses the reverse index so accessing recent messages never
        # walks every preceding row through an OFFSET from the start.
        reverse=offset>total//2
        skip=total-offset-count if reverse else offset
        direction='DESC' if reverse else 'ASC'
        with self.connect(readonly=True) as db:
            db.execute('BEGIN');self._check_generation(db)
            rows=db.execute(f'SELECT token,position,data FROM history_{kind}{where} ORDER BY position {direction} LIMIT ? OFFSET ?',
                            (*parameters,count,skip)).fetchall()
        if reverse:rows.reverse()
        return [(token,position,self._decode_page(kind,owner,raw)) for token,position,raw in rows]

    def conversation_owner(self,identifier):
        owners=set()
        with self.connect(readonly=True) as db:
            for owner,raw in db.execute('SELECT owner,data FROM history_conversations'):
                if json.loads(raw).get('id')==identifier:owners.add(owner)
        return next(iter(owners)) if len(owners)==1 else None

    def verified_sources(self,db,records,user_id):
        """Resolve small search candidates against this authoritative snapshot."""
        from datetime import datetime
        from allma_model.core.history_projection import source_token
        from allma_model.core.autobiographical_identity import delivery_visible
        result=[]
        for item in records:
            token=source_token(item.get('source_key'))
            if not token:continue  # Domain memories are not autobiographical user reports.
            found=db.execute('SELECT data FROM history_messages WHERE token=?',(token,)).fetchone()
            if found is None:continue
            row=self._decode_page('messages',None,found[0]);metadata=row.get('metadata',{})
            owner=row.get('user_id') or metadata.get('user_id')
            if not owner:
                owners=set()
                for candidate,raw in db.execute('SELECT owner,data FROM history_conversations'):
                    conversation=self._decode_page('conversations',candidate,raw)
                    if conversation['id']==row['conversation_id']:owners.add(candidate)
                owner=next(iter(owners)) if len(owners)==1 else None
            if (owner!=user_id or row['role']!='user' or metadata.get('is_valid') is False
                    or metadata.get('revoked') is True or metadata.get('status') in ('revoked','superseded')
                    or not delivery_visible(metadata) or item.get('content')!=row['content']
                    or item.get('timestamp')!=datetime.fromisoformat(row['timestamp']).isoformat()):
                continue
            result.append({**item,'metadata':{**metadata,'role':row['role'],
                          'conversation_id':row['conversation_id'],'user_id':owner}})
        return result

    def load_pages(self,ingest=None):
        """Validate all bytes progressively; retain only a small recent window.

        The same decoded rows can feed the rebuildable index transaction. A bad
        final record rolls that transaction back before any state is published.
        """
        if not self.loaded:self.initialize()
        plan={'counts':{},'last':{},'recent':deque(maxlen=128),'highwater':0,'message_counts':{}}
        with self.connect(readonly=True) as db:
            # A disposable SQLite lookup bounds Python memory even with many
            # legacy conversation IDs. TEMP remains writable on a read-only
            # source connection and cannot change the authoritative archive.
            db.execute('PRAGMA temp_store=FILE')
            db.execute('BEGIN')
            from functools import lru_cache
            @lru_cache(maxsize=128)
            def legacy_owner(identifier):
                found=db.execute('SELECT owner FROM temp.history_owners WHERE identifier=? LIMIT 2',
                                 (identifier,)).fetchall()
                return found[0][0] if len(found)==1 else None
            # Generator bridges the existing validator to the index importer
            # without constructing a Message for every historical text.
            def records():
                generation,state=self._validated_state(db)
                plan.update(generation=generation,state=state)
                if ingest is not None:
                    db.execute('CREATE TEMP TABLE history_owners(identifier TEXT,owner TEXT,PRIMARY KEY(identifier,owner)) WITHOUT ROWID')
                # Validate each conversation first and build its owner lookup in
                # the same snapshot. Ambiguous identifiers remain unattributed.
                for kind,token,position,row,owner in self._validated_rows(db,state,('conversations','messages')):
                    key=kind,owner
                    if kind=='messages':
                        plan['recent'].append((token,position,row))
                        uid=row.get('user_id') or row.get('metadata',{}).get('user_id')
                        count_key=(uid if isinstance(uid,str) else None,row['role'])
                        plan['message_counts'][count_key]=plan['message_counts'].get(count_key,0)+1
                        for intent_key in ('delivery_update','experience_update'):
                            intent=row.get('metadata',{}).get(intent_key)
                            if isinstance(intent,dict) and type(intent.get('sequence')) is int:
                                plan['highwater']=max(plan['highwater'],intent['sequence'])
                        source_owner=legacy_owner(row['conversation_id']) if ingest is not None and not uid else None
                    else:
                        if ingest is not None:
                            db.execute('INSERT OR IGNORE INTO temp.history_owners VALUES(?,?)',(row['id'],owner))
                        source_owner=owner
                    plan['last'][key]=position;plan['counts'][key]=plan['counts'].get(key,0)+1
                    yield kind,token,position,row,source_owner
                plan['complete']=True
            iterator=records()
            if ingest is None:
                for _ in iterator:pass
            else:
                try:ingest(iterator)
                except (sqlite3.Error,OSError):
                    # Index failures must not discard readable authoritative
                    # history. Finish validation; a failed source cursor cannot
                    # reach the complete marker and still fails closed.
                    for _ in iterator:pass
                    plan['index_deferred']=True
            if not plan.get('complete'):raise ValueError('Incomplete history validation')
        self.generation,self.loaded=plan['generation'],True
        self.read_error=None
        return plan

    def commit(self,changes,default):
        if self.read_error is not None:
            raise StateRecoveryRequired('History page could not be read; reload a repaired archive before saving') from self.read_error
        if not any(changes.dirty.values()) and not any(changes.deleted.values()) and not changes.sections:
            changes.committed();return
        # Serialize only modified records before opening the write transaction.
        encoded={kind:[(key,row._archive_position,
                       json.dumps({field:getattr(row,field) for field in self.FIELDS[kind]},
                                  ensure_ascii=False,default=default),row._archive_owner)
                       for key,row in rows.items()] for kind,rows in changes.dirty.items()}
        sections={name:json.dumps(list(changes.memory.conversations) if name=='conversation_users'
                                 else getattr(changes.memory,name),ensure_ascii=False,default=default)
                  for name in changes.sections}
        # Reject invalid edits before they can poison an otherwise valid archive.
        for kind,rows in encoded.items():
            for key,position,raw,owner in rows:
                row=json.loads(raw)
                if kind=='conversations':
                    if not isinstance(owner,str) or owner not in changes.memory.conversations:
                        raise ValueError('Invalid history owner')
                validate_history_record(kind,row)
        for name,raw in sections.items():
            value=json.loads(raw)
            if name=='conversation_users':
                if not isinstance(value,list) or any(not isinstance(uid,str) for uid in value):
                    raise ValueError('Invalid history users')
            else:validate_history_archive({name:value})
        with self.connect() as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                generation=db.execute('SELECT generation FROM history_meta WHERE singleton=1').fetchone()[0]
                if generation!=self.generation:
                    raise StateRecoveryRequired('History changed in another writer; reload before saving')
                for kind,rows in encoded.items():
                    table='history_'+kind
                    db.executemany(f'DELETE FROM {table} WHERE token=?',((key,) for key in changes.deleted[kind]))
                    for key,position,data,owner in rows:
                        if kind=='messages':
                            db.execute('INSERT INTO history_messages VALUES(?,?,?) ON CONFLICT(token) DO UPDATE SET position=excluded.position,data=excluded.data',
                                       (key,position,data))
                        else:
                            db.execute('INSERT INTO history_conversations VALUES(?,?,?,?) ON CONFLICT(token) DO UPDATE SET owner=excluded.owner,position=excluded.position,data=excluded.data',
                                       (key,owner,position,data))
                db.executemany('INSERT INTO history_state VALUES(?,?) ON CONFLICT(name) DO UPDATE SET data=excluded.data',sections.items())
                db.execute('UPDATE history_meta SET generation=generation+1 WHERE singleton=1')
                db.commit()
            except BaseException:
                db.rollback();raise
        self.generation=generation+1
        changes.committed()
