"""User-admitted task continuity in the existing ALLMA authority archive.

The conversation is the event history. This section holds current task state,
source references and one transactional replay checkpoint, never model commands.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import re
import time
import uuid

from allma_model.utils.persistence import StateRecoveryRequired


KINDS = {'create', 'progress', 'criterion', 'next_step', 'correct', 'result',
         'confirm', 'reject', 'pause', 'resume', 'reopen', 'cancel', 'initiative',
         'adopt_plan','step_result','step_confirm','step_reject',
         'lesson_positive','lesson_negative','lesson_forget'}


def valid_request(request):
    if not isinstance(request, dict) or not isinstance(request.get('kind'), str) or request['kind'] not in KINDS:
        return False
    kind = request['kind']
    fields = {'create':{'text','criterion','next_step'}, 'progress':{'text','next_step'},
              'initiative':{'enabled'}}.get(kind, {'text'} if kind in {'criterion','next_step','correct','result','reject','step_result','step_reject','lesson_positive','lesson_negative','lesson_forget'} else set())
    if set(request)-{'kind','target'}-fields:
        return False
    for key in set(request)-{'kind','enabled'}:
        if not isinstance(request[key], str) or not request[key].strip() or len(request[key]) > 1000:
            return False
    return ((kind == 'initiative' and type(request.get('enabled')) is bool)
            or (kind != 'initiative' and ('text' not in fields or bool(request.get('text','').strip()))))


def valid_control(control):
    from .goal_plans import valid_proposal
    return (isinstance(control, dict) and valid_request(control.get('request'))
            and control.get('kind') == control['request']['kind']
            and set(control) == ({'kind','request'} if control['kind'] == 'create' else
                {'kind','request','goal_id','revision','selected_plan'} if control['kind'] == 'adopt_plan' else
                {'kind','request','goal_id','revision'})
            and (control['kind'] != 'adopt_plan' or (isinstance(control.get('selected_plan'),dict)
                 and valid_proposal(control['selected_plan'].get('proposal'))
                 and all(isinstance(control['selected_plan'].get(k),str) and control['selected_plan'][k]
                         for k in ('timestamp','conversation'))))
            and (control['kind'] == 'create' or
                 (isinstance(control.get('goal_id'), str) and bool(control['goal_id'])
                  and type(control.get('revision')) is int and control['revision'] > 0)))


def valid_workflow(value):
    from .goal_plans import valid_plan
    from allma_model.learning_system.plan_experience import valid as valid_learning
    return (isinstance(value, dict) and type(value.get('version')) is int and value['version'] == 1
            and type(value.get('revision')) is int and value['revision'] > 0
            and isinstance(value.get('phase'), str) and value['phase'] in {'active','paused','awaiting_verification','completed','cancelled'}
            and all(isinstance(value.get(k), str) and len(value[k]) <= 1000
                    for k in ('criterion','next_step','progress'))
            and type(value.get('initiative')) is bool
            and isinstance(value.get('outcomes'), dict)
            and all(type(value['outcomes'].get(k)) is int and value['outcomes'][k] >= 0
                    for k in ('corrections','rejected','confirmed'))
            and valid_reference(value.get('last_event'))
            and (value.get('plan') is None or valid_plan(value['plan']))
            and ('learning' not in value or valid_learning(value['learning']))
            and (value.get('result') is None or
                 (isinstance(value['result'], dict) and value['result'].get('source') == 'user_report'
                  and isinstance(value['result'].get('text'), str)
                  and bool(value['result']['text'].strip()) and len(value['result']['text']) <= 1000
                  and bool(value['criterion']) and valid_reference(value['result'].get('event'))
                  and type(value['result'].get('criterion_revision')) is int
                  and 0 < value['result']['criterion_revision'] <= value['revision']))
            and (value.get('verification') is None or value.get('verification') == 'confirmed_by_user')
            and (value.get('verification') is None or value['phase'] == 'completed')
            and (value.get('phase') != 'awaiting_verification' or value.get('result') is not None)
            and (value.get('phase') != 'completed' or
                 (value.get('verification') == 'confirmed_by_user' and value.get('result') is not None)))


def valid_reference(reference):
    if (not isinstance(reference,dict) or reference.get('source') != 'user_report'
            or any(not isinstance(reference.get(k),str) or not reference[k]
                   for k in ('event','conversation','timestamp','input_sha256'))
            or not re.fullmatch(r'[0-9a-f]{64}',reference['input_sha256'])):
        return False
    try:datetime.fromisoformat(reference['timestamp'])
    except ValueError:return False
    return True


def valid_archive(state):
    if not isinstance(state,dict) or not isinstance(state.get('goals'),dict):return False
    checkpoint=state.get('workflow_checkpoint',0)
    if type(checkpoint) is not int or not 0 <= checkpoint < 2**53:return False
    from .action_authority import ActionAuthority
    for goal in state['goals'].values():
        if isinstance(goal,dict) and 'workflow' in goal:
            if (checkpoint == 0 or not ActionAuthority._valid_goal(goal) or not valid_workflow(goal['workflow'])
                    or (goal['status'] == 'completed') != (goal['workflow']['phase'] == 'completed')
                    or (goal['status'] == 'revoked') != (goal['workflow']['phase'] == 'cancelled')):
                return False
            for case in goal['workflow'].get('learning',{}).get('cases',{}).values():
                expected = hashlib.sha256((goal['user_id']+'\0'+case['reviewed']['event']).encode()).hexdigest()[:16]
                if case['id'] != expected:return False
    return True


class GoalProgress:
    def __init__(self, authority):
        self.authority = authority

    def _state(self):
        authority = self.authority
        raw = authority.store.get(authority.SECTION) if authority.store else authority._transient
        if authority.store is not None and authority.store.load_error is not None:
            raise StateRecoveryRequired('Stato cognitivo non leggibile')
        state = deepcopy(raw) if raw else {'goals':{}}
        if not valid_archive(state):raise StateRecoveryRequired('Archivio obiettivi non valido')
        return state

    @property
    def delivery_checkpoint(self):
        with self.authority.lock:
            return self._state().get('workflow_checkpoint', 0)

    def goals(self, user):
        with self.authority.lock:
            return [dict(deepcopy(goal), id=key) for key, goal in self._state()['goals'].items()
                    if isinstance(goal, dict) and goal.get('user_id') == user and 'workflow' in goal]

    def prepare(self, user, request):
        """Resolve a host-parsed explicit command; never guess between tasks."""
        if not valid_request(request):raise ValueError('Invalid task request')
        goals = self.goals(user)
        kind = request['kind']
        if kind == 'create':
            if any(g['status'] == 'active' and g['objective'].casefold() == request['text'].casefold() for g in goals):
                return None, 'Esiste già un obiettivo attivo con questo nome. Puoi aggiornarlo o annullarlo.'
            return {'kind':kind, 'request':deepcopy(request)}, None
        target = request.get('target')
        from allma_model.learning_system.plan_experience import FEEDBACK_KINDS, find, has_reviewed_result
        lesson = None
        if kind in FEEDBACK_KINDS:
            lesson = find(goals,request['text'])
            if lesson is None or lesson[1]['withdrawn'] or lesson[1]['outcome'] != 'rejected':
                return None, 'Non trovo un’ipotesi utilizzabile con questo identificatore nel tuo profilo.'
            if kind == 'lesson_forget':
                target = lesson[0]['objective']
        matches = ([g for g in goals if g['id'] == lesson[0]['id']] if kind == 'lesson_forget' else
                   [g for g in goals if g['objective'].casefold() == target.casefold()] if target else
                   [g for g in goals if g['status'] == 'active'])
        if not matches:
            return None, 'Non trovo un obiettivo attivo corrispondente. Puoi crearne uno con «Nuovo obiettivo: …».'
        if len(matches) != 1:
            return None, 'A quale obiettivo ti riferisci? ' + '; '.join('«'+g['objective']+'»' for g in matches[:8]) + '. Usa «Per l’obiettivo “nome”: …».'
        goal = matches[0]
        wf = goal['workflow']
        if kind == 'reopen' and goal['status'] == 'revoked':
            return None, 'Questo obiettivo è annullato. Per ripartire, crea un nuovo obiettivo.'
        if goal['status'] != 'active' and kind not in FEEDBACK_KINDS | {'reopen'}:
            return None, 'Questo obiettivo è già concluso. Puoi riaprire esplicitamente un obiettivo completato.'
        if kind in {'lesson_positive','lesson_negative'}:
            if goal['id'] == lesson[0]['id']:
                return None, 'Il compito che ha originato l’ipotesi non è una nuova verifica. Valutala in un altro obiettivo.'
            if not has_reviewed_result(goal,kind == 'lesson_positive'):
                return None, 'Prima della valutazione serve un risultato del nuovo compito confermato da te, oppure corretto per un esito negativo.'
            learning = wf.get('learning',{})
            if request['text'] not in learning.get('feedback',{}) and len(learning.get('feedback',{})) >= 32:
                return None, 'Questo obiettivo ha già 32 valutazioni di ipotesi. Usa un nuovo compito per altre verifiche.'
        if kind == 'result' and not wf['criterion']:
            return None, 'Prima definiamo il criterio: come riconosceremo che l’obiettivo è raggiunto? Usa «Criterio obiettivo: …».'
        if kind == 'confirm' and (wf['phase'] != 'awaiting_verification' or not wf['result']):
            return None, 'Non c’è un risultato in attesa di conferma. Registralo prima con «Risultato obiettivo: …».'
        if kind == 'reject' and not wf['result']:
            return None, 'Non c’è un risultato da correggere. Puoi registrare il progresso o modificare il prossimo passo.'
        if kind.startswith('step_'):
            plan = wf.get('plan')
            if not plan or plan['status'] != 'active' or plan['index'] >= len(plan['steps']):
                return None, 'Non c’è un passo attivo da aggiornare. Chiedi un piano, adottalo o rivedi quello precedente.'
            step = plan['steps'][plan['index']]
            if kind in {'step_confirm','step_reject'} and step['status'] != 'awaiting_confirmation':
                return None, 'Prima registra «Risultato del passo: …». La sola richiesta di avanzare non conferma il lavoro svolto.'
        return {'kind':kind, 'request':deepcopy(request), 'goal_id':goal['id'], 'revision':wf['revision']}, None

    def apply(self, user, control, reference, sequence):
        if not valid_control(control) or type(sequence) is not int or not 0 < sequence < 2**53:
            raise ValueError('Invalid goal update')
        if not valid_reference(reference):
            raise ValueError('Goal updates need an attributed durable event')
        with self.authority.lock:
            state = self._state()
            if sequence <= state.get('workflow_checkpoint', 0):
                return {'status':'replay' if sequence == state.get('workflow_checkpoint') else 'stale'}
            request, kind = control['request'], control['kind']
            if kind == 'create':
                if len(state['goals']) >= 256:
                    raise RuntimeError('Goal archive full')
                key = uuid.uuid5(uuid.NAMESPACE_OID, user+'\0'+reference['event']).hex
                wf = {'version':1, 'revision':1, 'phase':'active', 'criterion':request.get('criterion',''),
                      'next_step':request.get('next_step',''), 'progress':'', 'result':None, 'verification':None,
                      'initiative':False, 'outcomes':{'corrections':0,'rejected':0,'confirmed':0},
                      'last_event':deepcopy(reference)}
                goal = {'user_id':user, 'objective':request['text'], 'event_id':reference['event'],
                        'priority':1, 'status':'active', 'allowed_actions':{'review_goal':'read'},
                        'created_at':time.time(), 'workflow':wf}
                state['goals'][key] = goal
            else:
                key = control['goal_id']
                goal = state['goals'].get(key)
                if goal is None or goal.get('user_id') != user:
                    raise ValueError('Goal ownership mismatch')
                wf = goal['workflow']
                from allma_model.learning_system.plan_experience import FEEDBACK_KINDS, find, has_reviewed_result, empty
                if wf['revision'] != control['revision'] or (goal['status'] != 'active' and kind not in FEEDBACK_KINDS | {'reopen'}):
                    report = {'status':'stale','goal_id':key,'kind':kind}
                    state.update(workflow_checkpoint=sequence, workflow_report=report)
                    self.authority._save(state)
                    return report
                if kind == 'adopt_plan':
                    from .plan_review import review
                    candidate = control['selected_plan']['proposal']
                    if candidate['goal_id'] != key or candidate['goal_revision'] != control['revision']:
                        raise ValueError('Plan refers to a different goal revision')
                    checked = review(candidate['steps'],wf['criterion'])
                    if checked['status'] == 'needs_review':
                        report = {'status':'review_required','goal_id':key,'kind':kind,'revision':wf['revision'],'review':checked}
                        state.update(workflow_checkpoint=sequence,workflow_report=report)
                        self.authority._save(state)
                        return deepcopy(report)
                prior_result = deepcopy(wf.get('result'))
                prior_step = None
                if kind.startswith('step_') and wf.get('plan') and wf['plan']['index'] < len(wf['plan']['steps']):
                    index = wf['plan']['index'];step = wf['plan']['steps'][index]
                    prior_step = {'index':index,'text':step['text']}
                    prior_result = deepcopy(step.get('result'))
                wf['revision'] += 1
                if kind in {'correct','criterion','next_step','progress','reopen'} and wf.get('plan'):
                    wf['plan']['status'] = 'needs_review'
                    if kind != 'next_step' and 'next_step' not in request:
                        wf['next_step'] = ''
                if kind in {'correct','criterion','next_step','progress','reopen','reject'}:
                    wf.update(result=None, verification=None)
                    if wf['phase'] != 'paused' or kind in {'reopen','reject'}:
                        wf['phase'] = 'active'
                if kind == 'correct':
                    goal['objective'] = request['text'];wf['outcomes']['corrections'] += 1
                elif kind in {'criterion','next_step','progress'}:
                    wf[kind] = request['text']
                    if kind != 'progress':wf['outcomes']['corrections'] += 1
                    if 'next_step' in request:wf['next_step'] = request['next_step']
                elif kind == 'result':
                    if not wf['criterion']:raise ValueError('Missing completion criterion')
                    wf.update(phase='awaiting_verification', verification=None,
                              result={'text':request['text'], 'source':'user_report',
                                      'criterion_revision':wf['revision'], 'event':deepcopy(reference)})
                elif kind == 'confirm':
                    if wf['phase'] != 'awaiting_verification' or not wf['result']:
                        raise ValueError('No current result to confirm')
                    goal['status'] = 'completed';wf.update(phase='completed', verification='confirmed_by_user')
                    wf['outcomes']['confirmed'] += 1
                elif kind == 'reject':
                    wf['progress'] = request['text'];wf['outcomes']['rejected'] += 1
                elif kind == 'reopen':goal['status'] = 'active'
                elif kind == 'cancel':goal['status'] = 'revoked';wf.update(phase='cancelled', initiative=False)
                elif kind == 'pause':wf['phase'] = 'paused'
                elif kind == 'resume':
                    wf['phase'] = 'awaiting_verification' if wf['result'] else 'active'
                elif kind == 'initiative':wf['initiative'] = request['enabled']
                elif kind in FEEDBACK_KINDS:
                    owned = [dict(g,id=k) for k,g in state['goals'].items() if g.get('user_id') == user and 'workflow' in g]
                    chosen = find(owned,request['text'])
                    if chosen is None or chosen[1]['withdrawn'] or chosen[1]['outcome'] != 'rejected':
                        raise ValueError('Lesson source unavailable')
                    if kind == 'lesson_forget':
                        if chosen[0]['id'] != key:raise ValueError('Lesson withdrawal target mismatch')
                        chosen[1]['withdrawn'] = True
                    else:
                        if chosen[0]['id'] == key or not has_reviewed_result(goal,kind == 'lesson_positive'):
                            raise ValueError('Lesson evaluation needs another confirmed task')
                        learning = wf.setdefault('learning',empty())
                        if request['text'] not in learning['feedback'] and len(learning['feedback']) >= 32:
                            raise ValueError('Too many lesson evaluations in one task')
                        learning['feedback'][request['text']] = {'positive':kind == 'lesson_positive',
                            'text':request['text'],'event':deepcopy(reference)}
                elif kind == 'adopt_plan':
                    chosen = control['selected_plan']['proposal']
                    if chosen['goal_id'] != key or chosen['goal_revision'] != control['revision']:
                        raise ValueError('Plan refers to a different goal revision')
                    wf['plan'] = {'version':1,'proposal_id':chosen['id'], 'source':'user_admitted_model_proposal',
                        'status':'active','index':0,'adopted_by':deepcopy(reference),
                        'steps':[{'text':text,'status':'pending','result':None} for text in chosen['steps']]}
                    if chosen.get('notes'):wf['plan']['notes'] = chosen['notes']
                    wf.update(next_step=chosen['steps'][0], result=None, verification=None)
                    if wf['phase'] != 'paused':wf['phase'] = 'active'
                elif kind.startswith('step_'):
                    plan = wf.get('plan')
                    if not plan or plan['status'] != 'active' or plan['index'] >= len(plan['steps']):
                        raise ValueError('No active planned step')
                    step = plan['steps'][plan['index']]
                    if kind == 'step_result':
                        step.update(status='awaiting_confirmation',result={'text':request['text'],'event':deepcopy(reference)})
                    else:
                        if step['status'] != 'awaiting_confirmation':raise ValueError('No step result to review')
                        if kind == 'step_confirm':
                            step.update(status='confirmed_by_user',confirmed_by=deepcopy(reference))
                            plan['index'] += 1
                            wf['next_step'] = plan['steps'][plan['index']]['text'] if plan['index'] < len(plan['steps']) else ''
                            wf['progress'] = f'Passi confermati da te: {plan["index"]}/{len(plan["steps"])}.'
                            wf['outcomes']['confirmed'] += 1
                        else:
                            step.update(status='pending',result=None)
                            wf['progress'] = 'Correzione del passo corrente: '+request['text']
                            wf['outcomes']['rejected'] += 1
                    wf.update(result=None,verification=None)
                    if wf['phase'] != 'paused':wf['phase'] = 'active'
                if kind in {'confirm','cancel'} and wf.get('plan'):
                    wf['plan']['status'] = 'closed'
                wf['last_event'] = deepcopy(reference)
                from allma_model.learning_system.plan_experience import observe
                outcome_ref = dict(reference,text=request['text']) if kind in {'reject','step_reject'} else reference
                observe(goal,kind,outcome_ref,prior_result,prior_step)
            if not valid_workflow(wf) or not self.authority._valid_goal(goal):
                raise ValueError('Invalid resulting task state')
            report = {'status':'applied','goal_id':key,'kind':kind,'revision':wf['revision'],
                      'verification':wf['verification'],'source':'user_report'}
            if kind == 'adopt_plan':report['plan_review'] = checked
            state.update(workflow_checkpoint=sequence, workflow_report=report)
            self.authority._save(state)
            return deepcopy(report)

    def report(self, sequence):
        with self.authority.lock:
            state = self._state()
            return deepcopy(state.get('workflow_report')) if state.get('workflow_checkpoint') == sequence else None

    def experience_view(self, user):
        from allma_model.learning_system.plan_experience import describe
        return describe(self.goals(user))

    def initiative(self, user):
        goals = [g for g in self.goals(user) if g['status'] == 'active'
                 and g['workflow']['phase'] == 'active' and g['workflow']['initiative']
                 and g['workflow']['next_step']]
        if not goals:return None
        goal = sorted(goals, key=lambda g:(-g['priority'],g['created_at']))[0]
        return {'id':goal['id'],'revision':goal['workflow']['revision'],
                'objective':goal['objective'],'next_step':goal['workflow']['next_step'],
                'source':'user_report'}

    def current_reference(self, user, reference):
        return any(g['id'] == reference.get('id') and g['workflow']['revision'] == reference.get('revision')
                   and g['status'] == 'active' and g['workflow']['phase'] == 'active'
                   and g['workflow']['initiative'] for g in self.goals(user))
