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


def test_general_answer_streams_before_model_finishes_and_is_not_duplicated(core):
    conversation = core.start_conversation('u')
    events = []
    def generate(**kwargs):
        kwargs['callback']('Un pensiero.</think>')
        kwargs['callback']('La bicicletta si muove grazie ai pedali. ')
        assert any(e['type'] == 'answer' for e in events), 'Prima frase disponibile durante la generazione'
        kwargs['callback']('Le ruote permettono di avanzare.')
        return 'La bicicletta si muove grazie ai pedali. Le ruote permettono di avanzare.'
    core._llm = Mock()
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta', stream_callback=events.append)
    assert ''.join(e['content'] for e in events if e['type'] == 'answer') == result.content
    assert result.metadata['generation']['delivery_mode'] == 'progressive'
    assert result.metadata['generation']['first_answer_ms'] is not None
    assert core.conversational_memory.messages[-1].metadata['generation'] == result.metadata['generation']


def test_explicit_delivery_preference_uses_no_model_and_changes_next_turn(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    response = core.process_message('u', conversation, 'Scrivimi tutto insieme')
    core._llm.generate.assert_not_called()
    assert response.metadata['generation']['llm_used'] is False
    events = []
    def generate(**kwargs):
        kwargs['callback']('Pensiero.</think>La bicicletta usa i pedali. ')
        assert not any(e['type'] == 'answer' for e in events)
        return 'La bicicletta usa i pedali.'
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta', stream_callback=events.append)
    assert [e['content'] for e in events if e['type'] == 'answer'] == [result.content]
    assert result.metadata['generation']['delivery_mode'] == 'complete'


def test_personal_requests_and_hallucinated_names_remain_guarded(core):
    conversation = core.start_conversation('u')
    events = []
    def generate(**kwargs):
        kwargs['callback']('Pensiero.</think>Mi chiamo Sophia. ')
        assert not any(e['type'] == 'answer' for e in events)
        return 'Mi chiamo Sophia.'
    core._llm = Mock()
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta', stream_callback=events.append)
    assert result.is_valid is False
    assert all('Sophia' not in e['content'] for e in events if e['type'] == 'answer')
    assert 'ALLMA' in result.content


def test_hot_device_reduces_actual_budget_and_reserves_answer_tokens(core):
    from types import SimpleNamespace
    conversation = core.start_conversation('u')
    core.temperature_monitor.get_temperatures = lambda: {'cpu': 72, 'battery': 42}
    core.system_monitor.get_metabolic_state = lambda: SimpleNamespace(is_tired=False)
    core._llm = Mock()
    core._llm.generate.return_value = 'Le ruote permettono di avanzare.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta')
    options = core._llm.generate.call_args.kwargs
    assert options['max_tokens'] in {192, 384}
    assert options['thought_budget'] <= options['max_tokens'] // 3


def test_emotional_history_is_owned_by_each_core(core):
    from allma_model.emotional_system.emotional_milestones import get_emotional_milestones
    shared = get_emotional_milestones()
    shared.record_emotion('u', 'sadness', .9, 'A global test event')
    assert core.emotional_milestones is not shared
    assert core.emotional_milestones.emotional_history.get('u', []) == []


def test_post_generation_reflection_cannot_add_an_unverified_personal_claim(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'La bicicletta usa i pedali.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.emotional_milestones.should_reflect = Mock(return_value=(True, 'spontaneous'))
    core.emotional_milestones.generate_reflection = Mock(return_value='Ho vissuto questa esperienza a Roma.')
    response = core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta')
    assert response.content == 'La bicicletta usa i pedali.'


def test_duplicate_feedback_keeps_reference_without_counting_twice_or_using_model(core):
    conversation = core.start_conversation('u')
    question = 'Quanto fa 31 per 3?'
    core._llm = Mock()
    core._llm.generate.return_value = '93.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    response = core.process_message('u', conversation, question)
    key = response.metadata['recall_key']
    core.process_message('u', conversation, 'Risposta corretta')
    acknowledgement = core.process_message('u', conversation, 'Confermo la risposta')
    assert acknowledgement.metadata['source'] == 'learning_feedback'
    assert core._llm.generate.call_count == 1
    assert len(core.answer_recall.records[key]['confirmations']) == 1
    correction = core.process_message('u', conversation, 'Risposta sbagliata')
    assert correction.metadata['source'] == 'learning_feedback'
    assert core.answer_recall.records[key]['rejected'] is True
    assert core._llm.generate.call_count == 1


def test_repeated_confirmation_does_not_inflate_cognitive_tracking(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'La ruota consente alla bicicletta di avanzare.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta')
    core.process_message('u', conversation, 'Risposta corretta')
    after = core.cognitive_tracker.get_cognitive_state()
    core.process_message('u', conversation, 'Risposta corretta')
    assert core.cognitive_tracker.get_cognitive_state() == after
    core.process_message('u', conversation, 'Risposta sbagliata')
    assert core.cognitive_tracker.successful_interactions == 0
    assert core._llm.generate.call_count == 1


def test_optional_tracking_failure_does_not_undo_answer_feedback(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'La ruota consente alla bicicletta di avanzare.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta')
    core.cognitive_tracker.record_feedback = Mock(side_effect=OSError('disk failure'))
    result = core.process_message('u', conversation, 'Risposta corretta')
    assert result.is_valid
    assert result.metadata['source'] == 'learning_feedback'
    assert core._llm.generate.call_count == 1


def test_orchestrator_is_used_in_real_core_prompt_and_reports_observation(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'Definisci obiettivi e vincoli, poi organizza le attività.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('u', conversation, 'Pianifica il progetto della bicicletta')
    assert 'non inventare tempi' in core._llm.generate.call_args.kwargs['prompt']
    outcomes = result.metadata['modules']['outcomes']
    assert outcomes['planning']['output_role'] == 'guidance'
    assert outcomes['language_processing']['output_role'] == 'observational'
    assert result.metadata['knowledge_verified'] is False


def test_reviewed_dream_context_is_used_then_removed_from_prompt_and_history(core):
    conversation = core.start_conversation('u')
    manager = core.dream_manager
    manager.current_user_id = 'u'
    # The scheduler is idle; direct helper respects its normal cancellation contract.
    manager._cancel_event.is_set = lambda: False
    manager._consolidate_insights(['La bicicletta verde potrebbe rendere piacevole il viaggio.'])
    row = core.get_dream_review_state('u')['items'][0]
    core._llm = Mock()
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core._llm.generate.return_value = 'Una bicicletta può essere utile per viaggiare.'
    first = core.process_message('u', conversation, 'Spiega i vantaggi della bicicletta')
    assert first.metadata['dream_review_ids'] == []
    assert row['original_text'] not in core._llm.generate.call_args.kwargs['prompt']
    core.review_dream_hypothesis('u', row['id'], 'confirm')
    core._llm.generate.return_value = 'La bicicletta verde rende piacevole il viaggio secondo la tua valutazione.'
    second = core.process_message('u', conversation, 'Spiega i vantaggi della bicicletta')
    assert second.metadata['dream_review_ids'] == [row['id']]
    assert 'non fatti verificati indipendentemente' in core._llm.generate.call_args.kwargs['prompt']
    assert row['original_text'] in core._llm.generate.call_args.kwargs['prompt']
    assert second.metadata['knowledge_verified'] is False
    core.review_dream_hypothesis('u', row['id'], 'reject', expected_revision=1)
    core.process_message('u', conversation, 'Spiega i vantaggi della bicicletta')
    prompt = core._llm.generate.call_args.kwargs['prompt']
    assert row['original_text'] not in prompt
    assert second.content not in prompt


def test_dream_review_cannot_change_context_during_active_generation(core):
    core._user_active.set()
    with pytest.raises(ValueError, match='Attendi'):
        core.review_dream_hypothesis('u', 'id', 'confirm')
    core._user_active.clear()


def test_retraction_invalidates_previously_confirmed_answer_recall(core):
    conversation = core.start_conversation('u')
    manager = core.dream_manager
    manager.current_user_id = 'u'
    manager._cancel_event.is_set = lambda: False
    manager._consolidate_insights(['La bicicletta può rendere il viaggio più piacevole.'])
    identifier = core.get_dream_review_state('u')['items'][0]['id']
    core.review_dream_hypothesis('u', identifier, 'confirm')
    core._llm = Mock()
    core._llm.generate.return_value = 'La bicicletta può aiutare durante il viaggio.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    question = 'Spiega i vantaggi della bicicletta'
    core.process_message('u', conversation, question)
    core.process_message('u', conversation, 'Risposta corretta')
    core.process_message('u', conversation, question)
    core.process_message('u', conversation, 'Risposta corretta')
    recalled = core.process_message('u', conversation, question)
    assert recalled.metadata['source'] == 'confirmed_answer_recall'
    calls = core._llm.generate.call_count
    core.review_dream_hypothesis('u', identifier, 'reject', expected_revision=1)
    result = core.process_message('u', conversation, question)
    assert core._llm.generate.call_count == calls + 1
    assert result.metadata['source'] == 'model_generated'
    assert result.metadata['dream_review_ids'] == []


def test_missing_review_archive_does_not_block_main_chat_or_use_reviewed_history(core):
    core.dream_manager.review_store = None
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'Le ruote aiutano la bicicletta ad avanzare.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    response = core.process_message('u', conversation, 'Spiega il funzionamento della bicicletta')
    assert response.is_valid
    assert response.metadata['dream_review_ids'] == []
    with pytest.raises(OSError):
        core.get_dream_review_state('u')


def test_repetition_from_backend_is_invalid_and_never_learned(core):
    conversation=core.start_conversation('u')
    raw='Una frase valida. '+ 'ghiandole '*12
    core._llm=Mock()
    core._llm.generate.return_value=raw
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.incremental_learner.learn_from_interaction=Mock()
    response=core.process_message('u',conversation,'Spiega come funziona la respirazione')
    assert not response.is_valid
    assert response.metadata['generation']['status']=='repetition'
    assert 'ripetitiva' in response.content and 'ghiandole' not in response.content
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert core.answer_recall.records=={}
    assert core.conversational_memory.messages[-1].metadata['is_valid'] is False


def test_native_early_stop_remains_invalid_even_if_safe_prefix_is_returned(core):
    conversation=core.start_conversation('u')
    core._llm=Mock();core._llm.generate.return_value='Una frase breve.'
    core._llm.get_generation_meta.return_value={'finish_reason':'repetition'}
    response=core.process_message('u',conversation,'Spiega una cosa semplice')
    assert not response.is_valid and response.metadata['generation']['status']=='repetition'


def test_legacy_repetitive_assistant_is_excluded_from_future_prompt(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    conversation=core.start_conversation('u')
    core.conversational_memory.store_message(conversation,'ghiandole '*12,
        {'identity_policy':POLICY_VERSION,'is_valid':True},role='assistant',user_id='u')
    core._llm=Mock();core._llm.generate.return_value='Nuova risposta.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.process_message('u',conversation,'Spiega la respirazione dei pesci')
    assert 'ghiandole' not in core._llm.generate.call_args.kwargs['prompt']


def test_emotion_evidence_reaches_prompt_metadata_memory_without_extra_inference(core):
    conversation = core.start_conversation('emotion-user')
    core._llm = Mock()
    core._llm.generate.return_value = 'Possiamo affrontare questa situazione con calma.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('emotion-user', conversation, 'Sono felice ma anche preoccupata per il nuovo lavoro')
    assert result.is_valid
    core._llm.generate.assert_called_once()
    prompt = core._llm.generate.call_args.kwargs['prompt']
    assert 'Indizi emotivi dell’utente' in prompt
    assert 'anxiety' in prompt and 'ambivalenza' in prompt
    analysis = result.metadata['emotion_analysis']
    assert set(analysis['nuances']) == {'joy', 'anxiety'}
    assert analysis['context']['user_id'] == 'emotion-user'
    assert result.metadata['emotion_confidence'] == analysis['confidence']
    assert result.confidence == 0 # No measured probability of answer correctness.
    assert core.emotional_core.get_user_emotional_state('emotion-user').nuances == analysis['nuances']
    assert core.conversational_memory.messages[-1].metadata['emotion_analysis'] == analysis


def test_borrowed_user_experience_is_rejected_not_learned(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'Sono felice per il nuovo lavoro e preoccupata per il primo giorno.'
    core._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
    core.incremental_learner.learn_from_interaction = Mock()
    response = core.process_message('u',conversation,'Sono felice per il nuovo lavoro e preoccupata per il primo giorno.')
    assert not response.is_valid
    assert response.metadata['generation']['status'] == 'subject_mismatch'
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records
    core._llm.generate.assert_called_once()


def test_invalid_output_shape_is_not_silently_truncated(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'No. Una spiegazione non richiesta.'
    core._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
    response = core.process_message('u',conversation,'Tutti i gatti sono mammiferi. Vale anche il contrario? Rispondi soltanto sì o no.')
    assert not response.is_valid
    assert response.metadata['generation']['status'] == 'format_mismatch'
    assert core._llm.generate.call_args.kwargs['answer_contract'] == 'yes_no_it'
    assert response.content != 'No'


def test_cross_turn_duplicate_is_not_streamed_or_learned(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    conversation=core.start_conversation('u')
    old='Ciao! Sto bene, grazie. Il tempo è 20:13, in carica. Come ti senti?'
    core.conversational_memory.store_message(conversation,'Bene, tu?',{'source':'user_statement'},'user','u')
    core.conversational_memory.store_message(conversation,old,
        {'identity_policy':POLICY_VERSION,'is_valid':True},'assistant','u')
    core._llm=Mock()
    def generate(**kwargs):
        kwargs['callback']('</think>'+old)
        return old
    core._llm.generate.side_effect=generate
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.incremental_learner.learn_from_interaction=Mock()
    events=[]
    response=core.process_message('u',conversation,'Ti ho già risposto, sto bene',stream_callback=events.append)
    assert not response.is_valid
    assert response.metadata['generation']['status']=='dialogue_repetition'
    assert old not in ''.join(e['content'] for e in events if e['type']=='answer')
    assert 'L’utente segnala una ripetizione' in core._llm.generate.call_args.kwargs['prompt']
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records
    core._llm.generate.assert_called_once()
    assert not core.conversational_memory.messages[-1].metadata['is_valid']


def test_rephrased_checkin_after_user_answer_is_validated_before_stream(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    conversation=core.start_conversation('u')
    core.conversational_memory.store_message(conversation,'Ciao',{'source':'user_statement'},'user','u')
    core.conversational_memory.store_message(conversation,'Ciao! Come stai?',
        {'identity_policy':POLICY_VERSION,'is_valid':True},'assistant','u')
    core._llm=Mock()
    def generate(**kwargs):
        kwargs['callback']('</think>Sto bene, grazie. Come ti va?')
        return 'Sto bene, grazie. Come ti va?'
    core._llm.generate.side_effect=generate
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    events=[]
    result=core.process_message('u',conversation,'Bene, tu?',stream_callback=events.append)
    assert not result.is_valid
    assert result.metadata['generation']['status']=='dialogue_repetition'
    assert result.metadata['generation']['delivery_reason']=='answered_checkin_validation'
    assert 'Come ti va?' not in ''.join(e['content'] for e in events if e['type']=='answer')
    assert 'Non reiterare domande sul benessere' in core._llm.generate.call_args.kwargs['prompt']
    core._llm.generate.assert_called_once()


def test_sentence_contract_and_model_sampling_are_applied_before_display(core):
    conversation=core.start_conversation('u')
    core._llm=Mock();core._llm.model_path='/models/qwen3-1.7b-q8_0.gguf'
    def generate(**kwargs):
        kwargs['callback']('</think>Una sola frase.')
        return 'Una sola frase.'
    core._llm.generate.side_effect=generate
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.incremental_learner.learn_from_interaction=Mock()
    events=[]
    result=core.process_message('u',conversation,'Spiega un cambiamento in due frasi.',stream_callback=events.append)
    assert not result.is_valid
    assert result.metadata['generation']['status']=='format_mismatch'
    assert 'Una sola frase.' not in ''.join(e['content'] for e in events if e['type']=='answer')
    options=core._llm.generate.call_args.kwargs
    assert options['temperature']==.6 and options['top_p']==.95
    assert options['top_k']==20 and options['min_p']==0.
    assert options['thought_budget']>0
    assert 'Non consumare il ragionamento' in options['prompt']
    core.incremental_learner.learn_from_interaction.assert_not_called()
    core._llm.generate.assert_called_once()


def test_emotional_reflection_cannot_break_requested_sentence_count(core):
    conversation=core.start_conversation('u')
    core._llm=Mock();core._llm.generate.return_value='Un passo alla volta. Possiamo parlarne.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.emotional_milestones.should_reflect=Mock(return_value=(True,'milestone'))
    core.emotional_milestones.generate_reflection=Mock(return_value='Una riflessione aggiuntiva.')
    result=core.process_message('u',conversation,'Sono preoccupata, rispondimi in due frasi.')
    assert result.is_valid and result.content=='Un passo alla volta. Possiamo parlarne.'
    core.emotional_milestones.generate_reflection.assert_not_called()


def test_model_switch_preserves_state_and_relinks_all_consumers(core,tmp_path,monkeypatch):
    from types import SimpleNamespace
    import json
    models=tmp_path/'models';models.mkdir()
    for name in ('old.gguf','new.gguf'):
        (models/name).write_bytes(b'GGUF')
    core.models_dir=str(models)
    def engine(name):
        return SimpleNamespace(model_path=str(models/name),llm=object(),close=Mock(),
            binding=SimpleNamespace(architecture='test',reasoning=False))
    old=engine('old.gguf');new=engine('new.gguf')
    core._llm=old;core._llm_ready=True;core._owns_llm=True
    memory=core.conversational_memory
    conversation=core.start_conversation('u')
    memory.store_message(conversation,'Mi chiamo Ada',{'source':'user_statement'},'user','u')
    monkeypatch.setattr('allma_model.llm.mobile_gemma_wrapper.MobileGemmaWrapper',lambda *a,**kw:new)
    result=core.switch_model('new.gguf')
    assert result['changed']
    assert core.conversational_memory is memory and memory.messages[-1].content=='Mi chiamo Ada'
    assert core.reasoning_engine.llm is new and core.dream_manager.llm_wrapper is new and core.dream_manager.tot.llm is new
    assert core._llm is new and not core._user_active.is_set()
    old.close.assert_called_once()
    assert json.loads((tmp_path/'model_binding.json').read_text())['model_name']=='new.gguf'


def test_failed_model_switch_restores_old_motor_without_touching_memory(core,tmp_path,monkeypatch):
    from types import SimpleNamespace
    models=tmp_path/'models';models.mkdir()
    for name in ('old.gguf','bad.gguf'):
        (models/name).write_bytes(b'GGUF')
    core.models_dir=str(models)
    old=SimpleNamespace(model_path=str(models/'old.gguf'),llm=object(),close=Mock(),
                        binding=SimpleNamespace(architecture='test',reasoning=False))
    restored=SimpleNamespace(model_path=old.model_path,llm=object(),close=Mock(),binding=old.binding)
    core._llm=old;core._llm_ready=True;core._owns_llm=True
    original_memory=core.conversational_memory
    def factory(*a,**kw):
        if kw['model_name']=='bad.gguf':
            raise ValueError('Unsupported native architecture')
        return restored
    monkeypatch.setattr('allma_model.llm.mobile_gemma_wrapper.MobileGemmaWrapper',factory)
    with pytest.raises(RuntimeError,match='personal state was preserved'):
        core.switch_model('bad.gguf')
    assert core._llm is restored and core._llm_ready
    assert core.conversational_memory is original_memory
    assert not (tmp_path/'model_binding.json').exists()
    assert not core._user_active.is_set() and not core._model_switching


def test_model_switch_refuses_active_or_borrowed_motor(core,tmp_path):
    core._user_active.set()
    with pytest.raises(RuntimeError,match='Wait'):
        core.switch_model('anything.gguf')
    core._user_active.clear()


def test_native_nonreasoning_model_uses_its_template_and_preserves_identity(core):
    from allma_model.llm.model_binding import ModelBinding
    class Engine:
        def __init__(self):
            self.binding=ModelBinding({'general.architecture':'llama',
                'tokenizer.chat_template':'{% for m in messages %}[{{m.role}}]{{m.content}}{% endfor %}[assistant]'},context_size=2048)
            self.options=None
        def prepare_chat(self,messages,budget):
            return self.binding.prepare(messages,lambda b:b.split(),budget)
        def generate(self,**kwargs):
            self.options=kwargs
            kwargs['callback']('Possiamo iniziare con una domanda semplice. ')
            return 'Possiamo iniziare con una domanda semplice.'
        def get_generation_meta(self,request_id):
            return {'finish_reason':'stop'}
    engine=Engine();core._llm=engine
    conversation=core.start_conversation('u');events=[]
    response=core.process_message('u',conversation,'Parliamo di un progetto',stream_callback=events.append)
    assert response.is_valid
    assert engine.options['native_prompt'] is True and engine.options['thought_budget'] is None
    assert '<|im_start|>' not in engine.options['prompt'] and '<think>' not in engine.options['prompt']
    assert 'Il tuo nome è ALLMA' in engine.options['prompt']
    assert response.metadata['generation']['native_architecture']=='llama'
    assert any(e['type']=='answer' for e in events)


def test_borrowed_model_and_shutdown_do_not_release_shared_engine(core,tmp_path):
    from types import SimpleNamespace
    models=tmp_path/'models';models.mkdir();(models/'new.gguf').write_bytes(b'GGUF')
    core.models_dir=str(models)
    shared=SimpleNamespace(model_path=str(models/'old.gguf'),llm=object(),close=Mock(),
                           binding=SimpleNamespace(architecture='test',reasoning=False))
    core._llm=shared;core._owns_llm=False;core._llm_ready=True
    with pytest.raises(RuntimeError,match='borrowed'):
        core.switch_model('new.gguf')
    core.close()
    shared.close.assert_not_called()


def test_model_probe_never_updates_personal_memory_or_learning(core):
    from types import SimpleNamespace
    from allma_model.llm.model_binding import ModelBinding
    class Engine:
        def __init__(self):
            self.binding=ModelBinding({'general.architecture':'qwen3',
                'tokenizer.chat_template':'{% for m in messages %}{{m.content}}{% endfor %}'},context_size=2048)
            self.options=None
        def prepare_chat(self,messages,budget):
            return self.binding.prepare(messages,lambda b:b.split(),budget)
        def generate(self,**options):
            self.options=options
            return 'Una risposta da valutare.'
        def get_generation_meta(self,request_id):
            return {'request_id':request_id,'finish_reason':'stop'}
    engine=Engine();core._llm=engine
    conversation=core.start_conversation('u')
    core.conversational_memory.store_message(conversation,'Ricordo personale da non usare',{'source':'user_statement'},'user','u')
    before=list(core.conversational_memory.messages)
    core.incremental_learner.learn_from_interaction=Mock()
    result=core.probe_model('Domanda nuova',max_tokens=128,thought_budget=32)
    assert result['source']=='isolated_model_probe' and result['answer']=='Una risposta da valutare.'
    assert core.conversational_memory.messages==before
    assert 'Ricordo personale' not in engine.options['prompt']
    assert engine.options['thought_budget']==32 and engine.options['native_prompt']
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core._user_active.is_set()


def test_exact_arithmetic_is_model_independent_and_does_not_learn_a_guessed_answer(core):
    conversation=core.start_conversation('u')
    core._llm=Mock()
    result=core.process_message('u',conversation,'Quanto fa 18 + 24? Rispondi solo con un numero')
    assert result.content=='42' and result.is_valid
    assert result.metadata['source']=='verified_calculation'
    assert result.metadata['knowledge_verified'] is True
    assert result.metadata['generation']['llm_used'] is False
    core._llm.generate.assert_not_called()
    bad=core.process_message('u',conversation,'Calcola 1/0')
    assert not bad.is_valid and bad.metadata['source']=='calculation_error'


def test_runtime_capabilities_and_followup_do_not_call_model(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    first = core.process_message('u', conversation, 'Cosa sai fare allma?')
    assert first.metadata['source'] == 'runtime_capabilities'
    assert first.metadata['generation']['llm_used'] is False
    assert 'pesi del modello' in first.content
    assert 'esperienze personali' in first.content
    second = core.process_message('u', conversation, 'Solo questi sai fare?')
    assert second.metadata['source'] == 'runtime_capabilities'
    assert second.content != first.content
    core._llm.generate.assert_not_called()
    assert core.conversational_memory.messages[-1].content == second.content


def test_capability_followup_is_scoped_to_current_conversation(core):
    from allma_model.utils.runtime_capabilities import capability_reply
    assert capability_reply('Solo questi sai fare?', core, []) is None
    conversation = core.start_conversation('u')
    core.process_message('u', conversation, 'Cosa sai fare?')
    other = core.start_conversation('u')
    assert capability_reply('Solo questi sai fare?', core,
                            core.conversational_memory.get_conversation_history(other)) is None


def test_runtime_capabilities_respect_disabled_components(core):
    from allma_model.utils.runtime_capabilities import capability_items, capability_reply
    core.dream_enabled = False
    assert not any('Diario Sogni' in item for item in capability_items(core))
    assert not any('modello collegato' in item for item in capability_items(core))
    core.dream_enabled = True
    assert any('Diario Sogni' in item for item in capability_items(core))
    assert capability_reply('Scrivi una storia su cosa sai fare', core, []) is None
