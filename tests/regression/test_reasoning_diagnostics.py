import json
from pathlib import Path

import pytest

from test_context_inference import setup as context_setup
from allma_model.llm.reasoning_diagnostics import ReasoningDiagnosticRun, CASES, grade
from allma_model.utils.generation_control import check_cancelled


def setup(tmp_path):
    pool, old, source, base = context_setup(tmp_path)
    run = ReasoningDiagnosticRun();run.setup_brain(source);run.sample = base.sample
    def factory(**kwargs):
        engine = pool.make(**kwargs)
        if kwargs.get('backend_preference') == 'cpu':engine.backend_info['kind'] = 'cpu'
        engine.llm.tokenize = lambda data, **kw: list(data)
        engine.llm.detokenize = lambda tokens, **kw: bytes(tokens)
        def generate(**opts):
            pool.on_generate(engine);check_cancelled(opts['cancel_event'])
            pool.generated.append(opts)
            answer = '5' if 'palline' in opts['prompt'] else '7' if 'biglie' in opts['prompt'] else '{"codice":"BETA-816"}'
            opts['callback']('private synthetic reasoning')
            opts['callback']('\n</think>\n\n')
            opts['callback'](answer)
            return answer
        engine.generate = generate
        engine.get_generation_meta = lambda request_id: {'backend': engine.backend_info['kind'], 'request_id': request_id}
        return engine
    run.factory = factory
    return pool, old, source, run


def test_controlled_plan_changes_only_backend_or_reasoning_and_restores_runtime(tmp_path):
    pool, old, source, run = setup(tmp_path)
    run.run_tests()
    data = run.manifest['summary']
    assert data['completed'] == data['total'] == 12 and data['restored']
    assert data['stop_reason'] == 'completed' and pool.live == 1
    assert [row['variant'] for row in data['loads']] == ['gpu48', 'cpu48', 'gpu128', 'natural']
    for case, _, _, _ in CASES:
        rows = [r for r in data['results'] if r['case'] == case]
        assert len({r['prompt_audit']['prompt_sha256'] for r in rows}) == 1
        assert len({r['seed'] for r in rows}) == 1
        assert all(r['prompt_audit']['question_occurrences'] == 1 for r in rows)
        assert all(r['prompt_audit']['round_trip_exact'] for r in rows)
        assert all(r['checks']['correct_and_formatted'] for r in rows)
        assert all(r['first_answer_ms'] is not None and r['reasoning_close_observed'] for r in rows)
        assert [r['budget']['reserved_answer'] for r in rows] == [144, 144, 144, None]
        assert [r['budget']['total'] for r in rows] == [192, 192, 272, 272]
    assert source._llm.n_ctx == 2048 and source._llm.backend_info['kind'] == 'opencl'
    assert not source._user_active.is_set() and not source._benchmark_active
    assert source.reasoning_engine.llm is source.dream_manager.llm_wrapper is source._llm
    assert 'private synthetic reasoning' not in Path(run.report_path).with_suffix('.json').read_text()


@pytest.mark.parametrize('stage', ['before', 'cpu_load', 'cpu_generation', 'after_case'])
def test_interruptions_keep_partial_results_and_original_gpu(tmp_path, stage):
    pool, old, source, run = setup(tmp_path)
    if stage == 'before':run.cancel_event.set()
    if stage == 'cpu_load':
        pool.on_load = lambda engine: run.cancel_event.set() if len(pool.created) == 3 else None
    if stage == 'cpu_generation':
        pool.on_generate = lambda engine: run.cancel_event.set() if engine.backend_info['kind'] == 'cpu' else None
    def progress(done, total, text):
        if done == 1 and stage == 'after_case':run.cancel_event.set()
    run.run_tests(progress)
    data = run.manifest['summary']
    assert data['stop_reason'] == 'cancelled' and data['restored']
    assert data['completed'] < 12
    assert pool.live == 1 and source._llm.backend_info['kind'] == 'opencl'
    assert not source._benchmark_active and not source._user_active.is_set()


def test_cpu_load_failure_does_not_persist_cpu_preference(tmp_path):
    pool, old, source, run = setup(tmp_path)
    def fail(engine):
        if len(pool.created) == 3:raise RuntimeError('synthetic CPU load failure')
    pool.on_load = fail
    with pytest.raises(RuntimeError, match='synthetic CPU'):
        run.run_tests()
    assert run.manifest['summary']['restored']
    assert source._llm.backend_info['kind'] == 'opencl' and pool.live == 1


def test_modified_prompt_aborts_before_inference_and_restores(tmp_path):
    pool, old, source, run = setup(tmp_path)
    original = run.factory
    def factory(**kwargs):
        engine = original(**kwargs)
        engine.llm.detokenize = lambda tokens, **kw: b'corrupted prompt'
        return engine
    run.factory = factory
    with pytest.raises(RuntimeError, match='prompt nativo'):
        run.run_tests()
    assert not pool.generated
    assert run.manifest['summary']['restored'] and pool.live == 1


def test_grading_separates_numeric_value_from_extra_punctuation():
    assert grade('5.', '5') == {'correct_and_formatted': False, 'numeric_value_correct': True, 'format': 'number'}
    assert grade('{"codice":"BETA-816"}', {'codice': 'BETA-816'})['correct_and_formatted']
    assert not grade('```json\n{"codice":"BETA-816"}\n```', {'codice': 'BETA-816'})['correct_and_formatted']
    assert grade('No', 'no') == {'correct_and_formatted': True, 'format': 'yes_no'}
    assert grade('R', 'R') == {'correct_and_formatted': True, 'format': 'literal'}


def test_followup_changes_penalty_and_state_only_in_labeled_arms(tmp_path):
    from allma_model.llm.reasoning_diagnostics import ReasoningFollowupRun
    pool, old, source, run = setup(tmp_path)
    follow = ReasoningFollowupRun();follow.setup_brain(source)
    follow.factory = run.factory;follow.sample = run.sample
    resets = []
    factory = follow.factory
    def make(**kwargs):
        engine = factory(**kwargs);resets.append(engine.llm.reset)
        return engine
    follow.factory = make
    follow.run_tests()
    data = follow.manifest['summary']
    assert data['total'] == data['completed'] == 15 and data['restored']
    assert [r['repeat_penalty'] for r in data['results'][::3]] == [1.1, 1.0, 1.1, 1.0, 1.1]
    assert [r['answer_state_reset'] for r in data['results'][::3]] == [False, False, True, False, False]
    assert [r['thinking_enabled'] for r in data['results'][::3]] == [True, True, True, True, False]
    assert resets[0].call_count == resets[1].call_count == 3
    assert resets[2].call_count == 6
    assert data['results'][-1]['budget']['reserved_answer'] == 144
    assert 'reasoning_followup_' in follow.report_path


def test_holdout_plan_is_distinct_and_preserves_requested_budgets(tmp_path):
    from allma_model.llm.reasoning_diagnostics import ReasoningValidationRun
    pool, old, source, run = setup(tmp_path)
    validation = ReasoningValidationRun();validation.setup_brain(source)
    validation.factory = run.factory;validation.sample = run.sample
    assert {c[1] for c in validation.cases}.isdisjoint({c[1] for c in CASES})
    validation.run_tests()
    summary = validation.manifest['summary']
    assert summary['completed'] == summary['total'] == 13 and summary['restored']
    assert len([r for r in summary['results'] if r['variant'] == 'natural_end_check']) == 1
    assert summary['results'][-1]['question'] == CASES[0][1]
