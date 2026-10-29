from types import SimpleNamespace
from unittest.mock import Mock
from threading import RLock, Event
import json
import pytest
from allma_model.core.learning_insights import snapshot, response_origin
from allma_model.learning_system.answer_recall import AnswerRecall


def test_snapshot_reads_owned_documents_without_calling_a_model(tmp_path):
    recall=AnswerRecall(tmp_path/'answers.db')
    for user in ('u','other'):
        key=user+'_key'
        recall.observe(key,user,'Descrivi una bussola in una frase.','Indica il nord.','event_a')
        recall.feedback(key,user,'vote_a',True);recall.feedback(key,user,'vote_b',True)
    memory=SimpleNamespace(recent_messages=lambda limit,predicate: [])
    core=SimpleNamespace(_lock=RLock(),conversational_memory=memory,answer_recall=recall,
        goal_progress=None,meta_learner=None,_llm=Mock())
    before=(tmp_path/'answers.db').read_bytes()
    result=snapshot(core,'u')
    assert result['status']=='ok' and len(result['sections'][0]['items'])==1
    assert result['sections'][0]['items'][0]['usable'] is True
    core._llm.generate.assert_not_called()
    assert (tmp_path/'answers.db').read_bytes()==before
    recall.feedback('u_key','u','revoke',False)
    result=snapshot(core,'u')
    assert result['sections'][0]['items'][0]['usable'] is False
    assert 'Ritirata' in result['sections'][0]['items'][0]['detail']


@pytest.mark.parametrize('source,kind',[
    ('origin_identity','identity'),('confirmed_answer_recall','learned'),
    ('literal_user_memory','memory'),('user_declaration','memory'),('model_generated','model'),
    ('model_excerpt','model'),(None,'unknown')])
def test_sources_do_not_become_world_truth(source,kind):
    assert response_origin({'source':source})['kind']==kind


def test_snapshot_busy_does_not_block_a_live_turn():
    core=SimpleNamespace(_lock=SimpleNamespace(acquire=lambda **kw:False))
    assert snapshot(core,'u')=={'status':'busy','sections':[]}


def test_endurance_cancel_saves_partial_and_releases_runtime(tmp_path):
    import threading
    from allma_model.llm.endurance import LongSessionRun
    run=LongSessionRun();run.cancel_event.set()
    run.report_path=str(tmp_path/'session.md')
    run.source=SimpleNamespace(_lock=RLock(),_user_active=Event(),_shutdown_event=Event(),
        _foreground=True,_llm=SimpleNamespace(backend_info={'kind':'scripted'},n_ctx=2048),system_monitor=None)
    run.model.brain=SimpleNamespace(start_conversation=lambda user:'c')
    run.run_tests()
    assert run.manifest['summary']['stop_reason']=='cancelled'
    assert run.manifest['summary']['asr_microphone_tested'] is False
    assert not run.source._benchmark_active and not run.source._user_active.is_set()
    assert json.loads((tmp_path/'session.json').read_text())['elapsed_seconds']<5


def test_endurance_report_failure_still_releases_runtime(tmp_path,monkeypatch):
    from allma_model.llm.endurance import LongSessionRun
    run=LongSessionRun();run.cancel_event.set();run.report_path=str(tmp_path/'session.md')
    run.source=SimpleNamespace(_lock=RLock(),_user_active=Event(),_shutdown_event=Event(),
        _foreground=True,_llm=SimpleNamespace(backend_info={},n_ctx=2048),system_monitor=None)
    run.model.brain=SimpleNamespace(start_conversation=lambda user:'c')
    monkeypatch.setattr(run,'_save',Mock(side_effect=OSError('synthetic full disk')))
    with pytest.raises(OSError):run.run_tests()
    assert not run.source._benchmark_active and not run.source._user_active.is_set()


def test_endurance_initial_conversation_failure_releases_runtime(tmp_path):
    from allma_model.llm.endurance import LongSessionRun
    run=LongSessionRun();run.report_path=str(tmp_path/'session.md')
    run.source=SimpleNamespace(_lock=RLock(),_user_active=Event(),_shutdown_event=Event(),
        _foreground=True,_llm=SimpleNamespace(backend_info={},n_ctx=2048),system_monitor=None)
    run.model.brain=SimpleNamespace(start_conversation=Mock(side_effect=OSError('synthetic disk full')))
    with pytest.raises(OSError):run.run_tests()
    assert not run.source._benchmark_active and not run.source._user_active.is_set()
    assert json.loads((tmp_path/'session.json').read_text())['stop_reason']=='error'


def test_endurance_does_not_label_an_empty_time_window_as_complete(tmp_path,monkeypatch):
    from allma_model.llm.endurance import LongSessionRun
    from allma_model.llm import endurance
    run=LongSessionRun();run.duration=0.001;run.report_path=str(tmp_path/'session.md')
    run.source=SimpleNamespace(_lock=RLock(),_user_active=Event(),_shutdown_event=Event(),
        _foreground=True,_llm=SimpleNamespace(backend_info={},n_ctx=2048),system_monitor=None)
    run.model.brain=SimpleNamespace(start_conversation=lambda user:'c')
    ticks=iter(i*.01 for i in range(100))
    monkeypatch.setattr(endurance.time,'monotonic',lambda:next(ticks))
    run.run_tests()
    assert run.manifest['summary']['planned_tasks']==1
    assert run.manifest['summary']['workload_complete'] is False
    assert run.manifest['summary']['stop_reason']=='window_ended_with_pending_tasks'
    assert not run.source._benchmark_active
