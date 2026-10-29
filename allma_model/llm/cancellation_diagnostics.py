"""Controlled CPU cancellation pair and real Android thermal admission.

Same model, prepared prompt, seed and token budget. The legacy signal intentionally
uses iterator cancellation only; the Event enables the pinned CPU graph hook.
No chat/memory stores, model switches or production preference writes.
"""
from pathlib import Path
from threading import Event, Timer
import hashlib
import json
import time
import uuid
from .native_backend import native_work
from .context_inference import conditions
from allma_model.utils.generation_control import GenerationCancelled
from allma_model.utils.persistence import atomic_write_json


class IteratorSignal:
    def __init__(self,event,run,deadline):
        self.event,self.run,self.deadline=event,run,deadline
    def is_set(self):
        return bool(self.event.is_set() or self.run.cancel_event.is_set()
            or self.run.source._shutdown_event.is_set() or not self.run.source._foreground
            or time.monotonic()>self.deadline)


class RuntimeFollowupRun:
    def __init__(self):
        self.cancel_event=Event();self.manifest={};self.voice_probe=None

    def setup_brain(self,existing_brain):
        self.source=existing_brain
        self.report_path=str(Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/
            ('runtime_followup_'+uuid.uuid4().hex+'.md'))

    @native_work
    def run_tests(self,progress_callback=None):
        source=self.source
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._ensure_mobile_llm();engine=source._llm
            if engine is None or engine.backend_info.get('kind')!='cpu':
                raise RuntimeError('Questa prova controllata richiede il modello attuale su CPU')
            source._benchmark_active=True;source._user_active.set()
        results=[];reason='completed'
        summary={'scope':'controlled CPU cancellation pair; synthetic prompt; no personal data',
            'model_name':Path(engine.model_path).name,'model_backend':dict(engine.backend_info),
            'production_context':engine.n_ctx,'cancel_after_seconds':1.5,'results':results}
        path=Path(self.report_path)
        def save():atomic_write_json(path.with_suffix('.json'),summary)
        try:
            summary['conditions_before']=conditions(source)
            from allma_model.utils.background_work import power_allows_background,power_allows_initiative,power_allows_backup,power_allows_decision
            state=source.system_monitor.get_metabolic_state()
            summary['thermal_reading']={'status':state.thermal_status,'api_available':state.thermal_api_available,
                'battery_temperature_c':state.battery_temp_celsius,'power_valid':state.is_valid}
            summary['optional_admission']={name:fn(source.system_monitor) for name,fn in
                (('dreams',power_allows_background),('initiative',power_allows_initiative),('backup',power_allows_backup),('decider',power_allows_decision))}
            if not summary['optional_admission']['decider']:
                summary['decider_admission_probe']=source.decision_runtime.choose('thermal_diagnostic',
                    'Synthetic diagnostic, no user history.', 'Which branch?', {'wait':'Wait','reason':'Reason'},cancel_event=self.cancel_event)
            question='\n'.join('Appunto sintetico '+str(i)+': nel bosco si trovano querce, sentieri e un ruscello.' for i in range(28))
            question+='\nDescrivi questo bosco in un paragrafo.'
            prepared=engine.prepare_chat([{'role':'system','content':'Ti chiami ALLMA. Rispondi in italiano.'},
                {'role':'user','content':question}],64,reasoning=False)
            with engine.inference_lock:
                tokens=engine.llm.tokenize(prepared.prompt.encode(),add_bos=False,special=True)
            summary['prompt_sha256']=hashlib.sha256(prepared.prompt.encode()).hexdigest()
            summary['prompt_tokens']=len(tokens);summary['seed']=20261027;summary['max_tokens']=64
            save();print('ALLMA_RUNTIME_FOLLOWUP_REPORT '+str(path.with_suffix('.json')),flush=True)
            for index,variant in enumerate(('iterator_only','native_cpu_abort')):
                before=conditions(source)
                if self.cancel_event.is_set() or source._shutdown_event.is_set() or not source._foreground:
                    reason='cancelled';break
                if (before['temperature_c'] is None or before['temperature_c']>=40.5
                        or (type(before.get('thermal_status')) is int and before['thermal_status']>=3)):
                    reason='thermal_pause';break
                if progress_callback:progress_callback(index,3,'Cancellazione CPU · '+variant)
                with engine.inference_lock:
                    engine.llm.set_cache(None);engine.llm.reset();engine.llm._ctx.kv_cache_clear()
                event=Event();start=time.monotonic();timing={'cancel_set_ms':None}
                def cancel():
                    timing['cancel_set_ms']=(time.monotonic()-start)*1000;event.set()
                timer=Timer(1.5,cancel);timer.start()
                signal=event if variant=='native_cpu_abort' else IteratorSignal(event,self,start+65)
                request='CPU_CANCEL_PAIR:'+uuid.uuid4().hex
                row={'variant':variant,'before':before,'status':'not_started'}
                try:
                    answer=engine.generate(prepared.prompt,max_tokens=64,seed=20261027,
                        native_prompt=True,stop=list(prepared.stops),cancel_event=signal,
                        request_id=request,**engine.binding.sampling())
                    row.update(status='returned_before_cancel' if not event.is_set() else 'cancellation_not_propagated',answer=answer)
                except GenerationCancelled:row['status']='cancelled'
                finally:
                    timer.cancel();timer.join()
                row.update(elapsed_ms=(time.monotonic()-start)*1000,**timing,
                    generation=engine.get_generation_meta(request) or {},after=conditions(source))
                row['wait_after_signal_ms']=(row['elapsed_ms']-row['cancel_set_ms']) if row['cancel_set_ms'] is not None else None
                results.append(row);save()
            if len(results)==2 and not self.cancel_event.is_set():
                if progress_callback:progress_callback(2,3,'Verifico il recupero del modello')
                prepared=engine.prepare_chat([{'role':'user','content':'Rispondi solo con la parola pronto.'}],32,reasoning=False)
                text=engine.generate(prepared.prompt,max_tokens=32,seed=20261027,native_prompt=True,
                    stop=list(prepared.stops),cancel_event=self.cancel_event,request_id='CPU_RECOVERY:'+uuid.uuid4().hex,
                    **engine.binding.sampling())
                summary['recovery']={'nonempty':bool(text.strip()),'answer':text,'same_model_object':source._llm is engine}
        except Exception:
            reason='error';raise
        finally:
            try:
                summary.update(stop_reason=reason,conditions_after=conditions(source))
                self.manifest={'cancelled':reason!='completed','stop_reason':reason,'summary':summary}
                save()
                path.write_text('# CPU e temperatura: prova controllata\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
                compact={'stop_reason':reason,'completed':len(results),'thermal_reading':summary.get('thermal_reading'),
                    'recovery':summary.get('recovery'),'results':[{k:r.get(k) for k in
                    ('variant','status','elapsed_ms','cancel_set_ms','wait_after_signal_ms')} for r in results]}
                print('ALLMA_RUNTIME_FOLLOWUP_SUMMARY '+json.dumps(compact,ensure_ascii=False),flush=True)
            finally:source._benchmark_active=False;source._user_active.clear()

    def close(self):self.cancel_event.set()
