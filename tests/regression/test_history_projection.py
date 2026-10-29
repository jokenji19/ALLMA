"""Derived search must follow the current authoritative message, including failures."""
import hashlib
import json
import sqlite3
from unittest.mock import patch
import pytest

from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.agency_system.operational_actions import retrieve_user_memory


def memory_at(path):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    assert memory._load_error is None
    return memory


def reports(memory,user='u',query='Ricordi ZEFIRO742?'):
    return retrieve_user_memory(memory,user,query)


@pytest.mark.parametrize('operation',['edit','revoke','invalidate','delete','owner'])
def test_old_projection_disappears_immediately_and_after_reopen(tmp_path,operation):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    assert reports(memory)
    if operation=='edit':memory.messages[0].content='Il codice archivio è ORIONE931.'
    elif operation=='revoke':memory.messages[0].metadata['revoked']=True
    elif operation=='invalidate':memory.messages[0].metadata['is_valid']=False
    elif operation=='delete':del memory.messages[0]
    else:memory.messages[0].user_id='v'
    memory.save_memory()
    for current in (memory,memory_at(tmp_path)):
        assert not any('ZEFIRO742' in row['content'] for row in reports(current))
        if operation=='edit':assert reports(current,query='Ricordi ORIONE931?')
        if operation=='owner':assert reports(current,'v')
        assert current.vector_engine.count()<=1


def test_corrected_source_keeps_one_stable_index_identity(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    first=memory.vector_engine.search('u','ZEFIRO742')[0]['id']
    memory.messages[0].content='Il codice archivio è ORIONE931.'
    memory.save_memory()
    assert memory.vector_engine.search('u','ORIONE931')[0]['id']==first
    assert memory.vector_engine.count()==1


def test_index_failure_cannot_undo_a_durable_message_or_serve_old_evidence(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    with patch.object(memory.vector_engine,'_conn',side_effect=OSError('Synthetic index failure')):
        memory.messages[0].content='Il codice archivio è ORIONE931.'
        memory.save_memory()
        memory.store_message('c','Secondo appunto: STELLA211.',{},'user','u')
        with pytest.raises((OSError,RuntimeError)):
            reports(memory)
    assert len(memory.messages)==2
    assert not reports(memory)
    assert reports(memory,query='Ricordi ORIONE931?')
    restored=memory_at(tmp_path)
    assert len(restored.messages)==2 and not reports(restored)


def test_removed_source_stays_removed_when_the_index_fails_and_after_restart(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    with patch.object(memory.vector_engine,'_conn',side_effect=OSError('Synthetic index failure')):
        memory.messages.clear();memory.save_memory()
    assert not reports(memory) and not reports(memory_at(tmp_path))


def test_legacy_projection_cleanup_preserves_unrelated_vector_sources(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    row=memory.messages[0]
    old_key=hashlib.sha256(json.dumps([row.conversation_id,row.role,row.timestamp.isoformat(),row.content],ensure_ascii=False).encode()).hexdigest()
    memory.vector_engine.add('u',row.content,{'role':'user','conversation_id':'c'},row.timestamp,old_key)
    memory.vector_engine.add('u','External knowledge',{},source_key='external-domain-source')
    restored=memory_at(tmp_path)
    assert restored.vector_engine.count()==2
    assert len(reports(restored))==1
    assert restored.vector_engine.search('u','External knowledge')


def test_stale_memory_instance_cannot_supply_sources_from_a_newer_archive(tmp_path):
    first=memory_at(tmp_path)
    first.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    second=memory_at(tmp_path)
    first.messages.clear();first.save_memory()
    with pytest.raises(RuntimeError):reports(second)
    assert second.load_memory() and not reports(second)


def test_tampered_derived_content_is_not_authoritative_user_evidence(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    with memory.vector_engine._conn() as db:
        db.execute("UPDATE memories SET content='Falso appunto ZEFIRO742.'")
    assert not reports(memory)


def test_reconciliation_failure_rolls_back_updates_and_keeps_the_search_cache(tmp_path):
    from allma_model.core.history_projection import source_key
    from datetime import datetime
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    assert reports(memory) and not memory.vector_engine._index_dirty
    def broken():
        yield {'user_id':'u','content':'Transient','metadata':{},'timestamp':datetime.now(),'source_key':source_key('temporary')}
        raise OSError('Synthetic interrupted reconciliation')
    with pytest.raises(OSError):memory.vector_engine.sync_history(broken())
    assert memory.vector_engine.count()==1 and not memory.vector_engine._index_dirty
    assert reports(memory)


def test_append_and_old_metadata_edit_do_not_scan_the_whole_history(tmp_path):
    memory=memory_at(tmp_path)
    for i in range(20):memory.store_message('c',f'Ricordo {i}',{},'user','u')
    with patch.object(type(memory.messages),'__iter__',side_effect=AssertionError('Unexpected full history scan')):
        memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
        memory.messages[0].metadata['revoked']=True;memory.save_memory()
        assert not memory._projection_stale
    assert len(memory.messages)==21


def test_history_serializable_metadata_stays_searchable_without_restart(tmp_path):
    from datetime import datetime
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{'observed_at':datetime(2025,1,1)},'user','u')
    assert not memory._projection_stale
    assert reports(memory)[0]['metadata']['observed_at']=='2025-01-01T00:00:00'


def test_foreign_source_cannot_be_admitted_with_forged_index_metadata(tmp_path):
    memory=memory_at(tmp_path)
    memory.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','v')
    row=memory.messages[0]
    from allma_model.core.history_projection import source_key
    memory.vector_engine.add('u',row.content,{'role':'user','user_id':'u'},row.timestamp,source_key(row._archive_key))
    assert not reports(memory,'u') and reports(memory,'v')


def test_delayed_old_projection_cannot_overwrite_a_newer_writer(tmp_path):
    first=memory_at(tmp_path)
    first.store_message('c','Il codice archivio è ZEFIRO742.',{},'user','u')
    original=first.vector_engine.sync_history
    current=[]
    def delayed(*args,**options):
        second=memory_at(tmp_path)
        second.messages[0].content='Il codice archivio è NUOVO999.';second.save_memory()
        current.append(second)
        return original(*args,**options)
    with patch.object(first.vector_engine,'sync_history',side_effect=delayed):
        first.messages[0].content='Il codice archivio è ORIONE931.';first.save_memory()
    assert first._projection_stale
    assert reports(current[0],query='Ricordi NUOVO999?')
    assert not current[0].vector_engine.search('u','ORIONE931')

