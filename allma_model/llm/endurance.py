"""25 real minutes of intermittent, isolated Android chat/voice workload.

Latency and process residency are measurements. Charging invalidates any claim
about net battery consumption. TTS uses real callbacks; ASR text injection is
explicitly not a microphone recognition test.
"""
from collections import Counter
from pathlib import Path
import json
import math
import threading
import time
import uuid
from .context_inference import conditions
from .native_backend import native_work
from allma_model.utils.generation_control import GenerationCancelled
from allma_model.utils.persistence import atomic_write_json

DURATION_SECONDS = 25 * 60
INTERVAL_SECONDS = 75


class SessionCancellation:
    def __init__(self, run, event):
        self.run, self.event = run, event
        self.deadline = time.monotonic() + 65
        self.next_check = 0
        self.reason = None

    def native_is_set(self):
        # Safe inside a C CPU callback: no sensor reads or Java calls.
        return bool(self.event.is_set() or self.run.cancel_event.is_set()
            or self.run.source._shutdown_event.is_set() or not self.run.source._foreground
            or time.monotonic() > self.deadline)

    def is_set(self):
        now = time.monotonic()
        if self.event.is_set() or self.run.cancel_event.is_set() or self.run.source._shutdown_event.is_set():
            self.reason = 'cancelled'
        elif not self.run.source._foreground:
            self.reason = 'background'
        elif now > self.deadline:
            self.reason = 'request_timeout'
        elif now >= self.next_check:
            self.next_check = now + 2
            sample = conditions(self.run.source)
            temperature = sample['temperature_c']
            if temperature is None:
                self.reason = 'sensors_unavailable'
            elif temperature >= 40.5 or (type(sample.get('thermal_status')) is int and sample['thermal_status'] >= 3):
                self.reason = 'thermal_pause'
        return self.reason is not None


class LongSessionRun:
    report_prefix = 'ALLMA_LONG_SESSION'
    report_stem = 'long_session'
    cases = (('Quanto fa 31 + 17? Rispondi solo con un numero.', 'compute'), ('Il codice di prova è RIVA-582.', 'declaration'), ('Spiega in due frasi perché si forma un arcobaleno.', 'generation'), ('Dimmi in una frase a cosa serve una bussola.', 'voice'), ('Descrivi un bosco in dieci paragrafi.', 'cancel'), ('Quale codice di prova ti avevo indicato?', 'recall'))

    def __init__(self):
        from benchmark_iq import CognitiveBenchmark
        self.model = CognitiveBenchmark(profile='quick')
        self.cancel_event = self.model.cancel_event
        self.manifest = {}
        self.report_path = self.model.report_path
        self.voice_probe = None
        self.duration = DURATION_SECONDS
        self.interval = INTERVAL_SECONDS
        self.started = None
        self.summary = None

    def setup_brain(self, existing_brain):
        self.source = existing_brain
        self.model.setup_brain(existing_brain)
        self.report_path = str(Path(existing_brain.db_path).resolve().parent / 'benchmarks/reports' /
            (self.report_stem+'_' + uuid.uuid4().hex + '.md'))

    def _save(self):
        self.summary['elapsed_seconds'] = time.monotonic() - self.started
        atomic_write_json(Path(self.report_path).with_suffix('.json'), self.summary)

    def _sample(self):
        self.summary['samples'].append({'elapsed_seconds':time.monotonic()-self.started,
            'foreground':bool(self.source._foreground), **conditions(self.source)})
        self._save()

    def _tts(self, text):
        tts = self.voice_probe
        row = {'available':tts is not None, 'microphone_tested':False, 'events':[], 'error':None}
        if tts is None:
            return row
        prior = tts.on_state
        def observe(state, message=''):
            row['events'].append({'state':state, 'elapsed_ms':(time.monotonic()-start)*1000})
            if prior:
                prior(state,message)
        tts.on_state = observe
        start = time.monotonic()
        try:
            tts.speak(text, {'language':'it-IT'}, flush=True)
            deadline = start + 25
            while time.monotonic() < deadline and not self.cancel_event.wait(.1):
                events = [r['state'] for r in row['events']]
                if 'error' in events:
                    row['error'] = 'native_tts_error'; break
                if 'speaking' in events and 'idle' in events:
                    break
                if not self.source._foreground:
                    row['error'] = 'background'; break
            row['completed'] = any(e['state']=='speaking' for e in row['events']) and any(e['state']=='idle' for e in row['events'])
            if not row['completed']:
                tts.stop()
                row['error'] = row['error'] or 'tts_timeout_or_cancelled'
        finally:
            tts.on_state = prior
        return row

    @native_work
    def run_tests(self, progress_callback=None):
        source, core = self.source, self.model.brain
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False):
                raise RuntimeError('ALLMA occupata')
            if not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile')
            source._benchmark_active = True
            source._user_active.set()
        self.started = time.monotonic()
        self.summary = {'version':1,'planned_seconds':self.duration,'elapsed_seconds':0,
            'workload':'intermittent: one task every '+str(self.interval)+' seconds; chat, declared memory, TTS and cancellation',
            'personal_data_used':False,'asr_microphone_tested':False,'battery_energy_measured':False,
            'planned_tasks':math.ceil(self.duration/self.interval),
            'model_backend':dict(getattr(source._llm,'backend_info',{})),
            'production_context':getattr(source._llm,'n_ctx',None),'model_name':Path(source._llm.model_path).name if getattr(source._llm,'model_path',None) else None,'phase':'starting',
            'stop_reason':'running','results':[],'samples':[],'background_resumes':0}
        print(self.report_prefix+'_REPORT '+str(Path(self.report_path).with_suffix('.json')),flush=True)
        user = 'BENCHMARK_ENDURANCE_'+uuid.uuid4().hex
        core._capture_synthetic_candidates = False
        core.system_monitor = source.system_monitor
        reason, next_sample, index, was_background = 'completed',0,0,False
        try:
            cid = core.start_conversation(user)
            while time.monotonic()-self.started < self.duration:
                elapsed = time.monotonic()-self.started
                if self.cancel_event.is_set() or source._shutdown_event.is_set():
                    reason='cancelled'; break
                if elapsed >= next_sample:
                    self._sample();next_sample = elapsed + 5
                if not source._foreground:
                    was_background = True
                    self.summary['phase'] = 'background_pause'
                    self.cancel_event.wait(.3);continue
                if was_background:
                    self.summary['background_resumes'] += 1
                    was_background = False
                # Cooling and foreground pauses count as elapsed wall time, not
                # successful tasks; no missed workload is silently backfilled.
                if elapsed < index*self.interval:
                    self.summary['phase'] = 'waiting'
                    if progress_callback:progress_callback(int(elapsed),self.duration,'Sessione lunga · '+str(int(elapsed//60))+' min')
                    self.cancel_event.wait(.3);continue
                before = conditions(source)
                if before['temperature_c'] is None:
                    reason='sensors_unavailable';break
                if before['temperature_c'] >= 40 or (type(before.get('thermal_status')) is int and before['thermal_status'] >= 3):
                    self.summary['phase']='cooling';self.cancel_event.wait(5);continue
                question, kind = self.cases[index % len(self.cases)]
                self.summary['phase']='request';self._save()
                local = threading.Event()
                cancellation = SessionCancellation(self,local)
                cancelling = kind == 'cancel'
                timer = threading.Timer(1.5,local.set) if cancelling else None
                start = time.monotonic();first=None
                def stream(event):
                    nonlocal first
                    if first is None and event.get('type')=='answer' and event.get('content','').strip():
                        first = (time.monotonic()-start)*1000
                if timer:timer.start()
                row = {'index':index,'question':question,'before':before,'cancel_requested':cancelling,'kind':kind}
                try:
                    response = core.process_message(user,cid,question,
                        context={'disable_answer_recall':True,'benchmark_seed':20261027+index,
                            'benchmark_max_tokens':192,'benchmark_thought_budget':48,
                            **({'delivery_mode':'voice'} if kind=='voice' else {})},
                        cancel_event=cancellation,stream_callback=stream)
                    row.update(answer=response.content,is_valid=response.is_valid,
                        generation=response.metadata.get('generation',{}),source=response.metadata.get('source'),status='answered',
                        response_ms=(time.monotonic()-start)*1000)
                    if kind=='voice' and response.is_valid:
                        row['voice'] = self._tts(response.content)
                except GenerationCancelled:
                    row.update(status=cancellation.reason or 'cancelled',is_valid=False)
                    generation = getattr(core._llm,'last_generation',{})
                    if generation.get('status') == 'cancelled':row['generation'] = dict(generation)
                finally:
                    if timer:timer.cancel();timer.join()
                row.update(elapsed_ms=(time.monotonic()-start)*1000,first_answer_ms=first,after=conditions(source))
                self.summary['results'].append(row);index+=1;self._sample()
                if row['status'] in {'request_timeout','sensors_unavailable'}:
                    reason=row['status'];break
        except Exception:
            reason='error';raise
        finally:
            try:
                self.summary['workload_complete'] = index >= self.summary['planned_tasks']
                if reason == 'completed' and not self.summary['workload_complete']:
                    reason = 'window_ended_with_pending_tasks'
                self.summary.update(phase='finished',stop_reason=reason)
                self._sample()
                samples=self.summary['samples']
                self.summary['charging_seen']=any(s['charging'] is True for s in samples)
                self.summary['temperature_max_c']=max((s['temperature_c'] for s in samples if s['temperature_c'] is not None),default=None)
                self.summary['rss_max_mib']=max((s['rss_mib'] for s in samples if s['rss_mib'] is not None),default=None)
                self.summary['status_counts']=dict(Counter(r['status'] for r in self.summary['results']))
                self._save()
                Path(self.report_path).write_text('# Sessione lunga ALLMA\n\nDurata reale: '+str(round(self.summary['elapsed_seconds'],1))+
                    ' s. Carico intermittente, archivi sintetici.\n\nEsiti: '+json.dumps(self.summary['status_counts'])+
                    '\n\nIl consumo energetico non è misurato; RAM indica il processo, non tutta la memoria GPU. '
                    'I controlli vocali verificano la sintesi reale, non il riconoscimento dal microfono.\n')
                self.manifest={'cancelled':reason!='completed','stop_reason':reason,'summary':self.summary}
                print(self.report_prefix+'_SUMMARY '+json.dumps({k:self.summary[k] for k in
                    ('elapsed_seconds','stop_reason','background_resumes','temperature_max_c','rss_max_mib','status_counts')}),flush=True)
            finally:
                source._benchmark_active=False;source._user_active.clear()

    def close(self):
        self.cancel_event.set()
        self.model.close()

