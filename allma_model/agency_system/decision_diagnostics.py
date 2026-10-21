"""Synthetic EN/IT decision probes; never read or modify personal memories."""
import json
from pathlib import Path
import threading
import time
import uuid

from .decision_engine import DECIDER_MODEL, LocalDecisionEngine
from .action_cycle import ActionCycle, LocalAction
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled


OPTIONS = {
    'calculate': 'Use an exact arithmetic calculator for an explicit calculation.',
    'memory': 'Search the personal conversation memory for a past interaction.',
    'reason': 'Use the language and reasoning model for general knowledge or explanations.',
    'clarify': 'Ask for clarification because the request has no identifiable subject.',
}
CASES = [
    ('calc_en', 'Calculate 18 plus 24.', 'calculate'),
    ('calc_it', 'Quanto fa 18 più 24?', 'calculate'),
    ('memory_en', 'What did I tell you about my dog last time?', 'memory'),
    ('memory_it', 'Cosa ti avevo raccontato del mio cane?', 'memory'),
    ('general_en', 'Explain how a rainbow forms.', 'reason'),
    ('general_it', 'Spiegami come si forma un arcobaleno.', 'reason'),
    ('unclear_en', 'Do that thing with the other one.', 'clarify'),
    ('unclear_it', 'Fai quella cosa con quell’altro.', 'clarify'),
]


def measure(engine, cancel_event, progress_callback=None, temperature=None):
    results, reason = [], 'completed'
    for index, (case_id, text, expected) in enumerate(CASES):
        if cancel_event.is_set():
            reason = 'cancelled'
            break
        if temperature and (temperature() or 0) >= 42:
            reason = 'thermal_pause'
            break
        if progress_callback:
            progress_callback(index, len(CASES), f'Decisore: {case_id}')
        result = engine.decide(text, 'Which resource is most useful?', OPTIONS, cancel_event=cancel_event)
        if result.status == 'cancelled':
            reason = 'cancelled'
            break
        proposed = max(result.probabilities, key=result.probabilities.get) if result.probabilities else None
        results.append({'id': case_id, 'expected': expected, 'proposed': proposed,
                        'choice': result.choice, 'status': result.status,
                        'correct': result.choice == expected,
                        'top_choice_correct': proposed == expected,
                        'elapsed_ms': result.elapsed_ms, 'probabilities': result.probabilities})
    cycles = []
    if reason == 'completed':
        # Real actions on disposable fixtures. No model-generated tool arguments.
        fixtures = [('calculate', 'Calculate 18 plus 24.', lambda: 18 + 24, lambda x: type(x) is int and x == 42),
                    ('memory', 'Retrieve the user name from the supplied synthetic memory.',
                     lambda: {'source':'synthetic_memory','name':'Ada'},
                     lambda x: isinstance(x, dict) and x.get('source') == 'synthetic_memory' and x.get('name') == 'Ada')]
        for name, state, execute, verify in fixtures:
            if cancel_event.is_set():
                reason = 'cancelled'
                break
            if temperature and (temperature() or 0) >= 42:
                reason = 'thermal_pause'
                break
            cycle = ActionCycle(engine, {name: LocalAction(OPTIONS[name], execute, verify)}, max_steps=1,
                                diagnostic=True)
            result = cycle.run(state, cancel_event=cancel_event)
            cycles.append({'id': name, **result,
                           'verified_action': bool(result['steps']) and result['steps'][0]['verified']})
    return {'scope': 'synthetic routing probes and bounded actions; not general intelligence or energy efficiency',
            'mode': 'diagnostic_only', 'model_sha256': DECIDER_MODEL['sha256'],
            'total': len(CASES), 'completed': len(results), 'stop_reason': reason,
            'accepted_correct': sum(r['correct'] for r in results),
            'accepted_wrong': sum(r['choice'] is not None and not r['correct'] for r in results),
            'abstentions': sum(r['status'] == 'abstained' for r in results), 'results': results,
            'action_cycles': cycles}


class DecisionDiagnosticRun:
    """Same UI lifecycle as other benchmarks; explicit start, release on finish.

    No chat observer is enabled: additional inference is confined to this run.
    """
    def __init__(self):
        self.cancel_event = threading.Event()
        self.manifest = {}
        self.engine = None

    def setup_brain(self, existing_brain):
        self.source = existing_brain
        self.output = Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/('decider_'+uuid.uuid4().hex)
        self.output.mkdir(parents=True, exist_ok=True)
        self.report_path = str(self.output/'report.md')

    def run_tests(self, progress_callback=None):
        core = self.source
        with core._lock:
            if (core._user_active.is_set() or getattr(core, '_benchmark_active', False)
                    or getattr(core, '_model_switching', False) or core.dream_manager.is_dreaming
                    or core._shutdown_event.is_set()):
                raise RuntimeError('Attendi che ALLMA sia libera')
            core._benchmark_active = True
            core._user_active.set()
        started = time.perf_counter()
        summary = None
        try:
            # The explicit native probe must not allocate a second resident
            # Decider alongside the operational instance.
            runtime = getattr(core, 'decision_runtime', None)
            if runtime is not None:
                runtime.release()
            from allma_model.utils.model_downloader import ModelDownloader
            def temperature():
                return core.temperature_monitor.get_temperatures().get('battery')
            if (temperature() or 0) >= 42:
                raise RuntimeError('Telefono caldo: attendi che si raffreddi prima della prova')
            folder = Path(core.models_dir)/'decider-0.8b'
            downloader = ModelDownloader(str(folder))
            downloader.models = {'decider': DECIDER_MODEL}
            downloader.max_retries = 1
            def progress(current, total):
                check_cancelled(self.cancel_event)
                if progress_callback:
                    progress_callback(0, len(CASES), f'Download decisore: {current/total:.0%} · 529 MB')
            check_cancelled(self.cancel_event)
            ok, error = downloader.download_model('decider', progress)
            if not ok:
                raise RuntimeError(error or 'Download decisore non riuscito')
            check_cancelled(self.cancel_event)
            if progress_callback:
                progress_callback(0, len(CASES), 'Caricamento decisore sperimentale…')
            self.engine = LocalDecisionEngine(folder/DECIDER_MODEL['filename'])
            self.engine.load()
            summary = measure(self.engine, self.cancel_event, progress_callback, temperature)
        except GenerationCancelled:
            summary = {'mode': 'diagnostic_only', 'results': [], 'total': len(CASES),
                       'completed': 0, 'stop_reason': 'cancelled'}
        finally:
            try:
                if self.engine:
                    self.engine.close()
            finally:
                core._benchmark_active = False
                core._user_active.clear()
        summary['wall_ms'] = (time.perf_counter()-started)*1000
        self.manifest = {'cancelled': summary['stop_reason'] == 'cancelled',
                         'stop_reason': summary['stop_reason']}
        (self.output/'report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        text = '# Decisore locale sperimentale\n\n'
        text += 'Solo dati sintetici. Non modifica chat, identità o memoria. Nessuna attivazione automatica.\n\n'
        text += f"Esito: {summary['stop_reason']}. Casi completati: {summary['completed']}/{summary['total']}.\n\n"
        text += '| Caso | Atteso | Scelta | Stato | ms |\n|---|---|---|---|---|\n'
        for row in summary['results']:
            text += f"| {row['id']} | {row['expected']} | {row['choice'] or '—'} | {row['status']} | {row['elapsed_ms']:.0f} |\n"
        text += '\nLe probabilità Q4 e l’italiano richiedono validazione; nessuna stima di risparmio energetico.\n'
        for cycle in summary.get('action_cycles', []):
            text += f"\nAzione sintetica {cycle['id']}: {cycle['status']}; verificata: {cycle['verified_action']}.\n"
        Path(self.report_path).write_text(text, encoding='utf-8')
        print('ALLMA_DECIDER_SUMMARY '+json.dumps(summary), flush=True)

    def close(self):
        self.cancel_event.set()
        if self.engine:
            self.engine.close()
