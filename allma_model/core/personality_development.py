"""Evidence-based expression of personality; no autobiography or mood mirroring.

Persisted preferences are user instructions. Integrated tendencies are modest,
revisable defaults learned from repeated, distinct style requests. Neither is a
claim that ALLMA feels emotions, has human traits, or knows the user's character.
"""
import copy
import hashlib
import json
import math
import re
import unicodedata

VERSION = 1
AXES = {
    'verbosity':('brief','detailed'), 'formality':('informal','formal'),
    'humor':('serious','light'), 'directness':('gentle','direct'),
    'questions':('restrained','exploratory'),
    'support_mode':('listening','practical'),
}
HINTS = {
    'brief':'Rispondi in poche frasi (di norma 2–3), mantenendo le informazioni necessarie. Evita preamboli e sviluppi non richiesti.',
    'detailed':'Spiega con i dettagli pertinenti, evitando ripetizioni.',
    'informal':'Usa un tono semplice e informale.',
    'formal':'Usa un tono formale e rispettoso.',
    'serious':'Mantieni un tono serio, senza battute.',
    'light':'Puoi usare un umorismo leggero solo quando appropriato.',
    'gentle':'Esprimi il punto con delicatezza, senza essere evasiva.',
    'direct':'Esprimi il punto chiaramente e senza giri di parole.',
    'restrained':'Evita domande aggiuntive non necessarie.',
    'exploratory':'Se utile, proponi una sola domanda pertinente, senza insistere.',
    'listening':'L’utente desidera ascolto: accogli ciò che racconta, senza consigli o soluzioni non richiesti. Evita interrogatori e formule di conforto automatiche.',
    'practical':'L’utente desidera aiuto pratico: riconosci brevemente la situazione e proponi un piccolo passo pertinente, lasciando a lui la scelta.',
}
# Closed, self-directed style controls. Quotes, reports and extra tasks fall through.
_PREFIX = r"(?:(?:d['’]ora in poi|da ora in poi|in generale|con me|per le prossime risposte)[, ]+)?"
_PATTERNS = {
    'brief': r'(?:preferisco (?:le |delle )?risposte brevi|voglio (?:le |delle )?risposte brevi)',
    'detailed': r'(?:preferisco (?:le |delle )?risposte dettagliate|voglio (?:le |delle )?risposte dettagliate)',
    'formal': r'(?:preferisco (?:un |il )?tono formale|parlami (?:in modo formale|formalmente))',
    'informal': r'(?:preferisco (?:un |il )?tono informale|parlami (?:in modo informale|informalmente))',
    'serious': r'(?:non fare (?:più )?battute|evita (?:le )?battute|preferisco (?:un |il )?tono serio)',
    'light': r'(?:preferisco (?:un |il )?tono scherzoso|puoi usare (?:un po[’\']? di )?umorismo)',
    'gentle': r'(?:preferisco (?:un |il )?tono delicato|parlami con delicatezza)',
    'direct': r'(?:preferisco (?:un |il )?tono diretto|preferisco risposte dirette)',
    'restrained': r'(?:non farmi (?:più )?domande aggiuntive|evita (?:le )?domande aggiuntive)',
    'exploratory': r'(?:mi piacciono le tue domande di approfondimento|puoi farmi domande di approfondimento)',
    'listening': r'quando (?:sto male|sono in difficoltà) preferisco (?:essere ascoltat[oa] senza consigli|che tu mi ascolti senza consigli)',
    'practical': r'quando (?:sto male|sono in difficoltà) preferisco (?:consigli|suggerimenti) pratici',
}


def empty_state():
    return {'version':VERSION,'profiles':{}}


def canonical(text):
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().split()).strip(' .!?')


def _quoted(text):
    return bool(re.search(r'```|["«»“”]',text))


def controls(text):
    """Return only whole-message style controls, not open-ended user requests."""
    if not isinstance(text,str) or len(text)>600 or _quoted(text):
        return None
    plain=canonical(text)
    if re.fullmatch(r'(?:dimentica|azzera) la mia preferenza di supporto',plain):
        return {'action':'revoke','axis':'support_mode','values':{}}
    durable = re.fullmatch(r"(?:d['’]ora in poi|da ora in poi|per le prossime risposte)[, ]+(.+)",plain)
    if durable:
        requested=current_requests(durable.group(1))
        # Only an entire style command, never an additional content request.
        if re.fullmatch(r'rispondi (?:in breve|brevemente|in modo conciso|in dettaglio|dettagliatamente|formalmente|informalmente|in modo formale|in modo informale|con delicatezza|direttamente|in modo diretto)',durable.group(1)) and requested:
            return {'action':'set','values':requested}
    if re.fullmatch(r'(?:dimentica|azzera) (?:le mie |tutte le mie )preferenze di stile',plain):
        return {'action':'reset','values':{}}
    for axis,values in AXES.items():
        if re.fullmatch(r'non usare più la mia preferenza (?:per |di )'+{
            'verbosity':'lunghezza','formality':'formalità','humor':'umorismo',
            'directness':'tono diretto','questions':'domande aggiuntive',
            'support_mode':'modo di supporto'}[axis],plain):
            return {'action':'revoke','axis':axis,'values':{}}
        for value in values:
            if re.fullmatch(_PREFIX+_PATTERNS[value],plain):
                return {'action':'set','values':{axis:value}}
    return None


def current_requests(text):
    """Explicit current-turn constraints, never inferred from length or emoji."""
    if not isinstance(text,str) or _quoted(text):
        return {}
    plain=canonical(text)
    # Do not learn from hypothetical instructions or another person's request.
    if re.search(r'\b(?:se |supponi|immagina|dice|ha detto|vuole che|preferirebbe)\b',plain):
        return {}
    requests={}
    patterns={
        'brief':r'\b(?:rispondi (?:in breve|brevemente|in modo conciso)|sii (?:più )?concis[ao])\b',
        'detailed':r'\b(?:rispondi|spiega) (?:in dettaglio|dettagliatamente)\b',
        'formal':r'\brispondi (?:formalmente|in modo formale)\b',
        'informal':r'\brispondi (?:informalmente|in modo informale)\b',
        'serious':r'\b(?:senza battute|non fare battute)\b',
        'gentle':r'\brispondi con delicatezza\b',
        'direct':r'\brispondi (?:direttamente|in modo diretto)\b',
        'restrained':r'\b(?:senza domande aggiuntive|non farmi domande aggiuntive)\b',
    }
    for axis,values in AXES.items():
        found=[]
        for value in values:
            pattern=patterns.get(value)
            if pattern:
                matches=[m for m in re.finditer(pattern,plain)
                         if not re.search(r'\b(?:non|evita di)\s*$',plain[max(0,m.start()-15):m.start()])]
                if matches:found.append(value)
        if len(found)==1:requests[axis]=found[0]
    from allma_model.emotional_system.relational_perception import support_request
    support = support_request(text)
    if support:
        requests['support_mode'] = support
    return requests


def evolve(state,user_id,event_id,text):
    if not user_id or not event_id or not isinstance(text,str):
        raise ValueError('Attributed stored interaction required')
    control=controls(text)
    requested=current_requests(text) if not control else {}
    # A repeated need for listening is not evidence that listening was useful.
    # Support defaults require explicit declarations or assessed outcomes.
    requested.pop('support_mode',None)
    if control is None and not requested:
        return state,{'status':'no_style_evidence'}
    candidate=copy.deepcopy(state)
    profile=candidate['profiles'].setdefault(user_id,{'declared':{},'tendencies':{},'events':[],
                                                    'revision':0,'observations':0})
    event=hashlib.sha256(str(event_id).encode()).hexdigest()
    if event in profile['events']:
        return state,{'status':'duplicate_event'}
    if control:
        if control['action']=='reset':
            profile['declared']={};profile['tendencies']={};profile['outcomes']=[]
        elif control['action']=='revoke':
            profile['declared'].pop(control['axis'],None)
            profile['tendencies'].pop(control['axis'],None)
            profile['outcomes']=[r for r in profile.get('outcomes',[]) if r['axis']!=control['axis']]
        else:
            profile['declared'].update(control['values'])
        status={'set':'preference_saved','revoke':'preference_revoked','reset':'preferences_reset'}[control['action']]
    else:
        fingerprint=hashlib.sha256(canonical(text).encode()).hexdigest()
        changed=False
        for axis,value in requested.items():
            trend=profile['tendencies'].setdefault(axis,{'weights':{},'examples':[],'observations':0})
            if fingerprint in trend['examples']:continue
            trend['weights']={k:v*.85 for k,v in trend['weights'].items()}
            trend['weights'][value]=trend['weights'].get(value,0)+1
            trend['examples']=(trend['examples']+[fingerprint])[-64:]
            trend['observations']+=1;changed=True
        if not changed:return state,{'status':'repeated_context'}
        status='style_observed'
    profile['revision']+=1;profile['observations']+=1
    profile['events']=(profile['events']+[event])[-256:]
    return candidate,{'status':status,'revision':profile['revision']}


def view(state,user_id):
    profile=state.get('profiles',{}).get(user_id,{})
    preferences={axis:value for axis,value in profile.get('declared',{}).items()
                 if axis in AXES and value in AXES[axis]}
    tendencies={}
    for axis,trend in profile.get('tendencies',{}).items():
        if axis not in AXES:continue
        weights={k:v for k,v in trend.get('weights',{}).items() if k in AXES[axis] and type(v) in (int,float) and math.isfinite(v) and v>0}
        if not weights:continue
        strongest=max(weights,key=weights.get);support=weights[strongest]/sum(weights.values())
        integrated=trend.get('observations',0)>=3 and support>=.67
        tendencies[axis]={'value':strongest,'stage':'integrated' if integrated else 'suspended',
                          'observations':trend.get('observations',0),'support':round(support,3)}
    from .personality_outcomes import view as outcome_view
    return copy.deepcopy({'preferences':preferences,'tendencies':tendencies,
                          'outcome_learning':outcome_view(profile.get('outcomes',[])),
                          'revision':profile.get('revision',0),'observations':profile.get('observations',0)})


def plan(state,user_id,message,emotional_state=None):
    learned=view(state,user_id);values={};sources={}
    for axis,item in learned['tendencies'].items():
        if item['stage']=='integrated':values[axis]=item['value'];sources[axis]='integrated_requests'
    from .personality_outcomes import context_for
    response_context=context_for(message,emotional_state)
    # Listening versus practical help is specific to support, never a global
    # style applied to unrelated factual or technical questions.
    from allma_model.emotional_system.relational_perception import support_request
    current_support = support_request(message)
    support_context = response_context == 'support' or current_support is not None
    for axis,item in learned['outcome_learning']['contexts'].get(response_context,{}).items():
        if item['stage']=='integrated':values[axis]=item['value'];sources[axis]='interaction_outcomes'
        elif sources.get(axis)=='integrated_requests':
            assessed=item.get('assessments',{}).get(values[axis],{})
            if assessed.get('negative',0)>=2 and assessed.get('negative',0)>assessed.get('positive',0):
                # Negative utility suspends a derived default, never an explicit
                # user instruction and never invents preference for its opposite.
                values.pop(axis,None);sources.pop(axis,None)
    for axis,value in learned['preferences'].items():values[axis]=value;sources[axis]='declared_preference'
    current=current_requests(message)
    control=controls(message)
    if control and control['action']=='set':current.update(control['values'])
    # Exact current output constraints beat every learned verbosity preference.
    from allma_model.utils.output_contract import requested_contract,requested_sentence_count
    for axis,value in current.items():values[axis]=value;sources[axis]='current_request'
    if not support_context:
        values.pop('support_mode',None);sources.pop('support_mode',None)
    if requested_contract(message) or requested_sentence_count(message):
        values.pop('verbosity',None);sources.pop('verbosity',None)
        values.pop('support_mode',None);sources.pop('support_mode',None)
    read=(emotional_state.get if isinstance(emotional_state,dict) else
          lambda key,default=None:getattr(emotional_state,key,default))
    from allma_model.utils.cognitive_state import unit_number
    confidence=unit_number(read('confidence',0.),0.)
    emotion=read('primary_emotion','neutral');emotion=str(getattr(emotion,'value',emotion)).casefold()
    secondary=read('secondary_emotions',{}) or {}
    families={emotion}
    if isinstance(secondary,dict):
        families.update(str(k).casefold() for k,v in secondary.items() if unit_number(v,0.)>=.2)
    distress=confidence>=.6 and bool(families&{'sadness','fear','anger','grief','shame','anxiety'})
    if distress:
        # A temporary response policy, never a mutation of learned personality.
        values['humor']='serious';sources['humor']='current_emotional_context'
        if sources.get('directness') not in ('current_request','declared_preference','interaction_outcomes'):
            values['directness']='gentle';sources['directness']='current_emotional_context'
    hints=[HINTS[v] for _,v in values.items()]
    return {'values':values,'sources':sources,'revision':learned['revision'],
            'response_context':response_context,
            'instruction':' '.join(hints),'emotion_adaptation_transient':distress,
            'policy_version':VERSION,'subject':'ALLMA_response_policy'}


def revision(state,user_id):
    learned=view(state,user_id)
    # Courtesy acknowledgements do not invalidate confirmed answers.
    relevant={k:learned[k] for k in ('preferences','tendencies')}
    relevant['outcomes']=learned['outcome_learning']['contexts']
    return hashlib.sha256(json.dumps(relevant,sort_keys=True).encode()).hexdigest()


def validate(state):
    """Fail closed on a malformed persisted section; never overwrite it silently."""
    if not isinstance(state,dict) or state.get('version')!=VERSION or not isinstance(state.get('profiles'),dict):
        raise ValueError('Invalid personality expression schema')
    for owner,p in state['profiles'].items():
        if not isinstance(owner,str) or not owner or not isinstance(p,dict):
            raise ValueError('Invalid personality expression owner')
        if (not isinstance(p.get('declared'),dict) or not isinstance(p.get('tendencies'),dict)
                or type(p.get('revision')) is not int or p['revision']<0
                or type(p.get('observations')) is not int or p['observations']<0):
            raise ValueError('Invalid personality expression profile')
        for axis,value in p['declared'].items():
            if axis not in AXES or value not in AXES[axis]:raise ValueError('Invalid declared style')
        from .personality_outcomes import validate as validate_outcomes
        validate_outcomes(p.get('outcomes',[]))
        if not isinstance(p.get('events'),list) or len(p['events'])>256 or any(not isinstance(k,str) or not re.fullmatch('[a-f0-9]{64}',k) for k in p['events']):
            raise ValueError('Invalid expression events')
        for axis,t in p['tendencies'].items():
            if axis not in AXES or not isinstance(t,dict) or not isinstance(t.get('weights'),dict):
                raise ValueError('Invalid expression tendency')
            if any(k not in AXES[axis] or type(v) not in (int,float) or not math.isfinite(v) or v<0 for k,v in t['weights'].items()):
                raise ValueError('Invalid expression weights')
            if (type(t.get('observations')) is not int or t['observations']<0
                    or not isinstance(t.get('examples'),list) or len(t['examples'])>64
                    or any(not isinstance(k,str) or not re.fullmatch('[a-f0-9]{64}',k) for k in t['examples'])):
                raise ValueError('Invalid expression evidence')
    return state


def self_description_question(text):
    return bool(re.fullmatch(r'(?:che personalità hai|che carattere hai|com[’\']è (?:la tua personalità|il tuo carattere)|qual è (?:la tua personalità|il tuo carattere))',canonical(text)))


def preferences_question(text):
    return canonical(text) in ('quali sono le mie preferenze di stile',
                               'come preferisco che tu risponda')


def describe_preferences(expression):
    labels = {'brief':'risposte brevi', 'detailed':'risposte dettagliate',
              'formal':'tono formale', 'informal':'tono informale',
              'serious':'senza battute', 'light':'umorismo leggero quando appropriato',
              'gentle':'delicatezza', 'direct':'risposte dirette',
              'restrained':'senza domande aggiuntive non necessarie',
              'exploratory':'domande di approfondimento quando utili',
              'listening':'ascolto senza consigli nei momenti difficili',
              'practical':'suggerimenti pratici nei momenti difficili'}
    values = expression.get('preferences',{})
    if not values:
        return 'Non ho preferenze di stile esplicite registrate per te.'
    return 'Hai indicato queste preferenze di stile: '+', '.join(labels[values[a]] for a in AXES if a in values)+'.'


def history_eligible(record):
    """Keep the real archive intact; old style controls are not model instructions.

    The current host view is the sole authority for preferences, including
    revocation. Ordinary tasks with temporary style requests remain in context.
    """
    read = record.get if isinstance(record,dict) else lambda key,default=None:getattr(record,key,default)
    metadata = read('metadata',{}) or {}
    if metadata.get('source')=='personality_response_feedback':
        return False
    role = read('role',metadata.get('role'))
    if role == 'user' and controls(read('content','')):
        return False
    return not (role == 'assistant' and metadata.get('source') in
                ('personality_style_control','personality_style_summary','personality_self_description'))


def describe(expression,growth):
    """Only describe supported response dispositions, never baseline trait scores."""
    parts=[]
    mode=growth.get('response_disposition',{}).get('mode')
    if mode=='care':parts.append('una tendenza al sostegno attento e delicato')
    elif mode=='exploration':parts.append('una tendenza a esplorare e approfondire')
    earned=[item['value'] for item in expression['tendencies'].values() if item['stage']=='integrated']
    if earned:parts.append('un modo di comunicare che si adatta alle richieste ricorrenti')
    if any(item['stage']=='integrated' for axes in expression.get('outcome_learning',{}).get('contexts',{}).values() for item in axes.values()):
        parts.append('un modo di rispondere che tiene conto dei tuoi riscontri documentati')
    if parts:
        return 'Dalle nostre interazioni documentate sto sviluppando '+ ' e '.join(parts)+'.'
    if expression['preferences']:
        return 'Per ora ho registrato le tue preferenze di comunicazione; il mio modo personale di rispondere deve ancora consolidarsi con l’esperienza.'
    return 'Il mio modo personale di rispondere non è ancora consolidato: prenderà forma attraverso le nostre interazioni.'
