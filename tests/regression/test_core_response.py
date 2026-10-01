import asyncio
from datetime import datetime
from unittest.mock import Mock

import pytest


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'core.db'))
    instance._ensure_mobile_llm = lambda: None
    instance._llm = None
    yield instance
    instance.close()


def test_high_similarity_cannot_bypass_llm_or_validate_error(core):
    conversation = core.start_conversation('u')
    core.incremental_learner.learn_from_interaction = Mock()
    def search(**kwargs):
        assert not core.conversational_memory.messages
        return [{'content': 'Non è una risposta verificata', 'metadata': {},
                 'timestamp': datetime.now().isoformat(), 'score': 0.99}]
    core.conversational_memory.vector_engine.search = search
    response = core.process_message('u', conversation, 'Ti ricordi il mare?')
    assert response.is_valid is False
    assert response.metadata['memory_gate_status'] == 'LEVEL_3'
    assert response.content == core.conversational_memory.messages[-1].content
    assert core.conversational_memory.messages[-1].metadata['is_valid'] is False
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert core.conversational_memory.vector_engine.count() == 1


def test_dream_toggle_and_manual_trigger_respect_user_and_activity(core):
    core.dream_manager.check_and_start_dream = Mock()
    core._current_user_id = 'u'
    core.set_dream_mode(False)
    core.start_dreaming()
    core.dream_manager.check_and_start_dream.assert_not_called()
    core.set_dream_mode(True)
    core._user_active.set()
    core.start_dreaming()
    core.dream_manager.check_and_start_dream.assert_not_called()
    core._user_active.clear()
    core.start_dreaming()
    core.dream_manager.check_and_start_dream.assert_called_once_with(user_id='u')


def test_cancelled_inference_is_not_saved_or_learned(core):
    from threading import Event
    from allma_model.utils.generation_control import GenerationCancelled
    conversation = core.start_conversation('u')
    event = Event()
    core.incremental_learner.learn_from_interaction = Mock()
    def generate(**kwargs):
        assert kwargs['cancel_event'] is event
        event.set()
        return 'Risposta parziale da scartare'
    core._llm = Mock()
    core._llm.generate.side_effect = generate
    with pytest.raises(GenerationCancelled):
        core.process_message('u', conversation, 'Raccontami del mare', cancel_event=event)
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert all(message.role == 'user' for message in core.conversational_memory.messages)
    assert not core._user_active.is_set()


def test_stream_and_saved_answer_exclude_thought_and_do_not_auto_continue(core):
    conversation = core.start_conversation('u')
    events = []
    def generate(**kwargs):
        for token in ['Okay, the user said Ciao.', '</thi', 'nk>', 'Ciao']:
            kwargs['callback'](token)
        return 'Ciao'
    core._llm = Mock()
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'max_tokens'}
    result = core.process_message('u', conversation, 'Descrivi il mare', stream_callback=events.append)
    assert 'Okay' not in result.content
    assert 'Ciao' in result.content
    assert core._llm.generate.call_count == 1
    assert all('Okay' not in e['content'] for e in events if e.get('type') == 'answer')
    assert core.conversational_memory.messages[-1].content == result.content


def test_empty_budget_failure_is_not_reported_as_offline_and_metrics_survive(core):
    conversation = core.start_conversation('budget_user')
    core._llm = Mock()
    core._llm.generate.return_value = ''
    core._llm.get_generation_meta.return_value = {'finish_reason': 'length', 'completion_tokens': 512}
    response = core.process_message('budget_user', conversation, 'Spiega il principio di entropia')
    assert 'limite' in response.content
    assert 'raggiungibile' not in response.content
    assert response.is_valid is False
    assert response.metadata['generation']['status'] == 'budget_exhausted'
    assert response.metadata['generation']['completion_tokens'] == 512


def test_confirmed_recall_avoids_model_loading_and_correction_invalidates(core):
    conversation = core.start_conversation('u')
    question = 'Spiega il concetto di entropia'
    core._llm = Mock()
    core._llm.generate.return_value = 'I mattoncini possono essere disposti in molti modi.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    first = core.process_message('u', conversation, question)
    assert first.is_valid
    core.process_message('u', conversation, 'Risposta corretta')
    core.process_message('u', conversation, question)
    core.process_message('u', conversation, 'Risposta corretta')
    assert core._llm.generate.call_count == 2
    core._ensure_mobile_llm = Mock(side_effect=AssertionError('recall must avoid loading'))
    result = core.process_message('u', conversation, question)
    assert result.metadata['source'] == 'confirmed_answer_recall'
    assert result.metadata['knowledge_verified'] is False
    assert core._llm.generate.call_count == 2
    correction = core.process_message('u', conversation, 'Risposta sbagliata')
    assert correction.metadata['source'] == 'learning_feedback'
    assert core.answer_recall.lookup(result.metadata['recall_key'], 'u') is None
