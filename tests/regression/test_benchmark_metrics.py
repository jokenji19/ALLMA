from types import SimpleNamespace
from unittest.mock import Mock
from benchmark_iq import CognitiveBenchmark
from benchmark_iq import evaluate_response
from threading import Event
import json
import pytest


def test_benchmark_never_retries_or_reuses_global_metrics(tmp_path, monkeypatch):
    import benchmark_iq
    monkeypatch.setattr(benchmark_iq.time, 'sleep', lambda _: None)
    benchmark = CognitiveBenchmark()
    benchmark.report_path = str(tmp_path / 'report.md')
    benchmark.load_questions = lambda: [dict(id='X', category='Test', question='Una domanda')]
    repeated = 'Questa frase lunga si ripete senza aggiungere informazioni. ' * 12
    brain = Mock()
    brain.process_message.return_value = SimpleNamespace(content=repeated, thought_trace=None, metadata={})
    brain._llm.last_generation = {'completion_tokens': 999, 'finish_reason': 'length'}
    benchmark.brain = brain
    benchmark.run_tests()
    assert brain.process_message.call_count == 1
    assert benchmark.results[0]['completion_tokens'] is None
    assert benchmark.results[0]['anti_loop_triggered']
    assert not benchmark.results[0]['anti_loop_retry']
    brain.process_message.return_value.metadata = {'generation': {'completion_tokens': 12, 'status': 'completed', 'finish_reason': 'stop'}}
    benchmark.run_tests()
    assert len(benchmark.results) == 1
    assert benchmark.results[0]['completion_tokens'] == 12
    assert (tmp_path / 'report.json').exists()


def test_json_quality_check_distinguishes_boolean_and_number():
    q = {'auto_checks': {'json_answer': {'totale': 8, 'pari': True}}}
    assert evaluate_response(q, '{"totale":8,"pari":true}', {})['automatic_status'] == 'passed'
    assert evaluate_response(q, '{"totale":8,"pari":1}', {})['automatic_status'] == 'failed'
    assert evaluate_response(q, '```json\n{"totale":8,"pari":true}\n```', {})['automatic_status'] == 'failed'
    assert evaluate_response({'rubric':['Spiega correttamente']}, 'Una risposta.', {})['human_review_required']


def test_cancel_preserves_partial_report_and_releases_lock(tmp_path):
    from allma_model.utils.generation_control import GenerationCancelled
    benchmark = CognitiveBenchmark()
    benchmark.report_path = str(tmp_path/'partial.md')
    benchmark.load_questions = lambda: [dict(id='X', category='Test', question='Domanda')]
    brain = Mock()
    def cancel(**kwargs):
        kwargs['cancel_event'].set()
        raise GenerationCancelled()
    brain.process_message.side_effect = cancel
    benchmark.brain = brain
    benchmark.run_tests()
    assert benchmark.manifest['cancelled']
    assert benchmark.results[0]['evaluation']['automatic_status'] == 'failed'
    assert json.loads((tmp_path/'partial.manifest.json').read_text())['cancelled']
    assert benchmark._run_lock.acquire(blocking=False)
    benchmark._run_lock.release()


def test_workflow_keeps_case_scope_but_does_not_share_users_between_cases(tmp_path, monkeypatch):
    benchmark = CognitiveBenchmark()
    benchmark.cancel_event.wait = lambda _: False
    benchmark.report_path = str(tmp_path/'workflow.md')
    benchmark.load_questions = lambda: [dict(id='A',category='Memoria',question='Nome',messages=['Mi chiamo Ada','Come mi chiamo?']),
                                        dict(id='B',category='Memoria',question='Nome')]
    benchmark.brain = Mock()
    benchmark.brain.process_message.return_value = SimpleNamespace(content='Ada', metadata={}, is_valid=True)
    benchmark.run_tests()
    calls = benchmark.brain.process_message.call_args_list
    assert calls[0].kwargs['user_id'] == calls[1].kwargs['user_id']
    assert calls[2].kwargs['user_id'] != calls[0].kwargs['user_id']
    assert calls[1].kwargs['context']['benchmark_seed'] == benchmark.seed+1
    assert all(c.kwargs['context']['disable_answer_recall'] for c in calls)
    assert len(benchmark.results[0]['steps']) == 2
    assert benchmark.results[0]['completion_tokens'] is None


def test_real_isolated_core_preserves_original_memories_and_borrowed_model(tmp_path, monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    (tmp_path/'personal').mkdir()
    source = ALLMACore(mobile_mode=True, db_path=str(tmp_path/'personal'/'core.db'))
    source._ensure_mobile_llm = lambda: None
    source._llm = Mock()
    source._llm.generate.return_value = '42'
    source._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
    source.conversational_memory.store_message('personal-conv','Memoria personale',{},'user','personal-user')
    benchmark = CognitiveBenchmark()
    try:
        benchmark.setup_brain(existing_brain=source)
        assert benchmark.brain is not source
        assert benchmark.brain._llm is source._llm
        assert benchmark.brain.conversational_memory is not source.conversational_memory
        benchmark.load_questions = lambda: [dict(id='X',category='Calcolo',question='Quanto fa 23 + 19?')]
        benchmark.cancel_event.wait = lambda _: False
        benchmark.run_tests()
        assert len(source.conversational_memory.messages) == 1
        assert source.conversational_memory.messages[0].content == 'Memoria personale'
        assert not source._benchmark_active and not source._user_active.is_set()
        assert benchmark.manifest['state_isolated'] is True
        folder = benchmark._temporary.name
        benchmark.close()
        from pathlib import Path
        assert not Path(folder).exists()
        assert source._llm is not None and not source._shutdown_event.is_set()
    finally:
        benchmark.close()
        source.close()


def test_profiles_and_manual_rubrics_are_distinct():
    assert len(CognitiveBenchmark(profile='quick').load_questions()) == 6
    assert len(CognitiveBenchmark(profile='historical').load_questions()) == 6
    assert len(CognitiveBenchmark(profile='extended').load_questions()) == 14
    with pytest.raises(ValueError):
        CognitiveBenchmark(profile='unknown')
