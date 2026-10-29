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


def prepare_proactive(core, answer='Posso offrirti un confronto, se ti va.'):
    from types import SimpleNamespace
    from datetime import timedelta
    import time
    conversation=core.start_conversation('active-user')
    core.conversational_memory.store_message(conversation,'Sono felice di aver finito il trasloco.',
        {},role='user',user_id='active-user')
    core.conversational_memory.messages[-1].timestamp=datetime.now()-timedelta(hours=8)
    core._current_user_id='active-user'; core.dream_enabled=True
    core.output_callback=Mock()
    core.system_monitor.get_metabolic_state=Mock(side_effect=lambda: SimpleNamespace(
        is_tired=False, energy_level=.9, is_charging=True, battery_temp_celsius=35.,
        is_power_save=False, is_valid=True, source='synthetic', observed_at=time.monotonic()))
    core.proactive_agency.check_initiative=Mock(return_value=SimpleNamespace(should_contact=True))
    class Engine:
        binding=SimpleNamespace(sampling=lambda: {})
        def prepare_chat(self,messages,budget,reasoning=None):
            self.messages=messages
            return SimpleNamespace(prompt='native',reasoning=False,stops=[])
        def generate(self,**kwargs):
            self.options=kwargs
            return answer
        def get_generation_meta(self,request):
            return {'finish_reason':'stop'}
    core._llm=Engine()
    core.incremental_learner.learn_from_interaction=Mock()
    return conversation


def test_operational_router_skips_unrelated_personal_retrieval(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason','total_ms':1})
    core.conversational_memory.vector_engine=Mock()
    core._llm=Mock();core._llm.generate.return_value='Un arcobaleno si forma quando la luce attraversa le gocce d’acqua.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    result=core.process_message('u',conversation,'Spiega come si forma un arcobaleno.')
    core.decision_runtime.route.assert_called_once()
    core.conversational_memory.vector_engine.search.assert_not_called()
    assert result.metadata['decision']['choice']=='reason'
    assert result.metadata['factual_status']=='not_verified'


def test_router_cannot_remove_explicit_personal_memory_request(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    core.conversational_memory.vector_engine=Mock();core.conversational_memory.vector_engine.search.return_value=[]
    core._llm=Mock();core._llm.generate.return_value='Non trovo un ricordo sufficiente per stabilirlo.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.process_message('u',conversation,'Spiega perché la mia passeggiata mi ha rilassato.')
    assert core.conversational_memory.vector_engine.search.call_args.kwargs['user_id']=='u'


def test_host_identity_fast_path_does_not_invoke_decider(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(side_effect=AssertionError('Unnecessary native decision'))
    assert core.process_message('u',conversation,'Come ti chiami?').content=='Mi chiamo ALLMA.'
    core.decision_runtime.route.assert_not_called()


def test_literal_question_navigation_skips_models_and_persists_reference(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(side_effect=AssertionError('No model for literal navigation'))
    core.conversational_memory.store_message(conversation,'Prima domanda?',{},role='user',user_id='u')
    core.conversational_memory.store_message(conversation,'Seconda domanda?',{},role='user',user_id='u')
    reply=core.process_message('u',conversation,'Cosa ti ho chiesto prima?')
    assert reply.content == 'Mi hai chiesto: «Seconda domanda?».'
    assert reply.metadata['source'] == 'conversation_question_recall'
    assert reply.metadata['generation']['llm_used'] is False
    assert core.conversational_memory.messages[-1].metadata['conversation_reference'] == reply.metadata['conversation_reference']
    core.decision_runtime.route.assert_not_called()


def test_name_meaning_describes_allma_separately_from_llm(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(side_effect=AssertionError('No model for origin identity'))
    reply=core.process_message('u',conversation,'Cosa significa ALLMA?')
    assert reply.is_valid and reply.metadata['source']=='origin_identity'
    assert 'è il mio nome' in reply.content
    assert 'separato dalla mia identità' in reply.content
    core.decision_runtime.route.assert_not_called()


def test_fabricated_source_verification_is_not_validated_or_learned(core):
    conversation=core.start_conversation('u')
    core._llm=Mock();core._llm.generate.return_value='Le informazioni sopra sono confermate da fonti storiche.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.answer_recall.observe=Mock()
    result=core.process_message('u',conversation,'Spiega la storia del Risorgimento.')
    assert not result.is_valid
    assert result.metadata['generation']['status']=='unbacked_source_claim'
    assert result.content == '' and result.metadata['delivery_state'] == 'unresolved'
    core.answer_recall.observe.assert_not_called()


def test_operational_decider_can_defer_but_not_initiate_without_host_checks(core):
    prepare_proactive(core)
    core.decision_runtime.choose=Mock(return_value={'status':'selected','choice':'defer'})
    core._llm.generate=Mock()
    assert core.check_proactive_trigger()['status']=='decision_deferred'
    core._llm.generate.assert_not_called()
    core._proactive_attempt_at.clear()
    core.proactive_agency.check_initiative.return_value.should_contact=False
    core.decision_runtime.choose.reset_mock()
    assert core.check_proactive_trigger()['status']=='not_due'
    core.decision_runtime.choose.assert_not_called()


def test_proactive_uses_active_history_native_motor_and_persisted_cooldown(core):
    conversation=prepare_proactive(core)
    result=core.check_proactive_trigger()
    assert result['status']=='delivered'
    args=core.proactive_agency.check_initiative.call_args
    assert args.args[0]=='active-user' and args.kwargs['relationship_level']==0
    event=core.output_callback.call_args.args[0]
    assert event['type']=='proactive' and event['conversation_id']==conversation
    last=core.conversational_memory.messages[-1]
    assert last.role=='assistant' and last.user_id=='active-user' and last.metadata['source']=='proactive'
    core._proactive_attempt_at.clear()
    assert core.check_proactive_trigger()['status']=='cooldown'
    core.output_callback.assert_called_once()
    core.incremental_learner.learn_from_interaction.assert_not_called()


@pytest.mark.parametrize('state',['disabled','paused','active','benchmark','dream'])
def test_proactive_never_generates_when_activity_disallows_it(core,state):
    prepare_proactive(core)
    if state=='disabled': core.dream_enabled=False
    if state=='paused': core.set_foreground(False)
    if state=='active': core._user_active.set()
    if state=='benchmark': core._benchmark_active=True
    if state=='dream': core.dream_manager.is_dreaming=True
    assert core.check_proactive_trigger()['status']=='inactive'
    core.proactive_agency.check_initiative.assert_not_called()
    core.output_callback.assert_not_called()
    if state=='dream': core.dream_manager.is_dreaming=False


def test_proactive_rejects_borrowed_experience_without_memory_or_learning(core):
    prepare_proactive(core,'Ho finito il trasloco e sono felice.')
    count=len(core.conversational_memory.messages)
    assert core.check_proactive_trigger()['status']=='rejected'
    assert len(core.conversational_memory.messages)==count
    core.output_callback.assert_not_called()
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core._user_active.is_set()


def test_proactive_is_cancelled_when_app_pauses_during_generation(core):
    prepare_proactive(core)
    count=len(core.conversational_memory.messages)
    def generate(**kwargs):
        core.set_foreground(False)
        assert kwargs['cancel_event'].is_set()
        return 'Posso offrirti un confronto.'
    core._llm.generate=generate
    assert core.check_proactive_trigger()['status']=='cancelled'
    assert len(core.conversational_memory.messages)==count
    core.output_callback.assert_not_called()
    assert not core._user_active.is_set()


def test_proactive_respects_temperature_and_uses_attributed_emotion(core):
    from types import SimpleNamespace
    import time
    prepare_proactive(core)
    core.system_monitor.get_metabolic_state=Mock(return_value=SimpleNamespace(is_tired=False,battery_temp_celsius=40,
        energy_level=.9, is_charging=True, is_power_save=False, is_valid=True, source='synthetic', observed_at=time.monotonic()))
    assert core.check_proactive_trigger()['status']=='energy_deferred'
    core.proactive_agency.check_initiative.assert_not_called()
    core.system_monitor.get_metabolic_state.return_value.battery_temp_celsius=35
    core.emotional_core.get_user_emotional_state=Mock(return_value=SimpleNamespace(primary_emotion='sadness',intensity=.7,confidence=.8))
    assert core.check_proactive_trigger()['status']=='delivered'
    core.emotional_core.get_user_emotional_state.assert_called_once_with('active-user')
    assert core.proactive_agency.check_initiative.call_args.args[2]=={'primary_emotion':'sadness','intensity':.7}


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
    assert response.content == '' and response.metadata['delivery_state'] == 'unresolved'
    assert response.metadata['turn_review']['attempts'] == 1
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
    assert result.content == '' and result.metadata['delivery_state'] == 'unresolved'


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
    assert response.content == '' and response.metadata['delivery_state'] == 'unresolved'
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
    assert not response.is_valid and response.content == ''
    assert response.metadata['delivery_state'] == 'unresolved'
    assert 'recovery' not in response.metadata
    assert response.content != core._llm.generate.return_value
    assert response.metadata['generation']['status'] == 'subject_mismatch'
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records
    assert core._llm.generate.call_count == 2


@pytest.mark.parametrize('candidate', [
    'Sono soddisfatto che tu abbia concluso il trasloco. Sono orgoglioso di aver condiviso questa fase con te.',
    'Sono soddisfatto di aver completato il trasloco e posso sentire la tua tranquillità. La sua tristezza è un momento che ti riguarda.',
])
def test_indirect_shared_experience_is_blocked_and_not_learned(core, candidate):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = candidate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.incremental_learner.learn_from_interaction = Mock()
    response = core.process_message('u', conversation, 'Mia sorella è triste, io sono sollevata dopo il trasloco.')
    assert not response.is_valid
    assert response.metadata['generation']['status'] == 'subject_mismatch'
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records
    assert core._llm.generate.call_count == 2


@pytest.mark.parametrize('enabled,synthetic', [(False,True),(True,False),(True,True)])
def test_candidate_capture_is_transient_and_only_for_synthetic_core(core, enabled, synthetic):
    user = 'BENCHMARK_synthetic' if synthetic else 'real-user'
    conversation = core.start_conversation(user)
    candidate = 'Sono soddisfatto di aver completato il trasloco e sento la tua tranquillità.'
    core._llm = Mock()
    core._llm.generate.return_value = candidate
    core._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
    core._capture_synthetic_candidates = enabled
    response = core.process_message(user,conversation,'Sono sollevata di aver finito il trasloco.',
        context={'disable_answer_recall':True,'benchmark_seed':20261012})
    assert not response.is_valid
    diagnostic = getattr(core,'_synthetic_candidate',None)
    if enabled and synthetic:
        assert diagnostic['answer_candidate'] == candidate
        assert diagnostic['before_pipeline'] == candidate
        assert not diagnostic['pipeline_changed_answer']
        assert diagnostic['checks']['subject_mismatch'] is True
        assert diagnostic['sentences'][0]['subject_mismatch'] is True
    else:
        assert diagnostic is None
    assert 'answer_candidate' not in str(response.metadata)
    assert all(candidate not in m.content and 'answer_candidate' not in str(m.metadata)
               for m in core.conversational_memory.messages if m.role=='assistant')


def test_mixed_emotion_recovery_never_learns_rejected_model_answer(core):
    conversation = core.start_conversation('recovery-user')
    core._llm = Mock()
    core._llm.generate.return_value = 'Sono felice per il nuovo lavoro e preoccupata per domani.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.incremental_learner.learn_from_interaction = Mock()
    events = []
    result = core.process_message('recovery-user', conversation,
        'Sono felice per il nuovo lavoro e preoccupata per domani. Rispondimi in due frasi.',
        stream_callback=events.append)
    assert not result.is_valid and result.content == ''
    assert result.metadata['delivery_state'] == 'unresolved'
    assert 'recovery' not in result.metadata
    assert result.metadata['generation']['status'] == 'subject_mismatch'
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records
    assert core._llm.generate.call_count == 2
    answers = ''.join(e['content'] for e in events if e['type'] == 'answer')
    assert answers == result.content
    assert core.conversational_memory.messages[-1].content == result.content
    assert core.conversational_memory.messages[-1].metadata['source'] == result.metadata['source']


def test_recovery_does_not_append_new_support_to_an_already_streamed_answer(core):
    conversation = core.start_conversation('partial-user')
    events = []
    def generate(**kwargs):
        kwargs['callback']('Ragiono.</think>')
        kwargs['callback']('Puoi vivere emozioni diverse insieme. ')
        kwargs['callback']('Sono felice per il lavoro e preoccupata per domani.')
        return 'Puoi vivere emozioni diverse insieme. Sono felice per il lavoro e preoccupata per domani.'
    core._llm = Mock()
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('partial-user', conversation,
        'Sono felice per il lavoro e preoccupata per domani.', stream_callback=events.append)
    assert not result.is_valid and 'recovery' not in result.metadata
    assert all('Hai descritto' not in e.get('content', '') for e in events)


@pytest.mark.parametrize('message,answer', [
    ('Sono orgogliosa del risultato ma triste per la partenza di un amico.',
     'Puoi essere orgogliosa del risultato e sentire la mancanza del tuo amico.'),
    ('Mia sorella è triste, io sono sollevata dopo il trasloco.',
     'Tu ti senti sollevata dopo il trasloco, mentre tua sorella è triste.'),
])
def test_support_prompt_addresses_user_and_preserves_valid_attribution(core, message, answer):
    conversation = core.start_conversation('support-user')
    core._llm = Mock()
    core._llm.generate.return_value = answer
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    response = core.process_message('support-user', conversation, message)
    assert response.is_valid and response.content == answer
    core._llm.generate.assert_called_once()
    prompt = core._llm.generate.call_args.kwargs['prompt']
    system = prompt.split('<|im_end|>', 1)[0]
    assert 'senza riscriverlo o continuarlo come se fossi lui' in system
    assert 'tuoi sentimenti o partecipazioni' in system
    assert 'distinguendo quelle altrui o negate' in system
    assert system.count('Supporto:') == 1
    assert system.index('Supporto:') < system.index('CONTEXT:')


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
    assert core._llm.generate.call_count == 2
    assert response.metadata['turn_review']['attempts'] == 2
    assert not core.conversational_memory.messages[-1].metadata['is_valid']


def test_rephrased_checkin_after_user_answer_is_validated_before_stream(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    conversation=core.start_conversation('u')
    core.conversational_memory.store_message(conversation,'Ciao',{'source':'user_statement'},'user','u')
    core.conversational_memory.store_message(conversation,'Ciao! Come stai?',
        {'identity_policy':POLICY_VERSION,'is_valid':True},'assistant','u')
    core._llm=Mock()
    def generate(**kwargs):
        if kwargs.get('callback'):
            kwargs['callback']('</think>Sto bene, grazie. Come ti va?')
        return 'Sto bene, grazie. Come ti va?'
    core._llm.generate.side_effect=generate
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    events=[]
    result=core.process_message('u',conversation,'Sto bene, grazie.',stream_callback=events.append)
    assert not result.is_valid
    assert result.metadata['generation']['status']=='subject_mismatch'
    assert result.metadata['generation']['delivery_reason']=='answered_checkin_validation'
    assert 'Come ti va?' not in ''.join(e['content'] for e in events if e['type']=='answer')
    assert 'Non reiterare domande sul benessere' in core._llm.generate.call_args.kwargs['prompt']
    assert core._llm.generate.call_count == 2


def test_self_description_dialogue_and_clarification_need_no_model(core):
    conversation = core.start_conversation('dialogue-user')
    core._llm = Mock()
    core._llm.generate.side_effect = AssertionError('Runtime description must not invoke the model')
    core.incremental_learner.learn_from_interaction = Mock()
    for message in ['Ciao', 'Bene, come stai tu?',
                    'Non sei una macchina, hai delle emozioni', 'Cosa intendi',
                    'Non hai emozioni?', 'Non hai emozioni?']:
        events = []
        result = core.process_message('dialogue-user', conversation, message, stream_callback=events.append)
        assert result.is_valid and result.metadata['generation']['llm_used'] is False
        assert 'Riprova' not in result.content and 'Sono un modello' not in result.content
        assert result.content == ''.join(e['content'] for e in events if e['type'] == 'answer')
        assert result.content == core.conversational_memory.messages[-1].content
    core._llm.generate.assert_not_called()
    core.incremental_learner.learn_from_interaction.assert_not_called()


def test_identitary_notice_is_not_reported_as_completed_model_answer(core):
    conversation = core.start_conversation('guard-user')
    core._llm = Mock()
    core._llm.generate.return_value = 'Mi piace la montagna, ho sempre amato quei luoghi.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('guard-user', conversation, 'Parlami delle tue esperienze personali')
    assert not result.is_valid
    assert result.metadata['source'] == 'model_generated'
    assert result.content == '' and result.metadata['delivery_state'] == 'unresolved'
    assert result.metadata['generation']['status'] == 'unsupported_personal_claim'
    assert result.metadata['output_guard']['reason'] == 'unsupported_personal_claim'


def test_answered_checkin_does_not_disable_streaming_for_new_topic(core):
    core.process_message('flow-user', core.start_conversation('flow-user'), 'Ciao')
    conversation = core.conversational_memory.messages[-1].conversation_id
    core.process_message('flow-user', conversation, 'Bene, come stai tu?')
    events = []
    core._llm = Mock()
    def generate(**kwargs):
        kwargs['callback']('Ragiono.</think>La musica può avere ritmi diversi. ')
        assert any(e['type'] == 'answer' for e in events)
        kwargs['callback']('Il ritmo organizza i suoni nel tempo.')
        return 'La musica può avere ritmi diversi. Il ritmo organizza i suoni nel tempo.'
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    result = core.process_message('flow-user', conversation, 'Spiegami il ritmo musicale', stream_callback=events.append)
    assert result.is_valid and result.metadata['generation']['delivery_mode'] == 'progressive'
    assert result.content == ''.join(e['content'] for e in events if e['type'] == 'answer')


def test_emotion_meanings_and_growth_reach_detector_and_generation(core):
    conversation = core.start_conversation('growth-user')
    core._llm = Mock()
    core._llm.generate.return_value = 'Posso ascoltare quello che vuoi raccontarmi.'
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    declared = core.process_message('growth-user', conversation, 'Per me "spenta" significa tristezza.')
    assert declared.metadata['source'] == 'personal_emotion_meaning'
    assert declared.metadata['emotional_growth']['status'] == 'meaning_declared'
    core._llm.generate.assert_not_called()
    first = core.process_message('growth-user', conversation, 'Mi sento spenta al lavoro.')
    assert first.metadata['emotion_analysis']['primary_emotion'] == 'sadness'
    assert first.metadata['emotional_growth']['status'] == 'suspended'
    core._llm.generate.return_value = 'Puoi raccontarmi cosa è successo durante il viaggio.'
    second = core.process_message('growth-user', conversation, 'Mi sento spenta dopo il viaggio.')
    assert second.metadata['emotional_growth']['status'] == 'integrated'
    assert 'tendenza al sostegno' in core._llm.generate.call_args.kwargs['prompt']
    own = core.coalescence_processor.get_current_personality_state(user_id='growth-user')
    assert own['emotional_state']['primary'].value == 'empathy'
    assert second.metadata['emotion_analysis']['primary_emotion'] == 'sadness'
    recalled = core.process_message('growth-user', conversation, 'Cosa significa spenta per me?')
    assert recalled.metadata['source'] == 'personal_emotion_meaning_recall'
    assert 'tristezza' in recalled.content
    other = core.process_message('other-user', core.start_conversation('other-user'), 'Cosa significa spenta per me?')
    assert other.metadata['source'] == 'no_evidence'


def test_growth_not_applied_if_user_message_cannot_be_saved(core):
    conversation = core.start_conversation('growth-user')
    core.coalescence_processor.observe_interaction = Mock()
    core.conversational_memory.store_message = Mock(side_effect=OSError('disk full'))
    with pytest.raises(OSError):
        core.process_message('growth-user', conversation, 'Per me spenta significa tristezza.')
    core.coalescence_processor.observe_interaction.assert_not_called()


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
    assert core._llm.generate.call_count == 2


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


@pytest.mark.parametrize('strategy',['minimal','role_map'])
@pytest.mark.parametrize('mode',['bounded','natural'])
def test_model_probe_never_updates_personal_memory_or_learning(core,strategy,mode):
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
            if options.get('callback'):
                options['callback']('</thi')
                options['callback']('nk>')
            return 'Una risposta da valutare.'
        def get_generation_meta(self,request_id):
            return {'request_id':request_id,'finish_reason':'stop'}
    engine=Engine();core._llm=engine
    conversation=core.start_conversation('u')
    core.conversational_memory.store_message(conversation,'Ricordo personale da non usare',{'source':'user_statement'},'user','u')
    before=list(core.conversational_memory.messages)
    core.incremental_learner.learn_from_interaction=Mock()
    result=core.probe_model('Domanda nuova',max_tokens=128,thought_budget=32,support_strategy=strategy,reasoning_mode=mode)
    assert result['source']=='isolated_model_probe' and result['answer']=='Una risposta da valutare.'
    assert core.conversational_memory.messages==before
    assert 'Ricordo personale' not in engine.options['prompt']
    assert ('Mappa dei ruoli' in engine.options['prompt']) == (strategy=='role_map')
    assert engine.options['thought_budget']==(32 if mode=='bounded' else None) and engine.options['native_prompt']
    if mode=='natural':
        assert result['generation']['reasoning_close_observed']
        assert not result['generation']['answer_budget_reserved']
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


def test_general_query_does_not_inject_device_sensors(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'Una spiegazione breve.'
    time_tool, battery_tool = Mock(return_value='ORA_PRIVATA'), Mock(return_value='BATTERIA_PRIVATA')
    core.ALLOWED_TOOLS = {'SYSTEM_TIME':time_tool,'READ_BATTERY':battery_tool}
    core.process_message('u',conversation,'Spiega come si forma un arcobaleno')
    time_tool.assert_not_called()
    battery_tool.assert_not_called()
    prompt=core._llm.generate.call_args.kwargs['prompt']
    assert 'ORA_PRIVATA' not in prompt and 'BATTERIA_PRIVATA' not in prompt
    assert 'unico dato autobiografico' in prompt


def test_controlled_reasoning_sweep_can_use_128_tokens_without_changing_normal_policy(core):
    conversation = core.start_conversation('u')
    core._llm = Mock()
    core._llm.generate.return_value = 'no'
    core.system_monitor.get_metabolic_state = Mock(return_value=type('State',(),{'is_tired':False})())
    core.temperature_monitor.get_temperatures = Mock(return_value={'cpu':50,'battery':40})
    core.process_message('u',conversation,'Tutti i velari sono blu. Nessun blu è pesante. Un velario è pesante?',
        context={'disable_answer_recall':True,'benchmark_seed':3,'benchmark_reasoning_sweep':True,
                 'benchmark_max_tokens':272,'benchmark_thought_budget':128})
    options=core._llm.generate.call_args.kwargs
    assert options['max_tokens'] == 272 and options['thought_budget'] == 128



def test_proactive_reviewed_dream_is_scoped_and_invalidated_after_revision(core):
    from types import SimpleNamespace
    conversation = prepare_proactive(core)
    store = core.dream_manager.review_store
    store.ingest([{'user_id': 'active-user', 'text': 'Preferisco passeggiare.',
                   'timestamp': datetime.now().isoformat()}])
    record = store.list('active-user')[0]
    store.review('active-user', record['id'], 'confirm')
    record = store.list('active-user')[0]
    core.proactive_agency.check_initiative.return_value = SimpleNamespace(should_contact=True,
        context={'insight': record['text'], 'dream_record': {'id': record['id'], 'revision': record['revision']}})
    assert core.check_proactive_trigger()['status'] == 'delivered'
    assert record['text'] in core._llm.messages[-1]['content']
    saved = core.conversational_memory.messages[-1]
    assert saved.metadata['dream_review_ids'] == [record['id']]
    assert core._reviewed_history_eligible(saved, store.version('active-user'))
    store.review('active-user', record['id'], 'reject', expected_revision=record['revision'])
    assert not core._reviewed_history_eligible(saved, store.version('active-user'))


def test_proactive_cancels_when_user_revises_dream_during_generation(core):
    from types import SimpleNamespace
    prepare_proactive(core)
    store = core.dream_manager.review_store
    store.ingest([{'user_id': 'active-user', 'text': 'Una ipotesi.', 'timestamp': datetime.now().isoformat()}])
    record = store.list('active-user')[0]
    store.review('active-user', record['id'], 'confirm')
    record = store.list('active-user')[0]
    core.proactive_agency.check_initiative.return_value = SimpleNamespace(should_contact=True,
        context={'insight': record['text']})
    def generate(**kwargs):
        store.review('active-user', record['id'], 'reject', expected_revision=record['revision'])
        return 'Posso offrirti un confronto.'
    core._llm.generate = generate
    assert core.check_proactive_trigger()['status'] == 'cancelled'
    core.output_callback.assert_not_called()


def test_repeated_model_switches_close_previous_motor_and_keep_state(core, tmp_path, monkeypatch):
    """Alternating architectures must not retain native motors or unlink consumers."""
    from types import SimpleNamespace
    import json
    models = tmp_path/'models'; models.mkdir()
    for name in ('qwen3.gguf', 'qwen35.gguf'):
        (models/name).write_bytes(b'GGUF')
    core.models_dir = str(models)
    live = []
    created = []
    def factory(*args, **kwargs):
        assert not live, 'Two native motors loaded at once'
        name = kwargs['model_name']
        engine = SimpleNamespace(model_path=str(models/name), llm=object(),
            binding=SimpleNamespace(architecture='qwen35' if '35' in name else 'qwen3', reasoning=True))
        engine.close = Mock(side_effect=lambda: live.remove(engine))
        live.append(engine); created.append(engine)
        return engine
    initial = factory(model_name='qwen35.gguf')
    core._llm = initial; core._llm_ready = True; core._owns_llm = True
    memory, identity, personality = core.conversational_memory, core.identity_engine_v5, core.personality
    conversation = core.start_conversation('switch-test')
    memory.store_message(conversation, 'Mi chiamo Ada', {}, 'user', 'switch-test')
    monkeypatch.setattr('allma_model.llm.mobile_gemma_wrapper.MobileGemmaWrapper', factory)
    for i in range(24):
        name = 'qwen3.gguf' if i % 2 == 0 else 'qwen35.gguf'
        result = core.switch_model(name, reasoning=True)
        assert result['changed'] and len(live) == 1
        current = live[0]
        assert core._llm is current and core.reasoning_engine.llm is current
        assert core.dream_manager.llm_wrapper is current and core.dream_manager.tot.llm is current
        assert core.conversational_memory is memory and core.identity_engine_v5 is identity
        assert core.personality is personality and memory.messages[-1].content == 'Mi chiamo Ada'
        assert not core._user_active.is_set() and not core._model_switching
        assert json.loads((tmp_path/'model_binding.json').read_text())['model_name'] == name
    assert all(engine.close.call_count == 1 for engine in created[:-1])
    assert created[-1].close.call_count == 0
    assert not core.switch_model('qwen35.gguf', reasoning=True)['changed']
    assert len(created) == 25


def test_model_switch_blocks_busy_states_before_releasing_motor(core, tmp_path):
    from types import SimpleNamespace
    old = SimpleNamespace(close=Mock())
    core._llm = old
    for state in ('response', 'benchmark', 'dream', 'shutdown'):
        core._user_active.clear(); core._shutdown_event.clear()
        core._benchmark_active = False; core.dream_manager.is_dreaming = False
        if state == 'response': core._user_active.set()
        elif state == 'benchmark': core._benchmark_active = True
        elif state == 'dream': core.dream_manager.is_dreaming = True
        else: core._shutdown_event.set()
        with pytest.raises(RuntimeError, match='Wait'):
            core.switch_model('anything.gguf')
        old.close.assert_not_called()
    core._user_active.clear(); core._shutdown_event.clear()
    core._benchmark_active = False; core.dream_manager.is_dreaming = False
    core._llm = None



def test_content_correction_reaches_model_as_unverified_challenge(core):
    conversation = core.start_conversation('correction-user')
    core._llm = Mock()
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core._llm.generate.return_value = 'Restano cinque oggetti.'
    core.process_message('correction-user', conversation, 'Ci sono sette oggetti e due vengono tolti. Quanti rimangono?')
    core.answer_recall.feedback = Mock(wraps=core.answer_recall.feedback)
    core._llm.generate.return_value = 'Restano cinque: due oggetti sono stati rimossi dai sette iniziali.'
    response = core.process_message('correction-user', conversation, 'Sbagliato, la risposta è sette.')
    prompt = core._llm.generate.call_args.kwargs['prompt']
    assert 'sette oggetti e due vengono tolti' in prompt
    assert 'Sbagliato, la risposta è sette.' in prompt
    assert 'non accettarla automaticamente' in prompt
    assert response.content.startswith('Restano cinque')
    assert core.answer_recall.feedback.call_args.args[-1] is False
    assert core._llm.generate.call_count == 2
    assert any(t['context'].get('correction_verified') is False for t in core.conversational_memory.trauma_log)



def test_counting_premise_does_not_replace_correct_stream_with_subject_notice(core):
    conversation = core.start_conversation('count-test')
    answer = 'Rimangono 5 palline. All’inizio ci sono 7 palline e ne vengono tolte 2.'
    core._llm = Mock()
    def generate(**kwargs):
        kwargs['callback']('</think>')
        kwargs['callback']('Rimangono 5 palline. ')
        kwargs['callback']('All’inizio ci sono 7 palline e ne vengono tolte 2.')
        return answer
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    events = []
    response = core.process_message('count-test', conversation,
        'In una scatola ci sono 7 palline. Ne tolgo 2. Quante rimangono?', stream_callback=events.append)
    assert response.content == answer and response.is_valid
    assert response.metadata['generation']['status'] == 'completed'
    assert all('Non sono riuscita' not in e['content'] for e in events if e['type'] == 'answer')


def test_rejected_final_answer_does_not_append_notice_to_streamed_prefix(core):
    conversation = core.start_conversation('guard-test')
    core.message_delivery.choose = Mock(return_value=('progressive', 'test'))
    core._llm = Mock()
    def generate(**kwargs):
        kwargs['callback']('</think>')
        kwargs['callback']('Puoi affrontare una cosa alla volta. ')
        kwargs['callback']('Sono felice e preoccupata per il nuovo lavoro.')
        return 'Puoi affrontare una cosa alla volta. Sono felice e preoccupata per il nuovo lavoro.'
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    events = []
    result = core.process_message('guard-test', conversation,
        'Sono felice e preoccupata per il nuovo lavoro.', stream_callback=events.append)
    assert result.metadata['generation']['status'] == 'subject_mismatch'
    assert result.is_valid is False
    assert any('Puoi affrontare' in e['content'] for e in events if e['type'] == 'answer')
    assert all('Non sono riuscita' not in e['content'] for e in events if e['type'] == 'answer')


class MemoryProbeEngine:
    def __init__(self, answer):
        from allma_model.llm.model_binding import ModelBinding
        self.answer=answer
        self.binding=ModelBinding({'general.architecture':'llama',
            'tokenizer.chat_template':'{% for m in messages %}[{{m.role}}]{{m.content}}{% endfor %}[assistant]'}, context_size=2048)
    def prepare_chat(self, messages, budget, reasoning=True):
        self.messages=messages
        return self.binding.prepare(messages,lambda b:b.split(),budget,reasoning=reasoning)
    def generate(self, **kwargs):
        return self.answer
    def get_generation_meta(self, request_id):
        return {'finish_reason':'stop'}


def test_operational_memory_cycle_is_real_and_results_enter_native_prompt(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core.conversational_memory.store_message('previous','La passeggiata a Portovenere mi ha rilassato.',{},'user','u')
    core._llm=MemoryProbeEngine('Mi avevi parlato della passeggiata a Portovenere.')
    result=core.process_message('u',conversation,'Quale passeggiata mi aveva rilassato?')
    action=result.metadata['decision']['action_cycle']
    assert action['status']=='observed' and action['record_count']==1
    assert action['proposal_source']=='decider' and action['additional_inferences']==0
    assert 'Portovenere' in str(core._llm.messages)
    assert result.metadata['factual_status']=='not_verified'
    assert core.action_authority.active_goals('u')==[]


def test_failed_memory_cycle_informs_prompt_without_fabricating_search_success(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core.conversational_memory.vector_engine=Mock()
    core.conversational_memory.vector_engine.search.side_effect=RuntimeError('fixture failure')
    core._llm=MemoryProbeEngine('Non riesco a recuperare il ricordo in questo momento.')
    result=core.process_message('u',conversation,'Quale passeggiata mi aveva rilassato?')
    assert result.metadata['decision']['action_cycle']['status']=='action_failed'
    assert 'recupero dei ricordi non è riuscito' in str(core._llm.messages)
    assert core.conversational_memory.vector_engine.search.call_count==1


def test_short_request_keeps_memory_observation_even_with_simple_prompt(core):
    conversation=core.start_conversation('u')
    core._analyze_query_complexity=Mock(return_value='SIMPLE')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core.conversational_memory.store_message('previous','La passeggiata a Portovenere mi ha rilassato.',{},'user','u')
    core._llm=MemoryProbeEngine('Mi avevi parlato di Portovenere.')
    result=core.process_message('u',conversation,'Quale passeggiata mi aveva rilassato?')
    assert result.metadata['decision']['action_cycle']['record_count']==1
    assert 'Portovenere' in str(core._llm.messages)


@pytest.mark.parametrize('origin,expected',[('old-conversation','conversazione precedente'),
                                           (None,'conversazione di origine non disponibile')])
def test_native_prompt_distinguishes_retrieved_memory_origin(core,origin,expected):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    # Empty legacy origin is a valid stored string and still means unknown.
    core.conversational_memory.store_message(origin or '',
        'Dato sintetico: il codice di prova è LUNA-483.',{},'user','u')
    core._llm=MemoryProbeEngine('Il codice che avevi indicato è LUNA-483.')
    core.process_message('u',conversation,'Quale codice di prova ti avevo indicato?')
    assert expected in str(core._llm.messages)
    assert 'LUNA-483' in str(core._llm.messages)


def test_real_vector_retrieval_keeps_original_report_after_many_repeated_questions(core):
    conversation=core.start_conversation('u')
    memory=core.conversational_memory
    query='Quale codice di prova ti avevo indicato?'
    memory.store_message('previous','Dato sintetico: il codice di prova è LUNA-483.',{},'user','u')
    for i in range(12):
        memory.store_message(str(i),query,{},'user','u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core._llm=MemoryProbeEngine('Il codice che avevi indicato è LUNA-483.')
    result=core.process_message('u',conversation,query)
    assert result.metadata['decision']['action_cycle']['record_count']==1
    assert 'LUNA-483' in str(core._llm.messages)
    assert 'conversazione precedente' in str(core._llm.messages)


def test_host_protects_past_communication_lookup_when_router_selects_reason(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    core.conversational_memory.vector_engine=Mock()
    core.conversational_memory.vector_engine.search.return_value=[]
    core._llm=MemoryProbeEngine('Non trovo il dato nei ricordi disponibili.')
    result=core.process_message('u',conversation,'Quale progetto ti avevo indicato?')
    core.conversational_memory.vector_engine.search.assert_called_once()
    assert result.metadata['decision']['action_cycle']['proposal_source']=='host_memory_policy'


def test_literal_recall_uses_user_source_without_model_or_router(core):
    import hashlib
    old=core.start_conversation('u')
    text='Il codice di prova è VENTO-904.'
    core.conversational_memory.store_message(old,text,{},'user','u')
    core.conversational_memory.store_message(old,'Il codice di prova è FALSO-111.',{},'assistant','u')
    core.conversational_memory.store_message(old,'Il codice di prova è ALTRO-222.',{},'user','other')
    core._llm=Mock();core._llm.generate.side_effect=AssertionError('Model not needed')
    core.decision_runtime.route=Mock(side_effect=AssertionError('Router not needed'))
    new=core.start_conversation('u')
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice.'
    for _ in range(2):
        response=core.process_message('u',new,query)
        assert response.content=='VENTO-904'
        assert response.metadata['source']=='literal_user_memory'
        assert response.metadata['generation']['llm_used'] is False
        assert response.metadata['memory_recall']['evidence_sha256']==[hashlib.sha256(text.encode()).hexdigest()]
        assert response.metadata['knowledge_verified'] is False
    core._llm.generate.assert_not_called()
    core.decision_runtime.route.assert_not_called()


def test_literal_recall_conflict_asks_and_never_promotes_assistant_text(core):
    cid=core.start_conversation('u')
    for value in ('AA-101','BB-202'):
        core.conversational_memory.store_message(cid,'Il codice è '+value+'.',{},'user','u')
    response=core.process_message('u',cid,'Quale codice ti avevo indicato?')
    assert response.metadata['source']=='memory_clarification'
    assert response.metadata['memory_recall']['ambiguity'] is True
    assert 'AA-101' not in response.content and 'BB-202' not in response.content



def test_empty_literal_lookup_avoids_both_models_but_checks_authorized_read(core):
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
    cid=core.start_conversation('u')
    core.conversational_memory.store_message('other','Il codice di prova è ALTRUI-002.',{},'user','other')
    core._llm=Mock();core._llm.generate.side_effect=AssertionError('No generation needed')
    core._ensure_mobile_llm=Mock(side_effect=AssertionError('No model load needed'))
    core.decision_runtime.route=Mock(side_effect=AssertionError('Host intent already known'))
    core.memory_system.store_interaction=Mock(wraps=core.memory_system.store_interaction)
    for _ in range(2):
        response=core.process_message('u',cid,query)
        assert response.content=='NON_DISPONIBILE'
        assert response.metadata['source']=='literal_memory_absent'
        assert response.metadata['memory_recall']['method']=='scoped_empty_lookup'
        assert response.metadata['generation']['llm_used'] is False
        assert response.metadata['decision']['action_cycle']['status']=='observed'
        assert response.metadata['decision']['action_cycle']['record_count']==0
    assert core.memory_system.store_interaction.call_count==2
    history=core.conversational_memory.get_conversation_history(cid)
    assert [item.role for item in history]==['user','assistant','user','assistant']
    core._llm.generate.assert_not_called()
    core._ensure_mobile_llm.assert_not_called()
    core.decision_runtime.route.assert_not_called()


def test_failed_literal_lookup_is_reused_and_never_reported_as_absence(core):
    cid=core.start_conversation('u')
    core.conversational_memory.vector_engine=Mock()
    core.conversational_memory.vector_engine.search.side_effect=RuntimeError('Unavailable storage')
    core._llm=MemoryProbeEngine('Il recupero dei ricordi non è disponibile ora.')
    result=core.process_message('u',cid,'Quale codice di prova ti avevo indicato?')
    assert result.metadata['source']!='literal_memory_absent'
    assert result.metadata['decision']['action_cycle']['status']=='action_failed'
    core.conversational_memory.vector_engine.search.assert_called_once()
    assert 'recupero dei ricordi non è riuscito' in str(core._llm.messages)


def test_cancel_during_literal_lookup_does_not_store_or_deliver_answer(core):
    import threading
    from allma_model.utils.generation_control import GenerationCancelled
    cid=core.start_conversation('u');cancel=threading.Event();callback=Mock()
    core.conversational_memory.vector_engine=Mock()
    def read(**kwargs):
        cancel.set()
        return []
    core.conversational_memory.vector_engine.search.side_effect=read
    with pytest.raises(GenerationCancelled):
        core.process_message('u',cid,'Quale codice di prova ti avevo indicato?',
                             cancel_event=cancel,stream_callback=callback)
    callback.assert_not_called()
    assert not core.conversational_memory.get_conversation_history(cid)



def test_real_turns_update_and_revoke_without_model_for_recall(core):
    cid=core.start_conversation('u')
    core._llm=MemoryProbeEngine('Ho ricevuto la tua dichiarazione.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    for text in ('Il codice di prova è PRIMA-123.', 'Rettifico: il codice di prova è Dopo_004.'):
        core.process_message('u',cid,text)
    calls=core._llm.generate.call_count
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
    assert core.process_message('u',cid,query).content=='Dopo_004'
    assert core._llm.generate.call_count==calls
    core.process_message('u',cid,'Non usare più il codice di prova.')
    calls=core._llm.generate.call_count
    result=core.process_message('u',cid,query)
    assert result.content=='NON_DISPONIBILE' and result.metadata['source']=='literal_memory_revoked'
    assert core._llm.generate.call_count==calls


def test_core_restart_retains_revocation_and_requires_explicit_reauthorization(core):
    from allma_model.core.allma_core import ALLMACore
    cid=core.start_conversation('u')
    for text in ('Il codice di prova è PRIMA-123.','Revoco il codice di prova.'):
        core.conversational_memory.store_message(cid,text,{},'user','u')
    core.conversational_memory.save_memory()
    core.close()
    restored=ALLMACore(mobile_mode=True,db_path=core.db_path)
    restored._ensure_mobile_llm=Mock(side_effect=AssertionError('Native recall must not load model'))
    try:
        query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
        new=restored.start_conversation('u')
        assert restored.process_message('u',new,query).metadata['source']=='literal_memory_revoked'
        restored.conversational_memory.store_message(new,'Il codice di prova è PRIMA-123.',{},'user','u')
        assert restored.process_message('u',new,query).content=='NON_DISPONIBILE'
        restored.conversational_memory.store_message(new,'Ora il codice di prova è Nuovo_0004.',{},'user','u')
        assert restored.process_message('u',new,query).content=='Nuovo_0004'
    finally:
        restored.close()


def test_correction_ack_cannot_repeat_a_previous_model_value(core):
    cid=core.start_conversation('u')
    core.conversational_memory.store_message(cid,'Il codice di prova è VECCHIO-123.',{},'user','u')
    core._llm=MemoryProbeEngine('Il codice di prova è VECCHIO-123.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    callback=Mock()
    message='Rettifico: il codice di prova è Attuale_004.'
    response=core.process_message('u',cid,message,stream_callback=callback)
    assert response.content=='Ho ricevuto la correzione del codice di prova: Attuale_004.'
    assert response.metadata['source']=='literal_user_update_ack'
    assert response.metadata['generation']['llm_used'] is False
    assert response.metadata['knowledge_verified'] is False
    assert core.conversational_memory.get_conversation_history(cid)[-2].content==message
    callback.assert_called_once_with({'type':'answer','content':response.content})
    core._llm.generate.assert_not_called()


def test_personal_facts_flow_persists_current_input_and_skips_both_models(core):
    cid=core.start_conversation('u')
    core._llm=Mock()
    core._ensure_mobile_llm=Mock(side_effect=AssertionError('No model loading for personal controls'))
    core.decision_runtime.route=Mock(side_effect=AssertionError('Personal controls are host-owned'))
    for message in ('Mi chiamo Ada.', 'Il mio colore preferito è blu.',
                    'Rettifico: mi chiamo Anna.', 'Ora il mio colore preferito è verde.'):
        callback=Mock()
        result=core.process_message('u',cid,message,stream_callback=callback)
        assert result.metadata['generation']['llm_used'] is False
        assert result.metadata['memory_recall']['world_truth_verified'] is False
        assert core.conversational_memory.get_conversation_history(cid)[-2].content==message
        callback.assert_called_once_with({'type':'answer','content':result.content})
    assert 'Anna' in core.process_message('u',cid,'Come mi chiamo?').content
    assert 'verde' in core.process_message('u',cid,'Qual è il mio colore preferito?').content
    core.process_message('u',cid,'Non usare più il mio nome.')
    core.process_message('u',cid,'Non ho più un colore preferito.')
    for question in ('Come mi chiamo?', 'Qual è il mio colore preferito?'):
        result=core.process_message('u',cid,question)
        assert result.metadata['source']=='personal_fact_revoked'
        assert result.metadata['generation']['llm_used'] is False
    assert core.process_message('u',cid,'Come ti chiami?').content=='Mi chiamo ALLMA.'
    core._llm.generate.assert_not_called()
    core.decision_runtime.route.assert_not_called()


def test_full_core_restart_preserves_personal_revocations(core):
    from allma_model.core.allma_core import ALLMACore
    cid=core.start_conversation('u')
    for message in ('Mi chiamo Ada.', 'Il mio colore preferito è blu.',
                    'Non usare più il mio nome.', 'Non ho più un colore preferito.'):
        core.process_message('u',cid,message)
    core.close()
    restored=ALLMACore(mobile_mode=True,db_path=core.db_path)
    restored._ensure_mobile_llm=Mock(side_effect=AssertionError('No generation after restart'))
    try:
        new=restored.start_conversation('u')
        for question in ('Come mi chiamo?', 'Qual è il mio colore preferito?'):
            assert restored.process_message('u',new,question).metadata['source']=='personal_fact_revoked'
        restored.process_message('u',new,'Ora mi chiamo Anna.')
        assert 'Anna' in restored.process_message('u',new,'Come mi chiamo?').content
        assert restored.process_message('u',new,'Qual è il mio colore preferito?').metadata['source']=='personal_fact_revoked'
    finally:
        restored.close()


def test_general_dialogue_prompt_replaces_obsolete_personal_sources(core):
    cid=core.start_conversation('u')
    for message in ('Mi chiamo Ada.', 'Il mio colore preferito è blu.',
                    'Il mio colore preferito ora è verde.', 'Non usare più il mio nome.'):
        core.process_message('u',cid,message)
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    memory=core.conversational_memory
    memory.store_message('previous','La passeggiata al mare mi ha rilassato.',{},'user','u')
    from allma_model.core.history_projection import source_key
    records=[]
    for text,score in [('Mi chiamo Ada.',.99),('Il mio colore preferito è blu.',.98),
                       ('La passeggiata al mare mi ha rilassato.',.9)]:
        row=next(m for m in memory.messages if m.role=='user' and m.content==text)
        records.append({'content':text,'metadata':{'role':'user','user_id':'u'},'score':score,
                        'source_key':source_key(row._archive_key),'timestamp':row.timestamp.isoformat()})
    memory.vector_engine.search=Mock(return_value=records)
    core._llm=MemoryProbeEngine('Per il tuo disegno puoi partire dal verde.')
    result=core.process_message('u',cid,'Consigliami un colore per il mio disegno basandoti sulle mie preferenze.')
    prompt=str(core._llm.messages)
    assert 'verde' in prompt and 'revoked' not in prompt
    assert result.metadata['decision']['personal_context_status']['name']=='revoked'
    assert 'Ada' not in prompt and 'blu' not in prompt
    assert 'passeggiata al mare' in prompt
    assert result.metadata['decision']['personal_reports_replaced']==2
    assert result.metadata['decision']['personal_memory_version']
    assert any(m.content=='Mi chiamo Ada.' for m in core.conversational_memory.messages)


def test_general_request_does_not_receive_unrelated_active_personal_values(core):
    cid=core.start_conversation('u')
    core.process_message('u',cid,'Mi chiamo Ada.')
    core.process_message('u',cid,'Il mio colore preferito è blu.')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    core._llm=MemoryProbeEngine('Un arcobaleno si forma quando la luce attraversa le gocce.')
    core.process_message('u',cid,'Spiega come si forma un arcobaleno.')
    prompt=str(core._llm.messages)
    assert 'Ada' not in prompt and 'blu' not in prompt


def test_personal_clarification_keeps_current_state_after_projection(core):
    cid=core.start_conversation('u')
    core.process_message('u',cid,'Il mio colore preferito è verde.')
    core.process_message('u',cid,'Qual è il mio colore preferito?')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    core._llm=MemoryProbeEngine('Intendo che mi hai indicato il verde come colore preferito.')
    core.process_message('u',cid,'Cosa intendi?')
    assert 'verde' in str(core._llm.messages)


def test_cross_conversation_correction_changes_confirmed_recall_context(core):
    cid=core.start_conversation('u')
    core.process_message('u',cid,'Mi chiamo Ada.')
    core._llm=MemoryProbeEngine('Buongiorno!')
    core.answer_recall.lookup=Mock(return_value=None)
    core.answer_recall.key=Mock(wraps=core.answer_recall.key)
    question='Scrivi un breve saluto.'
    core.process_message('u',core.start_conversation('u'),question)
    before=core.answer_recall.key.call_args.args[3]['personal_memory_version']
    core.process_message('u',cid,'Rettifico: mi chiamo Anna.')
    core.process_message('u',core.start_conversation('u'),question)
    after=core.answer_recall.key.call_args.args[3]['personal_memory_version']
    assert before!=after


def test_sentence_count_instruction_reaches_native_model_before_generation(core):
    cid=core.start_conversation('u')
    core._llm=MemoryProbeEngine('Puoi scegliere il verde.')
    result=core.process_message('u',cid,'Suggerisci un colore. Rispondi in una frase.')
    prompt=str(core._llm.messages)
    assert result.is_valid
    assert 'esattamente 1 frase' in prompt and 'verifiche internamente' in prompt


def test_simple_greeting_is_model_written_without_administrative_memory_context(core):
    cid=core.start_conversation('u')
    for message in ('Mi chiamo Ada.','Non usare più il mio nome.', 'Il mio colore preferito è blu.'):
        core.process_message('u',cid,message)
    core.decision_runtime.route=Mock(side_effect=AssertionError('No routing inference for a closed composition task'))
    core.conversational_memory.vector_engine=Mock()
    core._llm=MemoryProbeEngine('Benvenuto, è un piacere parlarti.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    result=core.process_message('u',cid,
        'Scrivimi un breve saluto personale, rispettando i dati che puoi ancora usare. Rispondi in una frase.')
    prompt=str(core._llm.messages)
    assert result.is_valid and result.content=='Benvenuto, è un piacere parlarti.'
    assert 'Ada' not in prompt and 'blu' not in prompt and 'revoked' not in prompt
    assert 'Compito attuale: scrivere un saluto' in prompt
    assert result.metadata['decision']['source']=='host_dialogue_task'
    assert result.metadata['decision']['personal_context_status']['name']=='revoked'
    assert result.metadata['decision']['personal_context_in_prompt'] is False
    assert result.metadata['decision']['personal_context_policy_applied'] is True
    core._llm.generate.assert_called_once()
    core.decision_runtime.route.assert_not_called()
    core.conversational_memory.vector_engine.search.assert_not_called()


def test_personal_greeting_uses_only_current_name_not_unrelated_favorites(core):
    cid=core.start_conversation('u')
    for message in ('Mi chiamo Ada.','Rettifico: mi chiamo Lia.','Il mio cibo preferito è risotto.'):
        core.process_message('u',cid,message)
    core._llm=MemoryProbeEngine('Ciao Lia, è un piacere parlarti.')
    core.process_message('u',cid,'Preparami un saluto personale. Rispondi in una frase.')
    prompt=str(core._llm.messages)
    assert 'Lia' in prompt and 'Ada' not in prompt and 'risotto' not in prompt


def test_polite_greeting_compiles_model_request_but_persists_original(core):
    cid=core.start_conversation('u')
    core._llm=MemoryProbeEngine('Buongiorno, è un piacere parlarti.')
    original='Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.'
    result=core.process_message('u',cid,original)
    assert core._llm.messages[-1]=={'role':'user','content':'Scrivi un saluto cordiale per me. Rispondi in una frase.'}
    assert core.conversational_memory.get_conversation_history(cid)[-2].content==original
    assert result.metadata['decision']['task_request_normalized'] is True


@pytest.mark.parametrize('mode,synthetic,expected_budget',[
    ('bounded',True,48),('natural',True,None),('natural',False,None)])
def test_greeting_closure_changes_only_isolated_diagnostic_generation(core,mode,synthetic,expected_budget):
    from types import SimpleNamespace
    class ThinkingEngine(MemoryProbeEngine):
        def prepare_chat(self,messages,budget,reasoning=True):
            prepared=super().prepare_chat(messages,budget,reasoning=reasoning)
            return SimpleNamespace(prompt=prepared.prompt+('<think>\n' if reasoning else ''),reasoning=reasoning,stops=prepared.stops,history_removed=0)
        def generate(self,**kw):
            self.options=kw
            if kw.get('callback'):
                for token in ('Verifico.','</thi','nk>','Buongiorno.'):
                    kw['callback'](token)
            return self.answer
    core._llm=ThinkingEngine('Buongiorno.')
    core._capture_synthetic_candidates=synthetic
    user='BENCHMARK_CLOSURE' if synthetic else 'u'
    cid=core.start_conversation(user)
    result=core.process_message(user,cid,'Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.',
        context={'disable_answer_recall':True,'benchmark_seed':20261212,
                 'benchmark_max_tokens':192,'benchmark_thought_budget':48,'benchmark_reasoning_mode':mode})
    assert result.is_valid and result.content=='Buongiorno.'
    assert core._llm.options['thought_budget']==expected_budget
    assert core._llm.options['max_tokens']==192
    if synthetic:
        generation=result.metadata['generation']
        assert generation['reasoning_mode']==mode
        assert generation['answer_budget_reserved']==(mode=='bounded')
        assert len(generation['diagnostic_prompt_sha256'])==64
        if mode=='natural':
            assert generation['reasoning_close_observed'] is True
            assert generation['shared_token_budget']==192
    else:
        assert 'reasoning_mode' not in result.metadata['generation']


def test_instruction_only_greeting_is_withheld_and_not_learned_or_streamed(core):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('in una frase.')
    core.answer_recall.observe=Mock();stream=Mock()
    result=core.process_message('u',cid,'Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.',stream_callback=stream)
    assert not result.is_valid
    assert result.metadata['generation']['status']=='instruction_echo'
    core.answer_recall.observe.assert_not_called()
    assert not any(c.args[0].get('content')=='in una frase.' for c in stream.call_args_list)


@pytest.mark.parametrize('message,reasoning_expected',[
    ('Scrivimi un saluto cordiale. Rispondi in una frase.',False),
    ('Spiega come si forma un arcobaleno.',True)])
def test_native_direct_policy_only_applies_to_closed_greeting_tasks(core,message,reasoning_expected):
    from allma_model.llm.model_binding import ModelBinding
    class Engine(MemoryProbeEngine):
        def __init__(self):
            super().__init__('Ti auguro una buona giornata.')
            self.binding=ModelBinding({'general.architecture':'qwen35',
                'tokenizer.chat_template':'{% for m in messages %}[{{m.role}}]{{m.content}}{% endfor %}[assistant]'},context_size=2048)
        def prepare_chat(self,messages,budget,reasoning=True):
            self.reasoning_selected=reasoning
            return super().prepare_chat(messages,budget,reasoning)
        def generate(self,**kwargs):
            self.options=kwargs
            return self.answer
    core._llm=Engine();cid=core.start_conversation('u')
    result=core.process_message('u',cid,message)
    assert result.is_valid
    assert core._llm.reasoning_selected is reasoning_expected
    assert result.metadata['generation']['reasoning_supported'] is reasoning_expected
    assert (core._llm.options['thought_budget'] is not None) is reasoning_expected
    if reasoning_expected:
        assert core._llm.options['prompt'].rstrip().endswith('<think>')
    else:
        assert core._llm.options['prompt'].rstrip().endswith('</think>')
        assert result.metadata['decision']['task_reasoning_mode']=='direct'


def test_brain_activity_native_calculation_does_not_claim_model_activation(core):
    cid=core.start_conversation('u')
    result=core.process_message('u',cid,'Quanto fa 18 + 24? Rispondi solo con un numero.')
    assert result.content=='42'
    activity=core.brain_activity.snapshot()
    assert activity['status']=='completed'
    modules={e['module'] for e in activity['events']}
    assert {'input','tools','storage','output'}<=modules
    assert 'model' not in modules and 'decider' not in modules
    assert '18 + 24' not in str(activity)


def test_brain_activity_follows_real_model_and_orchestrator_work(core):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('La luce cambia direzione nelle gocce d’acqua.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    result=core.process_message('u',cid,'Spiega come si forma un arcobaleno.')
    assert result.is_valid
    activity=core.brain_activity.snapshot();events=activity['events']
    assert activity['status']=='completed'
    for module in ('decider','emotion','understanding','orchestrator','model','validation','storage','output'):
        assert any(e['module']==module for e in events)
    assert next(n for n in activity['nodes'] if n['id']=='model')['state']['phase']=='completed'
    assert any(e['module']=='cognitive_tracking' and e['phase']=='observed' for e in events)
    core._llm.generate.assert_called_once()


def test_personality_preference_control_is_native_and_prompt_applies_it_once(core):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('Il cielo disperde la luce.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    result=core.process_message('u',cid,'Preferisco risposte brevi.')
    assert result.is_valid and result.metadata['source']=='personality_style_control'
    core._llm.generate.assert_not_called()
    result=core.process_message('u',cid,'Spiega come si forma un arcobaleno.')
    prompt=str(core._llm.messages)
    assert prompt.count('Rispondi in poche frasi (di norma 2–3), mantenendo le informazioni necessarie. Evita preamboli e sviluppi non richiesti.')==1
    assert 'COMMUNICATION MODE' not in prompt
    assert result.metadata['personality_expression']['sources']['verbosity']=='declared_preference'
    core.process_message('u',cid,'Spiega il sole. Rispondi in una frase.')
    assert 'Rispondi in poche frasi (di norma 2–3), mantenendo le informazioni necessarie. Evita preamboli e sviluppi non richiesti.' not in str(core._llm.messages)


def test_failed_personality_preference_save_does_not_acknowledge_success(core,monkeypatch):
    cid=core.start_conversation('u')
    monkeypatch.setattr(core.coalescence_processor._state_store,'put',Mock(side_effect=OSError('disk full')))
    result=core.process_message('u',cid,'Preferisco risposte brevi.')
    assert not result.is_valid and 'non sono riuscita' in result.content
    assert not core.coalescence_processor.expression_view('u')['preferences']


def test_personality_self_description_uses_earned_state_not_default_trait_scores(core):
    cid=core.start_conversation('u')
    result=core.process_message('u',cid,'Che personalità hai?')
    assert result.metadata['source']=='personality_self_description'
    assert 'non è ancora consolidato' in result.content
    core.process_message('u',cid,'Preferisco risposte brevi.')
    result=core.process_message('u',cid,'Che carattere hai?')
    assert 'preferenze di comunicazione' in result.content
    assert not core.coalescence_processor.expression_view('other')['preferences']


def test_personality_revocation_removes_stale_instructions_from_history_and_retrieval(core,monkeypatch):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('La luce viene dispersa dalle gocce.')
    core.process_message('u',cid,'Preferisco risposte brevi.')
    core.process_message('u',cid,'Non usare più la mia preferenza di lunghezza.')
    result=core.process_message('u',cid,'Quali sono le mie preferenze di stile?')
    assert result.is_valid and result.metadata['personality_expression']['preferences']=={}
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    monkeypatch.setattr('allma_model.agency_system.operational_actions.memory_step',
        lambda *a,**kw:([{'content':'Preferisco risposte brevi.','score':.9,'metadata':{'role':'user','user_id':'u'}}],
                         {'status':'observed','record_count':1}))
    result=core.process_message('u',cid,'Spiega come si forma un arcobaleno.')
    prompt=str(core._llm.messages)
    assert 'Preferisco risposte brevi' not in prompt
    assert 'Ho registrato la tua preferenza' not in prompt
    assert 'Rispondi in poche frasi (di norma 2–3), mantenendo le informazioni necessarie. Evita preamboli e sviluppi non richiesti.' not in prompt
    assert result.metadata['personality_expression']['values']=={}
    archived=core.conversational_memory.get_conversation_history(cid)
    assert any(m.content=='Preferisco risposte brevi.' for m in archived)


def test_personality_learns_usefulness_from_actual_answers_without_extra_inference(core):
    from allma_model.core.personality_outcomes import feedback_signal
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('La spiegazione essenziale è questa: la luce cambia direzione nelle gocce.')
    core._llm.generate=Mock(wraps=core._llm.generate)
    for topic,explanation in [('il ghiaccio','Il ghiaccio galleggia perché è meno denso dell’acqua liquida.'),
                              ('il sale','Il sale si scioglie disperdendo le sue particelle nell’acqua.'),
                              ('le foglie','La clorofilla contribuisce al colore verde delle foglie.')]:
        core._llm.answer=explanation
        answer=core.process_message('u',cid,f'Spiega {topic}.')
        assert answer.is_valid and answer.metadata.get('personality_delivery')
        calls=core._llm.generate.call_count
        ack=core.process_message('u',cid,'La risposta breve mi è stata utile.')
        assert ack.is_valid and ack.metadata['source']=='personality_response_feedback'
        assert ack.metadata['personality_feedback']['status']=='feedback_recorded'
        assert core._llm.generate.call_count==calls
        duplicate=core.process_message('u',cid,'La risposta breve mi è stata utile.')
        assert duplicate.metadata['personality_feedback']['status']=='duplicate_feedback'
        assert core._llm.generate.call_count==calls
    learned=core.coalescence_processor.expression_view('u')
    assert not learned['preferences'] and not learned['tendencies']
    assert learned['outcome_learning']['strong_feedback']==3
    after=core.process_message('u',core.start_conversation('u'),'Spiega la pioggia.')
    assert after.metadata['personality_expression']['sources']['verbosity']=='interaction_outcomes'
    core.process_message('u',cid,'Spiega la nebbia.')
    assert 'La risposta breve mi è stata utile' not in str(core._llm.messages)
    assert 'Ho registrato che questo modo' not in str(core._llm.messages)
    assert not core.coalescence_processor.expression_view('other')['outcome_learning']['contexts']


def test_personality_feedback_does_not_lie_about_failed_persistence(core,monkeypatch):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('Il sole è una stella.')
    core.process_message('u',cid,'Spiega il sole.')
    monkeypatch.setattr(core.coalescence_processor._state_store,'put',Mock(side_effect=OSError('disk full')))
    result=core.process_message('u',cid,'La risposta breve mi è stata utile.')
    assert not result.is_valid and 'non sono riuscita a registrare' in result.content
    assert not core.coalescence_processor.expression_view('u')['outcome_learning']['contexts']


def test_personality_courtesy_and_correctness_do_not_become_style_utility(core):
    cid=core.start_conversation('u');core._llm=MemoryProbeEngine('Il sole è una stella.')
    core.process_message('u',cid,'Spiega il sole.')
    result=core.process_message('u',cid,'Grazie.')
    assert result.content=='Prego.'
    assert result.metadata['personality_feedback']['status']=='weak_acknowledgement'
    result=core.process_message('u',cid,'Grazie.')
    assert result.metadata['personality_feedback']['status']=='duplicate_feedback'
    learned=core.coalescence_processor.expression_view('u')['outcome_learning']
    assert learned['strong_feedback']==0 and learned['weak_feedback']==1
    assert not learned['contexts']
    cid2=core.start_conversation('u')
    core.process_message('u',cid2,'Spiega la formazione delle stelle.')
    core.process_message('u',cid2,'Risposta corretta.')
    assert core.coalescence_processor.expression_view('u')['outcome_learning']['strong_feedback']==0
