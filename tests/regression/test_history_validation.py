"""Full startup validation stays linear even for unattributed legacy messages."""
import json
import sqlite3
from unittest.mock import patch

from allma_model.memory_system.conversational_memory import ConversationalMemory


def legacy_archive(path,conversations=180,rounds=2):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    assert memory._load_error is None
    with sqlite3.connect(path/'conversation_history.db') as db:
        db.execute("UPDATE history_state SET data=? WHERE name='conversation_users'",(json.dumps(['u']),))
        db.executemany('INSERT INTO history_conversations VALUES(?,?,?,?)',
            ((f'c{i}','u',i,json.dumps({'id':f'c{i}','user_id':'u','timestamp':'2025-01-01T00:00:00',
              'content':'','metadata':{}})) for i in range(conversations)))
        db.executemany('INSERT INTO history_messages VALUES(?,?,?)',
            ((f'm{r}_{i}',r*conversations+i,json.dumps({'conversation_id':f'c{i}','role':'user',
              'content':f'Appunto sintetico {r}_{i}.','timestamp':'2025-01-01T00:00:00','metadata':{}}))
              for r in range(rounds) for i in range(conversations)))
        db.execute('UPDATE history_meta SET generation=generation+1')
    return memory


def test_legacy_startup_decodes_each_conversation_and_message_once(tmp_path):
    legacy_archive(tmp_path)
    with patch('allma_model.memory_system.history_store.json.loads',wraps=json.loads) as parse:
        restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is None
    assert len(restored.messages)==360 and restored.vector_engine.count('u')==360
    # No unbounded owner dictionary and no rescan per legacy identifier, even
    # when identifiers exceed the recent-page cache and recur in a later round.
    assert parse.call_count<=360+180+20
    assert len(restored._changes.live['messages'])<=128


def test_ambiguous_legacy_owner_stays_unattributed_and_explicit_owner_wins(tmp_path):
    legacy_archive(tmp_path,conversations=2,rounds=1)
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        db.execute("UPDATE history_state SET data=? WHERE name='conversation_users'",(json.dumps(['u','v']),))
        data={'id':'c0','user_id':'v','timestamp':'2025-01-01T00:00:00','content':'','metadata':{}}
        db.execute('INSERT INTO history_conversations VALUES(?,?,?,?)',('ambiguous','v',0,json.dumps(data)))
        message={'conversation_id':'c0','user_id':'explicit','role':'user','content':'Esplicito',
                 'timestamp':'2025-01-01T00:00:00','metadata':{}}
        db.execute('INSERT INTO history_messages VALUES(?,?,?)',('explicit',2,json.dumps(message)))
    restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is None and restored.vector_engine.count()==2
    assert restored.vector_engine.count('u')==1 and restored.vector_engine.count('v')==0
    assert restored.vector_engine.count('explicit')==1


def test_invalid_last_conversation_never_publishes_or_indexes_partial_archive(tmp_path):
    memory=legacy_archive(tmp_path,conversations=4,rounds=1)
    assert memory.load_memory()
    before=memory.messages
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        db.execute("UPDATE history_conversations SET data='{}' WHERE token='c3'")
        raw={'conversation_id':'c0','user_id':'u','role':'user','content':'Must not be indexed',
             'timestamp':'2025-01-01T00:00:00','metadata':{}}
        db.execute('INSERT INTO history_messages VALUES(?,?,?)',('new',4,json.dumps(raw)))
    assert not memory.load_memory() and memory.messages is before
    assert memory.vector_engine.count()==4


def test_same_owner_duplicate_identifier_is_not_ambiguous(tmp_path):
    legacy_archive(tmp_path,conversations=2,rounds=1)
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        raw=db.execute("SELECT data FROM history_conversations WHERE token='c0'").fetchone()[0]
        db.execute('INSERT INTO history_conversations VALUES(?,?,?,?)',('duplicate','u',2,raw))
    restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is None and restored.vector_engine.count('u')==2


def test_owner_lookup_and_messages_share_the_same_read_snapshot(tmp_path):
    memory=legacy_archive(tmp_path,conversations=2,rounds=1)
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        db.execute('PRAGMA journal_mode=WAL')
    store=memory._history_store
    reader=store._validated_rows
    changed=False
    def concurrent(db,state,order=None):
        nonlocal changed
        for item in reader(db,state,order):
            if item[0]=='messages' and not changed:
                changed=True
                with sqlite3.connect(tmp_path/'conversation_history.db') as writer:
                    writer.execute("UPDATE history_state SET data='[\"u\",\"v\"]' WHERE name='conversation_users'")
                    row={'id':'c0','user_id':'v','timestamp':'2025-01-01T00:00:00','content':'','metadata':{}}
                    writer.execute('INSERT INTO history_conversations VALUES(?,?,?,?)',('other','v',0,json.dumps(row)))
                    writer.execute('UPDATE history_meta SET generation=generation+1')
            yield item
    projected=[]
    with patch.object(store,'_validated_rows',side_effect=concurrent):
        plan=store.load_pages(lambda records:projected.extend((row[3]['conversation_id'],row[4])
                                    for row in records if row[0]=='messages'))
    assert plan['state']['conversation_users']==['u'] and projected==[('c0','u'),('c1','u')]
    current=[]
    store.load_pages(lambda records:current.extend((row[3]['conversation_id'],row[4])
                                     for row in records if row[0]=='messages'))
    assert current==[('c0',None),('c1','u')]
