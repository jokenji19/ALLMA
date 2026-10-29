from types import SimpleNamespace as T
from unittest.mock import Mock

import pytest

from allma_model.utils.dialogue_recovery import (
    dialogue_history, opening_recovery, unanswered_attempt,
)
from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.runtime_capabilities import self_description_reply
from allma_model.utils.output_contract import borrowed_user_experience


def turn(role, text, **metadata):
    return T(role=role, content=text, metadata=metadata)


def failure(request='Bene, ma ho un dubbio', reason='subject_mismatch'):
    return [turn('user', request), turn('assistant', 'Avviso tecnico.',
        is_valid=False, generation={'status': reason})]


OPENINGS = [
    'Bene, ma ho un dubbio', 'Ho un dubbio', 'Ho una domanda.',
    'Vorrei chiederti una cosa', 'Posso farti una domanda?',
    'Volevo porti un quesito', 'Posso dirti qualcosa?', 'Ho un problema.',
    'Grazie, vorrei dirti qualcosa.', 'Sto bene, però ho una domanda.',
    'I have a question', 'Can I ask you something?', 'I have a concern.',
    "I'm fine, but I have a question.",
]
SUBSTANTIVE = [
    'Ho un dubbio: quanto fa 18 + 24?', 'Ho una domanda su Roma.',
    'Ho un dubbio sul fatto che 2 + 2 faccia 4.',
    'Non ho un dubbio', 'Non posso farti una domanda?',
    'Mia sorella ha un dubbio', '«Ho un dubbio»', "'Ho un dubbio'", '"Ho un dubbio"',
    'Traduci: ho un dubbio', 'Ho un dubbio. Rispondi solo con JSON.',
    'Ho una domanda. Rispondi in inglese.', 'Sono triste e ho un dubbio.',
    'Ho un dubbio e penso di farmi male.', 'Ho un problema cardiaco.',
    'Ho un problema. Non riesco a respirare.',
    'Vorrei chiederti una cosa: perché il cielo è blu?',
    'Vorrei chiederti una cosa\nCome funziona?', 'Ho un dubbio su di te.',
    'I have a question about my medication.', 'I do not have a question.',
]


@pytest.mark.parametrize('message', OPENINGS)
def test_local_clarification_only_asks_for_missing_content(message):
    recovery = opening_recovery(message)
    assert recovery and recovery['source'] == 'grounded_dialogue_recovery'
    assert recovery['evidence'][0]['text'] == message
    assert not borrowed_user_experience(recovery['content'], message)
    assert not DialogueContinuity(message, []).duplicate(recovery['content'])


@pytest.mark.parametrize('message', SUBSTANTIVE)
def test_neutral_recovery_never_intercepts_substance_or_instructions(message):
    assert opening_recovery(message) is None
    assert self_description_reply(message, T(), failure()) is None


def test_pending_request_survives_explanation_but_not_topic_change_or_success():
    raw = failure()
    explanation = self_description_reply('Cosa intendi?', T(), raw)
    assert explanation[1] == 'runtime_recovery_explanation'
    assert 'qual è il dubbio?' in explanation[0]
    detour = [turn('user', 'Cosa intendi?'), turn('assistant', explanation[0], source=explanation[1])]
    history = raw + detour
    pending = unanswered_attempt(history)
    assert pending['request'] is raw[0] and pending['reason'] == 'subject_mismatch'
    recovery = self_description_reply('Ho un dubbio', T(), history)
    assert recovery[1] == 'grounded_dialogue_recovery'
    assert 'controllo' not in recovery[0] and 'Riprova' not in recovery[0]
    continuity = DialogueContinuity(raw[0].content, [raw[0]] + detour, history)
    assert continuity.retry_after_failure
    assert not continuity.duplicate(recovery[0])
    assert 'richiesta attuale' in continuity.guidance()
    assert self_description_reply('Ho un dubbio', T(), history + [turn('user', 'Nuovo tema')])[1] == 'dialogue_opening'
    assert unanswered_attempt(history + [turn('user', 'Nuovo tema'), turn('assistant', 'Risposta utile.')]) is None


@pytest.mark.parametrize('status', ['cancelled', 'truncated_answer', 'completed', 'model_switching'])
def test_cancelled_or_successful_turn_is_not_an_unanswered_guard_failure(status):
    assert unanswered_attempt(failure(reason=status)) is None


def test_projection_does_not_mutate_archive_or_strip_real_explanations():
    original = turn('user', 'Ho un dubbio')
    question = turn('user', 'Cosa intendi?')
    explanation = turn('assistant', 'Spiegazione del controllo.', source='runtime_recovery_explanation')
    actual = turn('assistant', 'Una spiegazione del fenomeno.', source='model_generated')
    history = [original, question, explanation, question, actual]
    assert dialogue_history(history) == [original, question, actual]
    assert len(history) == 5
    assert dialogue_history(dialogue_history(history)) == dialogue_history(history)


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'core.db'))
    instance._ensure_mobile_llm = lambda: None
    instance._llm = Mock()
    instance._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    instance.decision_runtime.route = Mock(return_value={'status': 'selected', 'choice': 'reason'})
    instance.incremental_learner.learn_from_interaction = Mock()
    instance.answer_recall.observe = Mock()
    yield instance
    instance.close()


@pytest.mark.parametrize('message', ['Bene, ma ho un dubbio', 'Posso farti una domanda?'])
def test_actual_pipeline_clarifies_content_free_opening_without_model_or_learning(core, message):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    core.process_message(user, cid, 'Ciao')
    core._llm.generate.side_effect = AssertionError('A content-free opening does not need inference')
    events = []
    result = core.process_message(user, cid, message, stream_callback=events.append)
    assert result.is_valid and result.metadata['source'] == 'dialogue_opening'
    assert result.metadata['generation']['llm_used'] is False
    assert result.content.startswith('Dimmi pure:')
    assert result.content == ''.join(e['content'] for e in events if e['type'] == 'answer')
    assert core.conversational_memory.messages[-1].content == result.content
    core._llm.generate.assert_not_called()
    core.answer_recall.observe.assert_not_called()
    core.incremental_learner.learn_from_interaction.assert_not_called()


def seed_legacy_failure(core, user, cid):
    core.conversational_memory.store_message(cid, 'Bene, ma ho un dubbio', {}, 'user', user)
    core.conversational_memory.store_message(cid, 'Avviso del controllo.',
        {'is_valid': False, 'generation': {'status': 'subject_mismatch'}}, 'assistant', user)


def test_legacy_error_detour_resumes_request_and_does_not_pollute_next_prompt(core):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    seed_legacy_failure(core, user, cid)
    explanation = core.process_message(user, cid, 'Cosa intendi?')
    resumed = core.process_message(user, cid, 'Ho un dubbio')
    assert explanation.metadata['source'] == 'runtime_recovery_explanation'
    assert resumed.metadata['source'] == 'grounded_dialogue_recovery'
    core._llm.generate.assert_not_called()
    core._llm.generate.return_value = 'L’acqua passa allo stato di vapore quando riceve sufficiente energia.'
    answer = core.process_message(user, cid, 'Perché evapora l’acqua?')
    assert answer.is_valid
    prompt = core._llm.generate.call_args.kwargs['prompt']
    assert explanation.content not in prompt and 'Cosa intendi?' not in prompt
    assert 'Bene, ma ho un dubbio' in prompt
    assert 'Perché evapora l’acqua?' in prompt
    assert explanation.content in [m.content for m in core.conversational_memory.messages]


def test_neutral_recovery_does_not_replace_a_specific_rejected_question(core):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    core._llm.generate.return_value = 'Ho un dubbio sulla mia salute.'
    answer = core.process_message(user, cid, 'Ho un dubbio sulla mia salute. Cosa posso verificare?')
    assert not answer.is_valid and answer.metadata['generation']['status'] == 'subject_mismatch'
    assert answer.metadata['source'] == 'model_generated'


def test_retrieved_technical_notice_cannot_reenter_prompt_as_a_personal_memory(core, monkeypatch):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    notice = 'Avviso tecnico da non reinserire come ricordo personale.'
    import allma_model.agency_system.operational_actions as actions
    monkeypatch.setattr(actions, 'memory_step', lambda *args, **kwargs: ([
        {'content': notice, 'score': .99, 'metadata': {'source': 'runtime_recovery_explanation', 'role': 'assistant'}}
    ], {'status': 'completed'}))
    core._llm.generate.return_value = 'Posso aiutarti a chiarire il messaggio attuale.'
    reply = core.process_message(user, cid, 'Vorrei chiarire il mio dubbio su questa spiegazione.')
    assert reply.is_valid
    assert notice not in core._llm.generate.call_args.kwargs['prompt']
    assert reply.metadata['memory_score'] == 0


def test_recovery_is_scoped_to_current_conversation_and_user(core):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    seed_legacy_failure(core, user, cid)
    core._llm.generate.return_value = 'Dimmi pure, qual è la domanda?'
    for owner, target in [(user, core.start_conversation(user)), ('other', core.start_conversation('other'))]:
        reply = core.process_message(owner, target, 'Ho un dubbio')
        assert reply.metadata['source'] == 'dialogue_opening'
    core._llm.generate.assert_not_called()


from allma_model.utils.dialogue_diagnostics import CASES


@pytest.mark.parametrize('group,name,criterion,fn', CASES, ids=[row[1] for row in CASES])
def test_shared_android_dialogue_scenario(tmp_path, group, name, criterion, fn, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / name
    path.mkdir()
    fn(path)


def test_recovery_never_appends_a_clarification_to_an_already_streamed_answer(core):
    user = 'synthetic-dialogue'
    cid = core.start_conversation(user)
    first = 'Puoi raccontarmi la tua domanda e indicarmi quale passaggio vorresti chiarire. '
    events = []
    def generate(**kwargs):
        kwargs['callback']('</think>' + first)
        assert any(e['type'] == 'answer' for e in events)
        kwargs['callback']('Ho un dubbio sulla mia salute.')
        return first + 'Ho un dubbio sulla mia salute.'
    core._llm.generate.side_effect = generate
    reply = core.process_message(user, cid, 'Ho un dubbio sulla mia salute, puoi aiutarmi a capire quali informazioni servono?', stream_callback=events.append)
    assert not reply.is_valid and reply.metadata['generation']['status'] == 'subject_mismatch'
    assert reply.metadata.get('recovery') is None
    assert 'Dimmi pure' not in ''.join(e['content'] for e in events if e['type'] == 'answer')
