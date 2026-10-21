from unittest.mock import patch

import pytest

from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.core.autobiographical_identity import grounded_reply
from allma_model.utils.output_contract import sentence_count, valid_sentence_count


def test_failed_message_is_not_saved_by_next_transaction(tmp_path):
    memory = ConversationalMemory(load_persistent=False, storage_dir=str(tmp_path))
    cid = memory.create_conversation('u')
    with patch.object(memory, 'save_memory', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            memory.store_message(cid, 'failed', role='user', user_id='u')
    assert not memory.messages
    memory.store_message(cid, 'retry', role='user', user_id='u')
    assert memory.load_memory()
    assert [m.content for m in memory.messages] == ['retry']


def test_failed_context_restores_original_object(tmp_path):
    memory = ConversationalMemory(load_persistent=False, storage_dir=str(tmp_path))
    cid = memory.create_conversation('u')
    memory.update_context(cid, {'original': 1})
    conversation = memory.conversations['u'][0]
    previous = conversation.metadata
    with patch.object(memory, 'save_memory', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            memory.update_context(cid, {'ghost': 2})
    assert conversation.metadata is previous
    memory.update_context(cid, {'retry': 3})
    assert memory.load_memory()
    assert memory.conversations['u'][0].metadata == {'original': 1, 'retry': 3}


@pytest.mark.parametrize('text,count', [
    ('"Prima". Seconda. Terza.', 3),
    ('«Prima.» Seconda.', 2),
    ('Vale 3.14. Va bene?', 2),
    ('“Prima! Seconda?” Terza.', 3),
])
def test_quoted_sentences_are_counted(text, count):
    assert sentence_count(text) == count
    assert valid_sentence_count(text, count)
    assert not valid_sentence_count(text, count + 1)


def test_unverifiable_sentence_count_does_not_pass():
    assert not valid_sentence_count('```python\nx = 2\n```', 2)
    assert valid_sentence_count('```python\nx = 2\n```', None)


def test_preferences_need_owned_explicit_evidence_and_allow_corrections(tmp_path):
    memory = ConversationalMemory(load_persistent=False, storage_dir=str(tmp_path))
    cid = memory.create_conversation('u')
    query = 'Qual è il mio colore preferito?'
    for content, role, owner in [
        ('Il mio colore preferito è rosso.', 'user', 'other'),
        ('Il mio colore preferito è rosso.', 'assistant', 'u'),
        ('Il personaggio dice: «Il mio colore preferito è rosso».', 'user', 'u'),
    ]:
        memory.store_message(cid, content, role=role, user_id=owner)
    assert grounded_reply(query, memory, 'u')[1] == 'no_evidence'
    memory.store_message(cid, 'Il mio colore preferito è blu.', role='user', user_id='u')
    memory.store_message(cid, 'Ora il mio colore preferito è verde.', role='user', user_id='u')
    assert memory.load_memory()
    assert 'verde' in grounded_reply(query, memory, 'u')[0]
    assert grounded_reply('Qual è il tuo colore preferito?', memory, 'u')[1] == 'no_evidence'
    memory.store_message(cid, 'Non ho più un colore preferito.', role='user', user_id='u')
    answer, source, _ = grounded_reply(query, memory, 'u')
    assert source == 'personal_fact_revoked'
    assert 'verde' not in answer and 'rosso' not in answer
