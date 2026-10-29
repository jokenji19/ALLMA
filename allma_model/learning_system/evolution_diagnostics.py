"""New held-out retrieval, transfer, curiosity and explanation challenges."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
import sqlite3
from memory_recovery_battery import require, run_challenges
from .learning_diagnostics import create, unit
from .learning_views import PagedHistory, LearningMap
from allma_model.core.curiosity_drive import CuriosityDrive

CASES=[]
def case(group,name,criterion):
    def register(fn):CASES.append((group,name,criterion,fn));return fn
    return register


def large(path, count=384):
    learner=create(path/'learning.db')
    learner.add_learning_unit(unit('archive','Old navigation report'))
    learner.knowledge_base['archive']=[unit('archive','Historical payload '+str(i)+' '+'x'*512) for i in range(count)]
    learner.save_state()
    return create(path/'learning.db')


@case('paging','cold_start','Opening learning validates but does not decode the whole history into retained RAM')
def cold_start(path):
    learner=large(path)
    require(isinstance(learner.knowledge_base,LearningMap) and not learner.knowledge_base.cache,'Payloads eagerly cached')
    sequence=learner.knowledge_base['archive']
    require(isinstance(sequence,PagedHistory) and not sequence.cache and len(sequence)==384,'History eagerly materialised')


@case('paging','old_and_latest','Old and latest records remain accessible with at most two decoded pages')
def old_and_latest(path):
    sequence=large(path).knowledge_base['archive']
    for i in range(0,len(sequence),17):require(('payload '+str(i)+' ') in sequence[i].content,'Wrong history page')
    require('payload 0 ' in sequence[0].content and 'payload 383 ' in sequence[-1].content,'Old/latest record lost')
    require(len(sequence.cache)<=2,'Unbounded page cache')


@case('paging','append_without_prefix','Normal learning appends without reading any historical page')
def append_without_prefix(path):
    learner=large(path)
    with patch.object(PagedHistory,'_page',side_effect=AssertionError('Historical payload read during append')):
        learner.add_learning_unit(unit('archive','new'))
    restored=create(path/'learning.db')
    require(len(restored.knowledge_base['archive'])==385 and restored.knowledge_base['archive'][-1].content=='new','Delta missing')


@case('paging','manual_edits','Explicitly saved manual historical edits survive page eviction')
def manual_edits(path):
    learner=large(path);history=learner.knowledge_base['archive']
    history[0].metadata['corrected']='manual synthetic edit'
    for i in range(0,len(history),32):history[i]
    learner.save_state()
    require(create(path/'learning.db').knowledge_base['archive'][0].metadata.get('corrected')=='manual synthetic edit','Edited historical page evicted')


@case('paging','cold_corruption','Corruption outside the first page blocks publishing any partial archive')
def cold_corruption(path):
    large(path)
    with sqlite3.connect(path/'learning.db') as db:
        db.execute("UPDATE learning_lists SET data='{}' WHERE kind='unit' AND position=350")
    from .incremental_learning import IncrementalLearner
    learner=IncrementalLearner(str(path/'learning.db'))
    require(learner.load_error is not None and not learner.knowledge_base,'Cold corrupt page missed')


@case('retrieval','owner_latest','Newer foreign declarations cannot suppress the latest declaration for the querying owner')
def owner_latest(path):
    learner=create(path/'learning.db');learner.add_learning_unit(unit('navigation','My compass points north'))
    other=unit('navigation','Foreign private compass');other.metadata={'user_id':'other'};other.source='user_other'
    learner.add_learning_unit(other)
    rows=learner.find_related_knowledge('compass north',user_id='u')
    require(rows and rows[0].content=='My compass points north','Foreign topic header replaced owner evidence')
    require(not learner.find_related_knowledge('compass',user_id='absent'),'Unattributed evidence leaked')


@case('retrieval','latest_correction','Old content is not combined with a newer correction to support a false match')
def latest_correction(path):
    learner=create(path/'learning.db');learner.add_learning_unit(unit('location','old address blue house'))
    learner.add_learning_unit(unit('location','current address green station'))
    rows=learner.find_related_knowledge('green station',user_id='u')
    require(rows and rows[0].content=='current address green station','Correction not retrieved')
    require(not learner.find_related_knowledge('blue house',user_id='u'),'Superseded declaration treated as current')


@case('retrieval','bounded_search','A search cannot build a second full TF-IDF archive in memory')
def bounded_search(path):
    learner=large(path)
    with patch.object(learner,'_ensure_index',side_effect=AssertionError('Global index rebuilt')):
        learner.find_related_knowledge('archive payload',user_id='u')
    require(not learner.topic_vectors,'Duplicate full-history vector index created')


def message(role,text,**metadata):
    return SimpleNamespace(role=role,content=text,metadata=metadata,user_id='u',conversation_id='c')


@case('curiosity','empty','No history or user request produces no fabricated curiosity')
def curiosity_empty(path):
    result=CuriosityDrive().process('Buongiorno',{'user_id':'u','conversation_id':'c'})
    require(not result['system_instruction'],'Routine personal question injected')


@case('curiosity','strict_format','A format constraint suppresses exploratory additions')
def strict_format(path):
    result=CuriosityDrive().process('Spiegami perché: rispondi solo con un numero',{'intent':'question'})
    require(not result['system_instruction'],'Curiosity violated exact output contract')


@case('curiosity','open_thread','A relevant unanswered question supplies a documented focus')
def open_thread(path):
    history=[message('user','Come posso riparare una bussola rotta?'),message('assistant','Risposta interrotta',is_valid=False)]
    result=CuriosityDrive().process('La bussola rotta ha ancora l’ago mobile',{'user_id':'u','conversation_id':'c','dialogue_history':history})
    require(result['metadata']['focus']['kind']=='open_question','Unresolved relevant question lost')


@case('curiosity','frequency','An admitted focus cannot be repeated each turn or after a valid resolution')
def frequency(path):
    history=[message('user','Come riparare una bussola rotta?'),message('assistant','Interrotta',is_valid=False)]
    context={'user_id':'u','conversation_id':'c','dialogue_history':history}
    drive=CuriosityDrive();focus=drive.process('La bussola rotta è sul tavolo',context)['metadata']['focus']
    history.append(message('assistant','Controlla l’ago',is_valid=True,curiosity_focus=focus))
    require(not drive.process('La bussola rotta è ancora qui',context)['metadata']['focus'],'Repeated a resolved focus')


@case('curiosity','decline','Topic closure suppresses follow-ups, while a new explicit explanation remains possible')
def decline(path):
    history=[message('user','Non farmi altre domande')]
    context={'dialogue_history':history}
    drive=CuriosityDrive()
    require(not drive.process('Oggi ho letto molto',context)['system_instruction'],'Opt-out ignored')
    require(drive.process('Spiegami perché le foglie cambiano colore',context)['metadata']['focus']['kind']=='requested_exploration','Explicit question blocked by old opt-out')


@case('curiosity','ownership','An unresolved question from a different owner cannot create a focus')
def curiosity_owner(path):
    history=[message('user','Come riparare una bussola rotta?'),message('assistant','Interrotta',is_valid=False)]
    require(not CuriosityDrive().process('La bussola rotta è qui',{'user_id':'other','dialogue_history':history})['metadata']['focus'],'Foreign open question leaked')


@case('explanation','source','Calculation, user memory and model output remain distinguishable')
def explanation(path):
    from allma_model.core.learning_insights import response_origin
    require(response_origin({'source':'verified_calculation','knowledge_verified':True})['kind']=='computation','Calculation source missing')
    require(response_origin({'source':'user_declaration'})['kind']=='memory','Personal source missing')
    require(response_origin({'source':'model_generated'})['kind']=='model','Model mislabeled as verified')
    require(response_origin({'source':'verified_calculation','knowledge_verified':False})['kind']!='computation','Unverified result labeled verified')
    require(response_origin({'source':'model_generated'},False)['kind']=='incomplete','Invalid result labeled validated')


@case('transfer','new_formulation','Learned counting criteria transfer to new words and a different request form, still requiring consent')
def new_formulation(path):
    from .tool_learning_diagnostics import cores, teach, TASKS
    with cores(path) as create_core:
        core=create_core();cid=core.start_conversation('u')
        for task in TASKS:teach(core,cid,task)
        request='Conta le occorrenze di "tat" in "tatatat". Rispondi solo con un numero.'
        proposal=core.process_message('u',cid,request)
        require(proposal.metadata['source']=='text_count_clarification' and proposal.metadata['evidence'][0].get('suggested_overlap') is True,'New formulation lost learned criterion')
        result=core.process_message('u',cid,'sì')
        require(result.content=='3' and result.metadata['generation']['llm_used'] is False,'New problem was not computed after consent')
        core.process_message('u',cid,'Risposta sbagliata')
        require(core.meta_learner.tool_learning.view('u')['confirmed_tasks']==3,'A new task correction mutated unrelated confirmations')


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    from .tool_learning_diagnostics import CASES as tool_cases
    from .plan_experience_diagnostics import CASES as plan_cases
    challenges=[(group,group+'_'+name,criterion,fn) for group,name,criterion,fn in CASES]
    challenges += [('tool_transfer','tool_'+name,criterion,fn) for name,criterion,fn in tool_cases]
    challenges += [(group,'plan_'+name,criterion,fn) for group,name,criterion,fn in plan_cases]
    return run_challenges(output,challenges,version='learning-evolution-v1',scope=scope,
        cancel_event=cancel_event,progress_callback=progress_callback,harness_path=__file__)
