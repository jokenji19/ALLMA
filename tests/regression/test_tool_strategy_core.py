"""Before/after procedural learning through the real ALLMA turn pipeline."""
from unittest.mock import Mock
import pytest
from tests.regression.test_exact_text_core import core

TASKS=[('ana','banana'),('aa','aaaa'),('aba','ababa')]


def teach(core,cid,needle,text,*,user='u',confirm=True):
    question=f'Quante volte compare "{needle}" in "{text}"? Rispondi solo con un numero.'
    first=core.process_message(user,cid,question)
    assert first.metadata['source']=='text_count_clarification'
    result=core.process_message(user,cid,'Con le sovrapposizioni')
    assert result.metadata['source']=='verified_text_count'
    if confirm:
        feedback=core.process_message(user,cid,'Risposta corretta')
        assert feedback.is_valid and feedback.metadata['source']=='tool_learning_feedback'
    return result


def test_real_learning_changes_suggestion_on_an_unseen_task_without_a_model(core):
    cid=core.start_conversation('u')
    for needle,text in TASKS:teach(core,cid,needle,text)
    learning=core.meta_learner.tool_learning
    assert learning.view('u')['confirmed_tasks']==3
    prompt='Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
    proposed=core.process_message('u',cid,prompt)
    assert proposed.metadata['evidence'][0]['strategy_source']=='meta_learning'
    assert proposed.metadata['evidence'][0]['suggested_overlap'] is True
    assert not proposed.metadata['knowledge_verified']
    result=core.process_message('u',cid,'sì')
    assert result.content=='2' and result.metadata['knowledge_verified']
    core.process_message('u',cid,'Risposta corretta')
    assert learning.view('u')['confirmed_tasks']==3
    core._llm.generate.assert_not_called()
    assert not core.answer_recall.records
    assert not core.incremental_learner.knowledge_base
    events=core.brain_activity.snapshot()['events']
    assert any(e['module']=='meta_learning' for e in events)


def test_one_choice_without_a_confirmation_is_not_a_preference(core):
    cid=core.start_conversation('u')
    teach(core,cid,*TASKS[0],confirm=False)
    next_question=core.process_message('u',cid,'Quante volte compare "aa" in "aaaa"?')
    assert 'suggested_overlap' not in next_question.metadata['evidence'][0]
    assert core.meta_learner.tool_learning.view('u')['confirmed_tasks']==0


def test_repeated_approval_and_then_correction_update_one_example(core):
    cid=core.start_conversation('u')
    for needle,text in TASKS:teach(core,cid,needle,text)
    for _ in range(3):core.process_message('u',cid,'Risposta corretta')
    assert core.meta_learner.tool_learning.view('u')['confirmed_tasks']==3
    correction=core.process_message('u',cid,'Risposta sbagliata')
    assert correction.metadata['source']=='tool_learning_feedback'
    assert core.meta_learner.tool_learning.view('u')['confirmed_tasks']==2
    assert core.meta_learner.tool_learning.view('u')['suggested_overlap'] is None
    core._llm.generate.assert_not_called()


def test_learned_state_and_transfer_survive_restart_without_crossing_users(core):
    from allma_model.core.allma_core import ALLMACore
    cid=core.start_conversation('u')
    for needle,text in TASKS:teach(core,cid,needle,text)
    database=core.db_path;core.close()
    restored=ALLMACore(mobile_mode=True,db_path=database)
    restored._llm=Mock();restored._ensure_mobile_llm=lambda:None
    try:
        new_chat=restored.start_conversation('u')
        question='Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
        proposal=restored.process_message('u',new_chat,question)
        assert proposal.metadata['evidence'][0]['suggested_overlap'] is True
        other=restored.process_message('other',restored.start_conversation('other'),question)
        assert 'suggested_overlap' not in other.metadata['evidence'][0]
        assert restored.process_message('u',new_chat,'sì').content=='2'
        restored._llm.generate.assert_not_called()
    finally:restored.close()


def test_explicit_reset_and_inspection_are_honest_and_saved(core):
    cid=core.start_conversation('u')
    teach(core,cid,*TASKS[0])
    view=core.process_message('u',cid,'Cosa hai imparato sui conteggi?')
    assert view.metadata['tool_learning']['confirmed_tasks']==1
    assert not view.metadata['knowledge_verified']
    reset=core.process_message('u',cid,'Dimentica le strategie di conteggio apprese')
    assert reset.is_valid and reset.metadata['tool_learning']['status']=='reset'
    assert core.meta_learner.tool_learning.view('u')['confirmed_tasks']==0
    assert len(core.conversational_memory.get_conversation_history(cid))>=8
    core._llm.generate.assert_not_called()


def test_learning_write_failure_does_not_destroy_a_verified_answer(core):
    cid=core.start_conversation('u')
    core.meta_learner.tool_learning.store.transact_state=Mock(side_effect=OSError('synthetic disk full'))
    result=core.process_message('u',cid,'Quante lettere contiene JSON? Rispondi solo con un numero.')
    assert result.content=='4' and result.is_valid and result.metadata['knowledge_verified']
    assert result.metadata['tool_learning']['status']=='not_saved'
    ack=core.process_message('u',cid,'Risposta corretta')
    assert not ack.is_valid and ack.metadata['tool_learning']['status']=='unavailable'
    core._llm.generate.assert_not_called()


def test_failed_conversation_write_cannot_train_on_a_phantom_answer(core):
    cid=core.start_conversation('u')
    learning=core.meta_learner.tool_learning
    core.conversational_memory.store_message=Mock(side_effect=OSError('synthetic conversation failure'))
    with pytest.raises(OSError):core.process_message('u',cid,'Quante lettere contiene JSON?')
    assert learning.view('u')['executions']=={}


def test_unknown_model_answer_does_not_create_verified_experience(core):
    core._llm.generate.return_value='Una spiegazione generica.'
    core.process_message('u',core.start_conversation('u'),'Spiega come funziona un arcobaleno.')
    assert core.meta_learner.tool_learning.view('u')['executions']=={}


def test_interrupted_experience_is_recovered_once_from_saved_history(core):
    from allma_model.core.allma_core import ALLMACore
    from unittest.mock import patch
    cid=core.start_conversation('u')
    learner=core.meta_learner.tool_learning
    with patch.object(learner.store,'transact_state',side_effect=OSError('synthetic interrupted write')):
        result=core.process_message('u',cid,'Quante lettere contiene JSON? Rispondi solo con un numero.')
        assert result.content=='4' and result.metadata['tool_learning']['status']=='not_saved'
    path=core.db_path;core.close()
    restored=ALLMACore(mobile_mode=True,db_path=path)
    try:
        assert restored.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
        assert restored.delivery_updates.recover()['pending']==0
        assert restored.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
    finally:restored.close()


def test_interrupted_journal_acknowledgement_cannot_count_one_tool_execution_twice(core):
    from unittest.mock import patch
    original=core.delivery_updates._ack
    def interrupted(event,completed):
        if completed==['tool_learning']:raise OSError('synthetic lost acknowledgement')
        return original(event,completed)
    with patch.object(core.delivery_updates,'_ack',side_effect=interrupted):
        result=core.process_message('u',core.start_conversation('u'),'Quante lettere contiene JSON?')
    assert result.is_valid and core.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
    assert core.delivery_updates.recover()['pending']==0
    assert core.meta_learner.tool_learning.view('u')['executions']=={'letters':1}
