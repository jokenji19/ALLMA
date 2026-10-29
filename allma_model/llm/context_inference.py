"""Isolated context experiment: one Qwen at a time, with runtime restoration.

Two opposite orders reduce (not eliminate) warm-up/thermal order effects.
Host identity, histories, learned answers and model preferences are never written.
RSS/PSS are process residency, not total GPU/device memory or energy usage.
"""
import json
import math
from pathlib import Path
import re
import threading
import time
import uuid

from .context_diagnostics import CONTEXTS, NOTES, synthetic_dialogue
from .native_backend import native_work
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled

TOTAL_BUDGET = 192
THOUGHT_BUDGET = 48
ORDERS = (CONTEXTS, tuple(reversed(CONTEXTS)))
MAX_TEMPERATURE = 40.5


def residency():
    result = {'rss_mib': None, 'pss_mib': None}
    for filename, key, metric in (('/proc/self/status', 'VmRSS', 'rss_mib'),
                                  ('/proc/self/smaps_rollup', 'Pss', 'pss_mib')):
        try:
            data = Path(filename).read_text()
            match = re.search(r'^' + key + r':\s+(\d+)\s+kB$', data, re.M)
            if match:
                result[metric] = int(match[1]) / 1024
        except OSError:
            pass
    return result


def conditions(source):
    from allma_model.core.system_monitor import current_power_reading
    result = residency()
    result.update(temperature_c=None, charging=None, battery_fraction=None, thermal_status=None, thermal_api_available=None)
    try:
        state = source.system_monitor.get_metabolic_state()
        if current_power_reading(state):
            value = state.battery_temp_celsius
            if type(value) in (int, float) and math.isfinite(value) and value > 0:
                result.update(temperature_c=float(value), charging=state.is_charging,
                              battery_fraction=state.energy_level, thermal_status=getattr(state,'thermal_status',None),
                              thermal_api_available=getattr(state,'thermal_api_available',None))
    except Exception:
        pass
    return result


def evaluate(case_id, answer, retained=None):
    """Only these fixed synthetic answers are graded; no global intelligence score."""
    if case_id == 'short':
        return {'exact_answer': answer.strip() == '5'}
    keys = ('iniziale', 'centrale', 'recente')
    try:
        data = json.loads(answer)
    except (ValueError, TypeError):
        data = None
    schema = (type(data) is dict and set(data) == set(keys)
              and all(value is None or type(value) is str for value in data.values()))
    expected = dict(zip(keys, NOTES))
    available = {key: expected[key] if retained[index] else None for index, key in enumerate(keys)}
    return {'json_schema': schema,
            'grounded_recall': bool(schema and data == available),
            'full_history_recall': bool(schema and data == expected),
            'expected_from_retained_prompt': available}


def requests():
    short = [{'role': 'system', 'content': 'Ti chiami ALLMA. Rispondi in italiano e segui il formato richiesto.'},
             {'role': 'user', 'content': 'Una scatola contiene 7 palline e ne vengono tolte 2. Quante restano? Rispondi solo con il numero.'}]
    long = synthetic_dialogue()
    long[-1]['content'] = ('Scrivi solo un JSON con le chiavi iniziale, centrale, recente. '
                          'Per ciascuna inserisci il codice della nota corrispondente, '
                          'oppure null se la nota non compare nel dialogo. Non inventare codici.')
    return (('short', short, 20261026), ('long', long, 20261027))


class ExperimentCancellation:
    def __init__(self, run):
        self.run = run
        self.deadline = time.monotonic() + 90
        self.next_sensor_read = 0
        self.reason = None
        self.rss_peak_mib = None

    def is_set(self):
        source = self.run.source
        if self.run.cancel_event.is_set() or source._shutdown_event.is_set():
            self.reason = 'cancelled'
        elif not getattr(source, '_foreground', True):
            self.reason = 'background'
        elif time.monotonic() >= self.deadline:
            self.reason = 'request_timeout'
        elif time.monotonic() >= self.next_sensor_read:
            self.next_sensor_read = time.monotonic() + 1
            sample = self.run.sample(source)
            rss = sample.get('rss_mib')
            if type(rss) in (int, float):
                self.rss_peak_mib = max(self.rss_peak_mib or 0, rss)
            temperature = sample.get('temperature_c')
            if temperature is None:
                self.reason = 'sensors_unavailable'
            elif temperature >= MAX_TEMPERATURE:
                self.reason = 'thermal_pause'
        return self.reason is not None


class ContextInferenceRun:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.manifest = {}
        self.sample = conditions
        self.factory = None

    def setup_brain(self, existing_brain):
        self.source = existing_brain
        self.report_path = str(Path(existing_brain.db_path).resolve().parent / 'benchmarks/reports' /
                               ('context_inference_' + uuid.uuid4().hex + '.md'))

    def _link(self, engine):
        source = self.source
        with source._lock:
            if engine is not None and source._shutdown_event.is_set():
                engine.close()
                raise GenerationCancelled('ALLMA chiusa durante il caricamento')
            source._llm = engine
            source._llm_ready = engine is not None
            source._owns_llm = engine is not None
            source.reasoning_engine.llm = engine
            source.dream_manager.llm_wrapper = engine
            source.dream_manager.tot.llm = engine

    def _load(self, config, size):
        factory = self.factory
        if factory is None:
            from .mobile_gemma_wrapper import MobileGemmaWrapper
            factory = MobileGemmaWrapper
        engine = factory(**config, n_ctx=size)
        if engine.llm is None:
            engine.close()
            raise RuntimeError('Caricamento del modello non riuscito')
        return engine

    def _write(self, summary):
        path = Path(self.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        from allma_model.utils.persistence import atomic_write_json
        atomic_write_json(path.with_suffix('.json'), summary)
        report = '# Contesto 2K / 4K / 8K: inferenza reale\n\n'
        report += ('Stesso modello, seed e budget per caso. Due ordini opposti; nessun retry. '
                   'Dati sintetici e percorso nativo, senza memoria personale o filtri della chat. '
                   'RSS/PSS indicano la residenza del processo, non tutta la memoria GPU. '
                   'Due repliche non sono una misura generale di qualità o risparmio energetico.\n\n')
        report += 'Esito: ' + summary['stop_reason'] + '; contesto ripristinato: ' + str(summary['restored']) + '.\n\n'
        for row in summary['results']:
            report += f"## Giro {row['round']} · {row['context_tokens']} token · {row['case']}\n\n{row['answer']}\n\n"
            report += json.dumps(row['checks'], ensure_ascii=False) + '\n\n'
        path.write_text(report)

    @native_work
    def run_tests(self, progress_callback=None):
        source = self.source
        # Reserve before changing any engine reference; a borrowed motor belongs
        # to a different core and must never be closed by this experiment.
        with source._lock:
            if (source._user_active.is_set() or getattr(source, '_benchmark_active', False)
                    or source._shutdown_event.is_set() or source.dream_manager.is_dreaming):
                raise RuntimeError('Attendi che ALLMA sia libera prima della prova')
            source._ensure_mobile_llm()
            old = source._llm
            if old is None or old.llm is None or not source._owns_llm:
                raise RuntimeError('Serve un modello caricato e posseduto da ALLMA')
            config = {'models_dir': old.models_dir, 'model_name': Path(old.model_path).name,
                      'reasoning': old.binding.reasoning, 'system_monitor': source.system_monitor}
            original_context = old.n_ctx
            original_backend = old.backend_info.get('kind')
            source._benchmark_active = True
            source._user_active.set()
        summary = {'scope': 'native GGUF inference; synthetic dialogue; no personal state',
                   'model_name': config['model_name'], 'production_context': original_context,
                   'original_backend': original_backend, 'orders': ORDERS,
                   'total': 12, 'completed': 0, 'results': [], 'loads': [],
                   'total_budget': TOTAL_BUDGET, 'reasoning_budget': THOUGHT_BUDGET,
                   'stop_reason': 'running', 'restored': False, 'restore_error': None,
                   'phase': 'reserved'}
        engine, disrupted, failure, cancellation = None, False, None, None
        try:
            self._write(summary)
            for round_index, order in enumerate(ORDERS, 1):
                for size in order:
                    cancellation = ExperimentCancellation(self)
                    check_cancelled(cancellation)
                    if progress_callback:
                        progress_callback(len(summary['results']), 12, f'Caricamento contesto {size} · giro {round_index}')
                    # Detach/close before the factory is called: at most one Qwen
                    # allocation exists, including failure and restoration paths.
                    if not disrupted:
                        self._link(None)
                        disrupted = True
                        old.close()
                    elif engine is not None:
                        self._link(None)
                        engine.close()
                        engine = None
                    summary['phase'] = f'load_{round_index}_{size}'
                    self._write(summary)
                    start = time.perf_counter()
                    engine = self._load(config, size)
                    self._link(engine)
                    loaded = self.sample(source)
                    summary['loads'].append({'round': round_index, 'context_tokens': size,
                        'load_ms': (time.perf_counter() - start) * 1000,
                        'backend': dict(engine.backend_info), 'conditions': loaded})
                    if engine.backend_info.get('kind') != original_backend:
                        raise RuntimeError('Backend cambiato: confronto non omogeneo')
                    for case_id, messages, seed in requests():
                        cancellation = ExperimentCancellation(self)
                        check_cancelled(cancellation)
                        before = self.sample(source)
                        if progress_callback:
                            progress_callback(len(summary['results']), 12, f'{size} token · {case_id} · giro {round_index}')
                        # Avoid prefix reuse between cases: this experiment
                        # compares cold prompts, not a warmed continuation cache.
                        with engine.inference_lock:
                            engine.llm.set_cache(None)
                            engine.llm.reset()
                        prepared = engine.prepare_chat(messages, TOTAL_BUDGET, reasoning=True)
                        retained = [note in prepared.prompt for note in NOTES]
                        request_id = 'CONTEXT_EXPERIMENT:' + uuid.uuid4().hex
                        stream = {'tail': '', 'answer_phase': not prepared.reasoning, 'first_answer_ms': None}
                        start = time.perf_counter()
                        def observe(token):
                            if stream['answer_phase']:
                                if token.strip() and stream['first_answer_ms'] is None:
                                    stream['first_answer_ms'] = (time.perf_counter() - start) * 1000
                            else:
                                stream['tail'] = (stream['tail'] + token)[-32:]
                                if '</think>' in stream['tail']:
                                    stream['answer_phase'] = True
                        answer = engine.generate(prompt=prepared.prompt, max_tokens=TOTAL_BUDGET,
                            thought_budget=THOUGHT_BUDGET if prepared.reasoning else None,
                            **engine.binding.sampling(), repeat_penalty=1.10, repeat_last_n=128,
                            stop=list(prepared.stops), native_prompt=True,
                            request_id=request_id, conversation_id=request_id, seed=seed,
                            cancel_event=cancellation, callback=observe)
                        elapsed = (time.perf_counter() - start) * 1000
                        generation = dict(engine.get_generation_meta(request_id) or {})
                        if (generation.get('backend') != original_backend
                                or str(answer).startswith(('Error:', 'Error during inference:'))):
                            raise RuntimeError('Inferenza non completata sul backend atteso')
                        row = {'round': round_index, 'context_tokens': size, 'case': case_id,
                               'seed': seed, 'answer': answer, 'checks': evaluate(case_id, answer, retained),
                               'history_pairs_removed': prepared.history_removed,
                               'notes_retained': retained if case_id == 'long' else None,
                               'elapsed_ms': elapsed, 'generation': generation,
                               'first_answer_ms': stream['first_answer_ms'],
                               'before': before, 'after': self.sample(source),
                               'rss_sampled_peak_mib': cancellation.rss_peak_mib}
                        summary['results'].append(row)
                        summary['completed'] = len(summary['results'])
                        summary['phase'] = 'case_completed'
                        self._write(summary)
            summary['stop_reason'] = 'completed'
        except GenerationCancelled:
            summary['stop_reason'] = (cancellation.reason if cancellation else None) or 'cancelled'
        except Exception as error:
            summary['stop_reason'] = 'error'
            summary['error'] = type(error).__name__ + ': ' + str(error)[:200]
            failure = error
        finally:
            summary['phase'] = 'restoring'
            try:
                if progress_callback:
                    try:
                        progress_callback(len(summary['results']), 12, 'Ripristino la configurazione iniziale')
                    except Exception:
                        pass  # UI feedback cannot prevent runtime restoration.
                if disrupted:
                    self._link(None)
                    if engine is not None:
                        engine.close()
                    if not source._shutdown_event.is_set():
                        restored = self._load(config, original_context)
                        self._link(restored)
                        summary['restored'] = (restored.n_ctx == original_context
                                               and restored.backend_info.get('kind') == original_backend)
                        summary['restored_backend'] = dict(restored.backend_info)
                        if not summary['restored']:
                            summary['stop_reason'] = 'restored_backend_changed'
                        source._mobile_llm_error = None
                    else:
                        summary['stop_reason'] = 'shutdown'
                else:
                    summary['restored'] = source._llm is old and old.llm is not None
            except GenerationCancelled:
                summary['stop_reason'] = 'shutdown'
            except Exception as error:
                self._link(None)
                source._mobile_llm_error = 'Ripristino del modello da verificare: ' + str(error)[:160]
                summary['restore_error'] = type(error).__name__ + ': ' + str(error)[:200]
                summary['stop_reason'] = 'restore_failed'
            finally:
                with source._lock:
                    source._benchmark_active = False
                    if not source._shutdown_event.is_set():
                        source._user_active.clear()
            summary['phase'] = 'finished'
            self.manifest = {'cancelled': summary['stop_reason'] != 'completed',
                             'stop_reason': summary['stop_reason'], 'summary': summary}
            self._write(summary)
            print('ALLMA_CONTEXT_INFERENCE_REPORT ' + str(Path(self.report_path).with_suffix('.json')), flush=True)
            print('ALLMA_CONTEXT_INFERENCE_SUMMARY ' + json.dumps({key: summary[key] for key in
                  ('completed', 'total', 'stop_reason', 'restored', 'restore_error')}, ensure_ascii=False), flush=True)
        if summary['restore_error']:
            raise RuntimeError('Il contesto originale non è stato ripristinato; riapri ALLMA')
        if failure:
            raise failure

    def close(self):
        self.cancel_event.set()
