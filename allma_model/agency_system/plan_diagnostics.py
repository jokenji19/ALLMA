"""Two isolated real-model proposals; structural checks are not semantic accuracy."""
from pathlib import Path
import json
import time
import uuid
from allma_model.utils.generation_control import GenerationCancelled


class PlanDiagnosticRun:
    experience_mode = False
    report_prefix = 'ALLMA_PLAN_MODEL'
    def __init__(self):
        from benchmark_iq import CognitiveBenchmark
        self.model=CognitiveBenchmark(profile='quick')
        self.cancel_event=self.model.cancel_event
        self.manifest={}
        self.report_path=self.model.report_path

    def setup_brain(self,existing_brain):
        self.source=existing_brain
        self.model.setup_brain(existing_brain)
        self.report_path=self.model.report_path

    def run_tests(self,progress_callback=None):
        core=self.model.brain;results=[];reason='completed'
        cases=[('list','Preparare una lista di tre oggetti','tre oggetti distinti controllati'),
               ('message','Preparare un breve messaggio di ringraziamento','testo cortese con saluto e ringraziamento')]
        with self.source._lock:
            if self.source._user_active.is_set() or getattr(self.source,'_benchmark_active',False):raise RuntimeError('ALLMA occupata')
            self.source._benchmark_active=True;self.source._user_active.set()
        try:
            for index,(case_id,title,criterion) in enumerate(cases):
                if self.cancel_event.is_set():reason='cancelled';break
                conditions=self.model._conditions()
                temperature=conditions.get('battery_temp_celsius')
                if type(temperature) in (int,float) and temperature>=41.5:reason='thermal_pause';break
                if progress_callback:progress_callback(index,len(cases),'Proposta piano: '+case_id)
                user='BENCHMARK_PLAN_'+uuid.uuid4().hex
                cid=core.start_conversation(user)
                def say(text):return core.process_message(user,cid,text,
                    context={'disable_answer_recall':True,'benchmark_seed':20261024+index},cancel_event=self.cancel_event)
                if self.experience_mode:
                    say('Nuovo obiettivo: '+title+' prima prova\nCriterio: '+criterion)
                    say('Risultato obiettivo: prima stesura pronta')
                    say('Risultato obiettivo sbagliato: '+(
                        'mancava uno dei tre oggetti richiesti nella lista' if case_id=='list' else
                        'il messaggio non specificava il motivo del ringraziamento'))
                    say('Risultato obiettivo: stesura corretta dopo il riscontro')
                    say('Confermo il risultato dell’obiettivo')
                    cid=core.start_conversation(user)
                say('Nuovo obiettivo: '+title+'\nCriterio: '+criterion)
                start=time.perf_counter();answer=say('Proponi un piano per questo obiettivo')
                row={'id':case_id,'objective':title,'criterion':criterion,'answer':answer.content,
                     'valid_answer':answer.is_valid,'proposal_ms':(time.perf_counter()-start)*1000,
                     'generation':answer.metadata.get('generation',{}),
                     'experience_context':answer.metadata.get('plan_experience'),
                     'proposal_saved':bool(answer.metadata.get('goal_proposal')),
                     'adopted':False,'step_requires_confirmation':None,'first_step_advanced':False,
                     'semantic_quality':'human_review_required'}
                if row['proposal_saved']:
                    adopted=say('Adotta questo piano')
                    goal=core.goal_progress.goals(user)[-1]
                    row['adopted']=bool(adopted.is_valid and goal['workflow'].get('plan'))
                    if row['adopted']:
                        say('Risultato del passo: riscontro sintetico per verificare il percorso software')
                        goal=core.goal_progress.goals(user)[-1]
                        row['step_requires_confirmation']=goal['workflow']['plan']['index']==0
                        confirmed=say('Confermo il risultato del passo')
                        goal=core.goal_progress.goals(user)[-1]
                        row['first_step_advanced']=bool(confirmed.is_valid and goal['workflow']['plan']['index']==1
                                                      and goal['status']=='active')
                results.append(row)
        except GenerationCancelled:
            reason='cancelled'
        except Exception:
            reason='error'
            raise
        finally:
            self.source._benchmark_active=False;self.source._user_active.clear()
            summary={'total':len(cases),'completed':len(results),'stop_reason':reason,
                     'state_isolated':True,'single_model_request_per_case':True,'semantic_accuracy':None,
                     'results':results}
            self.manifest={'cancelled':reason!='completed','summary':summary}
            path=Path(self.report_path);path.parent.mkdir(parents=True,exist_ok=True)
            path.with_suffix('.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
            report='# Proposte di piano con il modello reale\n\n'
            report+='Archivi sintetici isolati. Un’unica generazione per caso, senza retry. I controlli di formato e stato non misurano la qualità semantica.\n\n'
            for row in results:
                report+='## '+row['id']+'\n\n'+row['answer']+'\n\n'
                report+='Proposta salvata: '+str(row['proposal_saved'])+'; adottata: '+str(row['adopted'])+'; primo passo avanzato dopo conferma: '+str(row['first_step_advanced'])+'.\n\n'
            path.write_text(report)
            print(self.report_prefix+'_REPORT '+str(path.with_suffix('.json')),flush=True)
            compact={key:summary[key] for key in ('total','completed','stop_reason','state_isolated','single_model_request_per_case')}
            compact['results']=[{key:row[key] for key in ('id','valid_answer','proposal_ms','proposal_saved','adopted','step_requires_confirmation','first_step_advanced')} for row in results]
            print(self.report_prefix+'_SUMMARY '+json.dumps(compact,ensure_ascii=False),flush=True)

    def close(self):
        self.cancel_event.set();self.model.close()


class PlanExperienceModelRun(PlanDiagnosticRun):
    experience_mode = True
    report_prefix = 'ALLMA_PLAN_TRANSFER'
