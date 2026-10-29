from types import SimpleNamespace as T
from unittest.mock import Mock

import pytest

from allma_model.utils.dialogue_continuity import DialogueContinuity, task_content
from allma_model.utils.dialogue_output import project_answer
from allma_model.utils.answer_stream import AnswerStream
from allma_model.core.autobiographical_identity import POLICY_VERSION

COMMENT = "Non ho verificato se l'utente ha detto di avere dubbi reali o solo ipotizzativi."
FACT = 'La Luna riflette la luce del Sole.'
QUESTION = 'Il mio dubbio è questo: perché la Luna cambia forma durante il mese?'


def history(question, answer):
    return [T(role='user', content=question, metadata={}),
            T(role='assistant', content=answer, metadata={})]


@pytest.mark.parametrize('message,expected', [
    (QUESTION, 'perché la Luna cambia forma durante il mese?'),
    ('La mia domanda è: perché il cielo è blu?', 'perché il cielo è blu?'),
    ('Mi chiedo: come funziona un arcobaleno?', 'come funziona un arcobaleno?'),
    ('My question is this: why is the sky blue?', 'why is the sky blue?'),
    ('Il mio dubbio è questo: ti ho già parlato di Roma?', 'ti ho già parlato di Roma?'),
    ('La mia domanda è: dove ho messo il mio passaporto?', 'dove ho messo il mio passaporto?'),
])
def test_only_conversational_frame_is_removed_for_resource_selection(message, expected):
    assert task_content(message) == expected


@pytest.mark.parametrize('message', [
    'Il mio dubbio riguarda la mia infanzia.', 'La mia domanda è rimasta senza risposta.',
    'Non conosco il mio problema: puoi aiutarmi?', '«Il mio dubbio è questo: Roma?»',
    'Nel testo: la mia domanda è: chi sono?', 'Il mio dubbio è questo:',
    'Sono triste: perché la mia passeggiata non mi ha aiutato?',
])
def test_personal_reports_and_quoted_frames_are_preserved(message):
    assert task_content(message) == message


@pytest.mark.parametrize('message,mode', [
    ('Quindi la Luna riflette la luce del Sole?', 'confirmation'),
    ('Mi confermi che ho capito?', 'confirmation'),
    ('Puoi spiegare meglio?', 'elaboration'),
    ('Perché?', 'elaboration'),
    ('No, intendevo Venere e non la Luna.', 'subject_clarification'),
    ('Non intendevo il passato, parlavo di oggi.', 'subject_clarification'),
    ('Hai sbagliato: la risposta è diversa.', 'correction'),
    ('Continua', 'continuation'),
    ('Riassumi la spiegazione', 'repeat'),
    ('Ora spiegami i vulcani.', 'request'),
])
def test_working_view_distinguishes_followup_purposes_without_new_facts(message, mode):
    view = DialogueContinuity(message, history(QUESTION, FACT))
    state = view.state()
    assert state['mode'] == mode
    assert message not in str(state) and QUESTION not in str(state)
    assert bool(state['reference_sha256']) == (mode != 'request')


@pytest.mark.parametrize('include_greeting', [False, True])
@pytest.mark.parametrize('followup,expected_mode', [
    ('Quindi cambia solo la parte illuminata?', 'confirmation'),
    ('Puoi spiegare meglio?', 'elaboration'),
    ('No, intendevo Venere.', 'subject_clarification'),
])
def test_followup_after_failure_references_unanswered_question_instead_of_last_success(include_greeting, followup, expected_mode):
    import hashlib
    valid = history('Ciao', 'Come stai?') if include_greeting else []
    valid += [T(role='user', content=QUESTION, metadata={})]
    attempts = valid + [T(role='assistant', content='Avviso.',
        metadata={'is_valid': False, 'generation': {'status': 'format_mismatch'}})]
    view = DialogueContinuity(followup, valid, attempts)
    assert view.mode == expected_mode
    assert view.state()['reference_sha256'] == hashlib.sha256(QUESTION.encode()).hexdigest()
    assert view.reference_content == task_content(QUESTION)
    changed = DialogueContinuity('Ora parliamo di vulcani.', valid, attempts)
    assert changed.mode == 'request' and changed.state()['unanswered_sha256'] is None


def test_confirmation_can_repeat_a_long_fact_and_new_detail_is_not_a_duplicate():
    answer = 'La Luna mantiene la stessa forma fisica e riflette la luce proveniente dal Sole.'
    assert not DialogueContinuity('Quindi la forma fisica della Luna resta uguale?', history(QUESTION, answer)).duplicate(answer)
    assert DialogueContinuity('Spiegami la fotosintesi', history(QUESTION, answer)).duplicate('Certo. ' + answer)
    assert not DialogueContinuity('Puoi spiegare meglio?', history(QUESTION, answer)).duplicate(answer + ' Dipende dal punto di osservazione.')
    assert not DialogueContinuity('Quindi perché?', history(QUESTION, answer)).confirmation


@pytest.mark.parametrize('message', ['Ripeti la risposta', 'Riassumi la risposta', 'Riordina le frasi', 'Quote the answer'])
def test_requested_transformations_allow_reusing_the_actual_text(message):
    a = 'La Luna mantiene la stessa forma fisica e riflette la luce del Sole.'
    b = 'Il Sole illumina una metà della Luna mentre noi ne osserviamo una porzione variabile.'
    assert not DialogueContinuity(message, history(QUESTION, a + ' ' + b)).duplicate(b + ' ' + a)


def test_reordered_reused_sentences_do_not_satisfy_a_request_for_new_explanation():
    a = 'La Luna mantiene la stessa forma fisica e riflette la luce del Sole.'
    b = 'Il Sole illumina una metà della Luna mentre noi ne osserviamo una porzione variabile.'
    view = DialogueContinuity('Spiegami come funziona un vulcano', history(QUESTION, a + ' ' + b))
    assert view.duplicate('Certo. ' + b + ' ' + a)
    assert not view.duplicate(a.replace('mantiene', 'non mantiene'))
    assert not view.duplicate(a + ' Un vulcano emette magma.')


@pytest.mark.parametrize('query', ['Perché la Luna cambia aspetto?', QUESTION])
def test_unrequested_standalone_execution_commentary_is_removed_without_new_facts(query):
    result = project_answer(FACT + '\n\n' + COMMENT, query)
    assert result.text == FACT and len(result.removed) == 1
    assert COMMENT not in str(result.audit()) and not result.audit()['factual_verification']
    assert project_answer(result.text, query).text == result.text


@pytest.mark.parametrize('query,answer', [
    ('Analizza questa frase', COMMENT),
    ('Traduci in italiano', COMMENT),
    ('Spiega perché hai bloccato la risposta', COMMENT),
    ('Cosa significa verificare le istruzioni?', COMMENT),
    ('Descrivi un personaggio', COMMENT),
    ('Restituisci solo JSON', '{"nota": "' + COMMENT + '"}'),
    ('Perché la Luna cambia?', '«' + COMMENT + '»'),
    ('Perché la Luna cambia?', '```\n' + COMMENT + '\n```'),
    ('Perché la Luna cambia?', "Non ho verificato le fonti di questa affermazione."),
    ('Perché la Luna cambia?', COMMENT[:-1] + ', ma la Luna non cambia forma.'),
    ('Perché la Luna cambia?', 'La frase è «' + COMMENT + '».'),
])
def test_requested_or_mixed_content_is_not_silently_deleted(query, answer):
    projection = project_answer(answer, query)
    assert projection.text == answer and not projection.removed


@pytest.mark.parametrize('raw', [FACT + ' ' + COMMENT, COMMENT + '\n\n' + FACT, FACT + '\n\n' + COMMENT,
    FACT + '\n\n' + COMMENT + '\n\nLe fasi dipendono dal punto di osservazione.'])
@pytest.mark.parametrize('chunk_size', [1, 3, 500])
def test_stream_and_final_projection_agree_even_with_split_tokens(raw, chunk_size):
    events = []
    stream = AnswerStream(QUESTION, events.append)
    for index in range(0, len(raw), chunk_size):
        stream.feed(raw[index:index + chunk_size])
    stream.feed('', final=True)
    assert not stream.rejected
    projected = project_answer(raw, QUESTION).text
    assert ''.join(e['content'] for e in events) == projected
    assert FACT in projected and COMMENT not in projected


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


def test_actual_general_question_frame_and_followup_skip_personal_retrieval(core, monkeypatch):
    memory = Mock(return_value=([], {'status': 'observed', 'record_count': 0}))
    monkeypatch.setattr('allma_model.agency_system.operational_actions.memory_step', memory)
    core._llm.generate.return_value = FACT
    cid = core.start_conversation('u')
    for q in [QUESTION, 'Quindi la Luna cambia forma davvero o solo la parte illuminata?']:
        reply = core.process_message('u', cid, q)
        assert reply.is_valid
        assert 'La ricerca nei ricordi non ha trovato' not in core._llm.generate.call_args.kwargs['prompt']
    memory.assert_not_called()
    assert core.decision_runtime.route.call_args_list[0].args[0] == task_content(QUESTION)
    assert QUESTION in [m.content for m in core.conversational_memory.messages]
    assert reply.metadata['dialogue_state']['mode'] == 'confirmation'


@pytest.mark.parametrize('question', [
    'Il mio dubbio è questo: perché la mia passeggiata mi ha rilassato?',
    'La mia domanda è: ti avevo già raccontato del viaggio?',
])
def test_personal_scope_is_still_host_required_when_it_occurs_inside_the_question(core, monkeypatch, question):
    memory = Mock(return_value=([], {'status': 'observed', 'record_count': 0}))
    monkeypatch.setattr('allma_model.agency_system.operational_actions.memory_step', memory)
    core._llm.generate.return_value = 'Posso riferirmi a ciò che hai descritto, senza verificarlo indipendentemente.'
    core.process_message('u', core.start_conversation('u'), question)
    memory.assert_called_once()
    assert memory.call_args.args[1] == 'u'
    assert 'La ricerca nei ricordi non ha trovato' in core._llm.generate.call_args.kwargs['prompt']


def test_edited_model_text_is_streamed_and_saved_but_not_automatically_learned(core):
    def generate(**kwargs):
        kwargs['callback']('</think>' + FACT + '\n\n')
        kwargs['callback'](COMMENT)
        return FACT + '\n\n' + COMMENT
    core._llm.generate.side_effect = generate
    events = []
    reply = core.process_message('u', core.start_conversation('u'), QUESTION, stream_callback=events.append)
    assert reply.is_valid and reply.content == FACT
    assert reply.metadata['source'] == 'model_excerpt'
    assert not reply.metadata['recovery']['model_answer_valid']
    assert reply.metadata['dialogue_output']['removed_sentences'] == 1
    assert ''.join(e['content'] for e in events if e['type'] == 'answer') == reply.content
    assert core.conversational_memory.messages[-1].content == reply.content
    core.answer_recall.observe.assert_not_called()
    core.incremental_learner.learn_from_interaction.assert_not_called()
    core._llm.generate.assert_called_once()


def test_commentary_is_not_used_to_fake_compliance_with_two_sentence_requirement(core):
    core._llm.generate.return_value = FACT + ' ' + COMMENT
    reply = core.process_message('u', core.start_conversation('u'), QUESTION + ' Rispondi in due frasi.')
    assert not reply.is_valid
    assert reply.metadata['generation']['status'] == 'format_mismatch'
    assert reply.metadata['dialogue_output']['removed_sentences'] == 1
    core.answer_recall.observe.assert_not_called()


def test_pure_commentary_is_not_an_answer_and_the_request_survives(core):
    core._llm.generate.return_value = COMMENT
    cid = core.start_conversation('u')
    reply = core.process_message('u', cid, QUESTION)
    assert not reply.is_valid and reply.metadata['generation']['status'] == 'internal_commentary'
    explanation = core.process_message('u', cid, 'Cosa intendi?')
    assert explanation.metadata['source'] == 'runtime_recovery_explanation'
    assert QUESTION in [m.content for m in core.conversational_memory.messages]


@pytest.mark.parametrize('state_name', ['direct', 'simple'])
@pytest.mark.parametrize('streamed', [False, True])
def test_expression_is_guided_before_generation_without_rewriting_qualifiers_or_paragraphs(core, state_name, streamed):
    from allma_model.core.architecture.identity_state import IdentityState
    state = IdentityState(under_duress=state_name == 'direct', maturity=.95 if state_name == 'simple' else .5)
    core.identity_engine_v5.compute_state = Mock(return_value=state)
    raw = 'Mi sembra che il fenomeno vada chiarito.\n\nPotrebbe dipendere dalle condizioni di osservazione.'
    events = []
    def generate(**kwargs):
        if kwargs['callback']:
            kwargs['callback']('</think>' + raw)
        return raw
    core._llm.generate.side_effect = generate
    result = core.process_message('u', core.start_conversation('u'), 'Spiegami questo fenomeno.',
        stream_callback=events.append if streamed else None)
    assert result.is_valid and result.content == raw
    if streamed:
        assert ''.join(e['content'] for e in events if e['type'] == 'answer') == raw
    hint = core.volition_v5.guidance(state)
    assert hint and hint in core._llm.generate.call_args.kwargs['prompt']
    assert core.conversational_memory.messages[-1].content == raw


def test_preserved_output_cannot_be_silently_rewritten_by_a_structural_rule():
    from allma_model.core.cognitive_pipeline import CognitivePipeline, CognitiveValidationError
    validator = Mock()
    validator.validate.return_value = ('Una frase diversa.', True, [])
    with pytest.raises(CognitiveValidationError):
        CognitivePipeline(structural_core=validator).process('La frase originale.', preserve_text=True)


def test_optional_tone_guidance_failure_does_not_stop_the_conversation(core):
    core.volition_v5.guidance = Mock(side_effect=RuntimeError('synthetic optional failure'))
    core._llm.generate.return_value = FACT
    response = core.process_message('u', core.start_conversation('u'), QUESTION)
    assert response.is_valid and response.content == FACT


def test_explicit_learned_style_keeps_priority_over_transient_tone_guidance(core):
    from allma_model.core.architecture.identity_state import IdentityState
    cid = core.start_conversation('u')
    control = core.process_message('u', cid, 'Preferisco risposte brevi.')
    assert control.metadata['source'] == 'personality_style_control'
    core.identity_engine_v5.compute_state = Mock(return_value=IdentityState(under_duress=True))
    core.volition_v5.guidance = Mock(side_effect=AssertionError('Learned preferences own the style'))
    core._llm.generate.return_value = FACT
    response = core.process_message('u', cid, QUESTION)
    assert response.is_valid and response.content == FACT
    core.volition_v5.guidance.assert_not_called()
