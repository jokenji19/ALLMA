"""Shared, disposable checks for requirement gaps and learned retrieval routes."""
from copy import deepcopy
from memory_recovery_battery import require,run_challenges
from .plan_review import review
from .goal_diagnostics import plan_core,Fixture
from allma_model.learning_system.plan_experience import context
from allma_model.learning_system.plan_experience_diagnostics import failed,say

CASES=[]

def case(name,criterion):
    def wrap(fn):CASES.append(('plan_review',name,criterion,fn));return fn
    return wrap

def weak(n):
    def run(path):
        report=review(['Prepara i documenti.','Verifica un documento nella lista finale.'],f'{n} documenti verificati')
        require(report['status']=='needs_review' and report['findings'][0]['required']==n,'Insufficient guarantee passed')
    return run

for count in range(3,11):case('gap_'+str(count),'A weaker count admits a concrete incomplete result')(weak(count))

SAFE=[
 ['Prepara gli oggetti.','Controlla tutti gli oggetti.'],
 ['Controlla un oggetto.','Controlla gli altri due oggetti.'],
 ['Prepara gli oggetti.','Controlla un oggetto alla volta.'],
 ['Prepara gli oggetti.','Verifica ciascuno dei tre elementi.'],
 ['Controlla tutti gli oggetti.','Verifica un oggetto a campione per audit finale.'],
 ['Se ne manca uno, aggiungilo.','Verifica tutti gli oggetti.'],
 ['Non limitarti a controllare un oggetto.','Verifica tutti gli oggetti.'],
 ['Controlla il primo oggetto.','Controlla il secondo e il terzo oggetto.']]

def safe(steps):
    def run(path):require(review(steps,'tre oggetti controllati')['status']!='needs_review','Legitimate plan falsely blocked')
    return run

for index,steps in enumerate(SAFE):case('safe_'+str(index),'Legitimate partition, loop or nonbinding sample is not blocked')(safe(steps))

def unknown(criterion):
    def run(path):
        r=review(['Prepara il lavoro.','Controlla un oggetto.'],criterion)
        require(r['status']=='not_automatically_checkable' and not r['semantic_correctness_verified'],'Unsupported meaning certified')
    return run

for index,criterion in enumerate(['testo cortese con saluto','circa tre oggetti controllati','non controllare tre oggetti','tre giorni di controlli']):
    case('unknown_'+str(index),'Unsupported criteria stay explicitly unknown')(unknown(criterion))

@case('core_adoption','Actual core rejects a weak plan without granting actions or learning a fake outcome')
def core_adoption(path):
    with plan_core(path) as (core,talk):
        core._llm.generate.return_value='1. Scrivi la lista richiesta.\n2. Controlla una voce della lista finale.'
        answer=talk('Proponi un piano per questo obiettivo')
        require(answer.metadata['goal_plan_review']['status']=='needs_review','Missing host review')
        denied=talk('Adotta questo piano');wf=core.goal_progress.goals('u')[0]['workflow']
        require(not denied.is_valid and wf.get('plan') is None and 'learning' not in wf,'Bad plan adopted or learned')

@case('core_repair','The next proposal receives the host counterexample and can cover the full criterion')
def core_repair(path):
    with plan_core(path) as (core,talk):
        core._llm.generate.return_value='1. Scrivi la lista richiesta.\n2. Controlla una voce della lista finale.'
        talk('Proponi un piano per questo obiettivo');talk('Adotta questo piano')
        core._llm.generate.return_value='1. Scrivi tre voci distinte.\n2. Controlla tutte le voci.'
        answer=talk('Proponi un piano per questo obiettivo')
        require('previous_plan_gap' in core._llm.generate.call_args.kwargs['prompt'],'Counterexample lost')
        require(answer.metadata['goal_plan_review']['status']=='no_known_gap' and talk('Adotta questo piano').is_valid,'Covered plan blocked')

def bridge(path):
    f,lesson=failed(path);title='Passaporto prima della partenza'
    f.apply('Nuovo obiettivo: '+title+'\nCriterio: passaporto e biglietti validi')
    say(f,title,'Risultato obiettivo: passaporto e biglietti controllati');say(f,title,'Confermo il risultato dell’obiettivo')
    target={'id':'unseen','user_id':'u','objective':'Passaporto per la partenza invernale','workflow':{'criterion':'passaporto e biglietti validi'}}
    require(not any(r['id']==lesson for r in context(f.tracker.goals('u'),target)),'Untaught bridge invented')
    say(f,title,'Lezione utile: '+lesson)
    return f,lesson,title,target

@case('learned_bridge','Confirmed use links different vocabularies without a new model or hard-coded synonym')
def learned_bridge(path):
    f,lesson,title,target=bridge(path)
    rows=context(f.tracker.goals('u'),target)
    require(any(r['id']==lesson and r['retrieval']['kind']=='confirmed_task_bridge' for r in rows),'Learned route missed')

@case('bridge_withdrawal','A corrected evaluation removes the learned route')
def bridge_withdrawal(path):
    f,lesson,title,target=bridge(path);say(f,title,'Lezione non utile: '+lesson)
    require(not any(r['id']==lesson for r in context(f.tracker.goals('u'),target)),'Withdrawn route still used')

def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==24,'Unexpected review battery')
    return run_challenges(output,CASES,version='plan-review-v1',scope=scope,cancel_event=cancel_event,
                          progress_callback=progress_callback,harness_path=__file__)
