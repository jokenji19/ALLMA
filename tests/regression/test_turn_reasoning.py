from types import SimpleNamespace as T
from unittest.mock import Mock
import threading
import time

import pytest

from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.dialogue_reasoning import TurnWorkspace, copied_without_progress, repair_admission
from allma_model.utils.generation_control import GenerationCancelled


QUESTION = 'Descrivi il funzionamento di una bussola.'
OLD = ('Una bussola contiene un ago magnetizzato che può ruotare liberamente su un perno. '
       'L’ago si dispone lungo la direzione del campo magnetico terrestre e permette di orientarsi.')
NEW = 'Vicino a un magnete o a un oggetto metallico l’indicazione può essere alterata.'


def history():
    return [T(role='user', content=QUESTION, metadata={}), T(role='assistant', content=OLD, metadata={})]


def test_workspace_resolves_followup_from_user_question_and_never_treats_assistant_as_evidence():
    q = 'Dimmi anche altro su di essa'
    work = TurnWorkspace.build(q, DialogueContinuity(q, history()))
    assert work.purpose == 'elaboration' and work.hold_delivery
    assert work.anchor == QUESTION
    messages = work.repair_messages('Identità', 'Dati attribuiti',
        [{'role':'user','content':QUESTION}, {'role':'assistant','content':OLD}], 'dialogue_repetition')
    assert messages[-1] == {'role':'user', 'content':work.model_request(include_covered=True)}
    assert QUESTION in messages[-1]['content'] and messages[-1]['content'].endswith(q)
    assert OLD in messages[-1]['content'] and 'NON usare come prova' in messages[-1]['content']
    assert not any(row['role']=='assistant' for row in messages)
    assert QUESTION in messages[0]['content']
    assert not work.audit()['assistant_is_evidence']
    assert QUESTION not in str(work.audit())


def test_subject_survives_multiple_followups_without_using_model_claims():
    turns = history() + [T(role='user',content='Dimmi anche altro su di essa',metadata={}),
        T(role='assistant',content=NEW,metadata={})]
    q='Puoi spiegare meglio?'
    workspace=TurnWorkspace.build(q,DialogueContinuity(q,turns),turns)
    assert workspace.anchor == QUESTION
    projected = workspace.project_history(turns)
    assert projected == turns[-2:]
    assert len(turns) == 4 and turns[1].content == OLD


def test_reference_normalization_preserves_original_request_and_quoted_user_data(core):
    cid=seed(core)
    core._llm.generate.return_value=NEW
    original='Dimmi anche altro su di essa.'
    reply=core.process_message('test-owner',cid,original)
    assert reply.is_valid
    prompt=core._llm.generate.call_args.kwargs['prompt']
    current=prompt.rsplit('<|im_start|>user',1)[-1]
    assert QUESTION in current and original in current
    assert core.conversational_memory.messages[-2].content==original


def test_unresolved_turn_ui_and_edit_preserve_user_draft():
    import subprocess
    from pathlib import Path
    subprocess.run(['/opt/homebrew/opt/node@24/bin/node','tests/regression/unresolved_turn_checks.cjs'],
        cwd=Path(__file__).resolve().parents[2],check=True,capture_output=True,text=True)


@pytest.mark.parametrize('wrapper', ['ALLMA. ', 'Certo! ', 'Ecco altri dettagli. '])
def test_cosmetic_wrappers_do_not_make_a_copy_an_elaboration(wrapper):
    assert copied_without_progress(wrapper + OLD, OLD, 'Dimmi anche altro su di essa')
    assert DialogueContinuity('Dimmi anche altro su di essa',history()).duplicate(wrapper+OLD)


@pytest.mark.parametrize('query,answer', [
    ('Dimmi anche altro su di essa', OLD+' '+NEW),
    ('Ripeti la risposta precedente', OLD),
    ('Quindi confermi questo funzionamento?', OLD),
    ('Hai sbagliato: non funziona così.', OLD),
    ('Dimmi anche altro su di essa', NEW),
    ('Dimmi anche altro su di essa', OLD.replace('magnetizzato', 'non magnetizzato')),
])
def test_overlap_is_allowed_for_actual_new_content_and_legitimate_repetition(query, answer):
    assert not DialogueContinuity(query,history()).duplicate(answer)


@pytest.mark.parametrize('query', [
    'Dimmi anche altro, senza ripetere i punti già detti.',
    'Continua senza ripetere la parte già scritta.',
    'Approfondisci, non ripeterti.',
    'Tell me more without repeating the points already covered.',
])
def test_explicit_no_reuse_rejects_copied_sentences_even_with_new_details(query):
    view=DialogueContinuity(query,history())
    assert view.avoid_reuse
    assert view.duplicate(OLD+' '+NEW)
    assert not view.duplicate(NEW)


@pytest.mark.parametrize('query', [
    'Traduci «senza ripetere i punti già detti».',
    'Ripeti la risposta ma senza ripetere i titoli.',
    'Spiega questa istruzione: "non ripeterti".',
])
def test_quoted_instructions_and_only_titles_do_not_forbid_legitimate_body_reuse(query):
    assert not DialogueContinuity(query,history()).avoid_reuse


def test_repair_admission_keeps_controlled_benchmarks_single_pass_and_bounds_latency():
    monitor=T(is_android=False)
    assert repair_admission(['dialogue_repetition'], {'benchmark_seed':4}, 10, monitor)=='controlled_single_pass'
    assert repair_admission(['dialogue_repetition'], {}, 45001, monitor)=='latency_limit'
    assert repair_admission(['validation_unavailable'], {}, 10, monitor)=='not_repairable'
    assert repair_admission(['dialogue_repetition'], {}, 10, monitor)=='admitted'


@pytest.mark.parametrize('thermal', [2,3,4,5,6,None])
def test_repair_does_not_add_generation_under_thermal_pressure(thermal):
    monitor=T(is_android=True,get_metabolic_state=lambda:T(is_valid=True,source='android',
        observed_at=time.monotonic(),thermal_api_available=True,thermal_status=thermal,
        is_tired=False,is_power_save=False,battery_temp_celsius=35))
    assert repair_admission(['dialogue_repetition'], {}, 10, monitor)=='power_limit'


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    value=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    value._ensure_mobile_llm=lambda:None
    value._llm=Mock()
    value._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    value.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    value.answer_recall.observe=Mock()
    value.incremental_learner.learn_from_interaction=Mock()
    yield value
    value.close()


def seed(core):
    cid=core.start_conversation('test-owner')
    for turn in history():
        from allma_model.core.autobiographical_identity import POLICY_VERSION
        core.conversational_memory.store_message(cid,turn.content,{'identity_policy':POLICY_VERSION},turn.role,'test-owner')
    return cid


def test_actual_pipeline_repairs_instead_of_publishing_notice_or_draft(core):
    cid=seed(core);events=[]
    def draft(**kwargs):
        kwargs['callback']('</think>'+OLD+' ')
        assert not [e for e in events if e['type']=='answer']
        return OLD+' DRAFT_UNSHARED.'
    def revision(**kwargs):
        assert kwargs['callback'] is None and kwargs['request_id'].endswith(':revision')
        assert 'DRAFT_UNSHARED' not in kwargs['prompt']
        assert 'bussola' in kwargs['prompt'] and 'una frase' in kwargs['prompt']
        return NEW
    core._llm.generate.side_effect=[None,None]
    core._llm.generate.side_effect=lambda **kw: revision(**kw) if kw['request_id'].endswith(':revision') else draft(**kw)
    reply=core.process_message('test-owner',cid,'Spiega come funziona una bussola. Rispondi in una frase.',stream_callback=events.append)
    assert reply.is_valid and reply.content==NEW
    assert reply.metadata['source']=='model_generated'
    assert reply.metadata['turn_review']['repair_status']=='accepted'
    assert reply.metadata['turn_review']['attempts']==2
    assert ''.join(e['content'] for e in events if e['type']=='answer')==NEW
    assert core.conversational_memory.messages[-1].content==NEW
    core.answer_recall.observe.assert_called_once()
    assert core.answer_recall.observe.call_args.args[3]==NEW
    core.incremental_learner.learn_from_interaction.assert_called_once()
    assert core.incremental_learner.learn_from_interaction.call_args.args[0]['response']==NEW
    from allma_model.core.learning_insights import response_origin
    assert response_origin(reply.metadata)['label']=='Rielaborata dopo un controllo'


def test_only_the_accepted_revision_can_be_confirmed_for_learning(core):
    core.answer_recall.observe=type(core.answer_recall).observe.__get__(core.answer_recall)
    cid=seed(core)
    core._llm.generate.side_effect=[OLD,NEW]
    reply=core.process_message('test-owner',cid,'Spiega come funziona una bussola. Rispondi in una frase.')
    records=list(core.answer_recall.records.values())
    assert len(records)==1 and records[0]['answer']==NEW
    assert not records[0]['confirmations']
    assert core.answer_recall.lookup(reply.metadata['recall_key'],'test-owner') is None
    confirmed=core.process_message('test-owner',cid,'Risposta corretta')
    assert confirmed.metadata['source']=='learning_feedback'
    assert len(list(core.answer_recall.records.values())[0]['confirmations'])==1


def test_unresolved_revision_has_no_fake_utterance_no_learning_and_no_loop(core):
    cid=seed(core);events=[]
    core._llm.generate.return_value=OLD
    reply=core.process_message('test-owner',cid,'Dimmi anche altro su di essa',stream_callback=events.append)
    assert not reply.is_valid and reply.content==''
    assert reply.metadata['generation']['status']=='dialogue_repetition'
    assert reply.metadata['delivery_state']=='unresolved'
    assert reply.metadata['turn_review']['repair_status']=='needs_new_evidence'
    assert core._llm.generate.call_count==1
    assert not ''.join(e['content'] for e in events if e['type']=='answer')
    core.answer_recall.observe.assert_not_called()
    core.incremental_learner.learn_from_interaction.assert_not_called()


def test_valid_first_attempt_needs_no_additional_model_call(core):
    cid=seed(core)
    core._llm.generate.return_value=NEW
    reply=core.process_message('test-owner',cid,'Dimmi anche altro su di essa')
    assert reply.is_valid and reply.content==NEW
    assert reply.metadata['turn_review']['attempts']==1
    core._llm.generate.assert_called_once()


@pytest.mark.parametrize('status', ['model_missing','thermal_pause','disabled'])
def test_unavailable_decider_does_not_trigger_irrelevant_personal_retrieval(core,monkeypatch,status):
    memory=Mock(return_value=([],{'status':'observed','record_count':0}))
    monkeypatch.setattr('allma_model.agency_system.operational_actions.memory_step',memory)
    core.decision_runtime.route.return_value={'status':status,'choice':None}
    core._llm.generate.return_value=NEW
    cid=core.start_conversation('test-owner')
    reply=core.process_message('test-owner',cid,'Come funziona una bussola?')
    assert reply.is_valid
    memory.assert_not_called()
    assert 'La ricerca nei ricordi non ha trovato' not in core._llm.generate.call_args.kwargs['prompt']
    core.process_message('test-owner',cid,'Ti avevo raccontato della mia passeggiata?')
    memory.assert_called_once()


def test_cancel_during_revision_is_propagated_and_not_saved_as_answer(core):
    cid=seed(core)
    core._llm.generate.side_effect=['', GenerationCancelled()]
    with pytest.raises(GenerationCancelled):
        core.process_message('test-owner',cid,'Dimmi anche altro su di essa')
    assert core.conversational_memory.messages[-1].role=='user'
    assert not core._user_active.is_set()


def test_controlled_single_pass_diagnostic_does_not_silently_add_revision(core):
    cid=seed(core)
    core._llm.generate.return_value=OLD
    reply=core.process_message('test-owner',cid,'Dimmi anche altro su di essa',context={'benchmark_seed':42})
    assert not reply.is_valid
    assert reply.metadata['turn_review']['repair_status']=='controlled_single_pass'
    core._llm.generate.assert_called_once()


def test_empty_model_answer_gets_one_revision_instead_of_a_scripted_reply(core):
    cid=seed(core)
    core._llm.generate.side_effect=['',NEW]
    reply=core.process_message('test-owner',cid,'Dimmi anche altro su di essa')
    assert reply.is_valid and reply.content==NEW
    assert reply.metadata['turn_review']['initial_issues']==['empty_answer']
    assert reply.metadata['turn_review']['attempts']==2


def test_benchmark_entrypoint_accepts_actual_bridge_keyword():
    import inspect
    from allma_model.llm.dialogue_reasoning_diagnostics import DialogueReasoningRun
    assert 'existing_brain' in inspect.signature(DialogueReasoningRun.setup_brain).parameters


def test_unavailable_validator_never_publishes_an_unchecked_revision(core):
    from allma_model.core.cognitive_pipeline import CognitiveValidationError
    cid=seed(core)
    core._llm.generate.side_effect=[OLD,NEW]
    original=core.cognitive_pipeline.process
    count=0
    def validate(*args,**kwargs):
        nonlocal count
        count+=1
        if count==2:raise CognitiveValidationError('synthetic validator unavailable')
        return original(*args,**kwargs)
    core.cognitive_pipeline.process=validate
    reply=core.process_message('test-owner',cid,'Spiega come funziona una bussola. Rispondi in una frase.')
    assert not reply.is_valid and reply.content==''
    assert reply.metadata['turn_review']['repair_status']=='revision_unavailable'
    core.answer_recall.observe.assert_not_called()
