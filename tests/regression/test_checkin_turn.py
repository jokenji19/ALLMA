"""Dialogue progress, safe local editing and native reasoning policy."""
from types import SimpleNamespace as T
from unittest.mock import Mock
import json
import pytest

from allma_model.utils.checkin_turn import checkin_task
from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.dialogue_output import project_answer


def history(question='Ciao! Come stai?'):
    return [T(role='user',content='Ciao',metadata={}),
            T(role='assistant',content=question,metadata={'is_valid':True})]


@pytest.mark.parametrize('reply', ['Bene','Sto bene, grazie.','Mi sento bene','Abbastanza bene',
    'Grazie, tutto bene!','Non c’è male','Sono felice'])
def test_short_positive_reply_is_a_contextual_task_not_a_stored_answer(reply):
    task=checkin_task(reply,'Ciao! Come stai?')
    assert task.kind=='answer_checkin' and task.direct
    assert reply in task.model_request and not hasattr(task,'answer')
    state=DialogueContinuity(reply,history())
    assert state.mode=='checkin_answer' and state.responding_to_checkin
    assert state.checkin_task is not None


@pytest.mark.parametrize('reply',['Male','Non sto bene','Così così','Mi sento triste'])
def test_negative_short_reply_retains_reasoning_and_the_user_owns_the_report(reply):
    task=checkin_task(reply,'Come stai?')
    assert task is not None and not task.direct
    assert task.borrowed_state('Sto bene, grazie.')
    assert not task.borrowed_state('Mi hai detto «sto bene».')


@pytest.mark.parametrize('reply',['Fine','I am fine, thanks.','I’m good','Not bad'])
def test_english_short_answer_uses_the_pending_question(reply):
    continuity=DialogueContinuity(reply,history('Hello! How are you?'))
    assert continuity.mode=='checkin_answer'
    assert continuity.checkin_task.language=='inglese'


@pytest.mark.parametrize('reply',[
    'Bene, ma come funziona un arcobaleno?', 'Bene, ti ricordi la mia vacanza?',
    'Sto male da giorni e ho dolore al petto.', 'Bene, e tu?', 'Bene?',
    '«Bene»', 'Traduci la parola bene', 'Scrivi un dialogo',
    'Bene. Rispondi solo JSON', 'Mi sento bene perché ho finito il progetto.',
])
def test_substantive_requests_reciprocity_quotes_and_constraints_keep_normal_route(reply):
    assert checkin_task(reply,'Come stai?') is None


def test_bene_after_an_unrelated_question_does_not_become_a_checkin_task():
    assert DialogueContinuity('Bene',history('Di cosa vuoi parlare?')).checkin_task is None


def test_retry_after_withheld_short_answer_keeps_the_original_pending_task():
    attempts=history()+[T(role='user',content='Bene',metadata={}),
        T(role='assistant',content='',metadata={'is_valid':False,'generation':{'status':'dialogue_repetition'}})]
    state=DialogueContinuity('Bene',attempts[:-1],attempt_history=attempts)
    assert state.retry_after_failure and state.mode=='checkin_answer'
    assert state.checkin_task.reply=='Bene'


@pytest.mark.parametrize('question',['Come stai?','Come ti va?','Tutto bene?','Come va oggi?'])
def test_only_standalone_satisfied_question_is_removed(question):
    continuity=DialogueContinuity('Bene',history())
    original='Mi fa piacere che tu stia bene. '+question
    result=project_answer(original,'Bene',continuity)
    assert result.text=='Mi fa piacere che tu stia bene.'
    assert result.reason=='repeated_checkin' and len(result.removed)==1
    assert question not in json.dumps(result.audit())
    assert not continuity.duplicate(result.text)
    assert project_answer(result.text,'Bene',continuity).text==result.text


@pytest.mark.parametrize('answer',[
    'Come stai?', 'Certo! Come stai?', '«Come stai?»', '```Come stai?```',
    'Mi fa piacere. Come stai affrontando il progetto?',
    'Mi fa piacere sapere come stai? Raccontami.',
])
def test_filter_never_promotes_an_empty_wrapper_or_deletes_substantive_questions(answer):
    result=project_answer(answer,'Bene',DialogueContinuity('Bene',history()))
    assert result.text==answer and not result.removed


def test_explicit_question_repetition_and_sentence_contract_are_preserved():
    answer='Mi fa piacere. Come stai?'
    for request in ['Ripeti la domanda','Scrivi un dialogo con la frase «Come stai?»',
                    'Rispondi in due frasi.','Rispondi solo JSON']:
        assert project_answer(answer,request,DialogueContinuity(request,history())).text==answer


class Engine:
    def __init__(self, answers):
        from allma_model.llm.model_binding import ModelBinding
        self.answers=iter(answers);self.calls=[];self.messages=[];self.reasoning=[]
        self.binding=ModelBinding({'general.architecture':'qwen35',
            'tokenizer.chat_template':'{% for m in messages %}[{{m.role}}]{{m.content}}{% endfor %}[assistant]'},context_size=2048)
    def prepare_chat(self,messages,budget,reasoning=True):
        self.messages.append(messages);self.reasoning.append(reasoning)
        return self.binding.prepare(messages,lambda text:text.split(),budget,reasoning=reasoning)
    def generate(self,**kwargs):
        self.calls.append(kwargs);answer=next(self.answers)
        if kwargs.get('callback'):kwargs['callback'](answer)
        return answer
    def get_generation_meta(self,request):return {'finish_reason':'stop'}


@pytest.fixture
def core(tmp_path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    core._ensure_mobile_llm=lambda:None
    core.decision_runtime.route=Mock(side_effect=AssertionError('Unnecessary routing inference'))
    core.answer_recall.observe=Mock()
    core.incremental_learner.learn_from_interaction=Mock()
    yield core
    core.close()


def seed(core,question='Ciao! Come stai?'):
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    cid=core.start_conversation('u')
    core.conversational_memory.store_message(cid,'Ciao',{},'user','u')
    core.conversational_memory.store_message(cid,question,{'is_valid':True,'identity_policy':POLICY_VERSION},'assistant','u')
    core.conversational_memory.vector_engine.search=Mock(side_effect=AssertionError('Unnecessary episode lookup'))
    return cid


def test_whole_core_keeps_valid_model_ack_without_a_second_generation_or_episode_search(core):
    cid=seed(core);core._llm=Engine(['Mi fa piacere che tu stia bene. Come ti va?'])
    events=[]
    result=core.process_message('u',cid,'Bene',stream_callback=events.append)
    assert result.is_valid and result.content=='Mi fa piacere che tu stia bene.'
    assert result.metadata['source']=='model_excerpt'
    assert result.metadata['recovery']['reason']=='repeated_checkin'
    assert result.metadata['decision']['task']=='answer_checkin'
    assert result.metadata['generation']['reasoning_supported'] is False
    assert core._llm.calls[0]['max_tokens']<=96
    assert core._llm.reasoning==[False] and len(core._llm.calls)==1
    assert core._llm.calls[0]['thought_budget'] is None
    core.decision_runtime.route.assert_not_called()
    core.conversational_memory.vector_engine.search.assert_not_called()
    core.answer_recall.observe.assert_not_called()
    assert core.conversational_memory.messages[-2].content=='Bene'
    assert core.conversational_memory.messages[-2].metadata.get('experience_update')
    assert result.metadata['emotional_growth']['status'] not in {'not_stored','unavailable'}
    assert core.conversational_memory.messages[-1].content==result.content
    assert ''.join(e['content'] for e in events if e['type']=='answer')==result.content
    assert 'Come ti va?' not in result.content


def test_only_a_repeated_question_gets_one_contextual_repair_without_a_script(core):
    cid=seed(core);core._llm=Engine(['Come stai?','Mi fa piacere. Di cosa vuoi parlare?'])
    result=core.process_message('u',cid,'Bene')
    assert result.is_valid and result.metadata['turn_review']['repair_status']=='accepted'
    assert core._llm.reasoning==[False,False]
    assert 'L’utente ha risposto' in core._llm.messages[-1][-1]['content']
    assert len(core._llm.calls)==2


def test_user_wellbeing_is_not_adopted_as_allmas_state_after_local_question_removal(core):
    cid=seed(core);core._llm=Engine(['Sto bene, grazie. Come ti va?']*2)
    result=core.process_message('u',cid,'Sto bene, grazie.')
    assert not result.is_valid and result.content==''
    assert result.metadata['generation']['status']=='subject_mismatch'


def test_negative_response_retains_native_reasoning(core):
    cid=seed(core);core._llm=Engine(['Ti va di raccontarmi cosa è successo?'])
    result=core.process_message('u',cid,'Così così')
    assert result.is_valid and core._llm.reasoning==[True]
    assert result.metadata['generation']['reasoning_supported'] is True
    core.decision_runtime.route.assert_not_called()


def test_an_ineligible_previous_question_cannot_authorize_the_short_route(core):
    cid=seed(core);core._llm=Engine(['Dimmi pure di cosa vuoi parlare.'])
    core._reviewed_history_eligible=lambda row,revision: row.role!='assistant'
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    reply=core.process_message('u',cid,'Bene')
    assert reply.metadata['decision'].get('task')!='answer_checkin'
    core.decision_runtime.route.assert_called_once()


@pytest.mark.parametrize('status,label',[
    ('dialogue_repetition','Risposta da rielaborare'),
    ('cancelled','Risposta interrotta'),('inference_error','Errore di elaborazione'),
    ('subject_mismatch','Risposta non validata'),('validation_unavailable','Controllo non disponibile')])
def test_origin_exposes_actual_reason_without_an_assistant_utterance(status,label):
    from allma_model.core.learning_insights import response_origin
    origin=response_origin({'generation':{'status':status}},False)
    assert origin['kind']=='incomplete' and origin['label']==label and origin['reason']==status


def test_pruned_model_text_retains_honest_origin_and_is_not_called_confirmed_learning():
    from allma_model.core.learning_insights import response_origin
    origin=response_origin({'source':'model_excerpt','recovery':{'reason':'repeated_checkin'}})
    assert origin['kind']=='model' and origin['label']=='Domanda ripetuta rimossa'


def test_filter_never_launders_a_copied_previous_answer_by_removing_its_question():
    old='Mi fa piacere che tu stia bene. Come stai?'
    view=DialogueContinuity('Bene',history(old))
    result=project_answer(old,'Bene',view)
    assert result.text==old and view.duplicate(result.text)


@pytest.mark.parametrize('question,reply',[
    ('Quale tonalità immagini?','Zaffiro crepuscolare'),
    ('Quale ambiente preferisci?','Sentieri tranquilli con pochissime persone.'),
    ('Di cosa ti piacerebbe parlare?','Degli oceani sotto il ghiaccio.'),
    ('Quale giorno scegli?','Il ventitré, se possibile.'),
    ('Come stai?','Un groviglio di sollievo, nostalgia e impazienza.'),
    ('How does it feel?','Like a quiet room after a thunderstorm.'),
    ('¿Qué ambiente prefieres?','Un bosque tranquilo.'),
    ('Quale argomento scegli?','Spiegami le aurore boreali.'),
    ('Quale argomento scegli?','Puoi spiegarmi la gravità?'),
    ('Quale titolo scegli?','«La strada che manca»'),
    ('Quale formato scegli?','{"formato":"json"}'),
    ('Quale ambiente preferisci?','Non ho capito cosa intendi.'),
    ('Quale ambiente preferisci?','Preferisco non rispondere.'),
    ('Quale ambiente preferisci?','Una spiaggia.\nPoi vorrei parlare di astronomia.'),
])
def test_novel_words_phrases_requests_and_languages_receive_the_actual_question(question,reply):
    from allma_model.utils.dialogue_reasoning import TurnWorkspace
    view=DialogueContinuity(reply,history(question))
    assert view.preceding_questions==(question,)
    assert view.question_task is not None and not view.question_task.direct
    assert not view.question_task.host_route and not view.question_task.skip_episode_lookup
    assert reply in json.loads(view.question_task.model_request.split('Il suo messaggio attuale è: ')[1].split('. Interpretalo')[0])
    assert question in TurnWorkspace.build(reply,view).instruction()


@pytest.mark.parametrize('text,expected',[
    ('Mi hai chiesto «come stai?».',()),
    ('La frase è "come stai?".',()),
    ('```\nCome stai?\n```',()),
    ('Preferisci «mare» o «montagna»?',('Preferisci «mare» o «montagna»?',)),
    ('Come stai? Vuoi parlarne?',('Come stai?','Vuoi parlarne?')),
    ('Un esempio: «perché?». Quale argomento scegli?',('Quale argomento scegli?',)),
])
def test_real_questions_are_distinguished_from_reported_speech_and_code(text,expected):
    from allma_model.utils.conversation_reply import questions
    assert questions(text)==expected


def test_unknown_reply_is_not_assumed_to_have_satisfied_the_previous_question():
    question='Quale ambiente preferisci?'
    view=DialogueContinuity('Non ho capito cosa intendi.',history(question))
    answer='Intendo un paesaggio dove passeggiare. Quale ambiente preferisci?'
    assert project_answer(answer,view.message,view).text==answer
    assert not project_answer(answer,view.message,view).removed


def test_unanswered_parts_of_multiple_questions_are_preserved():
    view=DialogueContinuity('Azzurro',history('Quale colore preferisci? E quale forma?'))
    answer='Userò una tonalità azzurra. E quale forma?'
    assert project_answer(answer,'Azzurro',view).text==answer


def test_without_an_actual_pending_question_the_context_task_is_not_invented():
    for rows in ([],history('Va bene, ti ascolto.'),history()+[T(role='user',content='Bene',metadata={})]):
        assert DialogueContinuity('Zaffiro crepuscolare',rows).question_task is None


def test_general_context_survives_retry_without_using_failed_assistant_text():
    prior=history('Quale tonalità immagini?')
    attempts=prior+[T(role='user',content='Zaffiro crepuscolare',metadata={}),
        T(role='assistant',content='',metadata={'is_valid':False})]
    view=DialogueContinuity('Zaffiro crepuscolare',attempts[:-1],attempt_history=attempts)
    assert view.question_task.preceding_questions==('Quale tonalità immagini?',)
    assert view.retry_after_failure


def test_reply_context_retains_earlier_dialogue_for_indirect_references():
    from allma_model.utils.dialogue_reasoning import TurnWorkspace
    rows=history('Parlavamo di Europa e del suo oceano.')+[
        T(role='user',content='Quali aspetti possiamo approfondire?',metadata={}),
        T(role='assistant',content='Il ghiaccio oppure il calore interno. Quale scegli?',metadata={'is_valid':True})]
    view=DialogueContinuity('Il secondo',rows)
    projected=TurnWorkspace.build('Il secondo',view).project_history(rows)
    assert projected==rows and 'Europa' in projected[1].content


@pytest.mark.parametrize('question,message,answer',[
    ('Quale tonalità immagini?','Zaffiro crepuscolare','Un blu profondo con una sfumatura violacea.'),
    ('Di cosa ti piacerebbe parlare?','Degli oceani sotto il ghiaccio.',
        'Su Europa potrebbe esserci acqua liquida sotto una crosta ghiacciata.'),
    ('Quale argomento scegli?','Spiegami le aurore boreali.',
        'Le particelle solari eccitano i gas atmosferici, che emettono luce.'),
])
def test_whole_pipeline_interprets_new_content_and_preserves_the_normal_router(core,question,message,answer):
    cid=seed(core,question);core._llm=Engine([answer])
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason','total_ms':7})
    result=core.process_message('u',cid,message)
    assert result.is_valid and result.content==answer
    assert result.metadata['decision']['task']=='answer_question'
    assert result.metadata['decision']['total_ms']==7
    assert core._llm.reasoning==[True]
    assert question in core._llm.messages[0][-1]['content']
    assert message in core._llm.messages[0][-1]['content']
    core.decision_runtime.route.assert_called_once()


def test_contextual_reply_does_not_disable_personal_retrieval(core,monkeypatch):
    cid=seed(core,'Di quale passeggiata vuoi parlare?')
    core._llm=Engine(['Puoi dirmi quale particolare del sentiero vuoi approfondire?'])
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    memory=Mock(return_value=([],{'status':'observed','record_count':0}))
    monkeypatch.setattr('allma_model.agency_system.operational_actions.memory_step',memory)
    reply=core.process_message('u',cid,'Di quel sentiero che avevo percorso.')
    assert reply.is_valid and reply.metadata['decision']['task']=='answer_question'
    memory.assert_called_once()


def test_contextual_request_does_not_disable_public_reference_lookup(core):
    cid=seed(core,'Di cosa ti piacerebbe parlare?');core._llm=Engine([])
    core.public_references.lookup=Mock(return_value={'status':'unavailable','references':[],'network_used':False})
    result=core.process_message('u',cid,'Cerca le ultime notizie sullo spazio')
    core.public_references.lookup.assert_called_once()
    assert result.metadata['source']=='reference_unavailable'


def test_android_diagnostic_uses_isolated_history_and_checks_real_and_injected_cases(core,monkeypatch):
    import allma_model.llm.checkin_diagnostics as diagnostic
    engine=Engine(['Mi fa piacere. Di cosa vuoi parlare?','Grazie per avermelo detto.',
        'Ti va di raccontarmi qualcosa?','Thanks for sharing. What would you like to talk about?',
        'Un sentiero lontano dai centri abitati potrebbe fare al caso tuo.',
        'Sotto la crosta ghiacciata di Europa potrebbe esistere un oceano liquido.',
        'Mi fa piacere che tu stia bene.'])
    engine.backend_info={'kind':'synthetic'};engine.model_path='/synthetic/model.gguf'
    core._llm=engine;core._llm_ready=True;core._foreground=True
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    user_cid=core.start_conversation('private-user')
    core.conversational_memory.store_message(user_cid,'Preserva questo messaggio.',{},'user','private-user')
    before=list(core.conversational_memory.messages)
    monkeypatch.setattr(diagnostic,'conditions',lambda source:{'temperature_c':34,'thermal_status':0})
    monkeypatch.setattr('allma_model.llm.endurance.conditions',lambda source:{'temperature_c':34,'thermal_status':0})
    run=diagnostic.CheckinRun()
    try:
        run.setup_brain(core);run.run_tests()
        result=json.loads(__import__('pathlib').Path(run.report_path).with_suffix('.json').read_text())
        assert result['passed']==8 and result['useful_real_responses']==6
        assert [r['injected_draft'] for r in result['results']]==[False]*6+[True]*2
        assert all(r['answer']==r['published_text'] for r in result['results'])
        assert core.conversational_memory.messages==before
        assert not core._user_active.is_set() and not core._benchmark_active
        assert core.decision_runtime.route.call_count==2
    finally:run.close()
    assert core._llm is engine


@pytest.mark.parametrize('sample,reason',[
    ({'temperature_c':None,'thermal_status':None},'sensors_unavailable'),
    ({'temperature_c':41,'thermal_status':0},'thermal_pause'),
    ({'temperature_c':37,'thermal_status':2},'thermal_pause'),
])
def test_diagnostic_exposes_the_actual_preflight_sample_and_stop_reason(core,monkeypatch,sample,reason):
    import allma_model.llm.checkin_diagnostics as diagnostic
    from pathlib import Path
    core._llm=Engine([]);core._llm.backend_info={};core._llm.model_path='/synthetic/model.gguf'
    core._foreground=True
    monkeypatch.setattr(diagnostic,'conditions',lambda source:sample)
    run=diagnostic.CheckinRun()
    try:
        run.setup_brain(core);run.run_tests()
        report=json.loads(Path(run.report_path).with_suffix('.json').read_text())
        assert report['completed']==0 and report['stop_reason']==reason
        assert report['last_conditions']==sample
        assert not core._llm.calls and not core._user_active.is_set()
    finally:run.close()
