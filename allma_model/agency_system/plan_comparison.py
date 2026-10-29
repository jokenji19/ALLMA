"""Paired prompt ablation on isolated goals; host review is active in both arms."""
from pathlib import Path
import json
import time
import uuid
from .plan_diagnostics import PlanDiagnosticRun
from allma_model.utils.generation_control import GenerationCancelled


class PlanReviewComparisonRun(PlanDiagnosticRun):
    report_prefix='ALLMA_PLAN_COMPARISON'

    def run_tests(self,progress_callback=None):
        core=self.model.brain;rows=[];reason='completed'
        pairs=[('objects','Preparare una lista di tre oggetti','tre oggetti distinti controllati'),
               ('documents','Preparare una lista di cinque documenti','cinque documenti controllati')]
        with self.source._lock:
            if self.source._user_active.is_set() or getattr(self.source,'_benchmark_active',False):raise RuntimeError('ALLMA occupata')
            self.source._benchmark_active=True;self.source._user_active.set()
        core._plan_review_history=False
        try:
            for pair_index,(case_id,title,criterion) in enumerate(pairs):
                user='BENCHMARK_PLAN_PAIR_'+uuid.uuid4().hex
                core.process_message(user,core.start_conversation(user),'Nuovo obiettivo: '+title+'\nCriterio: '+criterion,cancel_event=self.cancel_event)
                variants=('baseline','requirements') if pair_index==0 else ('requirements','baseline')
                for variant in variants:
                    if self.cancel_event.is_set():reason='cancelled';break
                    conditions=self.model._conditions();temperature=conditions.get('battery_temp_celsius')
                    if type(temperature) in (int,float) and temperature>=41.5:reason='thermal_pause';break
                    if progress_callback:progress_callback(len(rows),4,case_id+' · '+variant)
                    core._plan_requirement_prompt=variant=='requirements'
                    start=time.perf_counter()
                    response=core.process_message(user,core.start_conversation(user),'Proponi un piano per questo obiettivo',
                        context={'disable_answer_recall':True,'benchmark_seed':20261025+pair_index,
                                 'benchmark_max_tokens':192,'benchmark_thought_budget':64},cancel_event=self.cancel_event)
                    report=response.metadata.get('goal_plan_review')
                    goal=core.goal_progress.goals(user)[0]
                    rows.append({'pair':case_id,'variant':variant,'objective':title,'criterion':criterion,
                        'goal_id':goal['id'],'goal_revision':goal['workflow']['revision'],
                        'seed':20261025+pair_index,'conditions':conditions,'answer':response.content,
                        'valid_answer':response.is_valid,'proposal_saved':bool(response.metadata.get('goal_proposal')),
                        'review':report,'local_verdict':report['status'] if report else 'unstructured_or_invalid',
                        'elapsed_ms':(time.perf_counter()-start)*1000,
                        'generation':response.metadata.get('generation',{}),'semantic_quality':'human_review_required'})
                if reason!='completed':break
        except GenerationCancelled:reason='cancelled'
        except Exception:
            reason='error';raise
        finally:
            core._plan_requirement_prompt=True;core._plan_review_history=True
            self.source._benchmark_active=False;self.source._user_active.clear()
            budget_matches=[]
            for pair in pairs:
                members=[row for row in rows if row['pair']==pair[0]]
                fields=('max_tokens','reasoning_budget','answer_budget','temperature','top_p')
                if len(members)!=2 or any(any(k not in row['generation'] for k in fields) for row in members):
                    budget_matches.append(None)
                else:budget_matches.append(all(members[0]['generation'][k]==members[1]['generation'][k] for k in fields))
            summary={'total':4,'completed':len(rows),'stop_reason':reason,'state_isolated':True,
                'single_model_request_per_case':True,'same_goal_and_seed_per_pair':True,'budget_matches':budget_matches,
                'alternating_order':True,'host_review_in_both_arms':True,'semantic_accuracy':None,'results':rows}
            self.manifest={'cancelled':reason!='completed','summary':summary}
            path=Path(self.report_path);path.parent.mkdir(parents=True,exist_ok=True)
            path.with_suffix('.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
            report='# Piani: confronto istruzioni sui requisiti\n\n'
            report+='Stesso obiettivo, seed e budget per coppia, chat distinte e ordine alternato. Il controllo locale è attivo in entrambe le varianti. Nessun retry. Non misura la correttezza semantica generale.\n\n'
            for row in rows:report+='## '+row['pair']+' · '+row['variant']+'\n\n'+row['answer']+'\n\nEsito locale: '+row['local_verdict']+'\n\n'
            path.write_text(report)
            print(self.report_prefix+'_REPORT '+str(path.with_suffix('.json')),flush=True)
            compact={k:summary[k] for k in ('total','completed','stop_reason','state_isolated','single_model_request_per_case')}
            compact['results']=[{k:row[k] for k in ('pair','variant','elapsed_ms','local_verdict','valid_answer')} for row in rows]
            print(self.report_prefix+'_SUMMARY '+json.dumps(compact,ensure_ascii=False),flush=True)
