"""Small procedural projections in GoalProgress, sourced from user-reviewed outcomes.

History remains canonical. Each task keeps its latest outcome per step/kind;
neither model answers nor repeated feedback manufacture independent evidence.
Candidates are contextual precautions, not proven causes or executable rules.
"""
from copy import deepcopy
import hashlib
import re

from allma_model.core.autobiographical_identity import normalized

FEEDBACK_KINDS = {'lesson_positive', 'lesson_negative', 'lesson_forget'}
_STOP = set('a ad al alla alle allo ai agli anche che chi ci come con da dal dalla dalle dei del della delle di e ed è gli i il in io la le lo ma mi mio mia miei mie nel nella nelle nello noi non o per più poi quale quali questo questa questi queste quello quella se si solo su sul sulla tra tu un una uno vorrei obiettivo criterio preparare fare'.split())


def tokens(text):
    return set(re.findall(r'[^\W_]+', normalized(text), re.UNICODE)) - _STOP


def empty():
    return {'version': 1, 'cases': {}, 'feedback': {}}


def valid(value):
    from allma_model.agency_system.goal_progress import valid_reference
    if (not isinstance(value, dict) or set(value) != {'version','cases','feedback'}
            or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['cases'], dict) or len(value['cases']) > 12
            or not isinstance(value['feedback'], dict) or len(value['feedback']) > 32):
        return False
    for slot, case in value['cases'].items():
        if (not re.fullmatch(r'(?:goal|step_[0-4])_(?:confirmed|rejected)', str(slot))
                or not isinstance(case, dict)
                or set(case) != {'id','outcome','step','text','reported','reviewed','withdrawn'}
                or not re.fullmatch(r'[a-f0-9]{16}', str(case['id']))
                or case['outcome'] not in ('confirmed','rejected') or not slot.endswith(case['outcome'])
                or any(not isinstance(case[k], str) or not case[k].strip() or len(case[k]) > 1000 for k in ('step','text'))
                or not valid_reference(case['reported']) or not valid_reference(case['reviewed'])
                or type(case['withdrawn']) is not bool):
            return False
    for key, row in value['feedback'].items():
        if (not re.fullmatch(r'[a-f0-9]{16}', str(key)) or not isinstance(row, dict)
                or set(row) != {'positive','text','event'} or type(row['positive']) is not bool
                or not isinstance(row['text'], str) or not row['text'].strip() or len(row['text']) > 1000
                or not valid_reference(row['event'])):
            return False
    return True


def cases(goals):
    for goal in goals:
        for case in goal['workflow'].get('learning', empty())['cases'].values():
            yield goal, case


def find(goals, lesson_id):
    return next(((g,c) for g,c in cases(goals) if c['id'] == lesson_id), None)


def has_confirmed_result(goal):
    wf = goal['workflow']
    return (wf.get('verification') == 'confirmed_by_user'
            or ((wf.get('plan') or {}).get('status') in {'active','closed'}
                and any(s['status'] == 'confirmed_by_user' for s in wf['plan']['steps'])))


def has_reviewed_result(goal, positive):
    return (goal['status'] != 'revoked' and (has_confirmed_result(goal) or (not positive
            and any(case['outcome'] == 'rejected' and not case['withdrawn']
                    for case in goal['workflow'].get('learning',empty())['cases'].values()))))


def observe(goal, kind, reference, previous_result=None, previous_step=None):
    """Runs inside the same atomic commit and replay checkpoint as task progress."""
    wf = goal['workflow']
    if kind in {'correct','criterion','reopen','cancel'}:
        learning = wf.get('learning')
        if learning:
            for case in learning['cases'].values():case['withdrawn'] = True
            learning['feedback'] = {}
        return
    if kind not in {'confirm','reject','step_confirm','step_reject'}:return
    if not previous_result:return
    learning = wf.setdefault('learning', empty())
    outcome = 'rejected' if kind.endswith('reject') else 'confirmed'
    slot = ('step_'+str(previous_step['index']) if previous_step else 'goal')+'_'+outcome
    # A revised result replaces this slot; the previous event remains in history.
    identifier = hashlib.sha256((goal['user_id']+'\0'+reference['event']).encode()).hexdigest()[:16]
    learning['cases'][slot] = {'id':identifier, 'outcome':outcome,
        'step':previous_step['text'] if previous_step else goal['objective'],
        'text':reference['text'] if 'text' in reference else previous_result['text'],
        'reported':deepcopy(previous_result['event']),
        'reviewed':{k:v for k,v in reference.items() if k != 'text'}, 'withdrawn':False}
    # A rejection corrects the latest positive projection for this same slot.
    positive = slot.removesuffix('_rejected')+'_confirmed'
    if outcome == 'rejected' and positive in learning['cases']:
        learning['cases'][positive]['withdrawn'] = True


def assessment(goals, origin, case):
    if case['outcome'] == 'confirmed':
        return {'status':'withdrawn' if case['withdrawn'] else 'user_confirmed_result',
                'supporting_tasks':0,'counterexamples':0}
    votes = {}
    original = (normalized(origin['objective']), normalized(origin['workflow']['criterion']))
    for goal in goals:
        signature = (normalized(goal['objective']), normalized(goal['workflow']['criterion']))
        row = goal['workflow'].get('learning', empty())['feedback'].get(case['id'])
        if goal['id'] == origin['id'] or signature == original or not row or not has_reviewed_result(goal,row['positive']):continue
        # Identical task descriptions do not become independent by changing chat/id.
        previous = votes.get(signature)
        if previous is None or (previous['positive'] and not row['positive']):votes[signature] = row
    positive = sum(row['positive'] for row in votes.values())
    negative = len(votes)-positive
    status = 'withdrawn' if case['withdrawn'] else 'contested' if negative else 'supported_by_user_reports' if positive >= 3 else 'candidate'
    return {'status':status,'supporting_tasks':positive,'counterexamples':negative}


def context(goals, target):
    owners={goal.get('user_id') for goal in goals}
    owner=target.get('user_id') or (next(iter(owners)) if len(owners)==1 else None)
    if owner is None:return []
    goals=[goal for goal in goals if goal.get('user_id')==owner]
    query = tokens(target['objective']+' '+target['workflow']['criterion'])
    # Cross-task evaluations supply learned routes, not a hand-written synonym map.
    # Build the route index once per plan request; no extra persistent projection.
    routes={}
    for goal in goals:
        signature=(normalized(goal['objective']),normalized(goal['workflow']['criterion']))
        for identifier,vote in goal['workflow'].get('learning',empty())['feedback'].items():
            if not has_reviewed_result(goal,vote['positive']):continue
            key=(identifier,signature)
            previous=routes.get(key)
            if previous is None or (previous[1]['positive'] and not vote['positive']):
                routes[key]=(goal,vote)
    by_case={}
    for (identifier,_),(goal,vote) in routes.items():
        if vote['positive']:
            by_case.setdefault(identifier,[]).append((goal,tokens(goal['objective']+' '+goal['workflow']['criterion']),vote['event']))
    ranked = []
    for origin, case in cases(goals):
        if origin['id'] == target['id'] or case['withdrawn']:continue
        prior = tokens(origin['objective']+' '+origin['workflow']['criterion'])
        overlap = query & prior
        score = len(overlap)/max(1,len(query | prior))
        basis={'kind':'original_context'}
        for bridge,features,event in by_case.get(case['id'],[]):
            if bridge['id'] in {origin['id'],target['id']}:continue
            shared=query & features
            alternative=len(shared)/max(1,len(query | features))
            if len(shared)>=2 and alternative>score:
                score=alternative;overlap=shared
                basis={'kind':'confirmed_task_bridge','task':bridge['objective'][:120],
                       'feedback_event':event['event']}
        if len(overlap) < 2 or score < .3:continue
        review = assessment(goals, origin, case)
        # Counterexamples remain visible as cautions, never as endorsed rules.
        ranked.append((score,case['reviewed']['timestamp'],origin,case,review,basis))
    ranked.sort(key=lambda row:(row[0],row[3]['outcome']=='rejected',row[1]),reverse=True)
    output=[]
    for _,_,origin,case,review,basis in ranked[:2]:
        output.append({'id':case['id'],'source':'user_report','outcome':case['outcome'],
            'scope':origin['objective'][:120], 'step':case['step'][:120],
            'report_excerpt':case['text'][:240], 'retrieval':basis, **review})
    return output


def describe(goals):
    rows = []
    for origin, case in cases(goals):
        if case['withdrawn']:continue
        review = assessment(goals, origin, case)
        label = ('risultato confermato da te' if case['outcome'] == 'confirmed' else
                 'ipotesi contestata' if review['status'] == 'contested' else
                 'precauzione sostenuta dai tuoi riscontri' if review['status'] == 'supported_by_user_reports' else 'ipotesi da verificare')
        rows.append(f'[{case["id"]}] {label}\nCompito: {origin["objective"]}\n'
                    f'Passo: {case["step"]}\nRiscontro: {case["text"]}\n'
                    f'Altri compiti: {review["supporting_tasks"]} utili, {review["counterexamples"]} contrari.')
    if not rows:return 'Non ho ancora esiti di piani confermati o corretti da cui ricavare esperienze utilizzabili.'
    return ('Queste esperienze derivano dai tuoi riscontri, non da verifiche fisiche indipendenti. '
            'Dalle difficoltà ricavo precauzioni da valutare nei compiti simili, senza considerarle cause dimostrate.\n\n'
            +(f'Mostro le ultime 8 di {len(rows)} esperienze disponibili.\n\n' if len(rows)>8 else '')
            +'\n\n'.join(rows[-8:])+'\n\nPer valutare un’ipotesi dopo un risultato confermato: '
            '«Lezione utile: ID» oppure «Lezione non utile: ID». Per ritirarla: «Dimentica lezione: ID».')


INSTRUCTION = ('Esperienze precedenti riferite dall’utente, con ambito limitato. '
    'Usale solo se pertinenti al nuovo compito. Un problema passato suggerisce una precauzione da verificare, '
    'non una causa certa o una legge generale. Un risultato confermato non prova che la strategia abbia funzionato. '
    'Per le ipotesi contestate cita il limite, senza raccomandarle come regole. '
    'Un collegamento confirmed_task_bridge indica che l’utente ha trovato utile l’esperienza in un altro compito: '
    'non dimostra che i due contesti siano identici. '
    'Se una precauzione è utile nel piano, indica brevemente la precedente esperienza nelle note, senza inventare ricordi.')
