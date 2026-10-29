"""Actual chat pipeline with public sources and disposable conversational memory."""
from pathlib import Path
import json
import threading
import time
import uuid

from allma_model.utils.generation_control import check_cancelled, GenerationCancelled
from allma_model.utils.persistence import atomic_write_json
from allma_model.core.learning_insights import response_origin


class InternetChatRun:
    def __init__(self):
        from benchmark_iq import CognitiveBenchmark
        self.model=CognitiveBenchmark(profile='quick')
        self.cancel_event=self.model.cancel_event
        self.manifest={}

    def setup_brain(self, existing_brain):
        self.source=existing_brain
        self.model.setup_brain(existing_brain)
        self.report_path=str(Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/
            ('internet_chat_'+uuid.uuid4().hex+'.json'))

    def run_tests(self, progress_callback=None):
        source,core=self.source,self.model.brain
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._benchmark_active=True;source._user_active.set()
        before=source.public_references.status()['enabled']
        rows=[];started=time.monotonic();reason='running'
        user='BENCHMARK_INTERNET_'+uuid.uuid4().hex
        original_reader=core.public_references.reader
        cases=(('research_followup','Cerca su internet','reference_excerpt'),
            ('new_contribution','Dimmi anche altro su di lui, senza ripetere i punti già detti.','reference_excerpt'),
            ('new_topic','Come funziona una bussola?','reference_excerpt'),
            ('local_calculation','Quanto fa 18 + 24? Rispondi solo con un numero','verified_calculation'),
            ('local_identity','Come ti chiami?','origin_identity'),
            ('source_unavailable','Cerca online una galassia','reference_unavailable'))
        try:
            core.public_references.configure(True)
            cid=core.start_conversation(user)
            from allma_model.core.autobiographical_identity import POLICY_VERSION
            core.conversational_memory.store_message(cid,'Chi era mussolini?',{'identity_policy':POLICY_VERSION},'user',user)
            core.conversational_memory.store_message(cid,'Non sono Mussolini.',
                {'source':'model_generated','identity_policy':POLICY_VERSION,'is_valid':True},'assistant',user)
            for index,(kind,question,expected) in enumerate(cases):
                check_cancelled(self.cancel_event)
                if not source._foreground:raise GenerationCancelled()
                if progress_callback:progress_callback(index,len(cases),kind)
                if kind=='source_unavailable':
                    class EmptyReader:
                        def fetch(self,*args):return []
                    core.public_references.reader=EmptyReader()
                events=[];tick=time.monotonic()
                reply=core.process_message(user,cid,question,context={'disable_answer_recall':True,'benchmark_seed':42},
                    cancel_event=self.cancel_event,stream_callback=events.append)
                source_kind=reply.metadata.get('source')
                activity=[event['content'] for event in events if event['type']=='reference']
                passed=source_kind==expected and (bool(reply.content) and reply.is_valid if expected!='reference_unavailable'
                    else not reply.content and not reply.is_valid)
                if kind=='local_calculation':passed=passed and reply.content=='42' and not activity
                if kind=='new_contribution':passed=passed and reply.content!=rows[0]['answer'] and all(e['state']!='searching' for e in activity)
                rows.append({'case':kind,'question':question,'answer':reply.content,'source':source_kind,
                    'valid':reply.is_valid,'passed':bool(passed),'origin':response_origin(reply.metadata,reply.is_valid),
                    'activity':activity,'seconds':time.monotonic()-tick})
            reason='completed'
        except GenerationCancelled:reason='cancelled'
        except Exception:
            reason='error'
            raise
        finally:
            core.public_references.reader=original_reader
            source._benchmark_active=False;source._user_active.clear()
            summary={'results':rows,'passed':sum(row['passed'] for row in rows),'completed':len(rows),
                'stop_reason':reason,'seconds':time.monotonic()-started,'personal_data_used':False,
                'source_preference_before':before,'source_preference_after':source.public_references.status()['enabled']}
            self.results=summary;self.manifest={'stop_reason':reason,'cancelled':reason!='completed'}
            atomic_write_json(self.report_path,summary)
            print('ALLMA_INTERNET_CHAT_REPORT '+self.report_path,flush=True)
            print('ALLMA_INTERNET_CHAT_SUMMARY '+json.dumps({'passed':summary['passed'],'completed':len(rows),'stop_reason':reason}),flush=True)

    def close(self):
        self.cancel_event.set();self.model.close()
