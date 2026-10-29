"""Short dialogue with the real motor, plus two labelled injected drafts.

The benchmark core and all state are isolated by CognitiveBenchmark. The
active conversation, selected motor and Decider preference are never changed.
"""
from pathlib import Path
import json
import threading
import time
import uuid

from .dialogue_reasoning_diagnostics import DialogueReasoningRun, RepeatedDraftOnce
from .native_backend import native_work
from .context_inference import conditions
from .endurance import SessionCancellation
from allma_model.utils.dialogue_continuity import wellbeing_question
from allma_model.utils.checkin_turn import checkin_task
from allma_model.utils.generation_control import GenerationCancelled
from allma_model.utils.persistence import atomic_write_json


class CheckinRun(DialogueReasoningRun):
    report_stem='checkin'
    cases=(('positive','Bene','Ciao! Come stai?',None),
        ('courtesy','Sto bene, grazie.','Come stai?',None),
        ('negative','Così così.','Come stai?',None),
        ('english',"I'm fine, thanks.",'Hello! How are you?',None),
        ('novel_phrase','Sentieri tranquilli con pochissime persone.',
            'Quale ambiente preferisci per una passeggiata?',None),
        ('new_topic','Degli oceani che potrebbero esistere sotto il ghiaccio.',
            'Di cosa ti piacerebbe parlare?',None),
        ('extractive_control','Bene','Come stai?',
            'Mi fa piacere che tu stia bene. Come ti va?'),
        ('ownership_control','Bene','Come stai?',
            'Sto bene, grazie. Come ti va?'))

    @native_work
    def run_tests(self,progress_callback=None):
        source,core=self.source,self.model.brain
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._benchmark_active=True;source._user_active.set()
        engine=core._llm;core.system_monitor=source.system_monitor
        path=Path(self.report_path);rows=[];reason='completed';cancellation=None
        summary={'results':rows,'personal_data_used':False,'human_quality_review_required':True,
            'automatic_scope':'routing, output validation and delivery consistency; semantic usefulness requires human review',
            'backend':dict(engine.backend_info),'model':Path(engine.model_path).name,
            'planned':len(self.cases),'stop_reason':'running'}
        user='BENCHMARK_CHECKIN_'+uuid.uuid4().hex
        print('ALLMA_CHECKIN_REPORT '+str(path.with_suffix('.json')),flush=True)
        try:
            for index,(kind,request,question,draft) in enumerate(self.cases):
                sample=conditions(source)
                summary['last_conditions']=sample
                state=getattr(source.system_monitor,'last_state',None)
                summary['power_sample']={key:getattr(state,key,None) for key in (
                    'source','is_valid','error','battery_temp_celsius','thermal_status','thermal_api_available')}
                summary['monitor_android']=getattr(source.system_monitor,'is_android',None)
                if self.cancel_event.is_set() or not source._foreground:
                    reason='cancelled';break
                if sample['temperature_c'] is None:
                    reason='sensors_unavailable';break
                if (sample['temperature_c']>=40
                        or (type(sample.get('thermal_status')) is int and sample['thermal_status']>=2)):
                    reason='thermal_pause';break
                cid=core.start_conversation(user)
                from allma_model.core.autobiographical_identity import POLICY_VERSION
                core.conversational_memory.store_message(cid,'Ciao',{},'user',user)
                core.conversational_memory.store_message(cid,question,
                    {'is_valid':True,'source':'model_generated','identity_policy':POLICY_VERSION},'assistant',user)
                core._llm=RepeatedDraftOnce(engine,draft) if draft is not None else engine
                if progress_callback:progress_callback(index,len(self.cases),'Dialogo breve · '+kind)
                events=[];started=time.monotonic()
                cancellation=SessionCancellation(self,threading.Event())
                reply=core.process_message(user,cid,request,context={'disable_answer_recall':True},
                    cancel_event=cancellation,stream_callback=events.append)
                task=checkin_task(request,question)
                decision=reply.metadata.get('decision',{})
                safe=not wellbeing_question(reply.content) and not (task and task.borrowed_state(reply.content))
                useful=bool(reply.is_valid and reply.content.strip())
                routed=(decision.get('task')=='answer_checkin' and decision.get('total_ms')==0
                    and not (decision.get('action_cycle') or {}).get('record_count')) if task else (
                    decision.get('task')=='answer_question' and decision.get('task_context_source')=='host_dialogue_context')
                passed=safe and routed and (useful or kind=='ownership_control')
                if kind=='extractive_control':
                    passed=passed and reply.content=='Mi fa piacere che tu stia bene.' and reply.metadata['turn_review']['attempts']==1
                rows.append({'case':kind,'preceding_question':question,'request':request,'answer':reply.content,'valid':reply.is_valid,
                    'useful_response':useful,'passed':bool(passed),'elapsed_ms':(time.monotonic()-started)*1000,
                    'injected_draft':draft is not None,'decision':decision,
                    'generation':reply.metadata.get('generation'),'turn_review':reply.metadata.get('turn_review'),
                    'projection':reply.metadata.get('dialogue_output'),'conditions':sample,
                    'published_text':''.join(e['content'] for e in events if e['type']=='answer')})
                core._llm=engine
                atomic_write_json(path.with_suffix('.json'),summary)
        except GenerationCancelled:reason=(cancellation.reason if cancellation is not None else None) or 'cancelled'
        except Exception:
            reason='error';raise
        finally:
            core._llm=engine
            try:
                summary.update(stop_reason=reason,completed=len(rows),passed=sum(r['passed'] for r in rows),
                    useful_real_responses=sum(r['useful_response'] for r in rows if not r['injected_draft']))
                atomic_write_json(path.with_suffix('.json'),summary)
                path.write_text('# Dialogo e contesto · risposte reali e controlli sintetici\n\n'+
                    json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
                self.manifest={'cancelled':reason!='completed','stop_reason':reason,'summary':summary}
                print('ALLMA_CHECKIN_SUMMARY '+json.dumps({k:summary[k] for k in
                    ('stop_reason','completed','passed','useful_real_responses')}),flush=True)
            finally:
                source._benchmark_active=False;source._user_active.clear()
