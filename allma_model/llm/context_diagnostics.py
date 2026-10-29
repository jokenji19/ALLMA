"""Compare prompt retention using one native tokenizer, without reloading a GPU.

This is a packing experiment, not a speed, RAM or semantic-quality benchmark.
Production context and personal memory are never modified.
"""
import json
from pathlib import Path
import threading
import time
import uuid

from .model_binding import ModelBinding
from .native_backend import native_work
from allma_model.utils.generation_control import check_cancelled, GenerationCancelled

CONTEXTS = (2048, 4096, 8192)
BUDGET = 256
NOTES = ('CEDRO-732', 'LAGO-184', 'NEVE-906')


def synthetic_dialogue():
    messages = [{'role': 'system', 'content': 'Ti chiami ALLMA. Considera solo il dialogo fornito.'}]
    for index in range(60):
        note = f' Il codice sintetico è {NOTES[(0, 30, 59).index(index)]}.' if index in (0, 30, 59) else ''
        messages.extend((
            {'role': 'user', 'content': f'Nota di archivio sintetico {index}: confronto di elementi geometrici, sequenze numeriche e descrizioni di paesaggi. Nessuna esperienza personale reale.' + note},
            {'role': 'assistant', 'content': 'Nota registrata in questa conversazione di prova: descrizione di quadrati, triangoli e cerchi, senza aggiungere informazioni.'},
        ))
    messages.append({'role': 'user', 'content': 'Quali codici sintetici sono presenti nelle note iniziale, centrale e finale? Non inventare quelli assenti.'})
    return messages


def compare_fit(binding, tokenize, cancel_event=None, *, rows=None, progress_callback=None):
    messages = synthetic_dialogue()
    rows = [] if rows is None else rows
    def checked_tokenize(data):
        check_cancelled(cancel_event)
        return tokenize(data)
    for size in CONTEXTS:
        check_cancelled(cancel_event)
        candidate = ModelBinding({'general.architecture': binding.architecture,
                                  'tokenizer.chat_template': binding.template_source},
                                 bos=binding.bos, eos=binding.eos, context_size=size,
                                 reasoning=binding.reasoning)
        candidate.extra_stops = binding.extra_stops
        start = time.perf_counter()
        prepared = candidate.prepare(messages, checked_tokenize, BUDGET, reasoning=True)
        tokens = len(tokenize(prepared.prompt.encode('utf-8')))
        rows.append({'context_tokens': size, 'prompt_tokens': tokens,
                     'completion_reserve': BUDGET, 'safety_reserve': 32,
                     'history_pairs_removed': prepared.history_removed,
                     'notes_retained': {name: note in prepared.prompt for name, note in zip(('initial', 'middle', 'recent'), NOTES)},
                     'packing_ms': (time.perf_counter() - start) * 1000})
        if progress_callback:
            progress_callback(len(rows), len(CONTEXTS), 'Storia conservata: ' + str(size) + ' token')
    return rows


class ContextFitRun:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.manifest = {}

    def setup_brain(self, existing_brain):
        self.source = existing_brain
        self.report_path = str(Path(existing_brain.db_path).resolve().parent / 'benchmarks/reports' / ('context_fit_' + uuid.uuid4().hex + '.md'))

    @native_work
    def run_tests(self, progress_callback=None):
        source = self.source
        with source._lock:
            if (source._user_active.is_set() or getattr(source, '_benchmark_active', False)
                    or source._shutdown_event.is_set() or source.dream_manager.is_dreaming):
                raise RuntimeError('Attendi che ALLMA sia libera prima della prova')
            source._benchmark_active = True
            source._user_active.set()
        rows, reason, actual = [], 'completed', None
        try:
            source._ensure_mobile_llm()
            engine = source._llm
            if engine is None or engine.llm is None:
                raise RuntimeError('Carica un modello prima della prova di contesto')
            if progress_callback:
                progress_callback(0, 3, 'Confronto della storia conservata, senza generazione')
            with engine.inference_lock:
                binding = engine.binding
                tokenize = lambda data: engine.llm.tokenize(data, add_bos=False, special=True)
                actual = engine.n_ctx
                compare_fit(binding, tokenize, self.cancel_event, rows=rows, progress_callback=progress_callback)
        except GenerationCancelled:
            reason = 'cancelled'
        except Exception:
            reason = 'error'
            raise
        finally:
            source._benchmark_active = False
            source._user_active.clear()
            summary = {'scope': 'native-tokenizer prompt packing; synthetic dialogue; no inference',
                       'stop_reason': reason, 'complete': len(rows) == 3,
                       'production_context': actual, 'production_context_changed': False,
                       'semantic_accuracy': None, 'inference_latency_ms': None, 'ram_comparison': None,
                       'rows': rows}
            self.manifest = {'cancelled': reason != 'completed', 'summary': summary}
            path = Path(self.report_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.with_suffix('.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            report = '# Confronto di contesto: storia conservata\n\n'
            report += 'Stesso tokenizer e template nativo, solo dialogo sintetico. Nessuna generazione o modifica al contesto della chat. Non misura correttezza, attesa del modello o RAM.\n\n'
            for row in rows:
                report += f"- {row['context_tokens']} token: {row['prompt_tokens']} occupati; {row['history_pairs_removed']} coppie rimosse; note presenti: {row['notes_retained']}.\n"
            path.write_text(report)
            print('ALLMA_CONTEXT_FIT_REPORT ' + str(path.with_suffix('.json')), flush=True)
            print('ALLMA_CONTEXT_FIT_SUMMARY ' + json.dumps(summary, ensure_ascii=False), flush=True)

    def close(self):
        self.cancel_event.set()
