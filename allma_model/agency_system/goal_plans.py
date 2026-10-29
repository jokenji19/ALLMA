"""Bounded model proposals: descriptions only, never executable tool commands."""
from copy import deepcopy
import hashlib
import re

from allma_model.core.autobiographical_identity import POLICY_VERSION, normalized


def requested(text):
    query = normalized(text)
    return (query in {'proponi un piano per questo obiettivo','proponi un piano per il mio obiettivo',
                     'pianifica questo obiettivo','organizza i passi per questo obiettivo'}
            or bool(re.fullmatch(r'(?:puoi |mi )?(?:proporre|proponi|preparare|prepara|organizzare|organizza) '
                                 r'(?:un |i )?(?:piano|passi) per (?:questo|il mio|il nostro) obiettivo',query)))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def valid_steps(steps):
    return (isinstance(steps,list) and 2 <= len(steps) <= 5
            and all(isinstance(s,str) and 8 <= len(s.strip()) <= 240 for s in steps)
            and len({re.sub(r'\W+','',s.casefold()) for s in steps}) == len(steps))


def extract_steps(text):
    rows = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(\d{1,2})[.)]\s+(.+?)\s*',line)
        if match:
            if int(match[1]) != len(rows)+1:return None
            rows.append(match[2])
        elif rows and line.strip():
            # No silent loss of wrapped requirements or mixed numbering styles.
            return None
    return rows if valid_steps(rows) else None


def proposal(text, context):
    steps,prelude,notes = [],[],[]
    trailing = False
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(\d{1,2})[.)]\s+(.+?)\s*',line)
        if match:
            if trailing or int(match[1]) != len(steps)+1:return None
            steps.append(match[2])
        elif not steps:
            if line.strip(' *#:').casefold() not in ('','proposta di piano'):
                prelude.append(line)
        elif line.strip():
            trailing = True;notes.append(line)
    if not valid_steps(steps):return None
    annotation = '\n'.join(prelude+notes).strip()
    if len(annotation)>600:return None
    result = {'version':1, 'id':digest(context['id']+':'+str(context['revision'])+':'+text),
            'goal_id':context['id'],'goal_revision':context['revision'], 'steps':steps,
            'answer_sha256':digest(text),'source':'model_proposal'}
    if annotation:result['notes'] = annotation
    return result


def valid_proposal(value):
    return (isinstance(value,dict) and type(value.get('version')) is int and value['version'] == 1
            and value.get('source') == 'model_proposal'
            and all(isinstance(value.get(k),str) and bool(value[k]) for k in ('id','goal_id','answer_sha256'))
            and type(value.get('goal_revision')) is int and value['goal_revision'] > 0
            and isinstance(value.get('notes',''),str) and len(value.get('notes',''))<=600
            and valid_steps(value.get('steps')))


def selection(record, user, goal_id, revision):
    value = record.metadata.get('goal_proposal')
    if (record.role != 'assistant' or (record.user_id or record.metadata.get('user_id')) != user
            or record.metadata.get('source') != 'model_generated' or record.metadata.get('is_valid') is not True
            or record.metadata.get('identity_policy') != POLICY_VERSION
            or record.metadata.get('generation',{}).get('status') != 'completed'
            or not valid_proposal(value) or value['goal_id'] != goal_id or value['goal_revision'] != revision
            or value != proposal(record.content,{'id':goal_id,'revision':revision})):
        return None
    return {'proposal':deepcopy(value),'conversation':record.conversation_id,
            'timestamp':record.timestamp.isoformat()}


def find_recent(memory, user, goal_id, revision):
    rows = memory.recent_messages(64,predicate=lambda m:(m.user_id or m.metadata.get('user_id')) == user)
    for record in reversed(rows):
        # A newer failed/cancelled attempt must not silently select an older plan.
        if record.role == 'user' and requested(record.content):return None
        chosen = selection(record,user,goal_id,revision)
        if chosen is not None:return chosen
    return None


def verify_saved(memory, user, chosen):
    if not isinstance(chosen,dict) or not valid_proposal(chosen.get('proposal')):
        return False
    value = chosen['proposal']
    with memory.lock:
        return any(record.conversation_id == chosen.get('conversation')
                   and record.timestamp.isoformat() == chosen.get('timestamp')
                   and selection(record,user,value['goal_id'],value['goal_revision']) == chosen
                   for record in reversed(memory.messages))


def valid_plan(plan):
    if (not isinstance(plan,dict) or type(plan.get('version')) is not int or plan['version'] != 1
            or plan.get('source') != 'user_admitted_model_proposal'
            or not isinstance(plan.get('proposal_id'),str) or not plan['proposal_id']
            or not isinstance(plan.get('notes',''),str) or len(plan.get('notes',''))>600
            or plan.get('status') not in ('active','needs_review','closed')
            or type(plan.get('index')) is not int or not isinstance(plan.get('steps'),list)
            or not 0 <= plan['index'] <= len(plan['steps'])
            or not valid_steps([s.get('text') if isinstance(s,dict) else None for s in plan['steps']])):
        return False
    from .goal_progress import valid_reference
    if not valid_reference(plan.get('adopted_by')):return False
    for index, step in enumerate(plan['steps']):
        if step.get('status') not in ('pending','awaiting_confirmation','confirmed_by_user'):
            return False
        result = step.get('result')
        if result is not None and (not isinstance(result,dict) or not isinstance(result.get('text'),str)
                or not result['text'].strip() or len(result['text']) > 1000
                or not valid_reference(result.get('event'))):return False
        if step['status'] in ('awaiting_confirmation','confirmed_by_user') and result is None:return False
        if step['status'] == 'pending' and result is not None:return False
        if step['status'] == 'confirmed_by_user' and not valid_reference(step.get('confirmed_by')):return False
        if index < plan['index'] and step['status'] != 'confirmed_by_user':return False
        if index >= plan['index'] and step['status'] == 'confirmed_by_user':return False
    return True


INSTRUCTION = ('Per questo obiettivo proponi un piano di 2–5 passi concreti. '
    'Scrivi ogni passo su una sola riga numerata da 1, senza sottoliste. '
    'Eventuali vincoli o domande vanno in brevi note separate dopo l’elenco. '
    'Puoi introdurlo con «Proposta di piano». Non inventare tempi, risorse disponibili o risultati ottenuti. '
    'I passi sono una proposta da adottare esplicitamente, non azioni già autorizzate o eseguite. '
    'Se mancano dati indispensabili, chiedi un chiarimento invece dell’elenco.')
