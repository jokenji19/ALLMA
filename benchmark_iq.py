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


def evaluate_response(question, content, metadata, valid=True, steps=None):
    checks = {}
    rules = question.get('auto_checks', {})
    if rules.get('no_model_calls') is True:
        checks['no_model_calls'] = bool(steps) and all(
            step.get('metadata', {}).get('generation', {}).get('llm_used') is False for step in steps)
    if 'personality_preferences' in rules:
        checks['personality_preferences'] = metadata.get('personality_expression',{}).get('preferences') == rules['personality_preferences']
    if 'personality_values' in rules:
        checks['personality_values'] = metadata.get('personality_expression',{}).get('values') == rules['personality_values']
    if rules.get('personality_instruction_received') is True:
        checks['personality_instruction_received'] = metadata.get('personality_expression',{}).get('instruction_received') is True
    if rules.get('personality_reload') is True:
        checks['personality_reload'] = metadata.get('personality_reload_verified') is True
    if rules.get('generation_completed') is True:
        generation = metadata.get('generation',{})
        checks['generation_completed'] = (generation.get('status') == 'completed'
            and generation.get('finish_reason') not in (None,'length','max_tokens'))
    if rules.get('personality_comparison') is True:
        comparison=metadata.get('personality_comparison',{})
        measured=comparison.get('checks',{})
        for key in ('workflow_complete','three_native_assessments','three_complete_training_answers',
                    'outcome_policy_acquired','same_probe_controls','both_probes_complete','outcomes_reload'):
            checks[key]=measured.get(key) is True
    if 'personal_context_received' in rules:
        checks['personal_context_received'] = metadata.get('decision', {}).get('personal_context_in_prompt') is rules['personal_context_received']
    if rules.get('personal_context_policy_applied') is True:
        checks['personal_context_policy_applied'] = metadata.get('decision', {}).get('personal_context_policy_applied') is True
    if 'decision_source' in rules:
        checks['decision_source'] = metadata.get('decision', {}).get('source') == rules['decision_source']
    if 'personal_field_statuses' in rules:
        checks['personal_field_statuses'] = metadata.get('decision', {}).get('personal_context_status') == rules['personal_field_statuses']
    if 'step_exact_answers' in rules:
        checks['step_exact_answers'] = [step.get('response', '').strip() for step in (steps or [])] == rules['step_exact_answers']
    if 'step_sources' in rules:
        checks['step_sources'] = [step.get('metadata', {}).get('source') for step in (steps or [])] == rules['step_sources']
    if 'growth_stages' in rules:
        checks['growth_stages'] = [step.get('metadata', {}).get('emotional_growth', {}).get('status') for step in (steps or [])] == rules['growth_stages']
        checks['learned_emotion_detected'] = bool(steps) and all(
            step.get('metadata', {}).get('emotion_analysis', {}).get('primary_emotion') == 'sadness' for step in steps[1:3]) and len(steps) >= 3
        checks['own_response_distinct'] = bool(steps) and len(steps) >= 3 and steps[2].get('metadata', {}).get('emotional_growth', {}).get('own_response', {}).get('mode') == 'care'
        checks['restart_retains_growth'] = metadata.get('coalescence_restart_verified')
    if 'literal_exact_answer' in rules:
        checks['literal_exact_answer'] = content.strip() == rules['literal_exact_answer']
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
    if rules.get('archive_reload_verified') is True:
        checks['archive_reload_verified'] = metadata.get('archive_reload_verified') is True
    if 'literal_evidence' in rules:
        checks['literal_evidence'] = rules['literal_evidence'] in metadata.get('memory_recall', {}).get('evidence_sha256', [])
    if 'recall_source' in rules:
        checks['recall_source'] = metadata.get('source') == rules['recall_source']
    if 'memory_fixture_in_prompt' in rules:
        evidence = metadata.get('decision', {}).get('memory_evidence', [])
        expected = rules['memory_fixture_in_prompt']
        checks['memory_fixture_in_prompt'] = any(
            item.get('sha256') == expected and item.get('included_in_prompt') is True
            and item.get('provenance') == 'previous' for item in evidence)
    if rules.get('empty_memory') is True:
        action = metadata.get('decision', {}).get('action_cycle', {})
        checks['empty_memory'] = action.get('status') == 'observed' and action.get('record_count') == 0
    if 'emotion_families' in rules:
        state = metadata.get('emotion_analysis', {})
        labels = {state.get('primary_emotion'), *state.get('secondary_emotions', {})} - {'neutral', None}
        checks['emotion_families'] = labels == set(rules['emotion_families']) if state else None
    return {'automatic_checks': checks, 'pipeline_valid': bool(valid),
            'answer_source': metadata.get('source', 'model_generated'),
            # Passing output guards is not factual verification; deterministic
            # paths have no model candidate to grade.
            'model_answer_valid': metadata.get('recovery', {}).get('model_answer_valid',
                None if metadata.get('generation', {}).get('llm_used') is False else bool(valid)),
            'recovery_used': bool(metadata.get('recovery')) or any(step.get('metadata', {}).get('recovery') for step in (steps or [])),
            'recovered_steps': [{'step': index + 1, 'model_answer_valid': False,
                                 'reason': step['metadata']['recovery']['reason']}
                                for index, step in enumerate(steps or []) if step.get('metadata', {}).get('recovery')],
            'automatic_status': 'failed' if not valid or False in checks.values() else
                                'passed' if checks and all(v is True for v in checks.values()) else 'not_measured',
            'human_review_required': bool(question.get('rubric')) or not rules,
            'rubric': question.get('rubric', []), 'human_score': None}


class CognitiveBenchmark:
    _run_lock = threading.Lock()

    def __init__(self, db_path=None, profile='quick', seed=20261012):
        if profile not in ('quick', 'historical', 'extended', 'comparison', 'reasoning', 'support', 'support_roles', 'support_reasoning', 'support_natural', 'dialogue', 'growth', 'memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback'):
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
            if getattr(existing_brain, 'decision_runtime', None) is not None:
                self.brain.decision_runtime.close()
                self.brain.decision_runtime = existing_brain.decision_runtime
                self.brain._owns_decision_runtime = False
        self.brain.set_dream_mode(False, persist=False)
        # Keep historical model-use comparisons unchanged by host literal recall.
        self.brain._disable_literal_memory_recall = self.profile in ('memory', 'memory_contract')
        # Only isolated synthetic benchmark cores capture answer candidates.
        self.brain._capture_synthetic_candidates = self.profile in ('support', 'quick', 'growth', 'memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback')

    def close(self):
        if self._owned and self.brain is not None:
            self.brain._synthetic_candidate = None
            self.brain.close()
            self.brain = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def load_questions(self):
        data = json.loads(Path(self.db_path).read_text(encoding='utf-8'))
        if self.profile == 'greeting_closure':
            case = next(q for q in data.get('tests', []) if q['id'] == 'MD3')
            return [dict(case, id=case['id']+'_'+mode, pair_id=case['id'],
                         execution_mode='pipeline', reasoning_mode=mode,
                         pair_seed=self.seed+case['seed_offset'])
                    for mode in ('bounded', 'natural')]
        if self.profile == 'support_natural':
            case = next(q for q in data.get('tests', []) if q['id']=='S4')
            return [dict(case,id=case['id']+'_'+mode,pair_id=case['id'],execution_mode='model',
                         pair_seed=self.seed+case['seed_offset'],thought_budget=128,total_budget=384,
                         reasoning_mode=mode) for mode in ('bounded','natural')]
        if self.profile == 'support_reasoning':
            case = next(q for q in data.get('tests', []) if q['id']=='S4')
            return [dict(case,id=case['id']+f'_r{budget}',pair_id=case['id'],execution_mode='model',
                         pair_seed=self.seed+case['seed_offset'],thought_budget=budget,total_budget=budget+144)
                    for budget in (48,128)]
        if self.profile == 'support_roles':
            cases = [q for q in data.get('tests', []) if q['id'] in ('S4','T2')]
            return [dict(case,id=case['id']+'_'+arm,pair_id=case['id'],execution_mode=arm,
                         pair_seed=self.seed+case['seed_offset'],thought_budget=48,total_budget=192)
                    for index,case in enumerate(cases)
                    for arm in (('model','role_map') if index%2==0 else ('role_map','model'))]
        if self.profile == 'memory_recall':
            cases = [q for q in data.get('tests', []) if q['id'] in ('MF1','MF2','MF3','MF4')]
            values = ('NUBE-271', 'vEnTo_004', '000015')
            prepared = []
            for index, original in enumerate(cases):
                case = dict(original, id=original['id']+'_host')
                expected = values[index] if index < 3 else 'NON_DISPONIBILE'
                checks = {'literal_exact_answer':expected, 'no_model_calls':True}
                if index < 3:
                    fixture = (original['memory_fixture'] if index == 0 else
                               'Il codice di prova è '+expected+'.')
                    case['memory_fixture'] = fixture
                    checks.update(recall_source='literal_user_memory',
                        literal_evidence=hashlib.sha256(fixture.encode()).hexdigest())
                else:
                    checks.update(empty_memory=True, recall_source='literal_memory_absent')
                case.update(auto_checks=checks,
                    rubric=['Tre valori distinti, con maiuscole e minuscole e zeri iniziali; assenza dopo una lettura verificata.',
                            'Nessuna generazione: questo profilo non misura il ragionamento del modello.'])
                prepared.append(case)
            return prepared
        if self.profile == 'memory_contract':
            cases = [q for q in data.get('tests', []) if q['id'] in ('MF1','MF4')]
            return [dict(case, id=case['id']+'_'+variant, pair_id=case['id'],
                         memory_variant=variant, pair_seed=self.seed+case['seed_offset'])
                    for index, case in enumerate(cases)
                    for variant in (('baseline','attributed') if index == 0 else ('attributed','baseline'))]
        cases = [q for q in data.get('tests', []) if self.profile in q.get('profiles', ['quick'])]
        if self.profile not in ('comparison', 'reasoning'):
            return cases
        paired = []
        for idx, case in enumerate(cases):
            budgets = (96, 128) if self.profile == 'reasoning' else (48,)
            for budget in budgets:
                order = ('pipeline', 'model') if (idx + (budget == 128)) % 2 == 0 else ('model', 'pipeline')
                pair_id = case['id'] + (f'_r{budget}' if self.profile == 'reasoning' else '')
                for arm in order:
                    paired.append(dict(case, id=pair_id+'_'+arm, pair_id=pair_id,
                                       execution_mode=arm, pair_seed=self.seed+case.get('seed_offset',idx*100),
                                       thought_budget=budget, total_budget=budget+144))
        return paired

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
            'runtime_cases_sha256':hashlib.sha256(json.dumps(questions,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            'case_order': [q['id'] for q in questions], 'conditions_start': self._conditions(),
            'cancelled': False, 'semantic_accuracy': None}
        if self.profile == 'support_roles':
            self.manifest.update(experiment='native_minimal_vs_speaker_role_map',reserved_answer_budget=144,
                thought_budget=48,order_counterbalanced=True,cold_cache_controlled=False,
                causal_attribution='not_established',personal_memory_used=False)
        if self.profile == 'support_reasoning':
            self.manifest.update(experiment='native_support_reasoning_48_vs_128',reserved_answer_budget=144,
                thought_budgets=[48,128],order_counterbalanced=False,cold_cache_controlled=False,
                causal_attribution='not_established',personal_memory_used=False,
                scope='One known emotional case; native minimal prompt, no CognitivePipeline')
        if self.profile == 'greeting_closure':
            self.manifest.update(experiment='pipeline_greeting_bounded_vs_natural',
                total_budget=192, bounded_partition={'reasoning':48, 'answer':144},
                natural_partition='shared; no reserved answer',
                order_counterbalanced=False, cold_cache_controlled=False,
                causal_attribution='not_established', human_review_required=True)
        if self.profile == 'support_natural':
            self.manifest.update(experiment='native_bounded_vs_natural_closure',total_budget=384,
                bounded_partition={'reasoning':128,'answer':256},natural_partition='shared; no reserved answer',
                order_counterbalanced=False,cold_cache_controlled=False,causal_attribution='not_established')
        if self.profile in ('comparison', 'reasoning'):
            self.manifest.update(comparison_protocol='paired_v1',
                comparison_max_tokens=192 if self.profile == 'comparison' else [240,272],
                comparison_thought_budget=48 if self.profile == 'comparison' else [96,128],
                reserved_answer_budget=144,
                order_counterbalanced=True, cold_cache_controlled=False,
                baseline='V0.9.0.0 application with diagnostic instrumentation',
                isolated_model_scope='Native wrapper, bounded reasoning and lexical repetition guard; no ALLMA memory, emotion context or final response guards',
                battery_consumption_measured=False)

        model_path = getattr(getattr(self.brain, '_llm', None), 'model_path', None)
        if isinstance(model_path, (str, os.PathLike)):
            model = Path(model_path)
            self.manifest['model'] = {'name': model.name, 'size_bytes': model.stat().st_size if model.exists() else None}
        main = Path(__file__).parent/'main.py'
        self.manifest['embedded_source_sha256'] = hashlib.sha256(main.read_bytes()).hexdigest() if main.exists() else None
        self.manifest['source_sha256'] = {
            name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
            for name in ('benchmark_iq.py', 'allma_model/core/allma_core.py',
                         'allma_model/emotional_system/emotion_analysis.py',
                         'allma_model/core/personality_development.py', 'allma_model/core/personality_adapter.py',
                         'allma_model/core/personality_coalescence.py', 'allma_model/core/personality_outcomes.py',
                         'allma_model/utils/model_comparison.py', 'allma_model/utils/output_contract.py',
                         'allma_model/utils/support_roles.py', 'allma_model/utils/sampling_policy.py', 'allma_model/core/autobiographical_identity.py',
                         'allma_model/utils/memory_prompt.py', 'allma_model/utils/personal_facts.py', 'allma_model/utils/dialogue_task.py',
                         'allma_model/utils/memory_evidence.py', 'allma_model/utils/literal_recall.py',
                         'allma_model/agency_system/operational_actions.py')
            if (Path(__file__).parent/name).exists()}
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError('Un benchmark è già in esecuzione')
        if self._source_brain is not None:
            self._source_brain._user_active.set()  # Yield background work during measurement.
            self._source_brain._benchmark_active = True
        try:
            if self._owned:
                self.brain._disable_literal_memory_recall = self.profile in ('memory', 'memory_contract')
            for idx, question in enumerate(questions):
                if self.cancel_event.is_set():
                    self.manifest['cancelled'] = True
                    break
                if self.profile in ('comparison', 'reasoning', 'support', 'support_roles', 'support_reasoning', 'support_natural', 'memory'):
                    temperature = self._conditions().get('battery_temp_celsius')
                    if type(temperature) in (int, float) and temperature >= 41.5:
                        self.manifest['stop_reason'] = 'thermal_pause'
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
                    if self.profile=='personality_feedback' and step_idx not in (2,4,6):
                        temperature=self._conditions().get('battery_temp_celsius')
                        if type(temperature) in (int,float) and temperature>=41.5:
                            self.manifest['stop_reason']='thermal_pause'
                            break
                    tick = time.perf_counter()
                    try:
                        if self.profile in ('memory','memory_contract','memory_recall','memory_lifecycle','memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback') and not self._owned:
                            raise RuntimeError('Memory benchmark steps require an isolated core')
                        if self.profile == 'memory_contract':
                            if not self._owned:
                                raise RuntimeError('Prompt comparisons require an isolated benchmark core')
                            self.brain._memory_prompt_variant = question['memory_variant']
                        if step_idx == 0 and 'memory_fixture' in question:
                            if self.profile not in ('memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback') or not self._owned:
                                raise RuntimeError('Memory fixtures require an isolated benchmark core')
                            fixture = question['memory_fixture']
                            fixtures = ([fixture] if isinstance(fixture, str) else fixture
                                        if self.profile in ('memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback') and isinstance(fixture, list) else None)
                            if (not fixtures or not 1 <= len(fixtures) <= 8
                                    or any(not isinstance(text, str) or not text.strip() or len(text) > 240 for text in fixtures)):
                                raise ValueError('Invalid synthetic memory fixture')
                            for text in fixtures:
                                self.brain.conversational_memory.store_message(user+':earlier', text,
                                    {'source':'synthetic_benchmark_fixture'}, 'user', user)
                        seed = question.get('pair_seed', self.seed+question.get('seed_offset',idx*100))+step_idx
                        conversation=user
                        if self.profile=='personality_feedback':
                            # Each independent training question has only its
                            # own follow-up assessment in history.
                            conversation=user+':training'+str((step_idx-1)//2)
                            # Identical held-out probe and seed in two fresh histories.
                            if step_idx in (0,7):
                                seed=self.seed
                                conversation=user+(':before' if step_idx==0 else ':after')
                            if step_idx in (2,4,6):
                                from allma_model.core.personality_outcomes import feedback_signal,feedback_target
                                history=self.brain.conversational_memory.get_conversation_history(conversation)
                                if not history or feedback_target(history[-1],user,feedback_signal(message)) is None:
                                    self.manifest['stop_reason']='unassessable_training_response'
                                    raise RuntimeError('Il riscontro sintetico non è applicabile alla risposta ricevuta; prova fermata senza altra inferenza')
                        if question.get('execution_mode') in ('model','role_map'):
                            options = {'support_strategy':'role_map'} if question['execution_mode']=='role_map' else {}
                            if self.profile == 'support_natural':
                                options['reasoning_mode']=question['reasoning_mode']
                            probe = self.brain.probe_model(message, max_tokens=question.get('total_budget',192), thought_budget=question.get('thought_budget',48),
                                seed=seed, cancel_event=self.cancel_event, **options)
                            content = probe['answer']
                            metadata = {'source': probe['source'], 'generation': probe['generation']}
                            valid_step = bool(content.strip()) and not content.startswith('Error')
                            if self.profile in ('support_roles','support_reasoning','support_natural'):
                                from allma_model.utils.output_contract import borrowed_user_experience, requested_sentence_count, valid_sentence_count
                                metadata['diagnostic_checks'] = {'subject_mismatch':borrowed_user_experience(content,message),
                                    'sentence_format':valid_sentence_count(content,requested_sentence_count(message))}
                                valid_step = valid_step and not metadata['diagnostic_checks']['subject_mismatch'] and metadata['diagnostic_checks']['sentence_format']
                        else:
                            context = {'disable_answer_recall': True, 'benchmark_seed': seed}
                            self.brain._synthetic_candidate = None
                            if self.profile in ('comparison', 'reasoning', 'support', 'memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback'):
                                context.update(benchmark_max_tokens=question.get('total_budget',192),
                                               benchmark_thought_budget=question.get('thought_budget',48),
                                               benchmark_reasoning_sweep=self.profile == 'reasoning')
                            if self.profile == 'greeting_closure':
                                context['benchmark_reasoning_mode'] = question['reasoning_mode']
                            response = self.brain.process_message(user_id=user, conversation_id=conversation, message=message,
                                context=context, cancel_event=self.cancel_event)
                            content, metadata = response.content, getattr(response, 'metadata', None) or {}
                            valid_step = getattr(response, 'is_valid', True)
                        if question.get('personality_reload'):
                            if self.profile != 'personality' or not self._owned:
                                raise RuntimeError('Personality reload requires an isolated core')
                            from allma_model.core.personality_coalescence import CoalescenceProcessor
                            restored = CoalescenceProcessor(self.brain.db_path)
                            metadata = dict(metadata)
                            metadata['personality_reload_verified'] = (restored.expression_view(user)
                                == self.brain.coalescence_processor.expression_view(user))
                        if question.get('archive_reload'):
                            if self.profile not in ('memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback') or not self._owned:
                                raise RuntimeError('Archive reload requires an isolated lifecycle benchmark')
                            from allma_model.memory_system.conversational_memory import ConversationalMemory
                            from allma_model.core.autobiographical_identity import user_events, grounded_reply
                            from allma_model.utils.literal_recall import literal_code_reply
                            self.brain.conversational_memory.save_memory()
                            restored = ConversationalMemory(storage_dir=self.brain.conversational_memory.storage_dir)
                            replayed = (grounded_reply(message, restored, user) if self.profile == 'memory_personal'
                                        else literal_code_reply(message, user_events(restored, user)))
                            metadata = dict(metadata)
                            metadata['archive_reload_verified'] = bool(replayed and replayed[0] == content
                                and replayed[1] == metadata.get('source'))
                            metadata['archive_reload_scope'] = 'isolated_data_reload_not_android_process_restart'
                        steps.append({'input': message, 'response': content,
                                      'duration': time.perf_counter()-tick,
                                      'metadata': metadata, 'valid': valid_step})
                        candidate = getattr(self.brain, '_synthetic_candidate', None)
                        if isinstance(candidate, dict):
                            steps[-1]['candidate_diagnostic'] = candidate
                        self.brain._synthetic_candidate = None
                    except GenerationCancelled:
                        self.manifest['cancelled'] = True
                        break
                    except Exception as error:
                        steps.append({'input': message, 'response': f'ERROR: {error}',
                                      'duration': time.perf_counter()-tick, 'metadata': {}, 'valid': False})
                        break
                duration = time.perf_counter()-started
                final = steps[-1] if steps else {'response':'Test interrotto', 'metadata':{}, 'valid':False}
                if self.profile == 'growth' and steps and self._owned:
                    from allma_model.core.personality_coalescence import CoalescenceProcessor
                    before_restart = self.brain.coalescence_processor.emotion_growth_view(user)
                    restored = CoalescenceProcessor(self.brain.db_path)
                    final['metadata']['coalescence_restart_verified'] = (restored.emotion_growth_view(user) == before_restart
                        and bool(before_restart['associations']))
                if self.profile=='personality_feedback' and self._owned:
                    from allma_model.core.personality_coalescence import CoalescenceProcessor
                    from allma_model.core.personality_outcomes import compare_protocol
                    expression=self.brain.coalescence_processor.expression_view(user)
                    restored=CoalescenceProcessor(self.brain.db_path).expression_view(user)
                    final['metadata']['personality_comparison']=compare_protocol(steps,expression,restored)
                generation = final['metadata'].get('generation', {})
                counts = [s['metadata'].get('generation', {}).get('completion_tokens') for s in steps]
                tokens = sum(counts) if counts and all(type(n) is int for n in counts) else None
                content = final['response']
                from allma_model.utils.repetition_guard import repetition_start
                looped = repetition_start(content) is not None
                valid = all(s['valid'] for s in steps) and final['valid'] and len(steps) == len(question.get('messages') or [question['question']]) and not self.manifest['cancelled']
                self.results.append({'pair_id':question.get('pair_id'), 'execution_mode':question.get('execution_mode','pipeline'), 'memory_variant':question.get('memory_variant'), 'source':final['metadata'].get('source'), 'id': question['id'], 'category': question['category'], 'question': question['question'],
                    'response': content, 'thought': 'Non raccolto; non indica assenza di ragionamento.',
                    'duration': duration, 'completion_tokens': tokens, 'tok_s': tokens/duration if tokens is not None and duration else None,
                    'max_new_tokens': generation.get('max_tokens'), 'stop_reason': generation.get('finish_reason','not_measured'),
                    'generation': generation, 'status': generation.get('status','not_measured'),
                    'anti_loop_triggered': looped, 'anti_loop_reason': 'lexical_loop' if looped else None,
                    'anti_loop_retry': False, 'steps': steps, 'conditions_before': before, 'conditions_after': self._conditions(),
                    'evaluation': evaluate_response(question, content, final['metadata'], valid, steps=steps)})
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
        if self.profile == 'memory':
            positive = [r for r in self.results if r['id'] in ('MF1','MF2','MF3')]
            controls = ('max_tokens','temperature','top_p','repeat_penalty','reasoning_budget','answer_budget')
            self.manifest['memory_protocol'] = {
                'scope':'Three seeds with the same synthetic prior declaration, then a separate user without it.',
                'fixture_setup_in_duration':True,
                'positive_cases_complete':len(positive)==3,
                'generation_controls_match':len(positive)==3 and all(
                    positive[0]['generation'].get(key) is not None and all(
                        row['generation'].get(key)==positive[0]['generation'][key] for row in positive)
                    for key in controls),
                'general_reliability_established':False}
            lines += ['', 'Fedeltà ai ricordi: tre seed con lo stesso dato sintetico in una conversazione precedente; '
                      'un quarto utente di prova non possiede quel dato. Nessun retry: il valore del codice è fornito soltanto dal ricordo sintetico, non dalla domanda. '
                      'Il tempo include la preparazione del dato sintetico. '
                      'Il formato chiuso misura estrazione e assenza del dato, non la qualità generale del dialogo.']
        if self.profile=='personality_feedback':
            self.manifest['personality_outcome_protocol']={'probe_order':'before_training_after',
                'training':'Three spontaneous responses with synthetic specific assessments; no declared style preferences',
                'inferences_planned':5,'feedback_inferences_planned':0,'fresh_probe_histories':True,
                'cold_cache_controlled':False,'semantic_accuracy':None,'general_reliability_established':False}
            lines += ['', 'Riscontri: stessa domanda e seed prima e dopo tre esperienze sintetiche, con cronologie di prova nuove. '
                      'Nessuna preferenza di brevità viene dichiarata. Il confronto misura acquisizione e applicazione della strategia; '
                      'utilità e correttezza delle risposte richiedono valutazione umana. Cache e temperatura non sono controllate.']
            for row in self.results:
                comparison=row['steps'][-1]['metadata'].get('personality_comparison',{}) if row['steps'] else {}
                lines += ['', 'Confronto misurato: '+json.dumps(comparison,ensure_ascii=False)]
        if self.profile == 'personality':
            self.manifest['personality_protocol'] = {
                'scope':'Synthetic isolated users; birth, preferences, correction, revocation, reset, model context',
                'reload_scope':'Data reload, not Android process restart',
                'semantic_accuracy':None, 'general_reliability_established':False}
            lines += ['', 'Personalità: lo stato è separato da quello personale. Le verifiche controllano preferenze, '
                      'correzioni, revoche e istruzioni effettivamente ricevute; la naturalezza del testo richiede valutazione umana. '
                      'La ricarica riguarda i dati salvati, non il riavvio del processo Android.']
        if self.profile == 'memory_recall':
            self.manifest['literal_recall_protocol'] = {'llm_expected':False,
                'scope':'Three distinct literal codes and one verified absence; exact case and leading zeros required', 'general_reliability_established':False}
            lines += ['', 'Richiamo letterale ALLMA: dati espliciti e assenza verificata senza LLM; errori e casi ambigui restano nel percorso completo. '
                      'Questa prova non misura miglioramenti del modello o affidabilità generale. '
                      'I profili di confronto del modello mantengono disabilitato questo percorso.']
        if self.profile in ('memory_dialogue', 'greeting', 'greeting_closure'):
            self.manifest['personal_dialogue_protocol'] = {
                'scope':'Usable task context on isolated synthetic users; administrative states stay host-side',
                'focus_case':'MD3' if self.profile in ('greeting', 'greeting_closure') else None,
                'protocol_version':2,
                'automatic_checks':'Prompt context inclusion/omission, host policy and declared control statuses only',
                'semantic_accuracy':None, 'human_review_required':True}
            lines += ['', 'Dialogo e memoria: le verifiche automatiche controllano il contesto ricevuto dal modello, '
                      'non la correttezza semantica delle risposte. Valutare manualmente pertinenza e attribuzione.']
        if self.profile == 'memory_personal':
            self.manifest['personal_memory_protocol'] = {
                'scope':'Explicit names, favorites and color likes, synthetic isolated users',
                'llm_expected':False, 'archive_reload_scope':'Data reload, not Android process restart',
                'general_reliability_established':False}
            lines += ['', 'Memoria personale: dichiarazioni, correzioni, revoche e conflitti su utenti sintetici separati. '
                      'Apprezzare un colore non equivale a dichiararlo preferito. '
                      'Il controllo di ricarica riguarda l’archivio, non un riavvio del processo Android.']
        if self.profile == 'memory_lifecycle':
            self.manifest['memory_lifecycle_protocol'] = {
                'fixture_scope':'Prior synthetic declarations; no model-generated setup',
                'llm_expected':False, 'archive_reload_scope':'Data reload, not Android process restart',
                'general_reliability_established':False}
            lines += ['', 'Correzioni e revoche: sei cronologie preparate e un dialogo sintetico attraverso process_message. '
                      'La ricarica controlla i dati salvati, non il riavvio completo dell’app Android. '
                      'Nessuna percentuale di affidabilità generale.']
        if self.profile == 'memory_contract':
            controls = ('max_tokens','temperature','top_p','repeat_penalty','reasoning_budget','answer_budget','seed')
            pairs = []
            for pair_id in ('MF1','MF4'):
                rows = [r for r in self.results if r['pair_id'] == pair_id]
                pairs.append({'id':pair_id, 'complete':len(rows)==2,
                    'generation_controls_match':len(rows)==2 and all(
                        rows[0]['generation'].get(key) is not None
                        and rows[0]['generation'][key] == rows[1]['generation'].get(key)
                        for key in controls)})
            self.manifest['memory_contract_protocol'] = {
                'variants':['baseline','attributed'], 'same_input_seed_budget_requested_per_pair':True,
                'observed_pairs':pairs,
                'order':'positive baseline first; absence attributed first',
                'general_reliability_established':False,
                'latency_caveat':'Prompt length, cache warmth and thermal state may differ.'}
            lines += ['', 'Confronto istruzioni memoria: due coppie sintetiche (dato presente e assente), '
                      'stessi input, seed e budget per coppia. Nessun retry. '
                      'Il prompt differisce: il tempo non misura da solo un miglioramento delle prestazioni.']
        if self.profile in ('comparison', 'reasoning'):
            from allma_model.utils.model_comparison import summarize_pairs
            self.manifest['pairs'] = summarize_pairs(self.results)
            lines += ['', 'Confronto a coppie: stesso input e seed, ordine alternato. Il prompt, i controlli e la cache differiscono: non attribuire automaticamente ogni errore al modello. Nessuna misura diretta della batteria.',
                      'Arresto: '+self.manifest.get('stop_reason', 'completed'),
                      'Coppie: '+json.dumps(self.manifest['pairs'], ensure_ascii=False)]
        lines += ['', '## Condizioni e provenienza', '```json', json.dumps(self.manifest,ensure_ascii=False,indent=2), '```',
                  '', 'Rubrica: assegnare 0 = non soddisfatto, 1 = parziale, 2 = soddisfatto per ciascun criterio. Lasciare non valutato senza un giudizio sul testo. I casi con più passi sono confrontabili con lo stesso protocollo, non con singole richieste.', '']
        for r in self.results:
            lines += [f"## {r['id']} — {r['question']}", r['response'], '',
                      'Criteri: '+ '; '.join(r['evaluation']['rubric']),
                      'Verifiche: '+json.dumps(r['evaluation'],ensure_ascii=False),
                      'Metadati: '+json.dumps(r['generation'],ensure_ascii=False)]
            for step in r['steps']:
                if self.profile in ('memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback'):
                    lines += ['Recupero e provenienza: '+json.dumps(step['metadata'].get('decision',{}),ensure_ascii=False)]
                if step['metadata'].get('diagnostic_checks'):
                    lines += ['Controlli sul candidato nativo (non misura completa di qualità): '+
                              json.dumps(step['metadata']['diagnostic_checks'],ensure_ascii=False)]
                if isinstance(step.get('candidate_diagnostic'), dict):
                    lines += ['Candidato diagnostico sintetico (non risposta validata, non ragionamento):',
                              '```json', json.dumps(step['candidate_diagnostic'],ensure_ascii=False,indent=2), '```']
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
