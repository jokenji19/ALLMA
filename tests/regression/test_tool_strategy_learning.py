"""Experience changes a bounded procedural policy, never numerical truth."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.core.module_state_manager import ModuleStateManager
from allma_model.learning_system.tool_strategy_learning import ToolStrategyLearning
from allma_model.utils.exact_text import text_count_reply

TASKS = [('ana','banana'),('aa','aaaa'),('aba','ababa')]


@pytest.fixture
def learning(tmp_path):
    return ToolStrategyLearning(ModuleStateManager(str(tmp_path/'modules.db')))


def episode(learning, needle, text, choice=True, *, user='u', approve=True, origin=None):
    question = f'Quante volte compare "{needle}" in "{text}"? Rispondi solo con un numero.'
    pending = text_count_reply(question)
    history = [SimpleNamespace(role='user', content=question),
               SimpleNamespace(role='assistant', metadata={'source':pending[1], 'evidence':pending[2]})]
    result = text_count_reply('Con le sovrapposizioni' if choice else 'Senza sovrapposizioni', history=history)
    if origin:
        result[2][0]['choice_origin'] = origin
    descriptor = learning.descriptor(user,result[1],result[2],verified=True)
    assert descriptor is not None
    learning.observe(user, descriptor)
    if approve is not None:
        learning.feedback(user, descriptor, approve)
    return descriptor


def test_empty_and_single_experience_do_not_become_a_stable_preference(learning):
    assert learning.view('u')['suggested_overlap'] is None
    episode(learning,*TASKS[0])
    assert learning.view('u')['confirmed_tasks'] == 1
    assert learning.view('u')['suggested_overlap'] is None


def test_three_independent_approved_choices_change_policy_and_transfer_to_unseen_text(learning):
    for needle,text in TASKS:
        episode(learning,needle,text)
    view = learning.view('u')
    assert view['confirmed_tasks'] == 3 and view['suggested_overlap'] is True
    assert view['support'] == .8 and view['requires_confirmation']
    question = 'Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
    result = text_count_reply(question,suggestion=view)
    assert result[1] == 'text_count_clarification'
    assert result[2][0]['suggested_overlap'] is True
    assert 'Vuoi usare questo criterio anche qui?' in result[0]
    history=[SimpleNamespace(role='user',content=question),SimpleNamespace(role='assistant',metadata={'source':result[1],'evidence':result[2]})]
    final = text_count_reply('sì',history=history)
    assert final[0] == '2' and final[2][0]['choice_origin'] == 'learned_suggestion_response'
    descriptor = learning.descriptor('u',final[1],final[2],verified=True)
    learning.observe('u',descriptor);learning.feedback('u',descriptor,True)
    assert learning.view('u')['confirmed_tasks'] == 3, 'Suggested answers cannot reward their own policy'


@pytest.mark.parametrize('positive', [None,False])
def test_unapproved_executions_cannot_produce_a_suggestion(learning,positive):
    for needle,text in TASKS:
        episode(learning,needle,text,approve=positive)
    assert learning.view('u')['executions']['occurrences'] == 3
    assert learning.view('u')['confirmed_tasks'] == 0
    assert learning.view('u')['suggested_overlap'] is None


def test_same_task_and_repeated_feedback_cannot_manufacture_independent_evidence(learning):
    for _ in range(6):
        descriptor=episode(learning,*TASKS[0])
        assert learning.feedback('u',descriptor,True)['status']=='duplicate_feedback'
    assert learning.view('u')['confirmed_tasks']==1


def test_preference_can_point_the_other_way_and_correction_withdraws_it(learning):
    for needle,text in TASKS:
        descriptor=episode(learning,needle,text,False)
    assert learning.view('u')['suggested_overlap'] is False
    learning.feedback('u',descriptor,False)
    assert learning.view('u')['confirmed_tasks']==2
    assert learning.view('u')['suggested_overlap'] is None


def test_state_survives_restart_and_is_scoped_per_user(learning):
    for needle,text in TASKS:episode(learning,needle,text)
    restored=ToolStrategyLearning(ModuleStateManager(learning.store.db_path))
    assert restored.view('u')['suggested_overlap'] is True
    assert restored.view('other')['confirmed_tasks']==0


def test_reset_invalidates_old_feedback_and_does_not_resurrect_erased_votes(learning):
    descriptor=episode(learning,*TASKS[0])
    learning.reset('u')
    assert learning.view('u')['confirmed_tasks']==0
    assert learning.feedback('u',descriptor,True)['status']=='stale'
    assert learning.observe('u',descriptor)['status']=='stale'


@pytest.mark.parametrize('verified',[None,False,1,'true'])
def test_model_or_unverified_output_is_not_admitted(learning,verified):
    result=text_count_reply('Quante lettere contiene JSON?')
    assert learning.descriptor('u',result[1],result[2],verified=verified) is None
    assert learning.descriptor('u','model_generated',result[2],verified=True) is None
    assert learning.view('u')['executions']=={}


def test_malformed_provenance_is_not_admitted(learning):
    result=text_count_reply('Quante lettere contiene JSON?')
    evidence=deepcopy(result[2]);evidence[0].pop('input_sha256')
    assert learning.descriptor('u',result[1],evidence,verified=True) is None


def test_bad_state_is_preserved_instead_of_becoming_a_new_empty_profile(learning):
    invalid={'version':99,'epoch':0,'executions':{},'events':{},'votes':{}}
    learning.store.save_state(learning.key('u'),invalid)
    with pytest.raises(ValueError):learning.view('u')
    with pytest.raises(ValueError):learning.reset('u')
    assert learning.store.load_state(learning.key('u'))==invalid


def test_sql_failure_leaves_votes_unchanged_and_can_retry(learning):
    descriptor=episode(learning,*TASKS[0],approve=None)
    original=learning.store.transact_state
    learning.store.transact_state=Mock(side_effect=OSError('synthetic disk failure'))
    with pytest.raises(OSError):learning.feedback('u',descriptor,True)
    assert learning.view('u')['confirmed_tasks']==0
    learning.store.transact_state=original
    learning.feedback('u',descriptor,True)
    assert learning.view('u')['confirmed_tasks']==1


def test_atomic_updates_do_not_lose_experiences_between_instances(learning):
    result=text_count_reply('Quante lettere contiene JSON?')
    descriptors=[learning.descriptor('u',result[1],result[2],verified=True) for _ in range(16)]
    def observe(descriptor):
        other=ToolStrategyLearning(ModuleStateManager(learning.store.db_path))
        return other.observe('u',descriptor)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(observe,descriptors))
    assert learning.view('u')['executions']['letters']==16


def test_store_contains_no_literal_operands_or_answers(learning):
    episode(learning,'privapriva','privaprivapriva')
    state=learning.store.load_state(learning.key('u'))
    serialized=json.dumps(state)
    assert 'priva' not in serialized and 'banana' not in serialized


def test_foreign_user_receipt_cannot_train_another_profile(learning):
    descriptor=episode(learning,*TASKS[0])
    assert learning.observe('other',descriptor)['status']=='not_verified'
    assert learning.feedback('other',descriptor,True)['status']=='not_saved'
    assert learning.view('other')['confirmed_tasks']==0


def test_declining_a_suggestion_leaves_choice_open_without_losing_the_original_operands(learning):
    for needle,text in TASKS:episode(learning,needle,text)
    question='Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
    first=text_count_reply(question,suggestion=learning.view('u'))
    history=[SimpleNamespace(role='user',content=question),SimpleNamespace(role='assistant',metadata={'source':first[1],'evidence':first[2]})]
    declined=text_count_reply('no',history=history,suggestion=learning.view('u'))
    assert declined[1]=='text_count_clarification'
    assert 'suggested_overlap' not in declined[2][0]
    history += [SimpleNamespace(role='user',content='no'),SimpleNamespace(role='assistant',metadata={'source':declined[1],'evidence':declined[2]})]
    final=text_count_reply('Senza sovrapposizioni',history=history)
    assert final[0]=='1'


def test_suggestion_state_is_not_read_for_an_unambiguous_operation():
    view=Mock(side_effect=AssertionError('Unnecessary learning lookup'))
    assert text_count_reply('Quante lettere contiene JSON?',suggestion=view)[0]=='4 lettere.'
    view.assert_not_called()


def test_negative_feedback_on_a_suggested_choice_reduces_confidence_without_rewriting_math(learning):
    for needle,text in TASKS:episode(learning,needle,text)
    question='Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
    first=text_count_reply(question,suggestion=learning.view('u'))
    history=[SimpleNamespace(role='user',content=question),SimpleNamespace(role='assistant',metadata={'source':first[1],'evidence':first[2]})]
    result=text_count_reply('sì',history=history)
    descriptor=learning.descriptor('u',result[1],result[2],verified=True)
    learning.observe('u',descriptor);learning.feedback('u',descriptor,False)
    assert result[0]=='2'
    assert learning.view('u')['confirmed_tasks']==3
    assert learning.view('u')['rejected_tasks']==1
    assert learning.view('u')['suggested_overlap'] is None
    learning.feedback('u',descriptor,True)
    assert learning.view('u')['confirmed_tasks']==3
    assert learning.view('u')['rejected_tasks']==0


def test_malformed_json_is_preserved_on_read_and_update(learning):
    import sqlite3
    result=text_count_reply('Quante lettere contiene JSON?')
    descriptor=learning.descriptor('u',result[1],result[2],verified=True)
    with sqlite3.connect(learning.store.db_path) as db:
        db.execute('INSERT INTO module_states(module_name,state_json) VALUES(?,?)',(learning.key('u'),'{broken'))
    with pytest.raises(ValueError):learning.view('u')
    with pytest.raises(ValueError):learning.observe('u',descriptor)
    with sqlite3.connect(learning.store.db_path) as db:
        assert db.execute('SELECT state_json FROM module_states WHERE module_name=?',(learning.key('u'),)).fetchone()[0]=='{broken'


def test_state_transaction_rolls_back_when_new_json_cannot_be_encoded(learning):
    learning.store.save_state('probe',{'count':1})
    with pytest.raises(ValueError):
        learning.store.transact_state('probe',lambda old:{'count':2,'invalid':float('nan')})
    assert learning.store.load_state('probe')=={'count':1}


@pytest.mark.parametrize('message',['Hai sbagliato: il codice di prova è NUOVO-123.',
    'Ti sbagli, mi chiamo Elena.','Spiega la frase "Risposta corretta".','Non dire risposta corretta.'])
def test_feedback_does_not_consume_new_user_facts_or_quoted_instructions(message):
    from allma_model.learning_system.tool_strategy_learning import feedback_signal
    assert feedback_signal(message) is None
