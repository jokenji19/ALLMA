"""Exact text tools must win over both model guesses and learned guesses."""
from unittest.mock import Mock
import pytest


@pytest.fixture
def core(tmp_path, monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    instance = ALLMACore(mobile_mode=True, db_path=str(tmp_path/'core.db'))
    instance._ensure_mobile_llm = lambda: None
    instance._llm = Mock()
    instance._llm.generate.return_value = '26'
    instance._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    yield instance
    instance.close()


@pytest.mark.parametrize('message, expected', [
    ('Rispondi solo con un numero: quante lettere contiene JSON?', '4'),
    ('Il testo JSON contiene quattro lettere? Rispondi solo si o no', 'sì'),
    ('Il testo JSON contiene ventisei lettere? Rispondi solo sì o no', 'no'),
    ('Quante lettere contiene «ippopotamo»? Rispondi solo con un numero.', '10'),
    ('Conta i caratteri di "A B". Rispondi solo con un numero.', '3'),
    ('Quante volte compare "ana" in "banana", senza sovrapposizioni? Rispondi solo con un numero.', '1'),
])
def test_exact_result_without_inference_or_answer_recall(core, message, expected):
    core.answer_recall.lookup = Mock(side_effect=AssertionError('A cached guess is not a count'))
    core.decision_runtime.decide = Mock(side_effect=AssertionError('No inference required'))
    events = []
    conversation = core.start_conversation('u')
    result = core.process_message('u', conversation, message, stream_callback=events.append)
    assert result.content == expected
    assert result.is_valid and result.metadata['knowledge_verified']
    assert result.metadata['source'] == 'verified_text_count'
    assert result.metadata['generation']['llm_used'] is False
    assert result.topics == ['text_count']
    assert result.metadata['evidence'][0]['value'] >= 0
    core._llm.generate.assert_not_called()
    core.answer_recall.lookup.assert_not_called()
    assert ''.join(e['content'] for e in events if e['type'] == 'answer') == expected
    history = core.conversational_memory.get_conversation_history(conversation)
    assert len([m for m in history if m.role == 'assistant']) == 1
    assert not core.answer_recall.records
    assert not core.incremental_learner.knowledge_base
    activity = core.brain_activity.snapshot()
    assert any(e['module'] == 'tools' and e['phase'] == 'running' for e in activity['events'])
    assert not any(e['module'] == 'model' for e in activity['events'])


@pytest.mark.parametrize('question', [
    'Spiega la frase «Quante lettere contiene JSON?»',
    'Quante lettere contiene JSON? Spiegalo in due frasi.',
    'Che cos’è JSON?',
])
def test_other_requests_keep_the_model_path(core, question):
    core._llm.generate.return_value = 'Una spiegazione breve. Una seconda frase.'
    result = core.process_message('u', core.start_conversation('u'), question)
    assert result.is_valid
    assert result.metadata.get('source') != 'verified_text_count'
    core._llm.generate.assert_called_once()


def test_old_wrong_answer_in_conversation_does_not_override_the_count(core):
    conversation = core.start_conversation('u')
    core.conversational_memory.store_message(conversation, '26', {'is_valid': True}, 'assistant', 'u')
    result = core.process_message('u', conversation, 'Quante lettere contiene JSON? Rispondi solo con un numero.')
    assert result.content == '4' and result.metadata['knowledge_verified']
    core._llm.generate.assert_not_called()


def test_native_failure_is_honest_and_does_not_fall_back_to_a_model_guess(core, monkeypatch):
    from allma_model.utils import exact_text
    def fail(_):
        raise RuntimeError('synthetic native failure')
    monkeypatch.setattr(exact_text, '_android_graphemes', fail)
    result = core.process_message('u', core.start_conversation('u'), 'Quanti caratteri contiene «👩‍💻»?')
    assert not result.is_valid and not result.metadata['knowledge_verified']
    assert result.metadata['source'] == 'text_count_unavailable'
    core._llm.generate.assert_not_called()


def test_empty_needle_is_a_clarification_not_verified_knowledge(core):
    result = core.process_message('u', core.start_conversation('u'), 'Quante volte compare "" in "banana"?')
    assert result.metadata['source'] == 'text_count_clarification'
    assert not result.is_valid and not result.metadata['knowledge_verified']
    assert not core.answer_recall.records
    core._llm.generate.assert_not_called()


def test_cancellation_after_count_does_not_save_or_stream(core, monkeypatch):
    import threading
    from allma_model.utils import exact_text
    from allma_model.utils.generation_control import GenerationCancelled
    cancel = threading.Event()
    original = exact_text.count_request
    def counted(request):
        result = original(request)
        cancel.set()
        return result
    monkeypatch.setattr(exact_text, 'count_request', counted)
    conversation = core.start_conversation('u')
    events = []
    with pytest.raises(GenerationCancelled):
        core.process_message('u', conversation, 'Quante lettere contiene JSON?',
                             cancel_event=cancel, stream_callback=events.append)
    assert not core.conversational_memory.get_conversation_history(conversation)
    assert not events
    core._llm.generate.assert_not_called()


def test_storage_failure_does_not_deliver_a_success(core):
    conversation = core.start_conversation('u')
    core.conversational_memory.store_message = Mock(side_effect=OSError('synthetic disk full'))
    events = []
    with pytest.raises(OSError):
        core.process_message('u', conversation, 'Quante lettere contiene JSON?', stream_callback=events.append)
    assert not events and not core.answer_recall.records
    core._llm.generate.assert_not_called()
