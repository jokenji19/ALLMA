"""Fixed 2K causal probes: CPU/GPU, bounded/natural reasoning, prompt audit.

One variable at a time; one native motor at a time. No personal memory or
production preference writes. The host's exact-answer tools are excluded.
"""
import hashlib
import json
from pathlib import Path
import time
import uuid

from .context_inference import ContextInferenceRun, ExperimentCancellation
from .native_backend import native_work
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled
from allma_model.utils.thinking_stream import ThinkingStream

CASES = (
    ('original', 'Una scatola contiene 7 palline e ne vengono tolte 2. Quante restano? Rispondi solo con il numero.', '5', 20261026),
    ('novel', 'Ho undici biglie e ne regalo quattro. Quante biglie mi rimangono? Rispondi soltanto con un numero.', '7', 20261028),
    ('format', 'Il codice sintetico di questa prova è BETA-816. Restituisci soltanto un JSON con una chiave codice e il suo valore, senza spiegazioni.', {'codice': 'BETA-816'}, 20261029),
)
VARIANTS = (
    ('gpu48', None, 48, 192),
    ('cpu48', 'cpu', 48, 192),
    ('gpu128', None, 128, 272),
    ('natural', None, None, 272),
)


def grade(answer, expected):
    if isinstance(expected, dict):
        try:
            value = json.loads(answer)
        except (TypeError, ValueError):
            value = None
        return {'correct_and_formatted': value == expected, 'format': 'json'}
    if expected in ('sì', 'no'):
        return {'correct_and_formatted': answer.strip().casefold() == expected, 'format': 'yes_no'}
    if expected.isdigit():
        return {'correct_and_formatted': answer.strip() == expected,
                'numeric_value_correct': answer.strip().rstrip('.') == expected, 'format': 'number'}
    return {'correct_and_formatted': answer.strip() == expected, 'format': 'literal'}


def prompt_audit(engine, prepared, question):
    with engine.inference_lock:
        tokens = engine.llm.tokenize(prepared.prompt.encode(), add_bos=False, special=True)
        decoded = engine.llm.detokenize(tokens, special=True).decode('utf-8')
    return {'prompt': prepared.prompt, 'prompt_sha256': hashlib.sha256(prepared.prompt.encode()).hexdigest(),
            'native_token_ids': list(tokens), 'token_count': len(tokens),
            'round_trip_exact': decoded == prepared.prompt,
            'question_occurrences': prepared.prompt.count(question),
            'history_removed': prepared.history_removed, 'stops': list(prepared.stops),
            'thinking_open': prepared.prompt.rstrip().endswith('<think>'),
            'template_sha256': hashlib.sha256(engine.binding.template_source.encode()).hexdigest()}


class ReasoningDiagnosticRun(ContextInferenceRun):
    variants = VARIANTS
    cases = CASES
    report_name = 'reasoning_diagnostic'
    report_prefix = 'ALLMA_REASONING_DIAGNOSTIC'
    report_title = 'CPU, GPU e ragionamento: diagnosi a 2K'
    report_description = ('Stessi prompt, seed e campionamento. 48/128 token con 144 riservati alla risposta; '
                          'chiusura naturale con limite totale 272, senza riserva garantita.')

    def setup_brain(self, existing_brain):
        super().setup_brain(existing_brain)
        self.report_path = self.report_path.replace('context_inference_', self.report_name + '_')

    def penalty(self, variant):
        return 1.10

    def reset_answer_state(self, variant):
        return False

    def thinking(self, variant):
        return True

    def case_plan(self, variant):
        return self.cases

    def _write(self, summary):
        from allma_model.utils.persistence import atomic_write_json
        path = Path(self.report_path);path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path.with_suffix('.json'), summary)
        report = '# ' + self.report_title + '\n\n'
        report += self.report_description + ' Nessun retry o memoria personale. Pochi casi sintetici, non una misura generale di accuratezza.\n\n'
        report += 'Esito: ' + summary['stop_reason'] + '; ripristinato: ' + str(summary['restored']) + '.\n\n'
        for row in summary['results']:
            report += '## ' + row['variant'] + ' · ' + row['case'] + '\n\n' + row['answer'] + '\n\n'
            report += json.dumps(row['checks'], ensure_ascii=False) + '\n\n'
        path.write_text(report)

    @native_work
    def run_tests(self, progress_callback=None):
        source = self.source
        with source._lock:
            if (source._user_active.is_set() or getattr(source, '_benchmark_active', False)
                    or source._shutdown_event.is_set() or source.dream_manager.is_dreaming):
                raise RuntimeError('Attendi che ALLMA sia libera prima della prova')
            source._ensure_mobile_llm();old = source._llm
            if old is None or old.llm is None or not source._owns_llm:
                raise RuntimeError('Serve un modello posseduto da ALLMA')
            if old.backend_info.get('kind') != 'opencl' or not old.binding.reasoning:
                raise RuntimeError('Questa prova richiede il modello ragionante già caricato su OpenCL')
            config = {'models_dir': old.models_dir, 'model_name': Path(old.model_path).name,
                      'reasoning': old.binding.reasoning, 'system_monitor': source.system_monitor}
            original_context = old.n_ctx
            source._benchmark_active = True;source._user_active.set()
        summary = {'scope': 'native synthetic causal probes; no host answer tools',
                   'model_name': config['model_name'], 'production_context': original_context,
                   'test_context': 2048, 'total': sum(len(self.case_plan(v[0])) for v in self.variants), 'completed': 0,
                   'phase': 'reserved', 'stop_reason': 'running', 'restored': False,
                   'restore_error': None, 'results': [], 'loads': []}
        engine, disrupted, failure, cancellation = None, False, None, None
        try:
            self._write(summary)
            print(self.report_prefix + '_REPORT ' + str(Path(self.report_path).with_suffix('.json')), flush=True)
            for name, backend, thought_budget, total_budget in self.variants:
                cancellation = ExperimentCancellation(self);check_cancelled(cancellation)
                if progress_callback:progress_callback(summary['completed'], summary['total'], 'Collego ' + name)
                if not disrupted:
                    self._link(None);disrupted = True;old.close()
                elif engine is not None:
                    self._link(None);engine.close();engine = None
                summary['phase'] = 'load_' + name;self._write(summary)
                options = dict(config)
                if backend:options['backend_preference'] = backend
                start = time.perf_counter();engine = self._load(options, 2048);self._link(engine)
                expected_backend = 'cpu' if backend else 'opencl'
                if engine.backend_info.get('kind') != expected_backend:
                    raise RuntimeError('Il backend della prova non coincide con quello richiesto')
                summary['loads'].append({'variant': name, 'backend': dict(engine.backend_info),
                                         'load_ms': (time.perf_counter()-start)*1000})
                for case_id, question, expected, seed in self.case_plan(name):
                    cancellation = ExperimentCancellation(self);check_cancelled(cancellation)
                    if progress_callback:progress_callback(summary['completed'], summary['total'], name + ' · ' + case_id)
                    before = self.sample(source)
                    with engine.inference_lock:
                        engine.llm.set_cache(None);engine.llm.reset()
                    prepared = engine.prepare_chat([
                        {'role': 'system', 'content': 'Ti chiami ALLMA. Rispondi in italiano e segui il formato richiesto.'},
                        {'role': 'user', 'content': question}], total_budget, reasoning=self.thinking(name))
                    audit = prompt_audit(engine, prepared, question)
                    if not audit['round_trip_exact'] or audit['question_occurrences'] != 1 or audit['history_removed']:
                        raise RuntimeError('Il prompt nativo non conserva esattamente la domanda sintetica')
                    stream = ThinkingStream(in_thought=prepared.reasoning)
                    timing = {'first_answer_ms': None, 'closed': False}
                    start = time.perf_counter()
                    def observe(token):
                        for event in stream.feed(token):
                            if event['type'] == 'answer' and event['content'].strip() and timing['first_answer_ms'] is None:
                                timing['first_answer_ms'] = (time.perf_counter()-start)*1000
                        timing['closed'] = not stream.in_thought
                        if self.reset_answer_state(name) and token == '\n</think>\n\n':
                            # bounded_completion has closed the first iterator;
                            # generate already owns the inference lock here.
                            engine.llm.reset()
                    request_id = 'REASONING_DIAGNOSTIC:' + uuid.uuid4().hex
                    answer = engine.generate(prompt=prepared.prompt, max_tokens=total_budget,
                        thought_budget=thought_budget, **engine.binding.sampling(),
                        repeat_penalty=self.penalty(name), repeat_last_n=128, stop=list(prepared.stops),
                        native_prompt=True, request_id=request_id, conversation_id=request_id,
                        seed=seed, cancel_event=cancellation, callback=observe)
                    elapsed = (time.perf_counter()-start)*1000
                    generation = dict(engine.get_generation_meta(request_id) or {})
                    if generation.get('backend') != expected_backend or answer.startswith(('Error:', 'Error during inference:')):
                        raise RuntimeError('Generazione non completata sul backend previsto')
                    row = {'variant': name, 'case': case_id, 'question': question, 'expected': expected,
                           'answer': answer, 'checks': grade(answer, expected), 'seed': seed,
                           'repeat_penalty': self.penalty(name), 'answer_state_reset': self.reset_answer_state(name),
                           'thinking_enabled': prepared.reasoning,
                           'budget': {'total': total_budget, 'reasoning': thought_budget,
                                      'reserved_answer': total_budget-thought_budget if thought_budget else total_budget if not prepared.reasoning else None},
                           'prompt_audit': audit, 'generation': generation, 'elapsed_ms': elapsed,
                           'first_answer_ms': timing['first_answer_ms'], 'reasoning_close_observed': timing['closed'],
                           'before': before, 'after': self.sample(source)}
                    summary['results'].append(row);summary['completed'] += 1
                    summary['phase'] = 'case_completed';self._write(summary)
                    print(self.report_prefix + '_PROGRESS ' + json.dumps({
                        'completed': summary['completed'], 'variant': name, 'case': case_id,
                        'correct': row['checks']['correct_and_formatted']}, ensure_ascii=False), flush=True)
            summary['stop_reason'] = 'completed'
        except GenerationCancelled:
            summary['stop_reason'] = (cancellation.reason if cancellation else None) or 'cancelled'
        except Exception as error:
            failure = error;summary['stop_reason'] = 'error'
            summary['error'] = type(error).__name__ + ': ' + str(error)[:200]
        finally:
            summary['phase'] = 'restoring'
            try:
                if progress_callback:
                    try:progress_callback(summary['completed'], summary['total'], 'Ripristino la configurazione iniziale')
                    except Exception:pass
                if disrupted:
                    self._link(None)
                    if engine is not None:engine.close()
                    if not source._shutdown_event.is_set():
                        restored = self._load(config, original_context);self._link(restored)
                        summary['restored'] = restored.n_ctx == original_context and restored.backend_info.get('kind') == 'opencl'
                        summary['restored_backend'] = dict(restored.backend_info)
                        source._mobile_llm_error = None
                        if not summary['restored']:summary['stop_reason'] = 'restored_backend_changed'
                    else:summary['stop_reason'] = 'shutdown'
                else:summary['restored'] = source._llm is old and old.llm is not None
            except GenerationCancelled:summary['stop_reason'] = 'shutdown'
            except Exception as error:
                self._link(None);source._mobile_llm_error = 'Ripristino del modello da verificare: ' + str(error)[:160]
                summary['restore_error'] = str(error)[:200];summary['stop_reason'] = 'restore_failed'
            finally:
                with source._lock:
                    source._benchmark_active = False
                    if not source._shutdown_event.is_set():source._user_active.clear()
            summary['phase'] = 'finished'
            self.manifest = {'cancelled': summary['stop_reason'] != 'completed', 'stop_reason': summary['stop_reason'], 'summary': summary}
            self._write(summary)
            print(self.report_prefix + '_SUMMARY ' + json.dumps({key: summary[key] for key in
                ('completed', 'total', 'stop_reason', 'restored', 'restore_error')}), flush=True)
        if summary['restore_error']:raise RuntimeError('Ripristino non riuscito: riapri ALLMA')
        if failure:raise failure


class ReasoningFollowupRun(ReasoningDiagnosticRun):
    """Distinguish sampler pressure from reuse at the answer boundary."""
    variants = (('baseline48', None, 48, 192), ('neutral48', None, 48, 192),
                ('fresh48', None, 48, 192), ('neutral128', None, 128, 272),
                ('native_direct', None, None, 144))
    report_name = 'reasoning_followup'
    report_prefix = 'ALLMA_REASONING_FOLLOWUP'
    report_title = 'Passaggio alla risposta e penalità: diagnosi a 2K'
    report_description = ('Stesse domande e seed. Baseline 48 token; penalità neutra; ricalcolo dello stato alla risposta; '
                          'penalità neutra a 128 token; modalità nativa senza pensiero come controllo. '
                          'Riserva finale 144 token. Le variabili modificate sono registrate per ogni caso.')

    def penalty(self, variant):
        return 1.0 if variant.startswith('neutral') else 1.10

    def reset_answer_state(self, variant):
        return variant == 'fresh48'

    def thinking(self, variant):
        return variant != 'native_direct'


class ReasoningValidationRun(ReasoningFollowupRun):
    variants = (('baseline48', None, 48, 192), ('neutral128', None, 128, 272),
                ('native_direct', None, None, 144), ('natural_end_check', None, None, 272))
    cases = (
        ('unseen_arithmetic', 'Un sacchetto contiene quattordici gettoni. Ne tolgo sei e ne aggiungo tre. Quanti gettoni ci sono? Rispondi soltanto con un numero.', '11', 20261030),
        ('unseen_deduction', 'Tutti i nori sono pavi. Nessun pavo è verde. Può esistere un noro verde? Rispondi soltanto sì o no.', 'no', 20261031),
        ('unseen_json', 'Per questa prova il codice è RAME-409 e lo stato è aperto. Restituisci soltanto un JSON con le chiavi codice e stato e i loro valori esatti.', {'codice': 'RAME-409', 'stato': 'aperto'}, 20261032),
        ('unseen_position', 'Qual è la terza lettera della parola MARE? Rispondi soltanto con la lettera maiuscola.', 'R', 20261033),
    )
    report_name = 'reasoning_validation'
    report_prefix = 'ALLMA_REASONING_VALIDATION'
    report_title = 'Verifica su casi nuovi e motivo di arresto nativo'
    report_description = ('Quattro casi nuovi per tre configurazioni, senza adattamenti o retry. '
                          'Una tredicesima richiesta ripete il precedente caso naturale per verificare il motivo di arresto nativo corretto.')

    def case_plan(self, variant):
        return (CASES[0],) if variant == 'natural_end_check' else self.cases
