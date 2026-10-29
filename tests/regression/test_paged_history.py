"""Full archive access with a bounded object cache, including old corrections."""
from datetime import datetime,timedelta
import gc
from unittest.mock import patch
import pytest
from allma_model.memory_system.conversational_memory import ConversationalMemory,Message


def seed(path,count=2000):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    assert memory._load_error is None
    memory.messages.extend(Message('c','user',f'Ricordo {i}',datetime(2025,1,1)+timedelta(seconds=i),{},'u') for i in range(count))
    memory.save_memory()
    return memory


def test_startup_and_full_scan_keep_a_bounded_number_of_live_rows(tmp_path):
    seed(tmp_path)
    memory=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert len(memory.messages)==2000
    gc.collect()
    assert len(memory._changes.live['messages'])<=256
    assert sum(1 for _ in memory.messages)==2000
    gc.collect()
    assert len(memory._changes.live['messages'])<=256
    assert [m.content for m in memory.messages[-3:]]==['Ricordo 1997','Ricordo 1998','Ricordo 1999']


def test_recent_history_does_not_read_every_old_message(tmp_path):
    seed(tmp_path)
    memory=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    with patch.object(type(memory.messages),'__iter__',side_effect=AssertionError('Full scan for recent history')):
        assert memory.get_recent_history(2,'u')==[
            {'role':'user','content':'Ricordo 1998'},{'role':'user','content':'Ricordo 1999'}]


def test_held_old_row_can_be_corrected_after_cache_eviction(tmp_path):
    seed(tmp_path)
    memory=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    old=memory.messages[0]
    for _ in memory.messages:pass
    old.content='Corretto';old.metadata['review']={'items':[1]}
    memory.save_memory()
    assert memory.messages[0] is old
    assert ConversationalMemory(storage_dir=str(tmp_path)).messages[0].content=='Corretto'


def test_activity_counter_does_not_rescan_disk_and_tracks_edits(tmp_path):
    memory=seed(tmp_path,200)
    with patch.object(type(memory.messages),'__iter__',side_effect=AssertionError('Polling scanned all messages')):
        assert memory.message_count('u','user')==200
        memory.store_message('c','New',role='user',user_id='u')
        assert memory.message_count('u','user')==201
    memory.messages[0].user_id='other'
    memory.messages[1].role='assistant'
    del memory.messages[2]
    memory.save_memory()
    assert memory.message_count('u','user')==198
    assert memory.message_count('other','user')==1
    restored=ConversationalMemory(storage_dir=str(tmp_path))
    assert restored.message_count('u','user')==198


@pytest.mark.parametrize('operation',[
    lambda rows:rows.reverse(),lambda rows:rows.sort(key=lambda row:row.content),
    lambda rows:rows.__delitem__(slice(60,70)),lambda rows:rows.insert(65,Message('c','user','Inserted',datetime.now(),{},'u')),
    lambda rows:rows.__imul__(2),lambda rows:rows.__setitem__(slice(2,3),[]),lambda rows:rows.clear(),
])
def test_structural_edits_commit_back_to_a_bounded_paged_collection(tmp_path,operation):
    seed(tmp_path,160)
    memory=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    operation(memory.messages)
    expected=[row.content for row in memory.messages]
    memory.save_memory()
    assert memory.messages.materialized is None
    assert [row.content for row in ConversationalMemory(storage_dir=str(tmp_path)).messages]==expected
    gc.collect()
    assert len(memory._changes.live['messages'])<=256


def test_reading_an_uncached_page_after_an_external_write_requires_reload(tmp_path):
    seed(tmp_path,400)
    first=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    second=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    second.store_message('c','Changed archive',role='user',user_id='u')
    with pytest.raises(RuntimeError):first.messages[0]
    assert first.load_memory() and len(first.messages)==401


def test_old_nested_edit_is_pinned_until_successful_save(tmp_path):
    memory=seed(tmp_path,500)
    old=memory.messages[0]
    old.metadata['nested']={'items':[]};old.metadata['nested']['items'].append('kept')
    for _ in memory.messages:pass
    gc.collect()
    assert old._archive_key in memory._changes.dirty['messages']
    with patch.object(memory._history_store,'connect',side_effect=OSError('Synthetic full disk')):
        with pytest.raises(OSError):memory.save_memory()
    memory.save_memory()
    assert ConversationalMemory(storage_dir=str(tmp_path)).messages[0].metadata['nested']['items']==['kept']


def test_literal_recall_and_late_revocation_cross_all_pages(tmp_path):
    from allma_model.core.autobiographical_identity import user_events
    from allma_model.utils.literal_recall import literal_code_reply
    memory=seed(tmp_path,600)
    memory.messages[0].content='Il codice di prova è OLD_991.';memory.save_memory()
    restored=ConversationalMemory(storage_dir=str(tmp_path))
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice.'
    assert literal_code_reply(query,user_events(restored,'u'))[0]=='OLD_991'
    assert literal_code_reply(query,user_events(restored,'other')) is None
    restored.store_message('c','Revoco il codice di prova.',role='user',user_id='u')
    assert literal_code_reply(query,user_events(restored,'u'))[1]=='literal_memory_revoked'
    assert len(restored.messages)==601


def test_invalid_uncached_page_blocks_writes_until_explicit_repair(tmp_path):
    import sqlite3
    seed(tmp_path,400)
    memory=ConversationalMemory(storage_dir=str(tmp_path))
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        original=db.execute('SELECT data FROM history_messages WHERE position=0').fetchone()[0]
        db.execute("UPDATE history_messages SET data='{}' WHERE position=0")
    with pytest.raises((ValueError,KeyError)):memory.messages[0]
    with pytest.raises(RuntimeError):memory.store_message('c','Must not overwrite damage',role='user',user_id='u')
    with sqlite3.connect(tmp_path/'conversation_history.db') as db:
        db.execute('UPDATE history_messages SET data=? WHERE position=0',(original,))
    assert memory.load_memory()
    memory.store_message('c','After verified repair',role='user',user_id='u')
    assert len(memory.messages)==401
