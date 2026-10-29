"""Isolated dialogue checks, plus an opening and four actual-model turns.

Software assertions and human assessment of model answers are reported apart.
Rejected candidates are never copied from a personal conversation.
"""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as T
from unittest.mock import Mock
import hashlib
import json
import time
import uuid

from memory_recovery_battery import require, run_challenges
from allma_model.agency_system.plan_diagnostics import PlanDiagnosticRun
from .dialogue_recovery import dialogue_history, opening_recovery, unanswered_attempt
from .dialogue_continuity import DialogueContinuity
from .dialogue_output import project_answer
from .answer_stream import AnswerStream
from .generation_control import GenerationCancelled

CASES = []


def case(name, criterion):
    def wrap(fn):
        CASES.append(('dialogue_recovery', name, criterion, fn))
        return fn
    return wrap


@contextmanager
def fixture(path):
    from allma_model.core.allma_core import ALLMACore
    core = ALLMACore(mobile_mode=True, db_path=str(path / 'core.db'))
    core._ensure_mobile_llm = lambda: None
    core._llm = Mock()
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core.decision_runtime.route = Mock(return_value={'status': 'selected', 'choice': 'reason'})
    core.incremental_learner.learn_from_interaction = Mock()
    core.answer_recall.observe = Mock()
    user = 'BENCHMARK_DIALOGUE_FIXTURE'
    cid = core.start_conversation(user)
    try:
        yield core, user, cid
    finally:
        core.close()


def seed_failure(core, user, cid, reason='subject_mismatch'):
    core.conversational_memory.store_message(cid, 'Bene, ma ho un dubbio', {}, 'user', user)
    core.conversational_memory.store_message(cid, 'Avviso tecnico sintetico.',
        {'is_valid': False, 'generation': {'status': reason}}, 'assistant', user)


def withheld(path, status):
    with fixture(path) as (core, user, cid):
        seed_failure(core, user, cid, status)
        core._llm.generate.side_effect = AssertionError('No inference for resuming an opening')
        events = []
        reply = core.process_message(user, cid, 'Bene, ma ho un dubbio', stream_callback=events.append)
        require(reply.is_valid and reply.metadata['source'] == 'grounded_dialogue_recovery', 'No useful recovery')
        require(reply.metadata['generation']['llm_used'] is False, 'Recovery credited to model')
        require(core.conversational_memory.messages[-3].metadata['generation']['status'] == status, 'Guard reason lost')
        require('qual è il dubbio?' in reply.content and 'Riprova' not in reply.content, 'Lost opening')
        require(reply.content == ''.join(e['content'] for e in events if e['type'] == 'answer'), 'Stream diverged')
        require(not core._llm.generate.called, 'Unnecessary generation')
        require(not core.answer_recall.observe.called and not core.incremental_learner.learn_from_interaction.called, 'Recovery trained as knowledge')


@case('subject_recovery', 'An old attribution failure resumes as a clarification, without learning or retry')
def subject_recovery(path):
    withheld(path, 'subject_mismatch')


@case('repeated_checkin', 'An old repetition failure cannot trap a retried opening')
def repeated_checkin(path):
    withheld(path, 'dialogue_repetition')


@case('legacy_detour', 'An old error and its explanation do not trap a rephrased request')
def legacy_detour(path):
    with fixture(path) as (core, user, cid):
        seed_failure(core, user, cid)
        clarification = core.process_message(user, cid, 'Cosa intendi?')
        reply = core.process_message(user, cid, 'Ho un dubbio')
        require('qual è il dubbio?' in clarification.content and reply.is_valid, 'Intent not resumed')
        require(reply.metadata['generation']['llm_used'] is False and not core._llm.generate.called, 'Unnecessary inference')


@case('prompt_projection', 'Technical explanations stay in the archive but are absent from the next model prompt')
def prompt_projection(path):
    with fixture(path) as (core, user, cid):
        seed_failure(core, user, cid)
        notice = core.process_message(user, cid, 'Cosa intendi?')
        core._llm.generate.return_value = 'La Luna riflette la luce del Sole.'
        reply = core.process_message(user, cid, 'Perché la Luna è luminosa?')
        prompt = core._llm.generate.call_args.kwargs['prompt']
        require(reply.is_valid and notice.content not in prompt and 'Cosa intendi?' not in prompt, 'Notice contaminated prompt')
        require('Bene, ma ho un dubbio' in prompt, 'Unanswered request removed')
        require(notice.content in [m.content for m in core.conversational_memory.messages], 'Archive modified')


@case('restart', 'A fresh core can resume an old withheld opening from the existing scoped history')
def restart(path):
    with fixture(path) as (core, user, cid):
        seed_failure(core, user, cid)
    with fixture(path) as (core, _, _):
        reply = core.process_message(user, cid, 'Vorrei chiederti una cosa')
        require(reply.is_valid and reply.metadata['source'] == 'grounded_dialogue_recovery', 'Restart lost pending request')
        require(not core._llm.generate.called, 'Restart needed model')


@case('scope', 'A failure in a different user or chat never triggers local recovery')
def scope(path):
    with fixture(path) as (core, user, cid):
        seed_failure(core, user, cid)
        core._llm.generate.return_value = 'Dimmi pure, qual è la domanda?'
        for owner in (user, 'BENCHMARK_OTHER'):
            reply = core.process_message(owner, core.start_conversation(owner), 'Ho un dubbio')
            require(reply.metadata['source'] == 'dialogue_opening', 'Cross-scope pending state')


@case('substantive', 'An actual question cannot be answered by the neutral clarification recovery')
def substantive(path):
    require(opening_recovery('Ho un dubbio: perché cambia il clima?') is None, 'Substantive task intercepted')


@case('formats', 'Explicit formatting instructions remain with the actual task pipeline')
def formats(path):
    require(opening_recovery('Ho un dubbio. Rispondi solo con JSON.') is None, 'Format ignored')


@case('emotion', 'An emotional or urgent request is not reduced to a neutral opening')
def emotion(path):
    for text in ('Sono triste e ho un dubbio.', 'Ho un problema. Non riesco a respirare.'):
        require(opening_recovery(text) is None, 'Emotional or urgent content dropped')


@case('quotes_negation', 'Quoted, negated and third-person openings are not user intentions')
def quotes_negation(path):
    for text in ('«Ho un dubbio»', 'Non ho un dubbio', 'Mia sorella ha un dubbio'):
        require(opening_recovery(text) is None, 'Unsupported intention attributed')


@case('successful_turn', 'Successful answers and cancellation close the pending-failure chain')
def successful_turn(path):
    for status in ('cancelled', 'completed'):
        history = [T(role='user', content='Ho un dubbio', metadata={}),
                   T(role='assistant', content='Risposta', metadata={'is_valid': False, 'generation': {'status': status}})]
        require(unanswered_attempt(history) is None, 'Closed turn resumed')
        require(dialogue_history(history) == history, 'Ordinary history removed')


@case('english', 'A supported English opening receives an English clarification')
def english(path):
    reply = opening_recovery('Can I ask you a question?')
    require(reply and reply['language'] == 'en' and 'ask' in reply['content'], 'Language changed')


MOON = 'La Luna mantiene la stessa forma fisica e riflette la luce del Sole.'
META = "Non ho verificato se l'utente ha detto di avere dubbi reali o solo ipotizzativi."
MOON_QUESTION = 'Il mio dubbio è questo: perché la Luna cambia forma durante il mese?'


@case('general_frame', 'A conversational frame is not a compulsory autobiographical lookup')
def general_frame(path):
    with fixture(path) as (core, user, cid):
        core._llm.generate.return_value = MOON
        answer = core.process_message(user, cid, MOON_QUESTION)
        require(answer.is_valid, 'General answer failed')
        require('La ricerca nei ricordi non ha trovato' not in core._llm.generate.call_args.kwargs['prompt'], 'Spurious empty lookup warning')
        require('action_cycle' not in answer.metadata['decision'], 'Unnecessary personal read')


@case('personal_frame', 'Personal references inside the real question still require a scoped read')
def personal_frame(path):
    with fixture(path) as (core, user, cid):
        core._llm.generate.return_value = 'Posso considerare la situazione che hai descritto.'
        answer = core.process_message(user, cid, 'Il mio dubbio è questo: perché la mia passeggiata mi ha rilassato?')
        require(answer.is_valid and answer.metadata['decision']['action_cycle']['status'] == 'observed', 'Mandatory read lost')


@case('followup_frame', 'A general follow-up does not inherit autobiographical scope from a discourse frame')
def followup_frame(path):
    with fixture(path) as (core, user, cid):
        core._llm.generate.return_value = MOON
        core.process_message(user, cid, MOON_QUESTION)
        answer = core.process_message(user, cid, 'Quindi la Luna mantiene la stessa forma fisica?')
        require(answer.is_valid and answer.metadata['dialogue_state']['mode'] == 'confirmation', 'Confirmation rejected')
        require('action_cycle' not in answer.metadata['decision'], 'Inherited unrelated memory search')


@case('scope_projection', 'Discarded execution commentary never becomes verified model knowledge')
def scope_projection(path):
    with fixture(path) as (core, user, cid):
        core._llm.generate.return_value = MOON + ' ' + META
        answer = core.process_message(user, cid, MOON_QUESTION)
        require(answer.is_valid and answer.content == MOON and answer.metadata['source'] == 'model_excerpt', 'Wrong excerpt')
        require(not core.answer_recall.observe.called and not core.incremental_learner.learn_from_interaction.called, 'Edited answer learned automatically')


@case('projection_format', 'Execution commentary cannot pad an exact sentence count')
def projection_format(path):
    with fixture(path) as (core, user, cid):
        core._llm.generate.return_value = MOON + ' ' + META
        answer = core.process_message(user, cid, MOON_QUESTION + ' Rispondi in due frasi.')
        require(not answer.is_valid and answer.metadata['generation']['status'] == 'format_mismatch', 'Fake format compliance')


@case('projection_stream', 'Streaming and stored text omit the same standalone commentary')
def projection_stream(path):
    events = []
    stream = AnswerStream(MOON_QUESTION, events.append)
    raw = MOON + '\n\n' + META
    for character in raw:
        stream.feed(character)
    stream.feed('', final=True)
    require(not stream.rejected and ''.join(e['content'] for e in events) == MOON, 'Stream leaked commentary')
    from allma_model.core.architecture.identity_state import IdentityState
    with fixture(path) as (core, user, cid):
        core.identity_engine_v5.compute_state = Mock(return_value=IdentityState(under_duress=True))
        raw = MOON + '\n\nLa porzione illuminata visibile dipende dal punto di osservazione.'
        def generate(**kwargs):
            kwargs['callback']('</think>' + raw)
            return raw
        core._llm.generate.side_effect = generate
        events = []
        answer = core.process_message(user, cid, MOON_QUESTION, stream_callback=events.append)
        require(answer.is_valid and answer.content == raw, 'Expression rewrote streamed paragraphs')
        require(''.join(e['content'] for e in events if e['type'] == 'answer') == raw, 'Stream/final divergence under duress')


@case('preserve_analysis', 'A requested analysis or quotation preserves the actual sentence')
def preserve_analysis(path):
    for request, answer in [('Analizza questa frase', META), ('Perché la Luna cambia?', '«' + META + '»')]:
        require(project_answer(answer, request).text == answer, 'Requested text deleted')


@case('new_information', 'Useful overlap followed by new information remains allowed')
def new_information(path):
    h = [T(role='user', content=MOON_QUESTION), T(role='assistant', content=MOON)]
    view = DialogueContinuity('Puoi spiegare meglio?', h)
    require(not view.duplicate(MOON + ' La porzione visibile dipende anche dal punto di osservazione.'), 'Useful expansion blocked')


@case('whole_reuse', 'A new task cannot be answered by rearranging the same old sentences')
def whole_reuse(path):
    second = 'Le fasi dipendono dalla porzione illuminata che risulta visibile dalla Terra.'
    h = [T(role='user', content=MOON_QUESTION), T(role='assistant', content=MOON + ' ' + second)]
    view = DialogueContinuity('Spiegami la fotosintesi.', h)
    require(view.duplicate('Certo. ' + second + ' ' + MOON), 'Reordered whole duplicate passed')


@case('allowed_transform', 'An explicit summary can reuse the actual earlier content')
def allowed_transform(path):
    h = [T(role='user', content=MOON_QUESTION), T(role='assistant', content=MOON)]
    require(not DialogueContinuity('Riassumi la spiegazione', h).duplicate(MOON), 'Summary blocked')


@case('subject_clarification', 'A revised subject is distinct from an unverified factual correction')
def subject_clarification(path):
    h = [T(role='user', content=MOON_QUESTION), T(role='assistant', content=MOON)]
    view = DialogueContinuity('No, intendevo Venere e non la Luna.', h)
    require(view.mode == 'subject_clarification' and not view.factual_correction, 'Intent treated as factual dispute')


@case('working_references', 'The working view uses scoped references instead of copying a second archive')
def working_references(path):
    h = [T(role='user', content=MOON_QUESTION), T(role='assistant', content=MOON)]
    state = DialogueContinuity('Puoi spiegare meglio?', h).state()
    require(state['mode'] == 'elaboration' and len(state['reference_sha256']) == 64, 'Missing reference')
    require(MOON_QUESTION not in str(state) and MOON not in str(state), 'Working view duplicated content')
    failed_request = T(role='user', content=MOON_QUESTION, metadata={})
    failed_reply = T(role='assistant', content='Avviso sintetico.',
        metadata={'is_valid': False, 'generation': {'status': 'format_mismatch'}})
    state = DialogueContinuity('Quindi la forma fisica resta uguale?', [failed_request], [failed_request, failed_reply]).state()
    require(state['reference_sha256'] == hashlib.sha256(MOON_QUESTION.encode()).hexdigest(), 'Pending request lost after failure')


def run_battery(output, *, scope=None, cancel_event=None, progress_callback=None):
    return run_challenges(output, CASES, version='dialogue-recovery-v2', scope=scope,
        cancel_event=cancel_event, progress_callback=progress_callback, harness_path=__file__)


class DialogueRecoveryRun(PlanDiagnosticRun):
    report_prefix = 'ALLMA_DIALOGUE_RECOVERY'

    def run_tests(self, progress_callback=None):
        core = self.model.brain
        rows, software, reason = [], None, 'completed'
        path = Path(self.report_path)
        with self.source._lock:
            if self.source._user_active.is_set() or getattr(self.source, '_benchmark_active', False):
                raise RuntimeError('ALLMA occupata')
            self.source._benchmark_active = True
            self.source._user_active.set()
        try:
            software = run_battery(path.parent / (path.stem + '_software'),
                scope='Android; synthetic archives and scripted model', cancel_event=self.cancel_event,
                progress_callback=(lambda n, total, name: progress_callback(n, len(CASES) + 5, name)) if progress_callback else None)
            if not software['complete']:
                reason = 'cancelled'
            elif software['failures']:
                reason = 'software_failed'
            else:
                user = 'BENCHMARK_DIALOGUE_' + uuid.uuid4().hex
                cid = core.start_conversation(user)
                core.process_message(user, cid, 'Ciao', cancel_event=self.cancel_event)
                questions = ['Bene, ma ho un dubbio',
                    'Il mio dubbio è questo: perché la Luna cambia forma durante il mese? Rispondi in due frasi.',
                    'Quindi la Luna cambia davvero forma oppure cambia soltanto la parte illuminata che vediamo?',
                    'No, intendevo Venere: perché è così luminosa?',
                    'Ora cambiamo argomento: perché le foglie sono verdi? Una spiegazione breve.']
                for index, question in enumerate(questions):
                    if self.cancel_event.is_set():
                        reason = 'cancelled'; break
                    conditions = self.model._conditions()
                    temperature = conditions.get('battery_temp_celsius')
                    if type(temperature) in (int, float) and temperature >= 41.5:
                        reason = 'thermal_pause'; break
                    if progress_callback:
                        progress_callback(len(CASES) + index, len(CASES) + len(questions), 'Dialogo reale · ' + str(index + 1))
                    start = time.perf_counter()
                    streamed = []
                    core._synthetic_candidate = None
                    def observe(event):
                        if event['type'] == 'answer':
                            streamed.append(event['content'])
                    answer = core.process_message(user, cid, question,
                        context={'disable_answer_recall': True, 'benchmark_seed': 20261026 + index,
                                 'benchmark_max_tokens': 224, 'benchmark_thought_budget': 64},
                        cancel_event=self.cancel_event, stream_callback=observe)
                    candidate = core._synthetic_candidate or {}
                    rows.append({'question': question, 'answer': answer.content, 'is_valid': answer.is_valid,
                        'source': answer.metadata.get('source'), 'recovery': answer.metadata.get('recovery'),
                        'decision': answer.metadata.get('decision'), 'conditions': conditions,
                        'dialogue_state': answer.metadata.get('dialogue_state'),
                        'dialogue_output': answer.metadata.get('dialogue_output'),
                        'candidate_before_projection': candidate.get('before_dialogue_projection'),
                        'candidate_before_pipeline': candidate.get('before_pipeline'),
                        'streamed_text': ''.join(streamed),
                        'stream_matches_final': ''.join(streamed).strip() == answer.content.strip(),
                        'generation': answer.metadata.get('generation', {}),
                        'elapsed_ms': (time.perf_counter() - start) * 1000})
        except GenerationCancelled:
            reason = 'cancelled'
        except Exception:
            reason = 'error'; raise
        finally:
            self.source._benchmark_active = False
            self.source._user_active.clear()
            summary = {'software': software, 'results': rows, 'completed': len(rows), 'total': 5,
                'stop_reason': reason, 'state_isolated': True, 'semantic_accuracy': None}
            self.manifest = {'cancelled': reason != 'completed', 'summary': summary}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.with_suffix('.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
            report = '# Ripresa del dialogo\n\n24 scenari software sintetici, un’apertura gestita da ALLMA e quattro turni con il modello reale: spiegazione, conferma, precisazione e nuovo argomento. La qualità semantica richiede valutazione umana. Nessun retry. Le eventuali estrazioni sono segnalate nei metadati.\n\n'
            if software:
                report += f"Scenari software: {software['passed']}/{software['total']}.\n\n"
            for row in rows:
                report += '## ' + row['question'] + '\n\n' + row['answer'] + '\n\n'
            path.write_text(report)
            print(self.report_prefix + '_REPORT ' + str(path.with_suffix('.json')), flush=True)
            print(self.report_prefix + '_SUMMARY ' + json.dumps({
                'software_passed': software['passed'] if software else 0, 'software_total': len(CASES),
                'completed': len(rows), 'total': 5, 'stop_reason': reason, 'state_isolated': True}), flush=True)
