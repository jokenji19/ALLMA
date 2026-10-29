"""Isolated real-model dialogue and one explicitly injected repeated draft.

Answers require human review. Passing host checks does not certify world facts.
No user history, profile, weights or selected backend is changed.
"""
from pathlib import Path
import json
import threading
import time
import uuid

from .native_backend import native_work
from .context_inference import conditions
from .endurance import SessionCancellation
from allma_model.utils.generation_control import GenerationCancelled
from allma_model.utils.persistence import atomic_write_json

OLD = ('Una bussola contiene un ago magnetizzato che può ruotare liberamente su un perno. '
       'L’ago si dispone lungo la direzione del campo magnetico terrestre e permette di orientarsi.')


class RepeatedDraftOnce:
    def __init__(self, engine, draft=OLD):
        self.engine, self.used, self.draft_id = engine, False, None
        self.draft = draft
    def __getattr__(self, name):
        return getattr(self.engine, name)
    def prepare_chat(self, *args, **kwargs):
        return self.engine.prepare_chat(*args, **kwargs)
    def generate(self, **kwargs):
        if not self.used:
            self.used, self.draft_id = True, kwargs['request_id']
            if kwargs.get('callback'):
                kwargs['callback']('</think>' + self.draft)
            return self.draft
        return self.engine.generate(**kwargs)
    def get_generation_meta(self, request):
        if request == self.draft_id:
            return {'request_id':request,'finish_reason':'stop','injected_draft':True}
        return self.engine.get_generation_meta(request)


class DialogueReasoningRun:
    cases = (('independent', 'Chi era Napoleone Bonaparte? Rispondi in due frasi.'),
        ('elaboration', 'Dimmi anche altro su di lui, senza ripetere i punti già detti.'),
        ('new_subject', 'Ora cambia argomento: spiegami come si forma un arcobaleno in due frasi.'),
        ('injected_copy', 'Dimmi anche altro su di essa.'))
    report_stem = 'turn_reasoning'
    injected_draft = OLD
    def __init__(self):
        from benchmark_iq import CognitiveBenchmark
        self.model = CognitiveBenchmark(profile='quick')
        self.cancel_event = self.model.cancel_event
        self.manifest = {}

    def setup_brain(self, existing_brain):
        source = existing_brain
        self.source = source
        self.model.setup_brain(source)
        self.report_path = str(Path(source.db_path).resolve().parent/'benchmarks/reports'/
            (self.report_stem + '_' + uuid.uuid4().hex + '.md'))

    @native_work
    def run_tests(self, progress_callback=None):
        source, core = self.source, self.model.brain
        with source._lock:
            if source._user_active.is_set() or getattr(source, '_benchmark_active', False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._benchmark_active = True
            source._user_active.set()
        engine = core._llm
        rows, reason = [], 'completed'
        path = Path(self.report_path)
        summary = {'personal_data_used':False, 'human_quality_review_required':True,
            'backend':dict(engine.backend_info), 'model':Path(engine.model_path).name,
            'results':rows, 'stop_reason':'running', 'planned':len(self.cases)}
        user = 'BENCHMARK_TURN_' + uuid.uuid4().hex
        core._capture_synthetic_candidates = False
        core.system_monitor = source.system_monitor
        try:
            cid = core.start_conversation(user)
            cases = self.cases
            print('ALLMA_TURN_REASONING_REPORT ' + str(path.with_suffix('.json')), flush=True)
            for index, (kind, question) in enumerate(cases):
                sample = conditions(source)
                if self.cancel_event.is_set() or not source._foreground:
                    reason = 'cancelled'; break
                if (sample['temperature_c'] is None or sample['temperature_c'] >= 40
                        or (type(sample.get('thermal_status')) is int and sample['thermal_status'] >= 2)):
                    reason = 'thermal_pause'; break
                if kind == 'injected_copy':
                    cid = core.start_conversation(user)
                    from allma_model.core.autobiographical_identity import POLICY_VERSION
                    core.conversational_memory.store_message(cid,'Descrivi il funzionamento di una bussola.',
                        {},'user',user)
                    core.conversational_memory.store_message(cid,OLD,{'identity_policy':POLICY_VERSION,
                        'source':'model_generated','is_valid':True},'assistant',user)
                    core._llm = RepeatedDraftOnce(engine, self.injected_draft)
                if progress_callback: progress_callback(index, len(cases), 'Dialogo e revisione · ' + kind)
                events = []
                started = time.monotonic()
                reply = core.process_message(user,cid,question,context={'disable_answer_recall':True},
                    cancel_event=SessionCancellation(self,threading.Event()), stream_callback=events.append)
                rows.append({'case':kind,'question':question,'answer':reply.content,'valid':reply.is_valid,
                    'elapsed_ms':(time.monotonic()-started)*1000,
                    'turn_review':reply.metadata.get('turn_review'),
                    'generation':reply.metadata.get('generation'),
                    'source':reply.metadata.get('source'),
                    'published_text':''.join(e['content'] for e in events if e['type']=='answer'),
                    'first_draft_injected':kind=='injected_copy','conditions':sample})
                core._llm = engine
                atomic_write_json(path.with_suffix('.json'),summary)
        except GenerationCancelled:
            reason = 'cancelled'
        except Exception:
            reason = 'error'; raise
        finally:
            core._llm = engine
            try:
                summary.update(stop_reason=reason,completed=len(rows),same_model_object=source._llm is engine,
                    conditions_after=conditions(source))
                atomic_write_json(path.with_suffix('.json'),summary)
                path.write_text('# Dialogo e revisione mirata\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
                self.manifest = {'cancelled':reason!='completed','stop_reason':reason,'summary':summary}
                print('ALLMA_TURN_REASONING_SUMMARY '+json.dumps({'stop_reason':reason,'completed':len(rows),
                    'accepted':sum(r['valid'] for r in rows)},ensure_ascii=False),flush=True)
            finally:
                source._benchmark_active = False
                source._user_active.clear()

    def close(self):
        self.cancel_event.set()
        self.model.close()


class RevisionRecoveryRun(DialogueReasoningRun):
    cases = (('injected_copy', 'Dimmi anche altro su di essa, senza ripetere i punti già detti.'),)
    report_stem = 'turn_revision'
    injected_draft = OLD + ' Un magnete vicino può deviare l’indicazione.'
