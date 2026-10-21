"""Real core integration for natural exact requests and scoped clarifications."""
import json
from unittest.mock import Mock
import pytest
from tests.regression.test_exact_text_core import core


@pytest.mark.parametrize('question,answer,source', [
    ('Per favore, puoi dirmi quante lettere ha banana? Rispondi solo con un numero.', '6', 'verified_text_count'),
    ('Rispondi solo con un numero: quanto fa 18 + 24?', '42', 'verified_calculation'),
    ('Puoi calcolare 0,1 + 0,2? Rispondi solo con un numero.', '0.3', 'verified_calculation'),
    ('La parola a contiene una lettera? Rispondi solo sì o no.', 'sì', 'verified_text_count'),
    ('Calcola 0,1 + 0,2. Rispondi solo in JSON.', '{"risultato":0.3}', 'verified_calculation'),
])
def test_exact_tools_remain_before_cached_or_model_guesses(core, question, answer, source):
    core.answer_recall.lookup = Mock(side_effect=AssertionError('Must compute the result'))
    events = []
    result = core.process_message('u', core.start_conversation('u'), question, stream_callback=events.append)
    assert result.is_valid and result.metadata['source'] == source
    assert result.content == answer and result.metadata['knowledge_verified']
    assert result.metadata['generation']['llm_used'] is False
    core._llm.generate.assert_not_called()
    assert ''.join(e['content'] for e in events if e['type'] == 'answer') == answer
    assert not core.answer_recall.records


@pytest.mark.parametrize('choice,expected', [
    ('Con le sovrapposizioni', '2'),
    ('Senza sovrapposizioni', '1'),
    ('Includi anche le sovrapposizioni. Rispondi solo in JSON.', '{"conteggio":2}'),
])
def test_clarification_preserves_explicit_operands_and_output_across_turns(core, choice, expected):
    cid = core.start_conversation('u')
    first = core.process_message('u', cid, 'Quante volte compare "ana" in "banana"? Rispondi solo con un numero.')
    assert first.metadata['source'] == 'text_count_clarification'
    assert not first.is_valid and not first.metadata['knowledge_verified']
    assert 'value' not in first.metadata['evidence'][0]
    # Reloaded messages/metadata come from the real conversation store.
    history = core.conversational_memory.get_conversation_history(cid)
    assert json.loads(json.dumps(history[-1].metadata))['source'] == 'text_count_clarification'
    events = []
    second = core.process_message('u', cid, choice, stream_callback=events.append)
    assert second.content == expected and second.is_valid
    assert second.metadata['evidence'][0]['clarification_resolved']
    assert second.metadata['knowledge_verified']
    core._llm.generate.assert_not_called()
    assert ''.join(e['content'] for e in events if e['type'] == 'answer') == expected


@pytest.mark.parametrize('same_user', [True, False])
def test_pending_question_cannot_cross_conversation_or_user(core, same_user):
    first = core.start_conversation('u')
    core.process_message('u', first, 'Quante volte compare "ana" in "banana"?')
    user = 'u' if same_user else 'other'
    second = core.start_conversation(user)
    core._llm.generate.return_value = 'Quale testo vuoi contare?'
    result = core.process_message(user, second, 'Con le sovrapposizioni')
    assert result.metadata.get('source') != 'verified_text_count'
    core._llm.generate.assert_called_once()


def test_broken_evidence_cannot_silently_resume_another_literal(core):
    cid = core.start_conversation('u')
    core.process_message('u', cid, 'Quante volte compare "ana" in "banana"?')
    original = core.conversational_memory.get_conversation_history
    def tampered(conversation_id):
        messages = original(conversation_id)
        if messages and messages[-1].metadata.get('source') == 'text_count_clarification':
            messages[-1].metadata['evidence'][0]['needle_sha256'] = 'wrong'
        return messages
    core.conversational_memory.get_conversation_history = tampered
    core._llm.generate.return_value = 'Quale testo vuoi contare?'
    result = core.process_message('u', cid, 'Con le sovrapposizioni')
    assert result.metadata.get('source') != 'verified_text_count'
    core._llm.generate.assert_called_once()


def test_intervening_dialogue_clears_the_immediate_tool_question(core):
    cid = core.start_conversation('u')
    core.process_message('u', cid, 'Quante volte compare "ana" in "banana"?')
    core.conversational_memory.store_message(cid, 'Cambiamo argomento.', {}, 'user', 'u')
    core.conversational_memory.store_message(cid, 'Va bene.', {'is_valid': True}, 'assistant', 'u')
    core._llm.generate.return_value = 'Quale testo vuoi contare?'
    result = core.process_message('u', cid, 'Con le sovrapposizioni')
    assert result.metadata.get('source') != 'verified_text_count'
    core._llm.generate.assert_called_once()


def test_pending_choice_survives_core_restart_using_saved_conversation(core):
    from allma_model.core.allma_core import ALLMACore
    cid = core.start_conversation('u')
    core.process_message('u', cid, 'Quante volte compare "ana" in "banana"? Rispondi solo con un numero.')
    database = core.db_path
    core.close()
    restored = ALLMACore(mobile_mode=True, db_path=database)
    restored._ensure_mobile_llm = lambda: None
    restored._llm = Mock()
    restored._llm.generate.side_effect = AssertionError('A saved tool question does not need a model')
    try:
        result = restored.process_message('u', cid, 'Senza sovrapposizioni')
        assert result.content == '1' and result.is_valid
        assert result.metadata['evidence'][0]['clarification_resolved']
        restored._llm.generate.assert_not_called()
    finally:
        restored.close()
