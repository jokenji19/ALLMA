import json
from pathlib import Path
import threading
from types import SimpleNamespace as T
from unittest.mock import Mock

import pytest

from allma_model.llm.context_diagnostics import NOTES
from allma_model.llm.context_inference import ContextInferenceRun, ExperimentCancellation, MAX_TEMPERATURE, evaluate
from allma_model.llm.model_binding import ModelBinding
from allma_model.utils.generation_control import check_cancelled


class Pool:
    def __init__(self):
        self.live = 0
        self.created = []
        self.generated = []
        self.on_load = lambda engine: None
        self.on_generate = lambda engine: None

    def make(self, models_dir='/models', model_name='qwen.gguf', n_ctx=2048, **kwargs):
        assert self.live == 0, 'Two native models allocated simultaneously'
        self.live += 1
        pool = self
        class Engine:
            def __init__(self):
                self.models_dir = models_dir
                self.model_path = str(Path(models_dir) / model_name)
                self.n_ctx = n_ctx
                self.backend_info = {'kind': 'opencl', 'reason': 'fake'}
                self.binding = ModelBinding({'general.architecture': 'qwen35', 'tokenizer.chat_template':
                    '{% for m in messages %}{{ m.role }}:{{m.content}}\n{% endfor %}assistant:'}, context_size=n_ctx)
                self.llm = T(tokenize=lambda data, **kw: data.split(), set_cache=Mock(), reset=Mock())
                self.inference_lock = threading.Lock()
            def close(self):
                if self.llm is not None:
                    self.llm = None
                    pool.live -= 1
            def prepare_chat(self, messages, budget, reasoning=True):
                return self.binding.prepare(messages, lambda data: data.split(), budget, reasoning)
            def generate(self, **kwargs):
                pool.on_generate(self)
                check_cancelled(kwargs['cancel_event'])
                pool.generated.append(kwargs)
                kwargs['callback']('temporary reasoning')
                kwargs['callback']('\n</think>\n\n')
                kwargs['callback']('5')
                if 'palline' in kwargs['prompt']:
                    return '5'
                return json.dumps({key: value if value in kwargs['prompt'] else None
                    for key, value in zip(('iniziale', 'centrale', 'recente'), NOTES)})
            def get_generation_meta(self, request_id):
                return {'backend': 'opencl', 'request_id': request_id,
                        'max_tokens': 192, 'reasoning_budget': 48, 'ttft_ms': 10}
        engine = Engine()
        self.created.append(engine)
        try:
            self.on_load(engine)
        except Exception:
            engine.close()
            raise
        return engine


def setup(tmp_path):
    pool = Pool()
    old = pool.make(n_ctx=2048)
    source = T(db_path=str(tmp_path / 'synthetic.db'), _lock=threading.RLock(),
               _llm=old, _owns_llm=True, _llm_ready=True, _user_active=threading.Event(),
               _shutdown_event=threading.Event(), _benchmark_active=False, _foreground=True,
               system_monitor=Mock(), _ensure_mobile_llm=Mock(),
               reasoning_engine=T(llm=old), dream_manager=T(is_dreaming=False, llm_wrapper=old, tot=T(llm=old)))
    run = ContextInferenceRun()
    run.factory = pool.make
    run.sample = lambda core: {'temperature_c': 30., 'rss_mib': 100., 'pss_mib': 80., 'charging': False}
    run.setup_brain(source)
    return pool, old, source, run


def assert_released(source):
    assert not source._benchmark_active and not source._user_active.is_set()


def test_real_context_plan_has_fixed_budgets_no_cache_and_restores_every_consumer(tmp_path):
    pool, old, source, run = setup(tmp_path)
    run.run_tests()
    summary = run.manifest['summary']
    assert summary['completed'] == summary['total'] == 12
    assert summary['stop_reason'] == 'completed' and summary['restored']
    assert [load['context_tokens'] for load in summary['loads']] == [2048, 4096, 8192, 8192, 4096, 2048]
    assert pool.live == 1 and old.llm is None
    assert source._llm.n_ctx == 2048
    assert source.reasoning_engine.llm is source.dream_manager.llm_wrapper is source.dream_manager.tot.llm is source._llm
    assert len(pool.generated) == 12
    assert all(k['max_tokens'] == 192 and k['thought_budget'] == 48 for k in pool.generated)
    assert all(row['first_answer_ms'] is not None for row in summary['results'])
    assert [k['seed'] for k in pool.generated] == [20261026, 20261027] * 6
    for engine in pool.created[1:-1]:
        assert engine.llm is None
    assert_released(source)
    data = json.loads(Path(run.report_path).with_suffix('.json').read_text())
    assert data['completed'] == 12 and data['restored']


@pytest.mark.parametrize('when', ['before_load', 'during_load', 'during_generation', 'after_case'])
def test_cancellation_still_restores_original_model_and_retains_finished_rows(tmp_path, when):
    pool, old, source, run = setup(tmp_path)
    if when == 'before_load':
        run.cancel_event.set()
    elif when == 'during_load':
        pool.on_load = lambda engine: run.cancel_event.set()
    elif when == 'during_generation':
        pool.on_generate = lambda engine: run.cancel_event.set()
    def progress(done, total, text):
        if done == 1 and when == 'after_case':
            run.cancel_event.set()
    run.run_tests(progress)
    summary = run.manifest['summary']
    assert summary['stop_reason'] == 'cancelled' and summary['restored']
    assert pool.live == 1 and source._llm.n_ctx == 2048
    assert summary['completed'] == (1 if when == 'after_case' else 0)
    assert_released(source)


@pytest.mark.parametrize('cause', ['load', 'generation', 'backend'])
def test_failure_does_not_leave_a_larger_context_or_detached_consumers(tmp_path, cause):
    pool, old, source, run = setup(tmp_path)
    def on_load(engine):
        if engine.n_ctx == 4096:
            if cause == 'load':
                raise RuntimeError('synthetic load failure')
            if cause == 'backend':
                engine.backend_info['kind'] = 'cpu'
    pool.on_load = on_load
    def on_generate(engine):
        if engine.n_ctx == 4096 and cause == 'generation':
            raise RuntimeError('synthetic generation failure')
    pool.on_generate = on_generate
    with pytest.raises(RuntimeError):
        run.run_tests()
    assert run.manifest['summary']['stop_reason'] == 'error'
    assert run.manifest['summary']['restored']
    assert pool.live == 1 and source._llm.n_ctx == 2048
    assert_released(source)


def test_restore_failure_is_visible_and_next_start_can_load_the_original_preference(tmp_path):
    pool, old, source, run = setup(tmp_path)
    calls = 0
    def load(engine):
        nonlocal calls
        calls += 1
        if calls == 7:
            raise RuntimeError('synthetic restore failure')
    pool.on_load = load
    with pytest.raises(RuntimeError, match='non è stato ripristinato'):
        run.run_tests()
    assert pool.live == 0 and source._llm is None and not source._llm_ready
    assert source.reasoning_engine.llm is source.dream_manager.llm_wrapper is None
    assert run.manifest['summary']['stop_reason'] == 'restore_failed'
    assert source._mobile_llm_error
    assert_released(source)


@pytest.mark.parametrize('reason', ['background', 'thermal_pause', 'sensors_unavailable'])
def test_unavailable_conditions_stop_before_disrupting_original_engine(tmp_path, reason):
    pool, old, source, run = setup(tmp_path)
    if reason == 'background':
        source._foreground = False
    else:
        run.sample = lambda core: {'temperature_c': MAX_TEMPERATURE if reason == 'thermal_pause' else None}
    run.run_tests()
    assert source._llm is old and pool.live == 1
    assert run.manifest['summary']['stop_reason'] == reason
    assert run.manifest['summary']['restored']
    assert_released(source)


def test_shutdown_during_loading_never_publishes_a_model_to_a_closed_core(tmp_path):
    pool, old, source, run = setup(tmp_path)
    pool.on_load = lambda engine: source._shutdown_event.set()
    run.run_tests()
    assert run.manifest['summary']['stop_reason'] == 'shutdown'
    assert pool.live == 0 and source._llm is None
    assert source._user_active.is_set() and not source._benchmark_active


def test_borrowed_or_busy_model_is_not_closed(tmp_path):
    pool, old, source, run = setup(tmp_path)
    source._owns_llm = False
    with pytest.raises(RuntimeError, match='posseduto'):
        run.run_tests()
    assert source._llm is old and pool.live == 1
    source._user_active.set()
    with pytest.raises(RuntimeError, match='libera'):
        run.run_tests()
    assert source._user_active.is_set()


def test_grading_separates_missing_history_from_hallucinated_answers():
    missing = json.dumps({'iniziale': None, 'centrale': NOTES[1], 'recente': NOTES[2]})
    result = evaluate('long', missing, [False, True, True])
    assert result['grounded_recall'] and not result['full_history_recall']
    hallucination = json.dumps(dict(zip(('iniziale', 'centrale', 'recente'), NOTES)))
    assert not evaluate('long', hallucination, [False, True, True])['grounded_recall']
    assert not evaluate('long', '```json\n'+missing+'\n```', [False, True, True])['json_schema']
    assert evaluate('short', ' 5\n')['exact_answer']
    assert not evaluate('short', 'Sono 5')['exact_answer']
