from types import SimpleNamespace
from unittest.mock import Mock
from benchmark_iq import CognitiveBenchmark
from benchmark_iq import evaluate_response
from threading import Event
import json
import pytest


def test_personal_dialogue_context_check_does_not_certify_semantic_quality():
    q={'auto_checks':{'personal_context_received':True,'personal_field_statuses':{'name':'revoked'}},
       'rubric':['Il modello non deve inventare un nome.']}
    metadata={'decision':{'personal_context_in_prompt':True,'personal_context_status':{'name':'revoked'}}}
    result=evaluate_response(q,'Ciao, nome inventato.',metadata)
    assert result['automatic_status']=='passed' and result['human_review_required']
    assert evaluate_response(q,'Una risposta.',{})['automatic_status']=='failed'


def test_synthetic_candidate_is_reported_separately_and_cleared(tmp_path):
    benchmark=CognitiveBenchmark(profile='support')
    benchmark.report_path=str(tmp_path/'candidate.md')
    benchmark.load_questions=lambda: [dict(id='S',category='Test',question='Sono sollevata.')]
    brain=Mock()
    def process(**kwargs):
        brain._synthetic_candidate={'request_id':'synthetic:1','answer_candidate':'Sono sollevata.',
                                    'checks':{'subject_mismatch':True}}
        return SimpleNamespace(content='Risposta bloccata.',metadata={'generation':{'request_id':'synthetic:1'}},is_valid=False)
    brain.process_message.side_effect=process
    benchmark.brain=brain
    benchmark.run_tests()
    brain.process_message.assert_called_once()
    assert brain._synthetic_candidate is None
    data=json.loads((tmp_path/'candidate.json').read_text())
    assert data[0]['steps'][0]['candidate_diagnostic']['answer_candidate']=='Sono sollevata.'
    assert 'answer_candidate' not in data[0]['generation']
    assert data[0]['evaluation']['pipeline_valid'] is False
    assert 'Candidato diagnostico sintetico' in (tmp_path/'candidate.md').read_text()


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


def test_comparison_profile_pairs_have_same_input_seed_and_alternated_order():
    cases = CognitiveBenchmark(profile='comparison').load_questions()
    assert len(cases) == 8
    for idx in range(0, 8, 2):
        a, b = cases[idx:idx+2]
        assert a['pair_id'] == b['pair_id']
        assert a['question'] == b['question'] and a['pair_seed'] == b['pair_seed']
        assert {a['execution_mode'], b['execution_mode']} == {'pipeline', 'model'}
    assert cases[0]['execution_mode'] != cases[2]['execution_mode']


def test_comparison_runs_both_arms_without_retry_and_records_partial_pairs(tmp_path):
    benchmark = CognitiveBenchmark(profile='comparison')
    benchmark.report_path = str(tmp_path/'comparison.md')
    benchmark.cancel_event.wait = lambda _: False
    cases = benchmark.load_questions()[:2]
    benchmark.load_questions = lambda: cases
    benchmark.brain = Mock()
    benchmark._conditions = lambda: {'battery_temp_celsius': 35.0}
    benchmark.brain.process_message.return_value = SimpleNamespace(content='63', is_valid=True,
        metadata={'source':'verified_calculation', 'generation':{'llm_used':False}})
    benchmark.brain.probe_model.return_value = {'answer':'63', 'source':'isolated_model_probe',
        'generation':{'max_tokens':192, 'reasoning_budget':48, 'finish_reason':'stop'}}
    benchmark.run_tests()
    assert benchmark.brain.process_message.call_count == 1
    assert benchmark.brain.probe_model.call_count == 1
    pipeline = benchmark.brain.process_message.call_args.kwargs
    raw = benchmark.brain.probe_model.call_args.kwargs
    assert pipeline['context']['benchmark_seed'] == raw['seed']
    assert pipeline['context']['benchmark_max_tokens'] == raw['max_tokens']
    pair = benchmark.manifest['pairs'][0]
    assert pair['complete'] and pair['pipeline_bypassed_model']
    assert not pair['matched_generation_controls']
    assert pair['causal_attribution'] == 'not_established'
    assert (tmp_path/'comparison.manifest.json').exists()


def test_comparison_stops_before_inference_if_phone_is_hot(tmp_path):
    benchmark = CognitiveBenchmark(profile='comparison')
    benchmark.report_path = str(tmp_path/'hot.md')
    benchmark.brain = Mock()
    benchmark._conditions = lambda: {'battery_temp_celsius': 42.0}
    benchmark.run_tests()
    benchmark.brain.process_message.assert_not_called()
    benchmark.brain.probe_model.assert_not_called()
    assert not benchmark.results and benchmark.manifest['stop_reason'] == 'thermal_pause'
    assert (tmp_path/'hot.json').exists()


def test_diagnostic_budget_never_raises_thermal_cap_and_requires_test_context():
    from allma_model.utils.model_comparison import diagnostic_budgets, summarize_pairs
    context = {'disable_answer_recall':True, 'benchmark_seed':1,
               'benchmark_max_tokens':192, 'benchmark_thought_budget':48}
    assert diagnostic_budgets(context, 'Spiega', 'COMPLEX', 512) == (192, 48)
    assert diagnostic_budgets(context, 'Spiega', 'COMPLEX', 64) == (64, 21)
    assert diagnostic_budgets({}, 'Spiega', 'COMPLEX', 512) == (512, 128)
    assert diagnostic_budgets(dict(context, benchmark_seed=True), 'Spiega', 'COMPLEX', 512) == (512,128)
    assert summarize_pairs([{'pair_id':'A','execution_mode':'model'}]) == [{'pair_id':'A','complete':False}]


def test_comparison_raw_cancellation_saves_report_and_releases_lock(tmp_path):
    from allma_model.utils.generation_control import GenerationCancelled
    benchmark = CognitiveBenchmark(profile='comparison')
    benchmark.report_path = str(tmp_path/'cancel.md')
    benchmark.brain = Mock()
    benchmark._conditions = lambda: {}
    benchmark.load_questions = lambda: [dict(id='A_model',pair_id='A',execution_mode='model',
                                            category='Test',question='Una prova')]
    def cancel(*args, **kwargs):
        kwargs['cancel_event'].set()
        raise GenerationCancelled()
    benchmark.brain.probe_model.side_effect = cancel
    benchmark.run_tests()
    assert benchmark.manifest['cancelled']
    assert benchmark.manifest['pairs'] == [{'pair_id':'A','complete':False}]
    assert (tmp_path/'cancel.json').exists()
    assert benchmark._run_lock.acquire(blocking=False)
    benchmark._run_lock.release()


def test_reasoning_sweep_keeps_answer_budget_and_pair_seeds_equal():
    cases = CognitiveBenchmark(profile='reasoning').load_questions()
    assert len(cases) == 8
    assert {q['thought_budget'] for q in cases} == {96,128}
    for idx in range(0,8,2):
        a,b=cases[idx:idx+2]
        assert a['question'] == b['question'] and a['pair_seed'] == b['pair_seed']
        assert a['total_budget']-a['thought_budget'] == 144
        assert b['total_budget'] == a['total_budget']
    assert cases[0]['pair_seed'] == cases[2]['pair_seed']


def test_reasoning_sweep_uses_same_case_seed_as_48_token_comparison():
    baseline=CognitiveBenchmark(profile='comparison').load_questions()
    sweep=CognitiveBenchmark(profile='reasoning').load_questions()
    seeds={case['pair_id']:case['pair_seed'] for case in baseline}
    for case in sweep:
        assert case['pair_seed'] == seeds[case['pair_id'].split('_r')[0]]


def test_support_profile_is_short_and_retains_original_case_seed():
    support=CognitiveBenchmark(profile='support').load_questions()
    assert len(support)==3
    assert support[0]['id']=='S4' and support[0]['seed_offset']==300
    assert {'T1','T2'} <= {q['id'] for q in support}
    assert all(q['rubric'] for q in support)
