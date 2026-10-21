import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.agency_system.decision_runtime import DecisionRuntime
from allma_model.agency_system.decision_engine import Decision, DECIDER_MODEL
from allma_model.utils.cognitive_state import CognitiveStateStore


def runtime(tmp_path):
    model=tmp_path/'models'/'decider-0.8b'/DECIDER_MODEL['filename']
    model.parent.mkdir(parents=True);model.write_bytes(b'fixture')
    engine=Mock();engine.decide.return_value=Decision('reason',{'reason':.95},'selected',4)
    factory=Mock(return_value=engine)
    obj=DecisionRuntime(tmp_path/'models',CognitiveStateStore(str(tmp_path/'state'/'allma.db')),factory=factory)
    return obj,engine,factory


def test_operational_shared_load_once_and_no_personal_state_writes(tmp_path):
    obj,engine,factory=runtime(tmp_path)
    for _ in range(3):
        assert obj.route('Spiega gli arcobaleni')['choice']=='reason'
    factory.assert_called_once();engine.load.assert_called_once()
    assert not obj.store.path.exists()
    obj.release();engine.close.assert_called_once()
    assert not obj.status()['loaded']


def test_optout_persisted_and_never_loads_when_disabled(tmp_path):
    obj,engine,factory=runtime(tmp_path)
    obj.configure(False)
    assert obj.route('x')['status']=='disabled'
    factory.assert_not_called()
    restored=DecisionRuntime(obj.path.parent.parent,obj.store,factory=factory)
    assert not restored.enabled
    with pytest.raises(ValueError):obj.configure('true')


def test_heat_missing_busy_and_closed_preserve_host_fallback(tmp_path):
    obj,engine,factory=runtime(tmp_path)
    obj.temperature=lambda:43
    assert obj.route('x')['status']=='thermal_pause'
    factory.assert_not_called()
    obj.temperature=None
    obj._lock.acquire()
    try:assert obj.route('x')['status']=='busy'
    finally:obj._lock.release()
    obj.path.unlink()
    assert obj.route('x')['status']=='model_missing'
    obj.close()
    assert obj.route('x')['status']=='closed'


def test_errors_do_not_retry_every_turn_and_cancellation_discards_result(tmp_path):
    obj,engine,factory=runtime(tmp_path)
    engine.load.side_effect=RuntimeError('native error')
    assert obj.route('x')['status']=='unavailable'
    assert obj.route('x')['status']=='retry_deferred'
    assert factory.call_count==1
    engine.load.side_effect=None;obj.configure(True)
    event=threading.Event()
    def decide(*a,**k):
        event.set();return Decision('memory',{'memory':.9},'selected',1)
    engine.decide.side_effect=decide
    result=obj.route('x',cancel_event=event)
    assert result['choice'] is None and result['status']=='cancelled'


def test_routing_uses_user_context_without_assistant_inventions(tmp_path):
    obj,engine,_=runtime(tmp_path)
    history=[SimpleNamespace(role='user',content='Chi era Garibaldi?'),
             SimpleNamespace(role='assistant',content='Invented historical assertion')]
    obj.route('Perché era importante?',history)
    state=engine.decide.call_args.args[0]
    assert 'Garibaldi' in state and 'Perché' in state and 'Invented' not in state


def test_only_administrative_pairs_removed_from_general_prompt():
    turn=lambda r,c,s=None:SimpleNamespace(role=r,content=c,metadata={'source':s})
    history=[turn('user','Cosa sai fare?'),turn('assistant','Long capabilities','runtime_capabilities'),
             turn('user','Chi era Garibaldi?'),turn('assistant','Prior answer','model_generated')]
    assert DecisionRuntime.prompt_history(history,{'status':'selected','choice':'reason'})==history[2:]
    assert DecisionRuntime.prompt_history(history,{'status':'abstained','choice':None})==history


def test_large_input_does_not_load_or_poison_the_motor(tmp_path):
    obj,engine,factory=runtime(tmp_path)
    assert obj.route('x'*8001)['status']=='context_limit'
    factory.assert_not_called()
    assert obj.route('Spiega gli arcobaleni')['status']=='selected'


def test_router_ignores_administrative_user_intents_in_past_turns(tmp_path):
    obj,engine,_=runtime(tmp_path)
    history=[SimpleNamespace(role='user',content='Cosa sai fare?'),
             SimpleNamespace(role='assistant',content='Capabilities',metadata={'source':'runtime_capabilities'})]
    obj.route('Chi era Garibaldi?',history)
    assert engine.decide.call_args.args[0]=='Chi era Garibaldi?'


def test_dream_priority_only_reorders_attributed_records_without_promoting_them(tmp_path):
    obj,engine,_=runtime(tmp_path)
    engine.decide.return_value=Decision('1',{'1':.9},'selected',1)
    memories=[{'text':'First user report','status':'unverified'}, {'text':'Second report','status':'unverified'}]
    assert obj.prioritize_dreams(memories)==[memories[1],memories[0]]
    assert [m['status'] for m in memories]==['unverified','unverified']
    engine.decide.return_value=Decision(None,{},'abstained',1)
    assert obj.prioritize_dreams(memories)==memories


def test_router_only_advertises_bound_resources_after_exact_fast_path(tmp_path):
    obj,engine,_=runtime(tmp_path)
    obj.route('Spiega le frazioni')
    options=engine.decide.call_args.args[2]
    assert set(options)=={'memory','reason','clarify'}
