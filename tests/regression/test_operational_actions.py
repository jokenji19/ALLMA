from types import SimpleNamespace
from unittest.mock import Mock
import threading
import pytest
from allma_model.agency_system.operational_actions import memory_step, retrieve_user_memory
from allma_model.agency_system.action_authority import ActionAuthority
from allma_model.utils.cognitive_state import CognitiveStateStore


def setup(tmp_path, records):
    store=CognitiveStateStore(str(tmp_path/'state.db'))
    memory=SimpleNamespace(vector_engine=Mock())
    memory.vector_engine.search.return_value=records
    return SimpleNamespace(action_authority=ActionAuthority(store), conversational_memory=memory)


def record(content='My walk', **metadata):
    return {'content':content, 'metadata':{'role':'user','user_id':'u',**metadata},'score':.9}


def test_selected_memory_executes_once_without_native_inference_and_persists_only_counts(tmp_path):
    core=setup(tmp_path,[record()])
    records, result=memory_step(core,'u','Remember my walk?',{'status':'selected','choice':'memory'})
    assert records[0]['content']=='My walk'
    core.conversational_memory.vector_engine.search.assert_called_once_with(
        user_id='u',query='Remember my walk?',top_k=3,use_expansion=True,allowed_roles=('user',),exclude_query_replays=True)
    assert result['status']=='observed' and result['additional_inferences']==0
    assert result['proposal_source']=='decider'
    assert 'My walk' not in core.action_authority.store.path.read_text()
    assert core.action_authority.active_goals('u')==[]
    assert core.action_authority.store.get('action_authority')=={}
    assert next(iter(core.action_authority.store.get('decision_outcomes').values()))['with_records']==1


def test_host_personal_lookup_survives_bad_reason_route(tmp_path):
    core=setup(tmp_path,[record()])
    found, result=memory_step(core,'u','my walk',{'status':'selected','choice':'reason'})
    assert found and result['proposal_source']=='host_memory_policy'


def test_no_match_is_not_a_verified_answer(tmp_path):
    core=setup(tmp_path,[])
    found,result=memory_step(core,'u','missing',{'status':'selected','choice':'memory'})
    assert found==[] and result['status']=='observed' and result['record_count']==0
    assert result['evidence_kind']=='user_reports_not_world_verification'


@pytest.mark.parametrize('bad',[record(role='assistant'), record(user_id='other'),record(is_valid=False),
                                   {**record(),'score':float('nan')}, {**record(),'score':2},record('')])
def test_invalid_or_foreign_evidence_never_enters_context(tmp_path,bad):
    core=setup(tmp_path,[bad])
    found,_=memory_step(core,'u','my walk',{})
    assert found==[]


def test_cancelled_scope_does_not_execute_or_learn(tmp_path):
    core=setup(tmp_path,[record()]); event=threading.Event();event.set()
    found,result=memory_step(core,'u','x',{},event)
    assert found==[] and result['status']=='cancelled'
    core.conversational_memory.vector_engine.search.assert_not_called()
    assert core.action_authority.store.get('decision_outcomes')=={}


def test_backend_failure_no_retry_no_evidence_and_scope_revoked(tmp_path):
    core=setup(tmp_path,[])
    core.conversational_memory.vector_engine.search.side_effect=RuntimeError('private data')
    found,result=memory_step(core,'u','x',{})
    assert found==[] and result['status']=='action_failed'
    assert 'private data' not in str(result)
    assert core.conversational_memory.vector_engine.search.call_count==1


def test_turn_scope_expires_and_never_widens_persistent_grants():
    authority=ActionAuthority()
    with authority.turn_scope('u','look up',allowed_actions={'memory':'read'}) as (child,goal):
        assert child.permits('u',goal,'memory','read')
        assert not child.permits('other',goal,'memory','read')
    assert not child.permits('u',goal,'memory','read')
    with pytest.raises(ValueError):
        with authority.turn_scope('u','write',allowed_actions={'save':'memory_write'}):pass


def test_tfidf_scope_and_role_checked(tmp_path):
    core=setup(tmp_path,[]);core.conversational_memory.vector_engine=None
    make=lambda u,r:SimpleNamespace(user_id=u,metadata={'role':r},content='Report',timestamp=None)
    core.conversational_memory.retrieve_relevant_context=Mock(return_value=[(.8,make('other','user')),
        (.7,make('u','assistant')),(.6,make('u','user'))])
    assert len(retrieve_user_memory(core.conversational_memory,'u','x'))==1
