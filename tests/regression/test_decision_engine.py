import hashlib
import math
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from allma_model.agency_system import decision_engine as module
from allma_model.agency_system.decision_engine import Decision, LocalDecisionEngine
from allma_model.agency_system.action_cycle import ActionCycle, LocalAction
from allma_model.agency_system.decision_diagnostics import measure, CASES


def ready(tmp_path, monkeypatch, scores=(7., 0.)):
    path = tmp_path/'decider.gguf'
    path.write_bytes(b'verified test fixture')
    monkeypatch.setitem(module.DECIDER_MODEL, 'size_bytes', path.stat().st_size)
    monkeypatch.setitem(module.DECIDER_MODEL, 'sha256', hashlib.sha256(path.read_bytes()).hexdigest())
    native = SimpleNamespace(tokenize=lambda text, **kw: [ord(c) for c in text.decode()],
        reset=Mock(), eval=Mock(), close=Mock(), _ctx=SimpleNamespace(get_logits=lambda: {65+i:v for i,v in enumerate(scores)}))
    engine = LocalDecisionEngine(path, factory=Mock(return_value=native))
    engine.load()
    return engine, native


def test_real_score_readout_no_generation_and_idempotent_lifecycle(tmp_path, monkeypatch):
    engine, native = ready(tmp_path, monkeypatch)
    engine.load()
    result = engine.decide('state', 'Question?', {'one':'First', 'two':'Second'})
    assert result.choice == 'one' and result.status == 'selected'
    assert sum(result.probabilities.values()) == pytest.approx(1)
    assert ''.join(chr(i) for i in native.eval.call_args.args[0]) == 'Context:\nstate\n\nQuestion: Question?\nOptions:\n(A) First\n(B) Second\nAnswer: ('
    native.reset.assert_called_once()
    engine.close(); engine.close()
    native.close.assert_called_once()
    engine.factory.assert_called_once()
    assert engine.decide('x', 'q', {'a':'A','b':'B'}).status == 'unavailable'


@pytest.mark.parametrize('scores,status', [((0.,0.),'abstained'), ((math.nan,1.),'invalid_scores'), ((math.inf,1.),'invalid_scores')])
def test_uncertainty_never_becomes_an_action(tmp_path, monkeypatch, scores, status):
    engine, native = ready(tmp_path, monkeypatch, scores)
    result = engine.decide('x','q',{'a':'A','b':'B'})
    assert result.choice is None and result.status == status


def test_cancellation_busy_context_limits_and_lock_released(tmp_path, monkeypatch):
    engine, native = ready(tmp_path, monkeypatch)
    event = threading.Event(); event.set()
    assert engine.decide('x','q',{'a':'A','b':'B'},cancel_event=event).status == 'cancelled'
    engine._lock.acquire()
    try:
        assert engine.decide('x','q',{'a':'A','b':'B'}).status == 'busy'
    finally: engine._lock.release()
    engine.n_ctx = 3
    assert engine.decide('x','q',{'a':'A','b':'B'}).status == 'context_limit'
    native.eval.assert_not_called()
    engine.n_ctx = 1024
    native.eval.side_effect = RuntimeError('runtime failure')
    with pytest.raises(RuntimeError): engine.decide('x','q',{'a':'A','b':'B'})
    assert not engine._lock.locked()


def test_cancel_during_eval_discards_decision(tmp_path, monkeypatch):
    engine, native = ready(tmp_path, monkeypatch)
    event = threading.Event()
    native.eval.side_effect = lambda _: event.set()
    result = engine.decide('x','q',{'a':'A','b':'B'},cancel_event=event)
    assert result.choice is None and result.status == 'cancelled'


@pytest.mark.parametrize('thermal',[None,2,4])
def test_hot_or_unknown_npu_never_runs_a_decision(tmp_path,monkeypatch,thermal):
    from allma_model.llm import decision_backend
    engine,native=ready(tmp_path,monkeypatch)
    engine.backend_info={'kind':'hexagon'}
    monkeypatch.setattr(decision_backend,'android_thermal_status',lambda:thermal)
    result=engine.decide('state','question',{'one':'First','two':'Second'})
    assert result.status=='thermal_pause' and result.choice is None
    native.eval.assert_not_called()


def test_cancelled_npu_clears_marker_and_discards_result(tmp_path,monkeypatch):
    from allma_model.llm import decision_backend,native_backend
    engine,native=ready(tmp_path,monkeypatch)
    engine.backend_info={'kind':'hexagon'}
    engine._native_guard=native_backend.NativeGuard(tmp_path,'test',filename='npu-decision-pending.json')
    monkeypatch.setattr(decision_backend,'android_thermal_status',lambda:0)
    event=threading.Event()
    native.eval.side_effect=lambda _:event.set()
    result=engine.decide('state','question',{'one':'First','two':'Second'},cancel_event=event)
    assert result.status=='cancelled' and result.choice is None
    assert not engine._native_guard.path.exists()


def test_npu_model_failure_retries_cpu_without_inheriting_other_devices(tmp_path,monkeypatch):
    import sys
    from allma_model.llm import decision_backend,native_backend
    engine,native=ready(tmp_path,monkeypatch)
    engine.close();engine.factory=None
    guard=native_backend.NativeGuard(tmp_path,'test',filename='npu-decision-pending.json')
    choice=native_backend.BackendChoice('hexagon','test',guard=guard,device_ids=(222,),batch_threads=2)
    monkeypatch.setattr(decision_backend,'prepare_android_backend',lambda:choice)
    calls=[]
    class Factory:
        _allma_explicit_devices=True
        def __new__(cls,**kwargs):
            calls.append(kwargs)
            if kwargs['n_gpu_layers']!=0:raise RuntimeError('NPU context unavailable')
            return native
    monkeypatch.setitem(sys.modules,'llama_cpp',SimpleNamespace(Llama=Factory))
    engine.load()
    assert len(calls)==2 and calls[0]['devices']==[222] and calls[1]['devices']==[]
    assert calls[1]['n_gpu_layers']==0 and calls[1]['offload_kqv'] is False
    assert engine.backend_info=={'kind':'cpu','reason':'npu_model_initialization_failed'}
    assert not guard.path.exists()


@pytest.mark.parametrize('state,question,options', [('x'*8001,'q',{'a':'A','b':'B'}),('x','',{'a':'A','b':'B'}),('x','q',{'a':'A'}),('x','q',{'a':'A','b':''})])
def test_bad_input_rejected_without_inference(tmp_path, state, question, options):
    with pytest.raises(ValueError): LocalDecisionEngine(tmp_path/'missing').decide(state,question,options)


def test_corruption_rejected_before_native_load(tmp_path, monkeypatch):
    engine, native = ready(tmp_path, monkeypatch)
    engine.close()
    engine.path.write_bytes(b'x'*module.DECIDER_MODEL['size_bytes'])
    with pytest.raises(ValueError, match='checksum'): engine.load()
    assert engine.factory.call_count == 1


def test_verified_download_and_native_reloads_share_checksum(tmp_path, monkeypatch):
    from allma_model.utils.model_downloader import ModelDownloader
    from allma_model.utils import model_integrity
    engine, native = ready(tmp_path, monkeypatch)
    engine.close()
    model_integrity.verified_models.verified.pop(str(engine.path))
    digest = Mock(wraps=hashlib.sha256)
    monkeypatch.setattr(model_integrity.hashlib, 'sha256', digest)
    downloader = ModelDownloader(str(tmp_path))
    assert downloader._valid(engine.path, module.DECIDER_MODEL)
    engine.load()
    engine.close()
    engine.load()
    assert digest.call_count == 1
    assert engine.factory.call_count == 3
    assert engine.load_metrics['total_ms'] >= 0
    assert sum(value for key, value in engine.load_metrics.items() if key != 'total_ms') == pytest.approx(engine.load_metrics['total_ms'])


def test_agent_verifies_and_never_repeats_actions():
    motor = Mock()
    motor.decide.side_effect = [Decision('read',{},'selected',1),Decision('stop',{},'selected',1)]
    execute = Mock(return_value={'source':'synthetic','value':42})
    second = Mock()
    actions = {'read':LocalAction('Read synthetic data',execute,lambda out:out['source']=='synthetic'),
               'other':LocalAction('Other lookup',second,lambda out:True)}
    result = ActionCycle(motor,actions,diagnostic=True).run('Find the stored value')
    assert result == {'status':'stopped','steps':[{'action':'read','verified':True}]}
    execute.assert_called_once_with(); second.assert_not_called()
    assert 'read' not in motor.decide.call_args_list[1].args[2]


@pytest.mark.parametrize('status,choice,expected', [('abstained',None,'abstained'),('selected','invented','invalid_action'),('selected','write','invalid_action')])
def test_agent_cannot_escalate_permissions(status,choice,expected):
    execute = Mock()
    motor = Mock();motor.decide.return_value = Decision(choice,{},status,1)
    result = ActionCycle(motor,{'read':LocalAction('Read',execute,lambda _:True),
                              'write':LocalAction('Write',execute,lambda _:True,'memory_write')},diagnostic=True).run('state')
    assert result['status'] == expected
    execute.assert_not_called()
    assert 'write' not in motor.decide.call_args.args[2]


def test_agent_failed_verification_stops_and_cancellation_prevents_execution():
    motor=Mock();motor.decide.return_value=Decision('read',{},'selected',1)
    execute=Mock(return_value='unchecked')
    cycle=ActionCycle(motor,{'read':LocalAction('Read',execute,lambda _:False)},diagnostic=True)
    assert cycle.run('state')['status']=='unverified'
    assert execute.call_count==1
    event=threading.Event();event.set()
    assert cycle.run('state',cancel_event=event)['status']=='cancelled'
    assert execute.call_count==1


def test_diagnostics_distinguish_abstention_from_wrong_answer_and_thermal_stop():
    engine=Mock()
    engine.decide.return_value=Decision(None,{'calculate':.4,'memory':.3,'reason':.2,'clarify':.1},'abstained',5)
    summary=measure(engine,threading.Event())
    assert summary['completed']==len(CASES) and summary['abstentions']==len(CASES)
    assert summary['accepted_wrong']==0 and summary['accepted_correct']==0
    assert measure(engine,threading.Event(),temperature=lambda:43)['stop_reason']=='thermal_pause'


def test_action_exception_and_step_budget_are_not_success():
    motor=Mock();motor.decide.return_value=Decision('read',{},'selected',1)
    execute=Mock(side_effect=RuntimeError('offline'))
    assert ActionCycle(motor,{'read':LocalAction('Read',execute,lambda _:True)},diagnostic=True).run('state')['status']=='action_failed'
    execute.side_effect=None;execute.return_value=42
    result=ActionCycle(motor,{'read':LocalAction('Read',execute,lambda _:True)},max_steps=1,diagnostic=True).run('state')
    assert result['status']=='budget_exhausted' and result['steps'][0]['verified']


@pytest.mark.parametrize('cancel,hot', [(True,False),(False,True)])
def test_diagnostic_preflight_releases_core_and_keeps_personal_state(tmp_path, monkeypatch, cancel, hot):
    from allma_model.agency_system.decision_diagnostics import DecisionDiagnosticRun
    # Block network at the downloader boundary; cancellation must not start it.
    from allma_model.utils.model_downloader import ModelDownloader
    download=Mock(side_effect=AssertionError('Unexpected download'))
    monkeypatch.setattr(ModelDownloader,'download_model',download)
    core=SimpleNamespace(db_path=str(tmp_path/'personal.db'),models_dir=str(tmp_path/'models'),
        _lock=threading.Lock(),_user_active=threading.Event(),_shutdown_event=threading.Event(),
        dream_manager=SimpleNamespace(is_dreaming=False),
        temperature_monitor=SimpleNamespace(get_temperatures=lambda:{'battery':43 if hot else 30}),
        identity={'name':'ALLMA','history':['personal']})
    run=DecisionDiagnosticRun();run.setup_brain(core)
    if cancel: run.cancel_event.set()
    if hot:
        with pytest.raises(RuntimeError,match='caldo'):run.run_tests()
    else:
        run.run_tests()
        assert run.manifest['cancelled']
        assert 'cancelled' in open(run.report_path).read()
    assert not core._user_active.is_set() and not core._benchmark_active
    assert core.identity=={'name':'ALLMA','history':['personal']}
    download.assert_not_called()
