"""Fixed synthetic challenges for sensitivity, attribution and support learning.

The generation stub is deliberately not an assessment of actual GGUF empathy.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch

from .emotion_analysis import analyze
from .relational_perception import plan, boundary_reply
from allma_model.core.personality_coalescence import CoalescenceProcessor

CASES=[]
NOW=datetime(2026,10,21,12,tzinfo=timezone.utc)


def case(name, criterion):
    def register(fn):
        CASES.append((name,criterion,fn));return fn
    return register


def require(value, message):
    if not value:raise AssertionError(message)


def turn(text, **extra):
    return dict(content=text, role='user', user_id='u', conversation_id='c',
                timestamp=NOW-timedelta(minutes=1), metadata={}) | extra


def perceive(text, history=()):
    return plan(text,analyze(text),history,'u','c',now=NOW)


@contextmanager
def core_at(path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
    core._ensure_mobile_llm=lambda:None
    core._llm=Mock()
    core._llm.generate.return_value='Ti ascolto. Puoi raccontare quello che desideri.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    try:yield core
    finally:core.close()


@case('no_diagnosis','No emotional label or past story is invented without evidence')
def no_diagnosis(path):
    result=perceive('Ho fallito ancora.')
    require(not result['current_labels'] and result['interpretation_uncertain'],'Uncertain event became an emotional diagnosis')
    require('senza inventare' in result['instruction'],'Repetition became an invented biography')


@case('correction','Self correction supersedes a previous emotional interpretation')
def correction(path):
    result=perceive('Non sono triste, sono stanco.',[turn('Sono triste.')])
    require(result['relation']=='self_correction' and 'sadness' in result['denied_labels']
            and 'sadness' not in result['prior_labels'],'Rejected emotion survived the correction')


@case('ambiguity','A short ambiguous phrase leaves room for literal intent and disengagement')
def ambiguity(path):
    result=perceive('Lascia perdere')
    require(result['interpretation_uncertain'] and not result['current_labels'],'Guessed sadness from an ambiguous phrase')
    require(boundary_reply('Lascia perdere') is None,'Consumed an ambiguous task')
    require(boundary_reply('Non voglio parlarne. Spiega il sole.') is None,'Consumed a mixed request')


@case('mixed_and_other','Mixed self emotions remain distinct from another person’s emotion')
def mixed(path):
    result=perceive('Mia sorella è triste, io sono felice ma preoccupato.')
    require(set(result['current_labels'])=={'joy','anxiety'},'Self and other were conflated')
    require('emozioni diverse' in result['instruction'],'Mixed emotions were collapsed')


@case('scope_and_time','Only recent self-attributed same-user same-chat evidence may be referenced')
def scope(path):
    good=perceive('Sto come prima',[turn('Sono triste.')])
    require(good['prior_labels']==['sadness'],'Recent reference was not connected')
    for change in ({'user_id':'other'},{'conversation_id':'other'}, {'role':'assistant'},
                   {'timestamp':NOW-timedelta(hours=1)}, {'timestamp':None}):
        require(not perceive('Sto come prima',[turn('Sono triste.',**change)])['prior_labels'],'Context crossed ownership, role or age boundary')
    require(not perceive('Sto come prima',[turn('Mia sorella è triste.')])['prior_labels'],'Another person taught the user’s mood')


@case('stop_boundary','Explicit disengagement is respected without a model call or follow-up question')
def boundary(path):
    with core_at(path) as core:
        reply=core.process_message('u',core.start_conversation('u'),'Non voglio parlarne.')
        require(reply.is_valid and reply.metadata['source']=='conversation_boundary' and '?' not in reply.content,'Boundary was not respected')
        core._llm.generate.assert_not_called()


@case('topic_and_format','Old emotion does not add counselling to unrelated tasks or strict formats')
def topic(path):
    require(not perceive('Spiega il sole',[turn('Sono triste.')])['instruction'],'Unrelated task received emotional carryover')
    require(not perceive('Sono triste e felice. Rispondi solo con JSON.')['instruction'],'Optional guidance changed a strict output task')
    require(not perceive('Traduci «Ho fallito ancora».')['instruction'],'Quoted text became personal evidence')


@case('current_need','Listening and practical help are distinct current requests, not immediate durable preferences')
def needs(path):
    p=CoalescenceProcessor(str(path/'state.db'))
    p.observe_interaction('u','e','Voglio solo sfogarmi.')
    require(not p.expression_view('u')['preferences'],'A single request became a declared permanent preference')
    require(p.expression_plan('u','Voglio solo sfogarmi.')['values'].get('support_mode')=='listening','Listening request was ignored')
    require(p.expression_plan('u','Dammi consigli pratici.')['values'].get('support_mode')=='practical','Practical request was ignored')


@case('preference_lifecycle','A declared support preference survives restart, is scoped, overridden and revocable')
def lifecycle(path):
    db=str(path/'state.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','e','Quando sto male preferisco essere ascoltato senza consigli.')
    p=CoalescenceProcessor(db);emotion={'primary_emotion':'sadness','confidence':.9}
    require(p.expression_plan('u','Sono triste.',emotion)['values'].get('support_mode')=='listening','Preference was not restored')
    require('support_mode' not in p.expression_plan('other','Sono triste.',emotion)['values'],'Preference leaked to another user')
    require(p.expression_plan('u','Sono triste. Dammi consigli pratici.',emotion)['values'].get('support_mode')=='practical','Old preference overrode current need')
    p.observe_interaction('u','revoke','Dimentica la mia preferenza di supporto.')
    require('support_mode' not in p.expression_plan('u','Sono triste.',emotion)['values'],'Revoked preference remained active')


@case('assessed_learning','Three distinct usefulness assessments integrate a support strategy; a correction withdraws it')
def learning(path):
    from allma_model.core.personality_outcomes import delivery_receipt
    p=CoalescenceProcessor(str(path/'state.db'));emotion={'primary_emotion':'sadness','confidence':.9}
    receipt=None
    for i in range(3):
        metadata={'source':'model_generated','generation':{'status':'completed','finish_reason':'stop'},
            'personality_expression':{'values':{'support_mode':'listening'},'instruction_received':True,'response_context':'support'}}
        receipt=delivery_receipt('u',str(i),f'Sono triste per il motivo {i}. Voglio solo sfogarmi.',
            'Ti ascolto. Puoi raccontare quello che desideri.',metadata,True,emotion)
        p.observe_interaction('u','f'+str(i),'Il tuo ascolto senza consigli mi è stato utile.',response_context=receipt)
        if i<2:require('support_mode' not in p.expression_plan('u','Sono triste.',emotion)['values'],'Consolidated too early')
    require(p.expression_plan('u','Sono triste.',emotion)['sources'].get('support_mode')=='interaction_outcomes','Assessed strategy was not integrated')
    p.observe_interaction('u','correct','Il tuo ascolto senza consigli non mi è stato utile.',response_context=receipt)
    require('support_mode' not in p.expression_plan('u','Sono triste.',emotion)['values'],'Correction did not withdraw support')


@case('write_failure','A failed preference write cannot change live or reloaded personality')
def write_failure(path):
    db=str(path/'state.db');p=CoalescenceProcessor(db)
    before=p.expression_view('u')
    with patch.object(p._state_store,'put',side_effect=OSError('synthetic disk full')):
        try:p.observe_interaction('u','e','Quando sto male preferisco suggerimenti pratici.')
        except OSError:pass
        else:raise AssertionError('Write failure was hidden')
    require(p.expression_view('u')==before and CoalescenceProcessor(db).expression_view('u')==before,'Failed preference mutated personality')


@case('core_integration','The real turn pipeline supplies needs and corrections without an extra inference')
def integration(path):
    with core_at(path) as core:
        cid=core.start_conversation('u')
        reply=core.process_message('u',cid,'Non sono triste, sono stanco. Voglio solo sfogarmi.')
        require(reply.is_valid and reply.metadata['relational_perception']['relation']=='self_correction','Core did not retain attributed correction')
        expression=reply.metadata['personality_expression']
        require(expression['values'].get('support_mode')=='listening' and expression['instruction_received'],'Host support plan was not supplied to generation')
        core._llm.generate.assert_called_once()
        feedback=core.process_message('u',cid,'Il tuo ascolto senza consigli mi è stato utile.')
        require(feedback.metadata['personality_feedback']['status']=='feedback_recorded','Feedback did not reach existing coalescence')
        core._llm.generate.assert_called_once()
        return {'generation_calls':1,'additional_perception_inferences':0,'support_mode':'listening','feedback_saved':True}


def run_battery(output, *, scope='Synthetic relational perception; scripted generation, no GGUF', cancel_event=None, progress_callback=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'plan.json').write_text(json.dumps([{'name':n,'criterion':c} for n,c,_ in CASES],indent=2))
    start=time.perf_counter();rows=[]
    for index,(name,criterion,fn) in enumerate(CASES):
        if cancel_event is not None and cancel_event.is_set():break
        if progress_callback:progress_callback(index+1,len(CASES),'Sensibilità e contesto: '+name)
        row={'name':name,'criterion':criterion,'passed':False,'error':None}
        try:
            with tempfile.TemporaryDirectory(prefix='relational-',dir=str(output)) as temporary:
                row['observations']=fn(Path(temporary))
            row['passed']=True
        except Exception as error:
            row['error']={'type':type(error).__name__,'detail':str(error)[:500]}
        rows.append(row)
        (output/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    passed=sum(r['passed'] for r in rows);complete=len(rows)==len(CASES)
    summary={'scope':scope,'passed':passed,'total':len(CASES),'complete':complete,
        'percent':100*passed/len(CASES) if complete else None,
        'groups':{'relational_perception':{'passed':passed,'total':len(CASES)}},
        'failures':[r for r in rows if not r['passed']],'seconds':time.perf_counter()-start,
        'statistical_generalization':'Fixed synthetic software checks; actual generated empathy requires separate evaluation.'}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary
