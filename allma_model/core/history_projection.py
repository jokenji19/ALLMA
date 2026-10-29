"""Rebuildable message search projection, separate from authoritative history."""
import hashlib
import json

PREFIX='history-message-v1:'


def source_key(token):
    if not isinstance(token,str) or not token:raise ValueError('Invalid history source token')
    return PREFIX+token


def source_token(key):
    return key[len(PREFIX):] if isinstance(key,str) and key.startswith(PREFIX) else None


def _retire_legacy(db):
    """Recognize only the exact message projection format used before stable IDs.

    Other source keys and anonymous/domain memories remain untouched. A batch
    is fetched before deleting, so writes never disturb an active table cursor.
    """
    after=0;changed=0
    while True:
        rows=db.execute('SELECT id,content,timestamp,metadata,source_key FROM memories '
                        "WHERE id>? AND length(source_key)=64 AND source_key NOT GLOB '*[^0-9a-f]*' "
                        'ORDER BY id LIMIT 128',(after,)).fetchall()
        if not rows:return changed
        discard=[]
        for identifier,content,timestamp,raw,key in rows:
            try:metadata=json.loads(raw)
            except (TypeError,ValueError):continue
            if (not isinstance(metadata,dict) or metadata.get('role') not in ('user','assistant','system')
                    or not isinstance(metadata.get('conversation_id'),str)):
                continue
            expected=hashlib.sha256(json.dumps([metadata['conversation_id'],metadata['role'],timestamp,content],
                                               ensure_ascii=False).encode()).hexdigest()
            if key==expected:discard.append((identifier,))
        db.executemany('DELETE FROM memories WHERE id=?',discard)
        changed+=len(discard);after=rows[-1][0]


def reconcile(engine,records,touched=None,*,default=None,guard=None):
    """Atomically replace only this projection; rollback includes stale removals.

    A full run consumes all validated sources and retires absent/legacy rows.
    A delta affects only touched stable IDs, including former owners. The source
    archive is already durable; callers must defer this derived work on failure.
    """
    with engine._lock:
        with engine._conn() as db:
            db.execute('PRAGMA temp_store=FILE')
            db.execute('BEGIN IMMEDIATE')
            # Check only after reserving the derived writer. A delayed older
            # commit must never overwrite a newer writer's projection.
            if guard is not None:guard()
            db.execute('CREATE TEMP TABLE history_seen(user_id TEXT,source_key TEXT,PRIMARY KEY(user_id,source_key)) WITHOUT ROWID')
            changed=_retire_legacy(db) if touched is None else 0
            if touched is not None:
                db.execute('CREATE TEMP TABLE history_touched(source_key TEXT PRIMARY KEY) WITHOUT ROWID')
                db.executemany('INSERT OR IGNORE INTO history_touched VALUES(?)',((source_key(token),) for token in touched))
            def values():
                for record in records:
                    key=record['source_key']
                    if source_token(key) is None:raise ValueError('Unscoped history projection')
                    db.execute('INSERT OR IGNORE INTO history_seen VALUES(?,?)',(record['user_id'],key))
                    yield (record['user_id'],record['content'],b'',record['timestamp'].isoformat(),
                           json.dumps(record['metadata'],default=default),key)
            cursor=db.executemany('''
                INSERT INTO memories(user_id,content,vector_blob,timestamp,metadata,source_key)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,source_key) DO UPDATE SET
                    content=excluded.content,timestamp=excluded.timestamp,metadata=excluded.metadata,vector_blob=excluded.vector_blob
                WHERE memories.content!=excluded.content OR memories.timestamp!=excluded.timestamp
                    OR memories.metadata!=excluded.metadata
            ''',values())
            changed+=cursor.rowcount
            scope=("source_key GLOB '"+PREFIX+"*'" if touched is None else
                   'source_key IN (SELECT source_key FROM history_touched)')
            changed+=db.execute('DELETE FROM memories WHERE '+scope+' AND NOT EXISTS '
                '(SELECT 1 FROM history_seen s WHERE s.source_key=memories.source_key AND s.user_id=memories.user_id)').rowcount
        if changed:engine._index_dirty=True
    return changed
