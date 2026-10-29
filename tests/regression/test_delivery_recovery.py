from copy import deepcopy
import json
import sqlite3
from unittest.mock import Mock, patch
from pathlib import Path
import os
import subprocess
import sys
import pytest


@pytest.fixture
def make_core(tmp_path):
    from allma_model.core.allma_core import ALLMACore
    instances = []
    def create():
        core = ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
        core._ensure_mobile_llm = lambda: None
        core._llm = Mock()
        core._llm.generate.return_value = 'La luce bianca contiene diversi colori.'
        core._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
        instances.append(core)
        return core
    yield create
    for core in instances:
        core.close()


def ask(core, question='Spiegami come funziona la luce bianca.'):
    return core.process_message('u', core.start_conversation('u'), question)


def counts(core):
    with sqlite3.connect(core.db_path) as db:
        knowledge = db.execute('SELECT COUNT(*) FROM knowledge_delivery_events').fetchone()[0]
    return (sum(len(v) for v in core.incremental_learner.knowledge_base.values()),
            sum(v['observations'] for v in core.answer_recall.records.values()),
            knowledge, core.identity_engine_v5.accepted_turns)


def test_assistant_save_failure_cannot_publish_recall_or_delivery_learning(make_core):
    core = make_core()
    original = core.conversational_memory.store_message
    def store(*args,**kwargs):
        if kwargs.get('role')=='assistant':
            raise OSError('full')
        return original(*args,**kwargs)
    core.conversational_memory.store_message = store
    with pytest.raises(OSError):
        ask(core)
    assert counts(core)==(0,0,0,0)
    with sqlite3.connect(core.db_path) as db:
        intents=[json.loads(row[0]) for row in db.execute('SELECT intent FROM delivery_updates')]
        assert all(intent['kind']=='experience' for intent in intents)


def test_failed_first_effect_is_recovered_on_restart(make_core):
    core = make_core()
    with patch.object(core.answer_recall,'_save',side_effect=OSError('full')):
        result = ask(core)
    assert result.is_valid
    assert result.metadata['delivery_updates']['status']=='pending'
    assert counts(core)==(0,0,0,0)
    core.close()
    restored = make_core()
    assert restored.delivery_recovery['status']=='completed'
    assert counts(restored)==(1,1,1,1)
    assert restored.delivery_updates.recover()['pending']==0
    assert counts(restored)==(1,1,1,1)


@pytest.mark.parametrize('action', ['answer_recall','incremental_learning','knowledge_memory','neuroplasticity','identity_state'])
def test_crash_after_component_save_before_ack_is_idempotent(make_core,action):
    core = make_core()
    original = core.delivery_updates._ack
    failed = False
    def ack(event,completed):
        nonlocal failed
        if completed[-1]==action and not failed:
            failed = True
            raise OSError('ack interrupted')
        return original(event,completed)
    with patch.object(core.delivery_updates,'_ack',side_effect=ack):
        result = ask(core)
    assert result.is_valid and result.metadata['delivery_updates']['status']=='pending'
    core.close()
    restored = make_core()
    assert counts(restored)==(1,1,1,1)
    assert restored.delivery_recovery['pending']==0


def test_history_recovers_an_intent_missing_from_the_journal(make_core):
    core = make_core()
    with patch.object(core.delivery_updates,'_enqueue',side_effect=OSError('journal unavailable')):
        result = ask(core)
    assert result.is_valid and counts(core)==(0,0,0,0)
    assert core.conversational_memory.messages[-1].metadata['delivery_update']
    core.close()
    restored = make_core()
    assert counts(restored)==(1,1,1,1)


def test_rebuilding_the_journal_cannot_relearn_completed_answers(make_core):
    core = make_core()
    assert ask(core).is_valid
    assert counts(core)==(1,1,1,1)
    with sqlite3.connect(core.db_path) as db:
        db.execute('DELETE FROM delivery_updates')
    core.close()
    restored = make_core()
    assert restored.delivery_recovery['pending']==0
    assert counts(restored)==(1,1,1,1)


def test_pending_events_keep_order_and_do_not_skip_a_failed_event(make_core):
    core = make_core()
    with patch.object(core.answer_recall,'_save',side_effect=OSError('full')):
        assert ask(core).is_valid
        core._llm.generate.return_value = 'Una lente convergente devia la luce.'
        assert ask(core,'Spiegami il funzionamento di una lente.').is_valid
    assert counts(core)==(0,0,0,0)
    assert core.delivery_updates.recover()['pending']==0
    assert counts(core)==(2,2,2,2)


def test_changed_or_missing_source_is_not_relearned(make_core):
    core = make_core()
    with patch.object(core.answer_recall,'_save',side_effect=OSError('full')):
        ask(core)
    answer = core.conversational_memory.messages[-1]
    answer.content = 'Testo diverso da quello ammesso.'
    core.conversational_memory.save_memory()
    report = core.delivery_updates.recover()
    assert report['pending']==0
    assert counts(core)==(0,0,0,0)
    with sqlite3.connect(core.db_path) as db:
        assert db.execute('SELECT state FROM delivery_updates').fetchone()[0]=='abandoned'


def test_rejected_output_cannot_create_a_delivery_intent(make_core):
    core = make_core()
    core._llm.generate.return_value = 'La risposta è verificata da fonti che ho consultato.'
    result = ask(core)
    assert not result.is_valid
    assert 'delivery_update' not in result.metadata
    assert counts(core)==(0,0,0,0)


def test_journal_contains_references_and_not_question_or_answer_text(make_core):
    core = make_core()
    result = ask(core)
    assert result.is_valid
    with sqlite3.connect(core.db_path) as db:
        encoded = next(row[0] for row in db.execute('SELECT intent FROM delivery_updates')
                       if json.loads(row[0]).get('kind')=='answer')
    assert 'Spiegami come funziona la luce bianca.' not in encoded
    assert result.content not in encoded
    intent=json.loads(encoded)
    assert intent['user']=='u' and intent['answer_sha256']


def test_failed_checkpoint_save_leaves_learning_state_and_sequence_unchanged(tmp_path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    interaction={'input':'La bussola indica il nord','topic':'navigazione'}
    learner.learn_from_interaction(interaction,'u',delivery_sequence=10)
    before=deepcopy(learner.knowledge_base)
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=OSError('full')):
        with pytest.raises(OSError):
            learner.learn_from_interaction(interaction,'u',delivery_sequence=11)
    assert learner.delivery_checkpoint==10 and learner.knowledge_base==before
    restored=IncrementalLearner(learner.storage_path)
    restored.learn_from_interaction(interaction,'u',delivery_sequence=10)
    assert len(restored.knowledge_base['navigazione'])==1


def test_user_experience_survives_personality_write_failure_and_restart(make_core):
    core=make_core()
    with patch.object(core.coalescence_processor._state_store,'put',side_effect=OSError('full')):
        result=ask(core,'Preferisco risposte brevi.')
    assert not result.is_valid
    assert core.coalescence_processor.experience_checkpoint==0
    core._llm.generate.assert_not_called()
    core.close()
    restored=make_core()
    assert restored.delivery_recovery['pending']==0
    assert restored.coalescence_processor.expression_view('u')['preferences']['verbosity']=='brief'
    assert counts(restored)==(0,0,0,0)


def test_personality_saved_before_ack_is_not_counted_again(make_core):
    core=make_core()
    original=core.delivery_updates._ack
    def interrupted(event,completed):
        if completed[-1]=='personality_growth':
            raise OSError('ack interrupted')
        return original(event,completed)
    with patch.object(core.delivery_updates,'_ack',side_effect=interrupted):
        ask(core,'Sono felice per il risultato di oggi.')
    before=core.coalescence_processor.emotion_growth_view('u')
    assert before['associations']['joy']['observations']==1
    core.close()
    restored=make_core()
    assert restored.coalescence_processor.emotion_growth_view('u')==before
    assert restored.delivery_recovery['pending']==0


def test_historical_unmarked_user_messages_are_not_silently_relearned(make_core):
    core=make_core()
    cid=core.start_conversation('u')
    core.conversational_memory.store_message(cid,'Sono felice per una vecchia esperienza.',role='user',user_id='u')
    core.close()
    restored=make_core()
    assert not restored.coalescence_processor.emotion_growth_view('u')['associations']
    assert restored.coalescence_processor.experience_checkpoint==0


def test_hybrid_memory_reaches_the_real_core_prompt_with_original_source(make_core):
    core=make_core()
    old=core.start_conversation('u')
    source='Il mio ombrello è riposto nell’armadio.'
    core.conversational_memory.store_message(old,source,role='user',user_id='u')
    core._llm.generate.return_value='Hai indicato che l’ombrello è nell’armadio.'
    result=ask(core,'Dove posso trovare ciò che uso per ripararmi dalla pioggia?')
    assert result.is_valid
    assert source in str(core._llm.generate.call_args)
    assert result.metadata['memory_score']>0


@pytest.mark.parametrize('section',['identity_state','neuroplasticity','personality'])
@pytest.mark.parametrize('checkpoint',[-1,True,'invalid',2**53])
def test_damaged_cognitive_receipt_cannot_reset_and_replay_updates(tmp_path,section,checkpoint):
    from allma_model.utils.cognitive_state import CognitiveStateStore
    from allma_model.core.architecture.identity_state import IdentityStateEngine
    from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem
    from allma_model.core.personality_coalescence import CoalescenceProcessor
    path=str(tmp_path/'core.db')
    store=CognitiveStateStore(path)
    store.put(section,{'experience_checkpoint' if section=='personality' else 'delivery_checkpoint':checkpoint})
    before=store.path.read_bytes()
    constructor={'identity_state':IdentityStateEngine,'neuroplasticity':NeuroplasticitySystem,
                 'personality':CoalescenceProcessor}[section]
    with pytest.raises(ValueError,match='checkpoint'):
        constructor(path)
    assert store.path.read_bytes()==before


@pytest.mark.parametrize('checkpoint',[-1,True,'invalid',2**53])
def test_invalid_recall_checkpoint_preserves_original_and_blocks_replay(tmp_path,checkpoint):
    from allma_model.learning_system.answer_recall import AnswerRecall
    from allma_model.utils.persistence import StateRecoveryRequired
    path=tmp_path/'recall.json'
    path.write_text(json.dumps({'version':1,'delivery_checkpoint':checkpoint,'records':{}}))
    before=path.read_bytes()
    recall=AnswerRecall(path)
    with pytest.raises(StateRecoveryRequired):
        recall.observe('k','u','Spiegami la luce bianca','Contiene diversi colori.','e',delivery_sequence=1)
    assert path.read_bytes()==before and not recall.records


@pytest.mark.parametrize('action',['incremental_learning','personality_growth','tool_learning','goal_tracking','goal_plan_step','goal_plan_review'])
def test_abrupt_process_exit_after_component_save_can_recover(tmp_path,action):
    # Deliberately bypass finally/close: persisted receipts must be sufficient.
    script='''
import os,sys
from unittest.mock import Mock
from allma_model.core.allma_core import ALLMACore
core=ALLMACore(mobile_mode=True,db_path=sys.argv[1])
core._ensure_mobile_llm=lambda:None
core._llm=Mock()
core._llm.generate.return_value='La luce bianca contiene diversi colori.'
core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
original=core.delivery_updates._ack
def ack(event,completed):
    if (sys.argv[2]=='goal_plan_review' and completed[-1]=='goal_tracking'
            and core.goal_progress.report(core.goal_progress.delivery_checkpoint).get('status')=='review_required'):os._exit(73)
    if (sys.argv[2]=='goal_plan_step' and completed[-1]=='goal_tracking'
            and core.goal_progress.goals('u')[0]['workflow'].get('plan',{}).get('index')==1):os._exit(73)
    if completed[-1]==sys.argv[2]:os._exit(73)
    return original(event,completed)
core.delivery_updates._ack=ack
if sys.argv[2] in ('goal_plan_step','goal_plan_review'):
    cid=core.start_conversation('u')
    core._llm.generate.return_value='1. Scrivi tre voci distinte nella lista.\\n2. Controlla ogni voce e correggi gli errori.'
    if sys.argv[2]=='goal_plan_review':core._llm.generate.return_value='1. Scrivi tre voci distinte nella lista.\\n2. Controlla una voce della lista finale.'
    for text in ['Nuovo obiettivo: Lista sintetica\\nCriterio: tre voci controllate',
                 'Proponi un piano per questo obiettivo','Adotta questo piano',
                 'Risultato del passo: tre voci scritte','Confermo il risultato del passo']:
        core.process_message('u',cid,text)
    raise RuntimeError('Step exit checkpoint not reached')
message=('Sono felice per il risultato di oggi.' if sys.argv[2]=='personality_growth' else
         'Quante lettere contiene JSON?' if sys.argv[2]=='tool_learning' else
         'Nuovo obiettivo: Lista sintetica' if sys.argv[2]=='goal_tracking' else 'Spiegami come funziona la luce bianca.')
core.process_message('u',core.start_conversation('u'),message)
raise RuntimeError('Abrupt-exit checkpoint not reached')
'''
    root=Path(__file__).resolve().parents[2]
    env=dict(os.environ,PYTHONPATH=str(root),KIVY_NO_ARGS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path/'core.db'),action],
                          cwd=tmp_path,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    assert result.returncode==73,result.stdout.decode(errors='replace')[-1500:]
    from allma_model.core.allma_core import ALLMACore
    restored=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    try:
        assert restored.delivery_recovery['pending']==0
        if action=='incremental_learning':
            assert counts(restored)==(1,1,1,1)
        elif action=='tool_learning':
            assert restored.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
            restored.delivery_updates.recover(synchronize=True)
            assert restored.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
        elif action=='goal_tracking':
            goals=restored.goal_progress.goals('u')
            assert len(goals)==1 and goals[0]['objective']=='Lista sintetica'
            restored.delivery_updates.recover(synchronize=True)
            assert restored.goal_progress.goals('u')==goals
        elif action=='goal_plan_step':
            assert restored.goal_progress.goals('u')[0]['workflow']['plan']['index']==1
            learning=restored.goal_progress.goals('u')[0]['workflow']['learning']
            assert list(learning['cases'])==['step_0_confirmed']
            restored.delivery_updates.recover(synchronize=True)
            assert restored.goal_progress.goals('u')[0]['workflow']['plan']['index']==1
            assert restored.goal_progress.goals('u')[0]['workflow']['learning']==learning
        elif action=='goal_plan_review':
            goal=restored.goal_progress.goals('u')[0]
            assert goal['workflow'].get('plan') is None and 'learning' not in goal['workflow']
            assert restored.goal_progress.report(restored.goal_progress.delivery_checkpoint)['status']=='review_required'
        else:
            assert restored.coalescence_processor.emotion_growth_view('u')['associations']['joy']['observations']==1
    finally:
        restored.close()
