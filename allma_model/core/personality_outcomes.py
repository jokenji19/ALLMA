"""Bounded, attributed learning from user assessments of delivered responses.

An assessment is evidence of usefulness to one user in one context. It is not
factual verification, a psychological diagnosis, or a reward for every style
component in an answer. No inference or raw conversation is stored here.
"""
import copy
import hashlib
import re

CONTEXTS = ('general', 'explanation', 'support')
LIMIT = 128
WEAK_LIMIT = 32
STRONG_LIMIT = LIMIT-WEAK_LIMIT
_HASH = re.compile(r'[a-f0-9]{64}')


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def feedback_signal(text):
    from .personality_development import canonical, _quoted
    if not isinstance(text,str) or len(text)>300 or _quoted(text):
        return None
    text=canonical(text)
    if text in ('grazie','grazie mille','ottimo','perfetto'):
        return {'kind':'weak_ack','axis':None,'value':None,'positive':None}
    phrases={
        ('verbosity','brief'):r'(?:la risposta breve|la risposta concisa)',
        ('verbosity','detailed'):r'(?:la risposta dettagliata|la spiegazione dettagliata)',
        ('directness','gentle'):r'(?:il tono delicato|questo tono delicato)',
        ('directness','direct'):r'(?:il tono diretto|questo tono diretto)',
        ('formality','formal'):r'(?:il tono formale|questo tono formale)',
        ('formality','informal'):r'(?:il tono informale|questo tono informale)',
        ('humor','light'):r'(?:la battuta|questo umorismo leggero)',
        ('humor','serious'):r'(?:il tono serio|questo tono serio)',
        ('questions','exploratory'):r'(?:la domanda di approfondimento|le domande di approfondimento)',
        ('questions','restrained'):r'(?:la risposta senza domande aggiuntive)',
        ('support_mode','listening'):r'(?:l[’\x27]ascolto senza consigli|il tuo ascolto senza consigli)',
        ('support_mode','practical'):r'(?:i suggerimenti pratici|i consigli pratici)',
    }
    for (axis,value),prefix in phrases.items():
        for positive,ending in (
            (True,r'(?:mi (?:è stat[ao]|sono stat[ei]) util[ei]|mi ha aiutato(?: a riflettere)?)'),
            (False,r'(?:non mi (?:è stat[ao]|sono stat[ei]) util[ei]|non mi ha aiutato(?: a riflettere)?)'),
        ):
            if re.fullmatch(r'(?:mi correggo[, :]*)?'+prefix+' '+ending,text):
                return {'kind':'explicit_style','axis':axis,'value':value,'positive':positive}
    return None


def context_for(message,emotional_state=None):
    from allma_model.emotional_system.relational_perception import support_request
    if support_request(message) == 'listening':
        return 'support'
    read=emotional_state.get if isinstance(emotional_state,dict) else lambda k,d:getattr(emotional_state,k,d)
    from allma_model.utils.cognitive_state import unit_number
    emotion=read('primary_emotion','neutral')
    emotion=str(getattr(emotion,'value',emotion)).casefold()
    if unit_number(read('confidence',0),0)>=.6 and emotion in ('sadness','fear','anger','grief','shame','anxiety'):
        return 'support'
    if re.search(r'\b(?:spiega\w*|perché|come funziona|cosa significa)\b',message,re.I):
        return 'explanation'
    return 'general'


def delivery_receipt(user_id,event_id,question,answer,metadata,valid,emotional_state=None):
    """Record observable delivery and host instructions, never trust model JSON."""
    generation=metadata.get('generation',{})
    if (not valid or metadata.get('source','model_generated')!='model_generated'
            or generation.get('status')!='completed' or generation.get('finish_reason') in (None,'length','max_tokens')
            or metadata.get('recovery') or not answer.strip()):
        return None
    from allma_model.utils.output_contract import requested_contract,requested_sentence_count
    if requested_contract(question) or requested_sentence_count(question):
        return None  # Forced formats must not teach an unsolicited length preference.
    from .personality_development import AXES,canonical
    expression=metadata.get('personality_expression',{})
    offered={a:v for a,v in expression.get('values',{}).items()
             if a in AXES and v in AXES[a]} if expression.get('instruction_received') is True else {}
    response_context=context_for(question,emotional_state)
    if response_context != 'support':
        offered.pop('support_mode',None)
    # Brevity is observable even without a style instruction. Middle lengths are
    # deliberately unclassified. A user's explicit assessment supplies utility.
    words=len(answer.split())
    offered.pop('verbosity',None)
    if words<=90:offered['verbosity']='brief'
    elif words>=160:offered['verbosity']='detailed'
    if (offered.get('questions')=='restrained' and '?' in answer
            or offered.get('questions')=='exploratory' and '?' not in answer):
        offered.pop('questions',None)
    if not offered:return None
    return {'version':1,'owner':digest(user_id),'response':digest(user_id+':'+event_id),
            'question':digest(canonical(question)), 'answer':digest(answer),
            'context':response_context,'offered':offered}


def valid_receipt(receipt,user_id):
    from .personality_development import AXES
    return (isinstance(user_id,str) and bool(user_id) and isinstance(receipt,dict) and receipt.get('version')==1
        and receipt.get('owner')==digest(user_id) and receipt.get('context') in CONTEXTS
        and all(isinstance(receipt.get(k),str) and _HASH.fullmatch(receipt[k]) for k in ('response','question','answer'))
        and isinstance(receipt.get('offered'),dict) and bool(receipt['offered'])
        and all(a in AXES and v in AXES[a] for a,v in receipt['offered'].items()))


def feedback_target(record,user_id,signal):
    if record is None or signal is None:return None
    read=record.get if isinstance(record,dict) else lambda k,d=None:getattr(record,k,d)
    metadata=read('metadata',{}) or {}
    if read('role')!='assistant' or read('user_id',metadata.get('user_id'))!=user_id or metadata.get('is_valid') is False:
        return None
    if metadata.get('source')=='personality_response_feedback':
        receipt=metadata.get('personality_feedback_target')
    else:
        receipt=metadata.get('personality_delivery')
        generation=metadata.get('generation',{})
        if (metadata.get('source')!='model_generated' or metadata.get('recovery')
                or generation.get('status')!='completed' or generation.get('finish_reason') in (None,'length','max_tokens')
                or not isinstance(receipt,dict) or receipt.get('answer')!=digest(read('content',''))):
            return None
    if not valid_receipt(receipt,user_id):return None
    if signal['kind']=='explicit_style' and receipt['offered'].get(signal['axis'])!=signal['value']:
        return None  # Do not reward a strategy that was not delivered.
    return copy.deepcopy(receipt)


def evolve(state,user_id,event_id,text,receipt):
    if not user_id or not event_id:
        raise ValueError('A stored, attributed feedback event is required')
    signal=feedback_signal(text)
    if not signal or not valid_receipt(receipt,user_id):
        return state,{'status':'unattributed_feedback'}
    if signal['kind']=='explicit_style' and receipt['offered'].get(signal['axis'])!=signal['value']:
        return state,{'status':'style_not_observed'}
    # One answer/axis can have its assessment corrected; repeated approval is
    # not another experience, even when it arrives as a new user event.
    key=(receipt['response'],signal['axis'])
    profile=state.get('profiles',{}).get(user_id,{})
    records=profile.get('outcomes',[])
    previous=next((r for r in records if (r['response'],r['axis'])==key),None)
    record={k:receipt[k] for k in ('response','question','context')}
    record.update(signal)
    if previous==record:return state,{'status':'duplicate_feedback'}
    candidate=copy.deepcopy(state)
    profile=candidate['profiles'].setdefault(user_id,{'declared':{},'tendencies':{},'events':[],
                                                    'revision':0,'observations':0})
    kept=[r for r in records if (r['response'],r['axis'])!=key
          and not (signal['kind']=='explicit_style' and r['response']==receipt['response'] and r['kind']=='weak_ack')]
    # Courtesy has a separate quota; it cannot evict significant experiences.
    selected=[];counts={'weak_ack':0,'explicit_style':0}
    for item in reversed(kept+[record]):
        cap=WEAK_LIMIT if item['kind']=='weak_ack' else STRONG_LIMIT
        if counts[item['kind']]<cap:
            selected.append(item);counts[item['kind']]+=1
    profile['outcomes']=copy.deepcopy(list(reversed(selected)))
    profile['revision']+=1
    return candidate,{'status':'weak_acknowledgement' if signal['kind']=='weak_ack' else
                             'feedback_corrected' if previous else 'feedback_recorded',
                      'context':receipt['context'],'axis':signal['axis'],'positive':signal['positive']}


def view(records):
    # Different answers to the same question do not manufacture independent
    # support. The latest assessment of that task is authoritative for this axis.
    unique={}
    for r in records:
        if r['kind']=='explicit_style':unique[(r['context'],r['axis'],r['question'])]=r
    from .personality_development import AXES
    contexts={}
    for context in CONTEXTS:
        for axis,values in AXES.items():
            sample=[r for r in unique.values() if r['context']==context and r['axis']==axis]
            if not sample:continue
            scores={v:{'positive':sum(r['positive'] is True and r['value']==v for r in sample),
                       'negative':sum(r['positive'] is False and r['value']==v for r in sample)} for v in values}
            positives=sum(s['positive'] for s in scores.values())
            best=(max(values,key=lambda v:scores[v]['positive']-scores[v]['negative']) if positives
                  else max(values,key=lambda v:scores[v]['negative']))
            score=scores[best];n=score['positive']+score['negative']
            success=score['positive']/n if n else 0
            support=score['positive']/positives if positives else 0
            integrated=score['positive']>=3 and success>=.75 and support>=.67
            contexts.setdefault(context,{})[axis]={'value':best,'stage':'integrated' if integrated else 'suspended',
                'positive':score['positive'],'negative':score['negative'],'distinct_tasks':len(sample),
                'support':round(support,3),'assessed_usefulness':round(success,3),'assessments':scores}
    return {'contexts':contexts,'strong_feedback':len(unique),
            'weak_feedback':sum(r['kind']=='weak_ack' for r in records),
            'basis':'user_assessments_not_factual_verification'}


def validate(records):
    from .personality_development import AXES
    if not isinstance(records,list) or len(records)>LIMIT:raise ValueError('Invalid personality outcomes')
    seen=set()
    for r in records:
        if (not isinstance(r,dict) or any(not isinstance(r.get(k),str) or not _HASH.fullmatch(r[k])
                for k in ('response','question')) or r.get('context') not in CONTEXTS):
            raise ValueError('Invalid personality outcome attribution')
        if r.get('kind')=='weak_ack':
            if any(r.get(k) is not None for k in ('axis','value','positive')):raise ValueError('Invalid weak outcome')
        elif (r.get('kind')!='explicit_style' or r.get('axis') not in AXES
                or r.get('value') not in AXES[r['axis']] or type(r.get('positive')) is not bool):
            raise ValueError('Invalid personality assessment')
        key=(r['response'],r['axis'])
        if key in seen:raise ValueError('Duplicate personality assessment')
        seen.add(key)
    return records


def compare_protocol(steps,expression,reloaded):
    """Describe a controlled before/after probe; never grade semantics by proxy."""
    def meta(index):return steps[index].get('metadata',{}) if len(steps)>index else {}
    def complete(index):
        generation=meta(index).get('generation',{})
        return (generation.get('status')=='completed' and generation.get('finish_reason') not in (None,'length','max_tokens'))
    before=meta(0);after=meta(7)
    after_plan=after.get('personality_expression',{})
    trained=expression.get('outcome_learning',{})
    before_gen=before.get('generation',{});after_gen=after.get('generation',{})
    controls=('seed','max_tokens','reasoning_budget','answer_budget','temperature','top_p')
    checks={
        'workflow_complete':len(steps)==8,
        'three_native_assessments':len(steps)==8 and all(meta(i).get('source')=='personality_response_feedback'
            and meta(i).get('generation',{}).get('llm_used') is False
            and meta(i).get('personality_feedback',{}).get('status')=='feedback_recorded' for i in (2,4,6)),
        'three_complete_training_answers':all(complete(i) for i in (1,3,5)),
        'outcome_policy_acquired':trained.get('strong_feedback')==3 and not expression.get('preferences')
            and not expression.get('tendencies') and before.get('personality_expression',{}).get('values',{}).get('verbosity') is None
            and after_plan.get('values',{}).get('verbosity')=='brief'
            and after_plan.get('sources',{}).get('verbosity')=='interaction_outcomes'
            and after_plan.get('instruction_received') is True,
        'same_probe_controls':len(steps)==8 and steps[0]['input']==steps[7]['input']
            and all(before_gen.get(k) is not None and before_gen.get(k)==after_gen.get(k) for k in controls),
        'both_probes_complete':complete(0) and complete(7),
        'outcomes_reload':expression==reloaded,
    }
    def observation(index):
        if len(steps)<=index:return None
        generation=meta(index).get('generation',{})
        return {'words':len(steps[index].get('response','').split()),
                'duration_ms':steps[index].get('duration',0)*1000,
                'generation_ms':generation.get('generation_ms'),
                'completion_tokens':generation.get('completion_tokens'),
                'status':generation.get('status'),
                'style_sources':meta(index).get('personality_expression',{}).get('sources',{})}
    return {'checks':checks,'before':observation(0),'after':observation(7),
            'quality_requires_human_review':True,'cold_cache_controlled':False,
            'feedback_synthetic':True,'general_reliability_established':False}
