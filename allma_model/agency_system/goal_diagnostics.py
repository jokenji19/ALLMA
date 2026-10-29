"""Disposable task-continuity challenges, shared by desktop and Android."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import Mock,patch
import hashlib

from memory_recovery_battery import require,run_challenges
from .action_authority import ActionAuthority
from .goal_progress import GoalProgress
from allma_model.utils.cognitive_state import CognitiveStateStore
from allma_model.utils.goal_dialogue import command
from allma_model.utils.persistence import StateRecoveryRequired

CASES=[]
CREATE='Nuovo obiettivo: Lista sintetica\nCriterio: tre voci controllate\nProssimo passo: controllare la prima voce'
def case(name,criterion):
    def wrap(fn):CASES.append(('goal_continuity',name,criterion,fn));return fn
    return wrap

class Fixture:
    def __init__(self,path):
        self.path=Path(path);self.tracker=GoalProgress(ActionAuthority(CognitiveStateStore(str(self.path/'core.db'))))
        self.seq=self.tracker.delivery_checkpoint
    def apply(self,text,user='u'):
        parsed=command(text);require(parsed is not None,'Fixture command not recognized')
        control,reason=self.tracker.prepare(user,parsed)
        if control is None:return {'status':'clarification','reason':reason}
        self.seq+=1
        ref={'event':'synthetic_'+str(self.seq),'conversation':'synthetic','timestamp':'2026-10-24T12:00:00',
             'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'source':'user_report'}
        return self.tracker.apply(user,control,ref,self.seq)
    def goal(self):return self.tracker.goals('u')[0]

def started(path):
    f=Fixture(path);f.apply(CREATE);return f

@case('newborn','No invented initial task or initiative')
def newborn(path):
    f=Fixture(path);require(f.tracker.goals('u')==[] and f.tracker.initiative('u') is None,'Invented task')

@case('create','An explicit task has attributed criteria, next step and no external grant')
def create(path):
    f=started(path);g=f.goal();require(g['allowed_actions']=={'review_goal':'read'} and g['workflow']['criterion']=='tre voci controllate','Task/grants incorrect')

@case('restart','Progress survives a fresh state reader')
def restart(path):
    f=started(path);f.apply('Progresso obiettivo: prima voce controllata');r=Fixture(path)
    require(r.goal()['workflow']['progress']=='prima voce controllata','Progress lost on restart')

@case('next_step','The next step can change independently')
def next_step(path):
    f=started(path);f.apply('Prossimo passo obiettivo: controllare la seconda voce')
    require(f.goal()['workflow']['next_step']=='controllare la seconda voce','Next step lost')

@case('criterion','A changed criterion invalidates an earlier result')
def criterion(path):
    f=started(path);f.apply('Risultato obiettivo: elenco pronto');f.apply('Criterio obiettivo: quattro voci')
    require(f.goal()['workflow']['result'] is None,'Old result survived criterion change')

@case('result','A user report is awaiting verification, not completed')
def result(path):
    f=started(path);f.apply('Risultato obiettivo: elenco pronto');g=f.goal()
    require(g['status']=='active' and g['workflow']['phase']=='awaiting_verification' and g['workflow']['result']['source']=='user_report','Report became verified completion')

@case('confirmation','Explicit confirmation has user provenance, not external verification')
def confirmation(path):
    f=started(path);f.apply('Risultato obiettivo: elenco pronto');f.apply('Confermo il risultato dell’obiettivo')
    require(f.goal()['status']=='completed' and f.goal()['workflow']['verification']=='confirmed_by_user','Confirmation not attributed')

@case('rejection','A rejected result is invalidated and counted')
def rejection(path):
    f=started(path);f.apply('Risultato obiettivo: elenco pronto');f.apply('Risultato obiettivo sbagliato: mancava una voce')
    require(f.goal()['workflow']['result'] is None and f.goal()['workflow']['outcomes']['rejected']==1,'Rejected result retained')

@case('missing_result','Confirmation needs a current result')
def missing_result(path):
    f=started(path);require(f.apply('Confermo il risultato dell’obiettivo')['status']=='clarification' and f.goal()['status']=='active','False completion')

@case('ambiguity','Multiple tasks require selection')
def ambiguity(path):
    f=started(path);f.apply('Nuovo obiettivo: Altra lista')
    require(f.apply('Progresso obiettivo: ambiguo')['status']=='clarification','Ambiguous update admitted')

@case('ownership','Tasks and initiative are scoped to their owner')
def ownership(path):
    f=started(path);require(f.tracker.goals('other')==[] and f.tracker.initiative('other') is None,'Cross-user task leak')

@case('consent','Initiative needs task opt-in and is suppressed by pause')
def consent(path):
    f=started(path);require(f.tracker.initiative('u') is None,'Implicit opt-in')
    f.apply('Puoi propormi il prossimo passo dell’obiettivo');reference=f.tracker.initiative('u');require(reference,'Consent ignored')
    f.apply('Sospendi obiettivo');require(not f.tracker.current_reference('u',reference) and f.tracker.initiative('u') is None,'Paused/stale proposal retained')

@case('revocation','Revocation prevents subsequent updates')
def revocation(path):
    f=started(path);f.apply('Annulla obiettivo');require(f.apply('Progresso obiettivo: tardivo')['status']=='clarification','Revoked task changed')

@case('write_failure','A failed task commit does not leak a partial state')
def write_failure(path):
    f=started(path);before=f.goal()
    with patch.object(f.tracker.authority.store,'put',side_effect=OSError('synthetic write failure')):
        try:f.apply('Progresso obiettivo: non salvato')
        except OSError:pass
        else:raise AssertionError('Failed commit acknowledged')
    require(f.goal()==before,'Partial failed state retained')

@case('invalid_archive','Invalid cognitive bytes cannot become an empty task list')
def invalid_archive(path):
    f=started(path);p=f.tracker.authority.store.path;p.write_text('{broken')
    try:f.tracker.goals('u')
    except StateRecoveryRequired:pass
    else:raise AssertionError('Invalid archive hidden')
    require(p.read_text()=='{broken','Invalid original overwritten')

@case('quoted_command','Story text and ordinary requests never silently create a task')
def quoted_command(path):
    require(command('Nel racconto: Nuovo obiettivo: altro') is None and command('Vorrei preparare una lista') is None,'Implicit goal admission')


def new_core(path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
    core._ensure_mobile_llm=lambda:None;core._llm=Mock();core._llm.generate.side_effect=AssertionError('No model for task continuity')
    return core

@case('core_restart','Actual core resumes and completes a task after process-state reconstruction')
def core_restart(path):
    core=new_core(path)
    try:
        cid=core.start_conversation('u');require(core.process_message('u',cid,CREATE).is_valid,'Create failed')
        require(core.process_message('u',cid,'Progresso obiettivo: prima voce controllata').is_valid,'Progress failed')
    finally:core.close()
    core=new_core(path)
    try:
        cid=core.start_conversation('u');reply=core.process_message('u',cid,'Riprendiamo l’obiettivo')
        require('prima voce controllata' in reply.content,'New core lost progress')
        core.process_message('u',cid,'Risultato obiettivo: tre voci controllate')
        reply=core.process_message('u',cid,'Confermo il risultato dell’obiettivo')
        require(reply.is_valid and core.goal_progress.goals('u')[0]['status']=='completed','New core could not complete task')
    finally:core.close()

@case('journal_recovery','A crash window after task commit does not create it twice')
def journal_recovery(path):
    core=new_core(path)
    try:
        with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic journal acknowledgement failure')):
            core.process_message('u',core.start_conversation('u'),CREATE)
        key=core.goal_progress.goals('u')[0]['id']
        require(core.delivery_updates.recover(synchronize=True)['status']=='completed','Recovery did not complete')
        require(len(core.goal_progress.goals('u'))==1 and core.goal_progress.goals('u')[0]['id']==key,'Duplicate task after recovery')
    finally:core.close()


PLAN='Proposta di piano\n1. Scrivi tre voci distinte nella lista.\n2. Controlla ogni voce e correggi gli errori.'

@contextmanager
def plan_core(path,adopt=False):
    core=new_core(path)
    try:
        cid=core.start_conversation('u')
        def say(text):return core.process_message('u',cid,text)
        say(CREATE)
        core._llm.generate.side_effect=None;core._llm.generate.return_value=PLAN
        core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
        core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
        require(say('Proponi un piano per questo obiettivo').metadata.get('goal_proposal'),'No saved model proposal')
        if adopt:require(say('Adotta questo piano').is_valid,'Adoption failed')
        yield core,say
    finally:core.close()


@case('proposal_only','A generated plan never silently changes the current task')
def proposal_only(path):
    with plan_core(path) as (core,say):
        require(core.goal_progress.goals('u')[0]['workflow'].get('plan') is None,'Proposal auto-adopted')


@case('plan_adoption','Explicit adoption stores pending steps with user provenance')
def plan_adoption(path):
    with plan_core(path,True) as (core,say):
        plan=core.goal_progress.goals('u')[0]['workflow']['plan']
        require(all(s['status']=='pending' for s in plan['steps']) and plan['adopted_by']['source']=='user_report','False execution')


@case('step_confirmation','A step cannot advance without a reported result and confirmation')
def step_confirmation(path):
    with plan_core(path,True) as (core,say):
        say('Confermo il risultato del passo')
        require(core.goal_progress.goals('u')[0]['workflow']['plan']['index']==0,'Step skipped')
        say('Risultato del passo: tre voci scritte');say('Confermo il risultato del passo')
        require(core.goal_progress.goals('u')[0]['workflow']['plan']['index']==1,'Confirmed result did not advance')


@case('step_rejection','A failed result keeps the current step open')
def step_rejection(path):
    with plan_core(path,True) as (core,say):
        say('Risultato del passo: lista incompleta');say('Risultato del passo sbagliato: manca una voce')
        plan=core.goal_progress.goals('u')[0]['workflow']['plan']
        require(plan['index']==0 and plan['steps'][0]['result'] is None,'Rejected result counted as completion')


@case('plan_revision','Task correction invalidates the admitted plan')
def plan_revision(path):
    with plan_core(path,True) as (core,say):
        say('Criterio obiettivo: quattro voci')
        wf=core.goal_progress.goals('u')[0]['workflow']
        require(wf['plan']['status']=='needs_review' and not wf['next_step'],'Stale plan remained operational')


@case('old_proposal','A newer unstructured answer does not fall back to an older plan')
def old_proposal(path):
    with plan_core(path) as (core,say):
        core._llm.generate.return_value='Mi servono altre informazioni.'
        say('Proponi un piano per questo obiettivo');say('Adotta questo piano')
        require(core.goal_progress.goals('u')[0]['workflow'].get('plan') is None,'Older proposal silently selected')


@case('plan_replay','Journal retry cannot advance a step twice')
def plan_replay(path):
    with plan_core(path,True) as (core,say):
        say('Risultato del passo: tre voci')
        with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic ack failure')):
            say('Confermo il risultato del passo')
        core.delivery_updates.recover(synchronize=True)
        require(core.goal_progress.goals('u')[0]['workflow']['plan']['index']==1,'Step advanced twice')


@case('plan_reload','An adopted plan and its pending result survive state reconstruction')
def plan_reload(path):
    with plan_core(path,True) as (core,say):
        say('Risultato del passo: prima stesura')
        fresh=GoalProgress(ActionAuthority(CognitiveStateStore(core.db_path)))
        require(fresh.goals('u')[0]['workflow']['plan']['steps'][0]['status']=='awaiting_confirmation','Step result lost on reload')


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==26,'Unexpected task-continuity plan')
    return run_challenges(output,CASES,version='goal-continuity-v2',scope=scope,cancel_event=cancel_event,
                          progress_callback=progress_callback,harness_path=__file__)
