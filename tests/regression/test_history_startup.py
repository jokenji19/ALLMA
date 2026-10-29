"""Startup must validate history once and avoid per-message DB connections."""
from datetime import datetime
import json
from unittest.mock import patch

from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
from allma_model.core.vector_memory_engine import VectorMemoryEngine


def seeded(path,count=300):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    assert memory._load_error is None
    memory.messages.extend(Message('c','user',f'Appunto {i} sul mare.',datetime.now(),{},'u') for i in range(count))
    memory.save_memory();memory._index_messages()
    return memory


def test_reopen_parses_each_historical_row_only_once(tmp_path):
    memory=seeded(tmp_path)
    with patch('allma_model.memory_system.history_store.json.loads',wraps=json.loads) as parse:
        restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is None and len(restored.messages)==300
    # Three state sections and one decode per message; generous allowance for
    # independent component headers, never a second pass through all texts.
    assert parse.call_count<=320


def test_reopen_does_not_open_a_sqlite_connection_for_each_old_message(tmp_path):
    seeded(tmp_path)
    original=VectorMemoryEngine._conn
    calls=[]
    def counted(engine):
        calls.append(engine.db_path)
        return original(engine)
    with patch.object(VectorMemoryEngine,'_conn',counted):
        restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored.vector_engine.count()==300
    assert len(calls)<=5


def test_conversational_startup_defers_derived_search_index_until_needed(tmp_path):
    seeded(tmp_path)
    with patch.object(VectorMemoryEngine,'_rebuild_index',side_effect=AssertionError('Premature index build')):
        restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is None and restored.vector_engine is not None
    assert restored.vector_engine.search('u','mare')[0]['metadata']['role']=='user'

import sqlite3
import pytest


def test_batch_reconciliation_is_idempotent_and_refreshes_revocation(tmp_path):
    memory=seeded(tmp_path,2)
    engine=memory.vector_engine
    before=engine.search('u','mare',allowed_roles=('user',))
    assert len(before)==2
    frequency=engine._tfidf.to_dict()
    memory._index_messages()
    assert engine._tfidf.to_dict()==frequency and not engine._index_dirty
    memory.messages[0].metadata['revoked']=True
    memory.save_memory()
    reopened=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    hits=reopened.vector_engine.search('u','mare',allowed_roles=('user',))
    assert len(hits)==1 and hits[0]['content']==memory.messages[1].content


def test_broken_batch_does_not_publish_first_half_or_dirty_cached_index(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Originale',source_key='original')
    engine.search('u','originale')
    def broken():
        yield {'user_id':'u','content':'Must roll back','timestamp':datetime.now(),
               'metadata':{},'source_key':'new'}
        raise OSError('Synthetic mid-batch failure')
    with pytest.raises(OSError):engine.add_many(broken())
    assert engine.count()==1 and not engine._index_dirty
    assert not engine.search('u','roll back')


def test_ambiguous_legacy_conversation_cannot_assign_a_message_to_an_owner(tmp_path):
    from allma_model.memory_system.conversational_memory import Conversation
    memory=ConversationalMemory(load_persistent=False,storage_dir=str(tmp_path))
    for user in ('one','two'):
        memory.conversations[user].append(Conversation('duplicate',user,datetime.now(),'',{}))
    memory.messages.append(Message('duplicate','user','Un ricordo senza proprietario.',datetime.now(),{}))
    memory._index_messages()
    assert memory.vector_engine.count()==0
