"""Production conversation persistence must not serialize old turns per append."""
from datetime import datetime
from unittest.mock import patch

from allma_model.core.allma_core import ALLMACore
from allma_model.memory_system.conversational_memory import Message


def test_production_append_does_not_serialize_earlier_turns(tmp_path):
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    try:
        memory=core.conversational_memory
        conversation=core.start_conversation('u')
        memory.messages.extend(Message(conversation,'user',f'Appunto storico {i}.',datetime.now(),{},'u')
                               for i in range(1000))
        memory.save_memory()
        with patch.object(memory,'_json_serial',wraps=memory._json_serial) as serialize:
            memory.store_message(conversation,'Nuovo appunto.',role='user',user_id='u')
        assert serialize.call_count<=4
        assert len(memory.messages)==1001
    finally:
        core.close()

import json
import sqlite3
from copy import deepcopy
import pytest
from allma_model.memory_system.conversational_memory import ConversationalMemory, Conversation
from allma_model.memory_system.history_store import HistoryStore


def opened(root):
    memory=ConversationalMemory(storage_dir=str(root),incremental=True)
    assert memory._load_error is None
    memory.vector_engine=None
    return memory


def add(memory,text='Originale'):
    memory.store_message('c',text,{'nested':{'items':['one']}},'user','u')


def test_migration_keeps_original_and_all_sections(tmp_path):
    legacy={'messages':[{'conversation_id':'c','role':'user','content':'Ciao',
        'timestamp':'2025-01-02T03:04:05','metadata':{},'user_id':'u'}],
        'conversations':{'u':[{'id':'c','user_id':'u','timestamp':'2025-01-02T03:04:05',
                              'content':'Ciao','metadata':{}}],'empty':[]},
        'user_data':{'u':{'name':'Prova'}},'trauma_log':[{'description':'synthetic'}]}
    original=json.dumps(legacy).encode();(tmp_path/'allma_memory.json').write_bytes(original)
    memory=opened(tmp_path)
    assert memory.messages[0].content=='Ciao'
    assert list(memory.conversations)==['u','empty']
    assert memory.user_data==legacy['user_data'] and memory.trauma_log==legacy['trauma_log']
    add(memory,'Nuovo')
    assert len(opened(tmp_path).messages)==2
    assert (tmp_path/'allma_memory.json').read_bytes()==original


@pytest.mark.parametrize('change',[
    lambda m:setattr(m.messages[0],'content','Corretto'),
    lambda m:m.messages[0].metadata['nested']['items'].append('two'),
    lambda m:m.messages[0].metadata.update({'revoked':True}),
    lambda m:m.user_data.setdefault('u',{}).update({'colour':'verde'}),
    lambda m:m.trauma_log.append({'description':'synthetic'}),
    lambda m:m.messages.reverse(),
    lambda m:m.messages.__setitem__(slice(None,1),[]),
    lambda m:setattr(m,'messages',m.messages[1:]),
    lambda m:setattr(m,'user_data',{'u':{'name':'Test'}}),
    lambda m:m.messages.__imul__(2),
])
def test_nested_mutations_and_structural_operations_survive_reload(tmp_path,change):
    memory=opened(tmp_path);add(memory);add(memory,'Secondo')
    change(memory)
    expected=deepcopy((memory.messages,memory.user_data,memory.trauma_log))
    memory.save_memory()
    restored=opened(tmp_path)
    assert (restored.messages,restored.user_data,restored.trauma_log)==expected


def test_groups_context_replacement_and_removal(tmp_path):
    memory=opened(tmp_path)
    identifier=memory.create_conversation('u')
    memory.update_context(identifier,{'nested':{'list':[1]}})
    memory.conversations['u'][0].metadata['nested']['list'].append(2)
    memory.conversations['empty']=[]
    memory.save_memory()
    memory.conversations['u']=memory.conversations['u'][:]
    memory.save_memory()
    restored=opened(tmp_path)
    assert restored.conversations['u'][0].metadata['nested']['list']==[1,2]
    assert 'empty' in restored.conversations
    del restored.conversations['u'];restored.save_memory()
    assert 'u' not in opened(tmp_path).conversations


def test_noop_save_and_single_old_row_edit_are_bounded(tmp_path):
    memory=opened(tmp_path)
    for i in range(50):add(memory,str(i))
    with patch.object(memory._history_store,'connect',side_effect=AssertionError('Unexpected write')):
        memory.save_memory()
    memory.messages[0].metadata['revoked']=True
    with patch.object(memory,'_json_serial',wraps=memory._json_serial) as serialize:
        memory.save_memory()
    assert serialize.call_count==1
    assert opened(tmp_path).messages[0].metadata['revoked'] is True


def test_write_failure_cannot_leak_popped_message_into_later_save(tmp_path):
    memory=opened(tmp_path);add(memory)
    with patch.object(memory._history_store,'connect',side_effect=OSError('Full disk')):
        with pytest.raises(OSError):add(memory,'Must not persist')
    memory.user_data['u']={'ok':True};memory.save_memory()
    assert [m.content for m in opened(tmp_path).messages]==['Originale']


def test_stale_writer_cannot_clobber_history(tmp_path):
    first=opened(tmp_path);second=opened(tmp_path)
    add(first,'First')
    with pytest.raises(RuntimeError):add(second,'Stale')
    assert [m.content for m in opened(tmp_path).messages]==['First']
    assert second.load_memory()
    add(second,'Second')
    assert len(opened(tmp_path).messages)==2


@pytest.mark.parametrize('damage',['corrupt','delete'])
def test_damaged_database_never_revives_legacy(tmp_path,damage):
    (tmp_path/'allma_memory.json').write_text('{}')
    memory=opened(tmp_path);add(memory)
    archive=tmp_path/'conversation_history.db'
    if damage=='delete':archive.unlink()
    else:archive.write_bytes(b'broken')
    assert not memory.load_memory() and memory.messages[0].content=='Originale'
    with pytest.raises(RuntimeError):memory.save_memory()
    restored=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    assert restored._load_error is not None


def test_invalid_edit_is_rejected_without_poisoning_archive(tmp_path):
    memory=opened(tmp_path);add(memory)
    memory.messages[0].role='invalid'
    with pytest.raises(ValueError):memory.save_memory()
    assert opened(tmp_path).messages[0].role=='user'
    memory.messages[0].role='assistant';memory.save_memory()
    assert opened(tmp_path).messages[0].role=='assistant'


def test_backup_includes_and_validates_new_history(tmp_path):
    from allma_model.utils.state_backup import StateBackups,verify_archive,_check_data,BackupError
    memory=opened(tmp_path);add(memory)
    backups=StateBackups(tmp_path);snapshot=backups.create()
    target=tmp_path/'restore';target.mkdir()
    manifest=verify_archive(backups.directory/snapshot['id'],target)
    assert 'conversation_history.db' in manifest['files']
    assert opened(target).messages[0].content=='Originale'
    with sqlite3.connect(target/'conversation_history.db') as db:
        db.execute("UPDATE history_state SET data='[]' WHERE name='user_data'")
    with pytest.raises(BackupError):_check_data(target/'conversation_history.db','conversation_history.db')
