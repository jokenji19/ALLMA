"""ALLMA diagnostic runs: isolated state, explicit checks, no hidden retries."""
import hashlib
import math
import json
import os
from pathlib import Path
import platform
import re
import statistics
import tempfile
import threading
import time
import uuid
from datetime import datetime

from allma_model.utils.generation_control import GenerationCancelled


def evaluate_response(question, content, metadata, valid=True):
    checks = {}
    rules = question.get('auto_checks', {})
    if 'exact_answer' in rules:
        answer = content.strip().casefold().rstrip('.!?')
        checks['exact_answer'] = answer == rules['exact_answer'].casefold()
    if 'json_answer' in rules:
        try:
            answer = json.loads(content)
            expected = rules['json_answer']
            # Python considers True == 1; JSON checks must distinguish types.
            checks['json_answer'] = (isinstance(answer, dict) and answer.keys() == expected.keys()
                and all(type(answer[k]) is type(v) and answer[k] == v for k, v in expected.items()))
        except (TypeError, ValueError):
            checks['json_answer'] = False
    if 'emotion_families' in rules:
        state = metadata.get('emotion_analysis', {})
        labels = {state.get('primary_emotion'), *state.get('secondary_emotions', {})} - {'neutral', None}
        checks['emotion_families'] = labels == set(rules['emotion_families']) if state else None
    return {'automatic_checks': checks, 'pipeline_valid': bool(valid),
            'automatic_status': 'failed' if not valid or False in checks.values() else
                                'passed' if checks and all(v is True for v in checks.values()) else 'not_measured',
            'human_review_required': bool(question.get('rubric')) or not rules,
            'rubric': question.get('rubric', []), 'human_score': None}


class CognitiveBenchmark:
    _run_lock = threading.Lock()

    def __init__(self, db_path=None, profile='quick', seed=20261012):
        if profile not in ('quick', 'historical', 'extended'):
            raise ValueError('Unknown benchmark profile')
        self.db_path = str(db_path or Path(__file__).parent/'benchmarks/questions_db.json')
        self.profile, self.seed = profile, seed
        self.results, self.brain = [], None
        self.cancel_event = threading.Event()
        self._temporary = None
        self._owned = False
        self._source_brain = None
        self.session_id = uuid.uuid4().hex
        self.manifest = {}
        reports = Path(__file__).parent/'benchmarks/reports'
        reports.mkdir(parents=True, exist_ok=True)
        self.report_path = str(reports/f'report_{self.session_id}.md')

    def setup_brain(self, existing_brain=None):
        from allma_model.core.allma_core import ALLMACore
        if existing_brain is not None:
            if existing_brain._user_active.is_set():
                raise RuntimeError('Attendi che la risposta corrente sia terminata')
            reports = Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'
            reports.mkdir(parents=True, exist_ok=True)
            self.report_path = str(reports/Path(self.report_path).name)
            existing_brain._ensure_mobile_llm()
        self._temporary = tempfile.TemporaryDirectory(prefix='allma-benchmark-')
        self._owned = True
        self._source_brain = existing_brain
        self.brain = ALLMACore(mobile_mode=True, db_path=str(Path(self._temporary.name)/'benchmark.db'),
                               models_dir=getattr(existing_brain, 'models_dir', None))
        if existing_brain is not None:
            # Share only the native model, not personality/history/learning stores.
            self.brain._llm = getattr(existing_brain, '_llm', None)
            self.brain._llm_ready = self.brain._llm is not None
            self.brain.reasoning_engine.llm = self.brain._llm
            self.brain.dream_manager.llm_wrapper = self.brain._llm
            self.brain.dream_manager.tot.llm = self.brain._llm
        self.brain.set_dream_mode(False, persist=False)

    def close(self):
        if self._owned and self.brain is not None:
            self.brain.close()
            self.brain = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def load_questions(self):
        data = json.loads(Path(self.db_path).read_text(encoding='utf-8'))
        return [q for q in data.get('tests', []) if self.profile in q.get('profiles', ['quick'])]

    def _conditions(self):
        try:
            state = self.brain.system_monitor.get_metabolic_state()
            result = {}
            for key in ('battery_temp_celsius', 'battery_level', 'is_charging'):
                value = getattr(state, key, None)
                if key == 'battery_level':
                    energy = getattr(state, 'energy_level', None)
                    value = energy*100 if type(energy) in (int,float) and 0 <= energy <= 1 else None
                result[key] = value if type(value) in (bool, int, float) and math.isfinite(value) else None
            return result
        except Exception:
            return {'battery_temp_celsius': None, 'battery_level': None, 'is_charging': None}

    def run_tests(self, progress_callback=None):
        self.results = []
        self.session_id = uuid.uuid4().hex
        questions = self.load_questions()
        source = Path(self.db_path)
        self.manifest = {'version': 3, 'session': self.session_id, 'profile': self.profile,
            'started_at': datetime.now().astimezone().isoformat(), 'seed_base': self.seed,
            'state_isolated': self._owned, 'model_already_loaded': self._source_brain is not None,
            'recall_disabled_for_cognitive_cases': True, 'platform': platform.platform(),
            'dataset_sha256': hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None,
            'case_order': [q['id'] for q in questions], 'conditions_start': self._conditions(),
            'cancelled': False, 'semantic_accuracy': None}
        model_path = getattr(getattr(self.brain, '_llm', None), 'model_path', None)
        if isinstance(model_path, (str, os.PathLike)):
            model = Path(model_path)
            self.manifest['model'] = {'name': model.name, 'size_bytes': model.stat().st_size if model.exists() else None}
        main = Path(__file__).parent/'main.py'
        self.manifest['embedded_source_sha256'] = hashlib.sha256(main.read_bytes()).hexdigest() if main.exists() else None
        self.manifest['source_sha256'] = {
            name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
            for name in ('benchmark_iq.py', 'allma_model/core/allma_core.py',
                         'allma_model/emotional_system/emotion_analysis.py')
            if (Path(__file__).parent/name).exists()}
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError('Un benchmark è già in esecuzione')
        if self._source_brain is not None:
            self._source_brain._user_active.set()  # Yield background work during measurement.
            self._source_brain._benchmark_active = True
        try:
            for idx, question in enumerate(questions):
                if self.cancel_event.is_set():
                    self.manifest['cancelled'] = True
                    break
                if progress_callback:
                    progress_callback(idx+1, len(questions), f"{question['category']} ({question['id']})")
                started = time.perf_counter()
                steps = []
                before = self._conditions()
                # Unique user per case, shared conversation only within a workflow.
                user = f'BENCHMARK_{self.session_id}_{question["id"]}'
                for step_idx, message in enumerate(question.get('messages') or [question['question']]):
                    if self.cancel_event.is_set():
                        self.manifest['cancelled'] = True
                        break
                    tick = time.perf_counter()
                    try:
                        response = self.brain.process_message(user_id=user, conversation_id=user, message=message,
                            context={'disable_answer_recall': True, 'benchmark_seed': self.seed+idx*100+step_idx},
                            cancel_event=self.cancel_event)
                        steps.append({'input': message, 'response': response.content,
                                      'duration': time.perf_counter()-tick,
                                      'metadata': getattr(response, 'metadata', None) or {},
                                      'valid': getattr(response, 'is_valid', True)})
                    except GenerationCancelled:
                        self.manifest['cancelled'] = True
                        break
                    except Exception as error:
                        steps.append({'input': message, 'response': f'ERROR: {error}',
                                      'duration': time.perf_counter()-tick, 'metadata': {}, 'valid': False})
                        break
                duration = time.perf_counter()-started
                final = steps[-1] if steps else {'response':'Test interrotto', 'metadata':{}, 'valid':False}
                generation = final['metadata'].get('generation', {})
                counts = [s['metadata'].get('generation', {}).get('completion_tokens') for s in steps]
                tokens = sum(counts) if counts and all(type(n) is int for n in counts) else None
                content = final['response']
                from allma_model.utils.repetition_guard import repetition_start
                looped = repetition_start(content) is not None
                valid = all(s['valid'] for s in steps) and final['valid'] and len(steps) == len(question.get('messages') or [question['question']]) and not self.manifest['cancelled']
                self.results.append({'id': question['id'], 'category': question['category'], 'question': question['question'],
                    'response': content, 'thought': 'Non raccolto; non indica assenza di ragionamento.',
                    'duration': duration, 'completion_tokens': tokens, 'tok_s': tokens/duration if tokens is not None and duration else None,
                    'max_new_tokens': generation.get('max_tokens'), 'stop_reason': generation.get('finish_reason','not_measured'),
                    'generation': generation, 'status': generation.get('status','not_measured'),
                    'anti_loop_triggered': looped, 'anti_loop_reason': 'lexical_loop' if looped else None,
                    'anti_loop_retry': False, 'steps': steps, 'conditions_before': before, 'conditions_after': self._conditions(),
                    'evaluation': evaluate_response(question, content, final['metadata'], valid)})
                if self.manifest['cancelled']:
                    break
                # Cooperative short pause; this is not a controlled cooldown.
                self.cancel_event.wait(1.)
        finally:
            self.manifest['finished_at'] = datetime.now().astimezone().isoformat()
            self.manifest['conditions_end'] = self._conditions()
            try:
                self._generate_report()
            finally:
                if self._source_brain is not None:
                    self._source_brain._benchmark_active = False
                    self._source_brain._user_active.clear()
                self._run_lock.release()

    def _generate_report(self):
        durations = [r['duration'] for r in self.results]
        lines = ['# ALLMA — Diagnostica di qualità e prestazioni', '',
            f"Profilo: {self.profile}; casi completati: {len(self.results)}; interrotto: {self.manifest.get('cancelled', False)}.",
            f"Una richiesta per passo, senza retry. Stato isolato: {self.manifest.get('state_isolated', False)}; il modello può essere già caldo. Le verifiche automatiche coprono solo i criteri dichiarati. Qualità semantica da valutare con la rubrica; nessun punteggio di intelligenza.", '',
            '| ID | Tempo (s) | Token | Tok/s end-to-end | Stop | Verifiche automatiche |',
            '|---|---:|---:|---:|---|---|']
        for r in self.results:
            lines.append(f"| {r['id']} | {r['duration']:.2f} | {r['completion_tokens']} | {r['tok_s']} | {r['stop_reason']} | {r['evaluation']['automatic_status']} |")
        if durations:
            lines += ['', f'Media: {statistics.mean(durations):.2f} s; mediana: {statistics.median(durations):.2f} s.']
        lines += ['', '## Condizioni e provenienza', '```json', json.dumps(self.manifest,ensure_ascii=False,indent=2), '```',
                  '', 'Rubrica: assegnare 0 = non soddisfatto, 1 = parziale, 2 = soddisfatto per ciascun criterio. Lasciare non valutato senza un giudizio sul testo. I casi con più passi sono confrontabili con lo stesso protocollo, non con singole richieste.', '']
        for r in self.results:
            lines += [f"## {r['id']} — {r['question']}", r['response'], '',
                      'Criteri: '+ '; '.join(r['evaluation']['rubric']),
                      'Verifiche: '+json.dumps(r['evaluation'],ensure_ascii=False),
                      'Metadati: '+json.dumps(r['generation'],ensure_ascii=False)]
            for step in r['steps']:
                lines += [f"Passo ({step['duration']:.2f}s): {step['input']}", step['response']]
        Path(self.report_path).write_text('\n'.join(lines),encoding='utf-8')
        # Preserve the old results-list JSON contract; provenance is separate.
        Path(self.report_path).with_suffix('.json').write_text(json.dumps(self.results,ensure_ascii=False,indent=2))
        Path(self.report_path).with_suffix('.manifest.json').write_text(json.dumps(self.manifest,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    benchmark = CognitiveBenchmark()
    try:
        benchmark.setup_brain()
        benchmark.run_tests()
    finally:
        benchmark.close()
