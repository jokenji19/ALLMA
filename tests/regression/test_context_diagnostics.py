import json
import threading
from types import SimpleNamespace as T
from unittest.mock import Mock

import pytest

from allma_model.llm.context_diagnostics import BUDGET, CONTEXTS, ContextFitRun, compare_fit, synthetic_dialogue
from allma_model.llm.model_binding import ModelBinding
from allma_model.utils.generation_control import GenerationCancelled


def binding():
    return ModelBinding({'general.architecture': 'qwen35', 'tokenizer.chat_template':
        '{% for m in messages %}{{m.role}}:{{m.content}}\n{% endfor %}assistant:'}, context_size=2048)


def tokenize(data, **kwargs):
    # Character tokenizer deliberately tests packing mechanics, not native quality.
    return list(data)


def test_context_comparison_preserves_runtime_binding_and_current_request():
    original = binding()
    rows = compare_fit(original, tokenize)
    assert [r['context_tokens'] for r in rows] == list(CONTEXTS)
    assert original.context_size == 2048
    assert [r['history_pairs_removed'] for r in rows] == sorted([r['history_pairs_removed'] for r in rows], reverse=True)
    assert rows[-1]['history_pairs_removed'] < rows[0]['history_pairs_removed']
    for row in rows:
        assert row['prompt_tokens'] + BUDGET + 32 <= row['context_tokens']
        assert row['notes_retained']['recent']
    assert synthetic_dialogue()[0]['role'] == 'system'
    assert synthetic_dialogue()[-1]['role'] == 'user'


def test_cancellation_preserves_completed_rows_and_stops_during_packing():
    event, rows = threading.Event(), []
    def progress(*args):
        event.set()
    with pytest.raises(GenerationCancelled):
        compare_fit(binding(), tokenize, event, rows=rows, progress_callback=progress)
    assert len(rows) == 1 and rows[0]['context_tokens'] == 2048
    def cancel_tokenize(data):
        event.set()
        return tokenize(data)
    event.clear()
    with pytest.raises(GenerationCancelled):
        compare_fit(binding(), cancel_tokenize, event)


def source(tmp_path):
    engine = T(llm=T(tokenize=tokenize), binding=binding(), n_ctx=2048, inference_lock=threading.Lock())
    return T(db_path=str(tmp_path / 'private.db'), _lock=threading.RLock(),
             _user_active=threading.Event(), _shutdown_event=threading.Event(),
             _benchmark_active=False, dream_manager=T(is_dreaming=False),
             _llm=engine, _ensure_mobile_llm=Mock())


def test_run_reports_its_limits_and_never_generates_or_changes_context(tmp_path):
    core = source(tmp_path)
    run = ContextFitRun()
    run.setup_brain(core)
    run.run_tests()
    summary = run.manifest['summary']
    assert summary['complete'] and len(summary['rows']) == 3
    assert summary['production_context'] == core._llm.n_ctx == 2048
    assert not summary['production_context_changed']
    assert summary['semantic_accuracy'] is summary['inference_latency_ms'] is summary['ram_comparison'] is None
    assert not core._benchmark_active and not core._user_active.is_set()
    assert json.loads(__import__('pathlib').Path(run.report_path).with_suffix('.json').read_text()) == summary


def test_failure_restores_busy_state_and_reports_failure(tmp_path):
    core = source(tmp_path)
    core._llm.llm = None
    run = ContextFitRun()
    run.setup_brain(core)
    with pytest.raises(RuntimeError, match='Carica un modello'):
        run.run_tests()
    assert not core._benchmark_active and not core._user_active.is_set()
    assert run.manifest['summary']['stop_reason'] == 'error'
    assert not run.manifest['summary']['complete']


def test_cancelled_run_keeps_partial_report_and_releases_runtime(tmp_path):
    run = ContextFitRun()
    core = source(tmp_path)
    run.setup_brain(core)
    def cancel_after_first(done, total, text):
        if done == 1:
            run.cancel_event.set()
    run.run_tests(cancel_after_first)
    summary = run.manifest['summary']
    assert summary['stop_reason'] == 'cancelled' and len(summary['rows']) == 1
    assert not summary['complete'] and run.manifest['cancelled']
    assert not core._user_active.is_set() and not core._benchmark_active


def test_busy_app_is_rejected_without_releasing_someone_elses_reservation(tmp_path):
    core = source(tmp_path)
    core._user_active.set()
    run = ContextFitRun()
    run.setup_brain(core)
    with pytest.raises(RuntimeError, match='libera'):
        run.run_tests()
    assert core._user_active.is_set()


def test_android_perception_battery_has_fixed_plan_and_no_inference(tmp_path):
    from allma_model.core.perception_diagnostics import run_battery
    summary = run_battery(tmp_path / 'perception')
    assert summary['passed'] == summary['total'] == summary['planned'] == 24
    assert summary['complete']
