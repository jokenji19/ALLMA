from types import SimpleNamespace
from unittest.mock import Mock
from benchmark_iq import CognitiveBenchmark


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
