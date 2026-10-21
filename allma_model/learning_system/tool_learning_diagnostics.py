"""Disposable before/after procedural challenges, runnable on Android without GGUF."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch

TASKS = [('ana','banana'), ('aa','aaaa'), ('aba','ababa')]
NOVEL = 'Quante volte compare "issi" in "mississippi"? Rispondi solo con un numero.'
CASES = []


def case(name, criterion):
    def register(fn):
        CASES.append((name,criterion,fn));return fn
    return register


def require(value, message):
    if not value:raise AssertionError(message)


@contextmanager
def cores(path):
    from allma_model.core.allma_core import ALLMACore
    instances=[]
    def create():
        core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
        core._ensure_mobile_llm=lambda:None
        core._llm=Mock()
        core._llm.generate.side_effect=AssertionError('This challenge must not use model inference')
        instances.append(core)
        return core
    try:yield create
    finally:
        for core in instances:core.close()


def view(core,user='u'):
    return core.meta_learner.tool_learning.view(user)


def teach(core,cid,task,*,confirm=True):
    needle,text=task
    question=f'Quante volte compare "{needle}" in "{text}"? Rispondi solo con un numero.'
    require(core.process_message('u',cid,question).metadata['source']=='text_count_clarification','Question did not request its matching criterion')
    answer=core.process_message('u',cid,'Con le sovrapposizioni')
    require(answer.metadata['knowledge_verified'] is True,'Chosen criterion was not verified')
    if confirm:
        reply=core.process_message('u',cid,'Risposta corretta')
        require(reply.is_valid and reply.metadata['tool_learning']['status'] in ('feedback_recorded','duplicate_feedback'),'Explicit feedback was not saved')


@case('newborn', 'No experience produces no learned suggestion')
def newborn(path):
    with cores(path) as create:
        core=create();require(view(core)['confirmed_tasks']==0 and view(core)['suggested_overlap'] is None,'Invented an initial preference')


@case('one_episode', 'One confirmed choice remains insufficient')
def one(path):
    with cores(path) as create:
        core=create();teach(core,core.start_conversation('u'),TASKS[0])
        require(view(core)['confirmed_tasks']==1 and view(core)['suggested_overlap'] is None,'One choice became a stable default')


@case('no_approval', 'Verified computation is distinct from user approval')
def no_approval(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task,confirm=False)
        require(view(core)['confirmed_tasks']==0,'Execution was counted as approval')


@case('transfer', 'Three independent approved choices support a proposal on unseen text; consent still required')
def transfer(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        before=core.process_message('u',cid,NOVEL)
        require('suggested_overlap' not in before.metadata['evidence'][0],'Preference existed before experience')
        for task in TASKS:teach(core,cid,task)
        after=core.process_message('u',cid,NOVEL)
        require(after.metadata['source']=='text_count_clarification' and after.metadata['evidence'][0].get('suggested_overlap') is True,'Learned proposal was absent or auto-executed')
        final=core.process_message('u',cid,'sì')
        require(final.content=='2' and final.metadata['generation']['llm_used'] is False,'Unseen task was not computed correctly')
        return {'before_proposal':False,'after_proposal':True,'confirmed_distinct_tasks':3,'novel_result':'2','model_used':False}


@case('duplicate_feedback', 'Repeated approval of the same outcome is idempotent')
def duplicate(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u');teach(core,cid,TASKS[0])
        for _ in range(4):core.process_message('u',cid,'Risposta corretta')
        require(view(core)['confirmed_tasks']==1,'Repeated praise increased experience count')


@case('same_operands', 'Repeating one task does not manufacture independent tasks')
def same_operands(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for _ in range(4):teach(core,cid,TASKS[0])
        require(view(core)['confirmed_tasks']==1 and view(core)['suggested_overlap'] is None,'Repeated operands manufactured confidence')


@case('correction', 'A correction withdraws its previous contribution')
def correction(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task)
        require(view(core)['suggested_overlap'] is True,'Training did not establish a proposal')
        core.process_message('u',cid,'Risposta sbagliata')
        require(view(core)['confirmed_tasks']==2 and view(core)['suggested_overlap'] is None,'Correction did not withdraw confidence')


@case('isolation', 'A user profile cannot teach another user')
def isolation(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task)
        other=core.process_message('other',core.start_conversation('other'),NOVEL)
        require('suggested_overlap' not in other.metadata['evidence'][0] and view(core,'other')['confirmed_tasks']==0,'Foreign strategy leaked')


@case('restart', 'Learned strategy survives core restart and new conversation')
def restart(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task)
        core.close();restored=create()
        require(view(restored)['suggested_overlap'] is True,'Learned strategy was lost on restart')
        result=restored.process_message('u',restored.start_conversation('u'),NOVEL)
        require(result.metadata['evidence'][0].get('suggested_overlap') is True,'Restored strategy was not used')


@case('reset', 'Explicit reset removes learned policy and invalidates stale receipts')
def reset(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u');teach(core,cid,TASKS[0])
        history=core.conversational_memory.get_conversation_history(cid)
        descriptor=next(m.metadata['tool_experience'] for m in reversed(history) if m.role=='assistant' and m.metadata.get('tool_experience'))
        require(core.process_message('u',cid,'Dimentica le strategie di conteggio apprese').is_valid,'Reset failed')
        require(view(core)['confirmed_tasks']==0,'Reset kept previous votes')
        require(core.meta_learner.tool_learning.feedback('u',descriptor,True)['status']=='stale','Old receipt resurrected a reset profile')


@case('write_failure', 'Learning failure does not destroy a verified result or fake a saved acknowledgement')
def write_failure(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        with patch.object(core.meta_learner.tool_learning.store,'transact_state',side_effect=OSError('synthetic disk failure')):
            answer=core.process_message('u',cid,'Quante lettere contiene JSON? Rispondi solo con un numero.')
            require(answer.content=='4' and answer.is_valid,'Learning failure destroyed the exact answer')
            feedback=core.process_message('u',cid,'Risposta corretta')
            require(not feedback.is_valid,'Unsaved feedback was acknowledged as saved')


@case('no_self_reward', 'A learned suggestion and its acceptance cannot reinforce themselves')
def no_self_reward(path):
    with cores(path) as create:
        core=create();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task)
        core.process_message('u',cid,NOVEL);core.process_message('u',cid,'sì');core.process_message('u',cid,'Risposta corretta')
        require(view(core)['confirmed_tasks']==3,'Suggested strategy rewarded itself')


def run_battery(output, *, scope='Synthetic procedural learning; no GGUF inference', cancel_event=None, progress_callback=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    plan=[{'name':name,'criterion':criterion} for name,criterion,_ in CASES]
    (output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    start=time.perf_counter();rows=[]
    for index,(name,criterion,fn) in enumerate(CASES):
        if cancel_event is not None and cancel_event.is_set():break
        if progress_callback:progress_callback(index+1,len(CASES),'Apprendimento strumenti: '+name)
        row={'name':name,'criterion':criterion,'passed':False,'error':None}
        try:
            with tempfile.TemporaryDirectory(prefix='tool-learning-',dir=str(output)) as temporary:
                row['observations']=fn(Path(temporary))
            row['passed']=True
        except Exception as error:
            row['error']={'type':type(error).__name__,'detail':str(error)[:500]}
        rows.append(row)
        (output/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    passed=sum(row['passed'] for row in rows);complete=len(rows)==len(CASES)
    summary={'scope':scope,'passed':passed,'total':len(CASES),'complete':complete,
             'percent':100*passed/len(CASES) if complete else None,
             'groups':{'procedural_learning':{'passed':passed,'total':len(CASES)}},
             'failures':[r for r in rows if not r['passed']], 'seconds':time.perf_counter()-start,
             'statistical_generalization':'Fixed synthetic challenges, not a general intelligence or reliability score.'}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary
