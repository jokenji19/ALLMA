"""Synthetic incremental history/index challenges; no personal archives or GGUF."""
from datetime import datetime
import json
import sqlite3
from unittest.mock import patch

from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
from allma_model.core.vector_memory_engine import VectorMemoryEngine
from memory_recovery_battery import run_challenges,require

CASES=[]


def case(group,name,criterion):
    def register(function):
        CASES.append((group,name,criterion,function))
        return function
    return register


def history(path):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(memory._load_error is None,'History initialization failed: '+str(memory._load_error))
    memory.vector_engine=None
    return memory


def add(memory,text='Synthetic original'):
    memory.store_message('c',text,{'items':[1]},'user','u')


@case('history','migration','All legacy rows migrate while original JSON bytes remain unchanged')
def migration(path):
    legacy={'messages':[{'conversation_id':'c','role':'user','content':'Synthetic original',
        'metadata':{},'timestamp':'2025-01-01T00:00:00','user_id':'u'}],
        'conversations':{'u':[]},'user_data':{'u':{'name':'Synthetic'}},'trauma_log':[]}
    raw=json.dumps(legacy);(path/'allma_memory.json').write_text(raw)
    memory=history(path);add(memory,'Second')
    restored=history(path)
    require(len(restored.messages)==2 and restored.user_data==legacy['user_data'],'Migrated state lost')
    require((path/'allma_memory.json').read_text()==raw,'Original JSON modified')


@case('history','bounded_append','One append does not serialize 1000 previous turns; a no-op save does not write')
def bounded(path):
    memory=history(path)
    memory.messages.extend(Message('c','user',f'Synthetic {i}',datetime.now(),{},'u') for i in range(1000))
    memory.save_memory()
    with patch.object(memory,'_json_serial',wraps=memory._json_serial) as serial:
        add(memory)
    require(serial.call_count==1,'Historical rows reserialized')
    with patch.object(memory._history_store,'connect',side_effect=AssertionError('Unexpected write')):
        memory.save_memory()
    require(len(history(path).messages)==1001,'Append lost rows')


@case('history','nested_edit','Nested metadata, user state and conversation context survive reload')
def nested(path):
    memory=history(path);add(memory)
    conversation=memory.create_conversation('u')
    memory.update_context(conversation,{'context':{'items':[1]}})
    memory.conversations['u'][0].metadata['context']['items'].append(2)
    memory.messages[0].metadata['items'].append(2)
    memory.messages[0].metadata['revoked']=True
    memory.user_data['u']={'name':'Synthetic'}
    memory.trauma_log.append({'description':'Synthetic event'})
    memory.save_memory();restored=history(path)
    require(restored.messages[0].metadata=={'items':[1,2],'revoked':True},'Nested edit lost')
    require(restored.conversations['u'][0].metadata['context']['items']==[1,2],'Context lost')
    require(restored.user_data==memory.user_data and restored.trauma_log==memory.trauma_log,'State lost')


@case('history','failed_transaction','Failure after the first row write rolls back all rows and can be retried')
def failed(path):
    memory=history(path);add(memory)
    memory.messages[0].content='Changed'
    memory.messages.append(Message('c','user','Second',datetime.now(),{},'u'))
    original=sqlite3.connect
    class Faulty(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            if sql.startswith('UPDATE history_meta SET'):raise OSError('Synthetic interrupted transaction')
            return super().execute(sql,*args,**kwargs)
    with patch('allma_model.memory_system.history_store.sqlite3.connect',
               side_effect=lambda *a,**k:original(*a,**dict(k,factory=Faulty))):
        try:memory.save_memory()
        except OSError:pass
        else:raise AssertionError('Fault did not reach the transaction')
    restored=history(path)
    require([m.content for m in restored.messages]==['Synthetic original'],'Partial transaction leaked')
    memory.save_memory()
    require([m.content for m in history(path).messages]==['Changed','Second'],'Retry lost changes')


@case('history','stale_writer','A stale history instance cannot overwrite newer turns')
def stale(path):
    first=history(path);second=history(path);add(first)
    try:add(second,'Stale')
    except RuntimeError:pass
    else:raise AssertionError('Stale writer accepted')
    require(len(history(path).messages)==1,'Stale write changed durable history')
    require(second.load_memory(),'Reload failed');add(second,'Current')
    require(len(history(path).messages)==2,'Reload did not recover writer')


@case('history','backup','Backup restores the new archive and corruption cannot resurrect legacy history')
def backup(path):
    from allma_model.utils.state_backup import StateBackups,verify_archive
    (path/'allma_memory.json').write_text('{}')
    memory=history(path);add(memory)
    snapshots=StateBackups(path);snapshot=snapshots.create()
    target=path/'restored';target.mkdir()
    manifest=verify_archive(snapshots.directory/snapshot['id'],target)
    require('conversation_history.db' in manifest['files'],'History DB absent from backup')
    require(history(target).messages[0].content=='Synthetic original','Restored row missing')
    (path/'conversation_history.db').write_bytes(b'Synthetic damage')
    failed=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(failed._load_error is not None,'Corrupt database accepted')
    try:failed.save_memory()
    except RuntimeError:pass
    else:raise AssertionError('Corrupt database overwritten')


@case('index','incremental_append','Ingestion after warmup only encodes new rows and preserves owner isolation')
def index_append(path):
    engine=VectorMemoryEngine(str(path/'vectors.db'))
    engine.add('u','Mare e stelle.');engine.search('u','mare')
    with patch.object(engine,'_rebuild_index',side_effect=AssertionError('Unexpected full rebuild')):
        for i in range(10):
            engine.add('u',f'Mare e pianeta {i}.')
            require(bool(engine.search('u','mare')),'New row not searchable')
    require(not engine.search('other','mare'),'Owner isolation failed')


@case('index','external_edits','External insert/update/delete invalidate the right search snapshot')
def index_edits(path):
    engine=VectorMemoryEngine(str(path/'vectors.db'));other=VectorMemoryEngine(str(path/'vectors.db'))
    identifier=engine.add('u','Ombrello nel mobile.');engine.search('u','ombrello')
    other.add('u','Forbici sul tavolo.')
    require(bool(engine.search('u','forbici')),'External insertion missed')
    with sqlite3.connect(engine.db_path) as db:
        db.execute('UPDATE memories SET content=? WHERE id=?',('Termometro nel mobile.',identifier))
    require(not engine.search('u','ombrello'),'Old content survived update')
    require(bool(engine.search('u','misurare la febbre')),'Updated concept missed')
    with sqlite3.connect(engine.db_path) as db:db.execute('DELETE FROM memories WHERE id=?',(identifier,))
    require(not engine.search('u','termometro'),'Deleted source survived')


@case('index','revocation','Updated revocation metadata removes a previously eligible source')
def index_revoked(path):
    engine=VectorMemoryEngine(str(path/'vectors.db'))
    identifier=engine.add('u','Ombrello nel mobile.',metadata={'role':'user'})
    require(bool(engine.search('u','ombrello',allowed_roles=('user',))),'Source unavailable')
    with sqlite3.connect(engine.db_path) as db:
        db.execute('UPDATE memories SET metadata=? WHERE id=?',(json.dumps({'role':'user','revoked':True}),identifier))
    require(not engine.search('u','ombrello',allowed_roles=('user',)),'Revoked source returned')


@case('index','cache_release','Releasing derived RAM retains all durable sources and their search scores')
def index_release(path):
    engine=VectorMemoryEngine(str(path/'vectors.db'))
    for text in ['Mare e stelle.','Mare mare.','Libro e stelle.']:engine.add('u',text)
    before=engine.search('u','mare stelle',use_expansion=False)
    engine.release_cache()
    after=engine.search('u','mare stelle',use_expansion=False)
    require([(r['id'],r['score']) for r in before]==[(r['id'],r['score']) for r in after],'Rebuild changed retrieval')


@case('startup','single_decode','Startup validates each row once while preserving every message')
def startup_decode(path):
    memory=history(path)
    memory.messages.extend(Message('c','user',f'Synthetic {i}',datetime.now(),{},'u') for i in range(120))
    memory.save_memory();memory._index_messages()
    with patch('allma_model.memory_system.history_store.json.loads',wraps=json.loads) as decode:
        restored=history(path)
    require(len(restored.messages)==120 and decode.call_count<=130,'History read twice')


@case('startup','bounded_connections','Reopening old turns does not open one index connection per row')
def startup_connections(path):
    memory=history(path)
    memory.messages.extend(Message('c','user',f'Synthetic {i}',datetime.now(),{},'u') for i in range(120))
    memory.save_memory()
    original=VectorMemoryEngine._conn;calls=[]
    def counted(engine):
        calls.append(True);return original(engine)
    with patch.object(VectorMemoryEngine,'_conn',counted):
        restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored._load_error is None and restored.vector_engine.count()==120,'Startup projection missing')
    require(len(calls)<=5,'Per-record connections remain')


@case('startup','deferred_search','Startup leaves derived index deferred; first search retrieves old sources')
def startup_deferred(path):
    memory=history(path);add(memory,'Ombrello nel mobile blu.')
    with patch.object(VectorMemoryEngine,'_rebuild_index',side_effect=AssertionError('Premature rebuild')):
        restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored.vector_engine is not None,'Deferred index unavailable')
    require(restored.vector_engine.search('u','ripararmi dalla pioggia')[0]['content']=='Ombrello nel mobile blu.',
            'Deferred search lost a source')


@case('startup','invalid_tail','An invalid final record cannot publish a partial live history')
def startup_invalid(path):
    memory=history(path);add(memory);add(memory,'Second')
    before=memory.messages
    with sqlite3.connect(path/'conversation_history.db') as db:
        db.execute("UPDATE history_messages SET data='{}' WHERE position=(SELECT MAX(position) FROM history_messages)")
    require(not memory.load_memory() and memory.messages is before and len(memory.messages)==2,'Partial history published')
    try:memory.save_memory()
    except RuntimeError:pass
    else:raise AssertionError('Invalid archive overwritten')


@case('startup','projection_rollback','A broken index batch rolls back every new row')
def startup_rollback(path):
    engine=VectorMemoryEngine(str(path/'vectors.db'))
    engine.add('u','Originale',source_key='original');engine.search('u','originale')
    def broken():
        yield {'user_id':'u','content':'Synthetic new','timestamp':datetime.now(),'metadata':{},'source_key':'new'}
        raise OSError('Synthetic interrupted projection')
    try:engine.add_many(broken())
    except OSError:pass
    else:raise AssertionError('Projection fault not reached')
    require(engine.count()==1 and not engine._index_dirty,'Partial index projection published')


@case('startup','projection_revocation','Startup refreshes changed revocation without duplicating a source')
def startup_revocation(path):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(memory._load_error is None,'History startup failed')
    add(memory,'Ombrello nel mobile blu.')
    require(bool(memory.vector_engine.search('u','ombrello')),'Source unavailable')
    memory.messages[0].metadata['revoked']=True;memory.save_memory()
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored.vector_engine.count()==1,'Startup duplicated a source')
    require(not restored.vector_engine.search('u','ombrello',allowed_roles=('user',)),'Old revocation ignored')


def paged_seed(path,count=600):
    memory=history(path)
    memory.messages.extend(Message('c','user',f'Synthetic note {i}',datetime.now(),{},'u') for i in range(count))
    memory.save_memory()
    return memory


@case('paging','bounded_cache','A full archive scan retains at most the bounded cache, without losing rows')
def paging_cache(path):
    import gc
    paged_seed(path)
    memory=history(path)
    require(len(memory.messages)==600,'Archive truncated')
    require(sum(1 for _ in memory.messages)==600,'Full scan missed rows')
    gc.collect()
    require(len(memory._changes.live['messages'])<=256,'Full archive retained in RAM')


@case('paging','page_boundaries','Random, reversed and recent access cross page boundaries correctly')
def paging_boundaries(path):
    paged_seed(path)
    memory=history(path)
    for index in (0,63,64,127,128,255,599):
        require(memory.messages[index].content==f'Synthetic note {index}','Wrong page position')
    require([m.content for m in memory.messages[-2:]]==['Synthetic note 598','Synthetic note 599'],'Tail misplaced')
    require(next(reversed(memory.messages)).content=='Synthetic note 599','Reverse scan missed last row')


@case('paging','old_held_edit','Evicting a held old row never discards nested corrections')
def paging_edit(path):
    paged_seed(path)
    memory=history(path);old=memory.messages[0]
    for _ in memory.messages:pass
    old.metadata['review']={'items':[]};old.metadata['review']['items'].append('kept')
    memory.save_memory()
    require(history(path).messages[0].metadata['review']['items']==['kept'],'Old correction lost')
    require(memory.messages[0] is old,'One archive row split into competing live objects')


@case('paging','old_recall_and_revocation','Literal recall finds an old page and respects a later revocation and owner')
def paging_recall(path):
    from allma_model.core.autobiographical_identity import user_events
    from allma_model.utils.literal_recall import literal_code_reply
    memory=paged_seed(path);memory.messages[0].content='Il codice di prova è PAGE_991.';memory.save_memory()
    memory=history(path);query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice.'
    require(literal_code_reply(query,user_events(memory,'u'))[0]=='PAGE_991','Old source missed')
    require(literal_code_reply(query,user_events(memory,'other')) is None,'Wrong owner received old source')
    memory.store_message('c','Revoco il codice di prova.',role='user',user_id='u')
    require(literal_code_reply(query,user_events(memory,'u'))[1]=='literal_memory_revoked','Late revocation ignored')


@case('paging','failed_append','An unsaved append is removed without materializing or leaking into a later save')
def paging_failure(path):
    memory=paged_seed(path)
    with patch.object(memory._history_store,'connect',side_effect=OSError('Synthetic full disk')):
        try:add(memory,'Must not persist')
        except OSError:pass
        else:raise AssertionError('Write fault not reached')
    require(memory.messages.materialized is None and len(memory.messages)==600,'Failure materialized the full archive')
    add(memory,'Valid new row')
    require(len(history(path).messages)==601 and history(path).messages[-1].content=='Valid new row','Failed row leaked')


@case('paging','structure_and_counts','An explicit reorder persists and returns to bounded paging with correct counters')
def paging_structure(path):
    import gc
    memory=paged_seed(path,160)
    memory.messages.reverse();memory.messages[0].user_id='other';memory.save_memory()
    require(memory.messages.materialized is None,'Explicit edit left a full list in RAM')
    require(history(path).messages[0].content=='Synthetic note 159','Reorder lost')
    require(memory.message_count('u','user')==159 and memory.message_count('other','user')==1,'Counts drifted')
    gc.collect();require(len(memory._changes.live['messages'])<=256,'Reordered rows retained forever')


@case('paging','stale_reader','A stale instance cannot mix an uncached page with a newer archive generation')
def paging_stale(path):
    paged_seed(path)
    first=history(path);second=history(path);add(second,'New generation')
    try:first.messages[0]
    except RuntimeError:pass
    else:raise AssertionError('Reader mixed archive generations')
    require(first.load_memory() and len(first.messages)==601,'Reader could not reload')


@case('paging','core_integration','Core startup/recovery remain bounded and literal old recall needs no model')
def paging_core(path):
    import gc
    from allma_model.core.allma_core import ALLMACore
    memory=paged_seed(path);memory.messages[0].content='Il codice di prova è PAGE_991.';memory.save_memory()
    del memory
    core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
    try:
        core._ensure_mobile_llm=lambda:None
        gc.collect()
        require(len(core.conversational_memory._changes.live['messages'])<=256,'Core recovery retained full history')
        response=core.process_message('u',core.start_conversation('u'),
            'Quale codice di prova ti avevo indicato? Rispondi solo con il codice.')
        require(response.is_valid and response.content=='PAGE_991','Pipeline lost an old page')
        gc.collect()
        require(len(core.conversational_memory._changes.live['messages'])<=256,'Core dialogue retained full history')
    finally:core.close()


@case('paging','damaged_later_page','A later malformed page blocks writes until a validated repaired reload')
def paging_damage(path):
    paged_seed(path,400);memory=history(path)
    with sqlite3.connect(path/'conversation_history.db') as db:
        original=db.execute('SELECT data FROM history_messages WHERE position=0').fetchone()[0]
        db.execute("UPDATE history_messages SET data='{}' WHERE position=0")
    try:memory.messages[0]
    except (ValueError,KeyError):pass
    else:raise AssertionError('Malformed uncached row exposed')
    try:add(memory,'Must not overwrite damage')
    except RuntimeError:pass
    else:raise AssertionError('Damaged source remained writable')
    with sqlite3.connect(path/'conversation_history.db') as db:
        require(db.execute('SELECT COUNT(*) FROM history_messages').fetchone()[0]==400,'Failed append persisted')
        db.execute('UPDATE history_messages SET data=? WHERE position=0',(original,))
    require(memory.load_memory(),'Repaired source could not reload')
    add(memory,'After repair');require(len(memory.messages)==401,'Repair could not resume writes')


@case('startup','legacy_owners','Legacy ownership resolves with one decode per record and a bounded Python cache')
def startup_legacy_owners(path):
    memory=history(path)
    with sqlite3.connect(path/'conversation_history.db') as db:
        db.execute("UPDATE history_state SET data='[\"u\"]' WHERE name='conversation_users'")
        db.executemany('INSERT INTO history_conversations VALUES(?,?,?,?)',
            ((str(i),'u',i,json.dumps({'id':str(i),'user_id':'u','timestamp':'2025-01-01T00:00:00',
              'content':'','metadata':{}})) for i in range(180)))
        db.executemany('INSERT INTO history_messages VALUES(?,?,?)',
            ((str(i),i,json.dumps({'conversation_id':str(i%180),'role':'user','content':f'Synthetic {i}',
              'timestamp':'2025-01-01T00:00:00','metadata':{}})) for i in range(360)))
        db.execute('UPDATE history_meta SET generation=generation+1')
    with patch('allma_model.memory_system.history_store.json.loads',wraps=json.loads) as parse:
        restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored._load_error is None and restored.vector_engine.count('u')==360,'Legacy sources lost')
    require(parse.call_count<=560,'Legacy conversations decoded repeatedly')
    require(len(restored._changes.live['messages'])<=128,'Unbounded row retention')


@case('startup','legacy_ambiguity','Duplicate owners are ambiguous; an explicit message owner remains authoritative')
def startup_legacy_ambiguity(path):
    memory=history(path)
    with sqlite3.connect(path/'conversation_history.db') as db:
        db.execute("UPDATE history_state SET data='[\"u\",\"v\"]' WHERE name='conversation_users'")
        for owner in ('u','v'):
            row={'id':'shared','user_id':owner,'timestamp':'2025-01-01T00:00:00','content':'','metadata':{}}
            db.execute('INSERT INTO history_conversations VALUES(?,?,?,?)',(owner,owner,0,json.dumps(row)))
        for i,owner in enumerate((None,'explicit')):
            row={'conversation_id':'shared','role':'user','user_id':owner,'content':f'Synthetic {i}',
                 'timestamp':'2025-01-01T00:00:00','metadata':{}}
            db.execute('INSERT INTO history_messages VALUES(?,?,?)',(str(i),i,json.dumps(row)))
        db.execute('UPDATE history_meta SET generation=generation+1')
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored._load_error is None and restored.vector_engine.count()==1,'Ambiguous owner guessed')
    require(restored.vector_engine.count('explicit')==1,'Explicit owner ignored')


@case('startup','invalid_conversation','A malformed old conversation blocks publication and leaves the source index unchanged')
def startup_invalid_conversation(path):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    conversation=memory.create_conversation('u');memory.store_message(conversation,'Original',{},'user','u')
    before=memory.messages
    with sqlite3.connect(path/'conversation_history.db') as db:
        db.execute("UPDATE history_conversations SET data='{}'")
        row={'conversation_id':conversation,'role':'user','user_id':'u','content':'Must not be projected',
             'timestamp':'2025-01-01T00:00:00','metadata':{}}
        db.execute('INSERT INTO history_messages VALUES(?,?,?)',('new',1,json.dumps(row)))
        db.execute('UPDATE history_meta SET generation=generation+1')
    require(not memory.load_memory() and memory.messages is before,'Partial archive published')
    require(memory.vector_engine.count()==1,'Partial projection leaked')


def attributed(path):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(memory._load_error is None,'History unavailable')
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    return memory


def projected(memory,user='u',query='Ricordi ZEFIRO742?'):
    from allma_model.agency_system.operational_actions import retrieve_user_memory
    return retrieve_user_memory(memory,user,query)


@case('projection','correction','An edited message retires its previous text immediately, preserves its index ID and survives restart')
def projection_correction(path):
    memory=attributed(path);identifier=memory.vector_engine.search('u','ZEFIRO742')[0]['id']
    memory.messages[0].content='Il codice archivio è ORIONE931.';memory.save_memory()
    require(not projected(memory),'Previous text retained')
    require(memory.vector_engine.search('u','ORIONE931')[0]['id']==identifier,'Source identity changed')
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(not projected(restored) and bool(projected(restored,query='Ricordi ORIONE931?')),'Restart lost correction')


@case('projection','source_revocation','Revoked and invalid sources stop supplying evidence without restarting')
def projection_revocation(path):
    memory=attributed(path);memory.messages[0].metadata['revoked']=True;memory.save_memory()
    require(not projected(memory),'Revocation requires a restart')
    memory.messages[0].metadata['revoked']=False;memory.messages[0].metadata['is_valid']=False;memory.save_memory()
    require(not projected(memory),'Invalid source remained eligible')
    require(not projected(ConversationalMemory(storage_dir=str(path),incremental=True)),'Invalid source resurrected')


@case('projection','deletion','Deleted messages disappear from the derived index and cannot return after restart')
def projection_deletion(path):
    memory=attributed(path);memory.messages.clear();memory.save_memory()
    require(not projected(memory) and memory.vector_engine.count()==0,'Deleted source remained')
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(not projected(restored) and len(restored.messages)==0,'Deleted source resurrected')


@case('projection','owner','A source moved to another owner cannot remain associated with its former owner')
def projection_owner(path):
    memory=attributed(path);memory.messages[0].user_id='v';memory.save_memory()
    require(not projected(memory,'u') and bool(projected(memory,'v')),'Owner update not propagated')
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(not projected(restored,'u') and bool(projected(restored,'v')),'Old owner resurrected')


@case('projection','deferred','An index failure preserves durable edits and insertions, then recovers without stale evidence')
def projection_deferred(path):
    memory=attributed(path)
    with patch.object(memory.vector_engine,'_conn',side_effect=OSError('Synthetic projection failure')):
        memory.messages[0].content='Il codice archivio è ORIONE931.';memory.save_memory()
        memory.store_message('c','Secondo appunto.',{},'user','u')
    require(len(memory.messages)==2 and not projected(memory),'Source save undone or stale evidence used')
    require(bool(projected(memory,query='Ricordi ORIONE931?')),'Projection did not recover')


@case('paging','suspended_writer','A suspended page reader holds no SQLite transaction that blocks a new message')
def paging_suspended_writer(path):
    memory=attributed(path);memory.store_message('c','Second',{},'user','u')
    iterator=iter(memory.messages);next(iterator)
    memory.store_message('c','Third',{},'user','u')
    try:next(iterator)
    except RuntimeError:pass
    else:raise AssertionError('Changed read was not invalidated')
    require(len(memory.messages)==3,'Concurrent insertion lost')


@case('paging','suspended_reorder','An old iterator cannot overwrite current cache positions after a reorder')
def paging_suspended_reorder(path):
    memory=history(path)
    for text in ('one','two','three'):add(memory,text)
    iterator=iter(memory.messages);next(iterator)
    memory.messages.reverse();memory.save_memory()
    try:list(iterator)
    except RuntimeError:pass
    else:raise AssertionError('Old reader continued after reorder')
    require([memory.messages[i].content for i in range(3)]==['three','two','one'],'Stale cache positions published')
    require([m.content for m in history(path).messages]==['three','two','one'],'Durable reorder lost')


@case('projection','source_gate','Tampered derived text cannot enter the response as an authoritative user report')
def projection_source_gate(path):
    memory=attributed(path)
    with memory.vector_engine._conn() as db:db.execute("UPDATE memories SET content='Falso ZEFIRO742.'")
    require(not projected(memory),'Derived text accepted without checking source')
    require(bool(projected(memory)),'Detected projection damage did not recover on the following lookup')


@case('projection','legacy_cleanup','Legacy message duplicates retire without removing unrelated domain memories')
def projection_legacy(path):
    import hashlib
    memory=attributed(path);row=memory.messages[0]
    key=hashlib.sha256(json.dumps([row.conversation_id,row.role,row.timestamp.isoformat(),row.content],ensure_ascii=False).encode()).hexdigest()
    memory.vector_engine.add('u',row.content,{'role':'user','conversation_id':'c'},row.timestamp,key)
    memory.vector_engine.add('u','External domain knowledge',{},source_key='external-domain')
    restored=ConversationalMemory(storage_dir=str(path),incremental=True)
    require(restored.vector_engine.count()==2 and len(projected(restored))==1,'Legacy migration removed unrelated sources or left duplicates')


@case('projection','writer_order','A delayed old projection cannot overwrite a newer committed writer')
def projection_writer_order(path):
    first=attributed(path);original=first.vector_engine.sync_history;latest=[]
    def delayed(*args,**options):
        second=ConversationalMemory(storage_dir=str(path),incremental=True)
        second.messages[0].content='Il codice archivio è NUOVO999.';second.save_memory();latest.append(second)
        return original(*args,**options)
    with patch.object(first.vector_engine,'sync_history',side_effect=delayed):
        first.messages[0].content='Il codice archivio è ORIONE931.';first.save_memory()
    require(first._projection_stale,'Stale writer was not deferred')
    require(bool(projected(latest[0],query='Ricordi NUOVO999?')),'Newer projection overwritten')
    require(not latest[0].vector_engine.search('u','ORIONE931'),'Delayed old content republished')


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==38,'Unexpected incremental-memory challenge plan')
    return run_challenges(output,CASES,version='memory-coherence-v6',scope=scope,
        cancel_event=cancel_event,progress_callback=progress_callback,harness_path=__file__)
