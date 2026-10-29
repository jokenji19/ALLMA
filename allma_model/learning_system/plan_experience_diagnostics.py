"""Transfer, counterexamples and persistence on synthetic task outcomes only."""
from pathlib import Path
from unittest.mock import patch

from memory_recovery_battery import require, run_challenges
from allma_model.agency_system.goal_diagnostics import Fixture
from allma_model.agency_system.goal_progress import valid_workflow
from .plan_experience import context, assessment, find, valid

CASES=[]
ORIGIN='Lista viaggio mare'
CRITERION='documenti viaggio controllati'

def case(name,criterion):
    def wrap(fn):CASES.append(('plan_experience',name,criterion,fn));return fn
    return wrap

def say(f,title,text):return f.apply('Per l’obiettivo “'+title+'”: '+text)

def create(f,title):
    return f.apply('Nuovo obiettivo: '+title+'\nCriterio: '+CRITERION)

def failed(path):
    f=Fixture(path);create(f,ORIGIN)
    say(f,ORIGIN,'Risultato obiettivo: lista preparata')
    say(f,ORIGIN,'Risultato obiettivo sbagliato: mancava il documento richiesto per il viaggio')
    goal=f.goal();lesson=next(iter(goal['workflow']['learning']['cases'].values()))['id']
    return f,lesson

def evaluate(f,title,lesson,positive=True):
    create(f,title);say(f,title,'Risultato obiettivo: documenti controllati')
    say(f,title,'Confermo il risultato dell’obiettivo')
    return say(f,title,('Lezione utile: ' if positive else 'Lezione non utile: ')+lesson)

def row(f,lesson):return find(f.tracker.goals('u'),lesson)

@case('empty','No learned experience is invented at birth')
def empty(path):
    f=Fixture(path);require('Non ho ancora' in f.tracker.experience_view('u'),'Invented experience')

@case('unconfirmed','A reported result alone cannot train the procedural projection')
def unconfirmed(path):
    f=Fixture(path);create(f,ORIGIN);say(f,ORIGIN,'Risultato obiettivo: lista pronta')
    require('learning' not in f.goal()['workflow'],'Unconfirmed result became evidence')

@case('confirmed','Confirmation records attributed outcome, not physical truth')
def confirmed(path):
    f=Fixture(path);create(f,ORIGIN);say(f,ORIGIN,'Risultato obiettivo: lista pronta')
    say(f,ORIGIN,'Confermo il risultato dell’obiettivo')
    result=f.goal()['workflow']['learning']['cases']['goal_confirmed']
    require(result['text']=='lista pronta' and result['reviewed']['source']=='user_report','Outcome/source lost')

@case('failure','Correction preserves the reported problem as an unverified precaution')
def failure(path):
    f,lesson=failed(path);g,c=row(f,lesson)
    require('mancava' in c['text'] and assessment(f.tracker.goals('u'),g,c)['status']=='candidate','False established rule')

@case('ownership','Another user cannot read or evaluate learned cases')
def ownership(path):
    f,lesson=failed(path)
    require('Non ho ancora' in f.tracker.experience_view('other'),'User leak')
    require(f.apply('Lezione utile: '+lesson,user='other')['status']=='clarification','Foreign evaluation admitted')

@case('held_out_transfer','A new related task retrieves a prior case without repeating the original task')
def transfer(path):
    f,lesson=failed(path);create(f,'Lista viaggio montagna')
    target=f.tracker.goals('u')[-1];rows=context(f.tracker.goals('u'),target)
    require(rows and rows[0]['id']==lesson and rows[0]['status']=='candidate','Related unseen task missed experience')

@case('unrelated','A shared generic word alone cannot transfer a procedural hypothesis')
def unrelated(path):
    f,_=failed(path);f.apply('Nuovo obiettivo: Lista libri letti\nCriterio: titoli romanzi distinti')
    require(context(f.tracker.goals('u'),f.tracker.goals('u')[-1])==[],'False generalization to books')

@case('self_support','The originating task cannot support its own hypothesis')
def self_support(path):
    f,lesson=failed(path)
    require(say(f,ORIGIN,'Lezione utile: '+lesson)['status']=='clarification','Self-reinforcement admitted')

@case('needs_outcome','A new task needs a reviewed outcome before positive feedback counts')
def needs_outcome(path):
    f,lesson=failed(path);create(f,'Lista viaggio montagna')
    require(say(f,'Lista viaggio montagna','Lezione utile: '+lesson)['status']=='clarification','Premature evaluation admitted')

@case('repeated_feedback','Repeated feedback on one task never multiplies support')
def repeated(path):
    f,lesson=failed(path);evaluate(f,'Lista viaggio montagna',lesson)
    for _ in range(4):say(f,'Lista viaggio montagna','Lezione utile: '+lesson)
    g,c=row(f,lesson);require(assessment(f.tracker.goals('u'),g,c)['supporting_tasks']==1,'Repeated feedback inflated support')

@case('duplicate_task','New ids with identical task/criterion do not create independent evidence')
def duplicate(path):
    f,lesson=failed(path);evaluate(f,'Lista viaggio montagna',lesson)
    evaluate(f,'Lista viaggio montagna',lesson)
    g,c=row(f,lesson);require(assessment(f.tracker.goals('u'),g,c)['supporting_tasks']==1,'Duplicate task inflated support')

@case('supported','Three distinct user-reviewed tasks support a bounded precaution')
def supported(path):
    f,lesson=failed(path)
    for suffix in ('montagna','lavoro','campeggio'):evaluate(f,'Lista viaggio '+suffix,lesson)
    g,c=row(f,lesson);r=assessment(f.tracker.goals('u'),g,c)
    require(r['status']=='supported_by_user_reports' and r['supporting_tasks']==3,'Independent support not reflected')

@case('counterexample','An explicit contrary report contests a previously supported hypothesis')
def counterexample(path):
    f,lesson=failed(path)
    for suffix in ('montagna','lavoro','campeggio'):evaluate(f,'Lista viaggio '+suffix,lesson)
    create(f,'Lista viaggio treno');say(f,'Lista viaggio treno','Risultato obiettivo: lista pronta')
    say(f,'Lista viaggio treno','Risultato obiettivo sbagliato: il controllo precedente non era utile per questo viaggio')
    say(f,'Lista viaggio treno','Lezione non utile: '+lesson)
    g,c=row(f,lesson);r=assessment(f.tracker.goals('u'),g,c)
    require(r['status']=='contested' and r['counterexamples']==1,'Counterexample ignored')

@case('corrected_vote','A later negative evaluation replaces the earlier positive vote')
def corrected_vote(path):
    f,lesson=failed(path);evaluate(f,'Lista viaggio montagna',lesson)
    say(f,'Lista viaggio montagna','Lezione non utile: '+lesson)
    g,c=row(f,lesson);r=assessment(f.tracker.goals('u'),g,c)
    require(r['supporting_tasks']==0 and r['counterexamples']==1,'Correction counted twice')

@case('withdrawal','Explicit withdrawal prevents future retrieval')
def withdrawal(path):
    f,lesson=failed(path);say(f,ORIGIN,'Dimentica lezione: '+lesson)
    create(f,'Lista viaggio montagna')
    require(context(f.tracker.goals('u'),f.tracker.goals('u')[-1])==[],'Withdrawn hypothesis retrieved')

@case('changed_scope','A corrected original task withdraws its old contextual cases')
def changed_scope(path):
    f,lesson=failed(path);say(f,ORIGIN,'Criterio obiettivo: libri letti')
    require(row(f,lesson)[1]['withdrawn'],'Old scope survived correction')

@case('reopened_evidence','Reopening an evaluating task withdraws its earlier support')
def reopened(path):
    f,lesson=failed(path);evaluate(f,'Lista viaggio montagna',lesson)
    say(f,'Lista viaggio montagna','Riapri obiettivo')
    g,c=row(f,lesson);require(assessment(f.tracker.goals('u'),g,c)['supporting_tasks']==0,'Reopened task still votes')

@case('restart','Cases and evaluations survive state reload')
def restart(path):
    f,lesson=failed(path);evaluate(f,'Lista viaggio montagna',lesson)
    restored=Fixture(path);g,c=row(restored,lesson)
    require(assessment(restored.tracker.goals('u'),g,c)['supporting_tasks']==1,'Experience lost on restart')

@case('schema','Malformed case provenance is rejected by workflow validation')
def schema(path):
    f,lesson=failed(path);g,c=row(f,lesson);c['reviewed']['source']='model_generated'
    require(not valid_workflow(g['workflow']),'Model source accepted as user report')

@case('atomic_failure','A failed cognitive commit preserves the previous state')
def atomic_failure(path):
    f,lesson=failed(path);before=f.tracker.authority.store.path.read_bytes()
    with patch.object(f.tracker.authority.store,'put',side_effect=OSError('synthetic write failure')):
        try:say(f,ORIGIN,'Dimentica lezione: '+lesson)
        except OSError:pass
        else:raise AssertionError('Expected save failure')
    require(f.tracker.authority.store.path.read_bytes()==before,'Failed commit changed experience')

@case('core_transfer','The complete chat pipeline supplies a prior outcome to the next plan prompt')
def core_transfer(path):
    from allma_model.agency_system.goal_diagnostics import plan_core
    with plan_core(path,True) as (core,talk):
        talk('Risultato del passo: lista incompleta')
        talk('Risultato del passo sbagliato: mancava una voce richiesta')
        lesson=core.goal_progress.goals('u')[0]['workflow']['learning']['cases']['step_0_rejected']['id']
        talk('Risultato obiettivo: lista completata');talk('Confermo il risultato dell’obiettivo')
        talk('Nuovo obiettivo: Lista sintetica seconda\nCriterio: tre voci controllate')
        response=talk('Proponi un piano per questo obiettivo')
        require(lesson in response.metadata.get('plan_experience',{}).get('case_ids',[]),'Core dropped experience')
        require('mancava una voce' in core._llm.generate.call_args.kwargs['prompt'],'Model prompt omitted evidence')

@case('core_cost','Reading and confirming experiences adds no model inference')
def core_cost(path):
    from allma_model.agency_system.goal_diagnostics import plan_core
    with plan_core(path,True) as (core,talk):
        before=core._llm.generate.call_count
        talk('Risultato del passo: lista incompleta');talk('Risultato del passo sbagliato: mancava una voce')
        reply=talk('Cosa hai imparato dai piani?')
        require(reply.is_valid and core._llm.generate.call_count==before,'Experience capture invoked model')

def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==22,'Unexpected plan-learning challenges')
    return run_challenges(output,CASES,version='plan-experience-v1',scope=scope,cancel_event=cancel_event,
                          progress_callback=progress_callback,harness_path=__file__)
