"""Procedural experience, inside the existing module-state DB, never answer recall.

Verified executions are not user approval. Only independent, explicitly approved
choices may support a suggestion; suggestions always ask for consent and cannot
reinforce themselves. No raw operands, answers or autobiographical facts stored.
"""
from copy import deepcopy
import hashlib
import re
import uuid

OPERATIONS = {'letters', 'characters', 'codepoints', 'occurrences', 'calculation'}
LIMIT = 256


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class ToolStrategyLearning:
    def __init__(self, state_manager):
        self.store = state_manager

    @staticmethod
    def key(user):
        if not isinstance(user, str) or not user:
            raise ValueError('User scope required')
        return 'meta_learning_tools:' + fingerprint(user)

    @staticmethod
    def empty(epoch=0):
        return {'version': 1, 'epoch': epoch, 'checkpoint':0, 'executions': {}, 'events': {}, 'votes': {}}

    @classmethod
    def valid(cls, state, owner=None):
        if state is None:
            return cls.empty()
        if (not isinstance(state, dict) or set(state) != {'version','epoch','checkpoint','executions','events','votes'}
                or type(state.get('version')) is not int or state['version'] != 1
                or type(state.get('epoch')) is not int or not 0 <= state['epoch'] < 2**53
                or type(state.get('checkpoint')) is not int or not 0 <= state['checkpoint'] < 2**53
                or any(not isinstance(state.get(k), dict) for k in ('executions', 'events', 'votes'))
                or len(state['events']) > LIMIT or len(state['votes']) > LIMIT):
            raise ValueError('Invalid tool-learning state')
        if any(k not in OPERATIONS or type(v) is not int or not 0 <= v < 2**53 for k,v in state['executions'].items()):
            raise ValueError('Invalid tool execution totals')
        for event, row in state['events'].items():
            if (not re.fullmatch(r'[a-f0-9]{32}', event) or not cls.valid_descriptor(row, include_event=False)
                    or (owner is not None and row['owner'] != owner)
                    or row.get('feedback') not in (None, True, False) or type(row.get('feedback')) not in (type(None), bool)):
                raise ValueError('Invalid tool experience')
        for signature, vote in state['votes'].items():
            if (not re.fullmatch(r'[a-f0-9]{64}', signature) or not isinstance(vote, dict)
                    or set(vote) != {'choice','event','approved'} or type(vote.get('approved')) is not bool
                    or type(vote.get('choice')) is not bool or not re.fullmatch(r'[a-f0-9]{32}', str(vote.get('event','')))):
                raise ValueError('Invalid tool strategy vote')
        return deepcopy(state)

    @staticmethod
    def valid_descriptor(row, *, include_event=True):
        fields = {'owner','operation','signature','epoch','verifier','choice','independent_choice'} | ({'event'} if include_event else {'feedback'})
        return (isinstance(row, dict) and set(row) == fields and row.get('verifier') == 'host_exact_v1'
                and row.get('operation') in OPERATIONS
                and isinstance(row.get('signature'), str) and bool(re.fullmatch(r'[a-f0-9]{64}', row['signature']))
                and isinstance(row.get('owner'), str) and bool(re.fullmatch(r'[a-f0-9]{64}', row['owner']))
                and type(row.get('epoch')) is int and 0 <= row['epoch'] < 2**53
                and type(row.get('independent_choice')) is bool
                and type(row.get('choice')) in (type(None), bool)
                and (not include_event or bool(re.fullmatch(r'[a-f0-9]{32}', str(row.get('event',''))))))

    def view(self, user):
        state = self.valid(self.store.load_state(self.key(user), strict=True), fingerprint(user))
        yes = sum(v['choice'] is True and v['approved'] for v in state['votes'].values())
        no = sum(v['choice'] is False and v['approved'] for v in state['votes'].values())
        rejected_yes = sum(v['choice'] is True and not v['approved'] for v in state['votes'].values())
        rejected_no = sum(v['choice'] is False and not v['approved'] for v in state['votes'].values())
        total = yes + no
        yes_support, no_support = (yes+1)/(total+rejected_yes+2), (no+1)/(total+rejected_no+2)
        choice = yes_support > no_support
        posterior = max(yes_support,no_support)
        suggestion = choice if total >= 3 and posterior >= .8 else None
        return {'epoch': state['epoch'], 'executions': dict(state['executions']),
                'confirmed_tasks': total, 'with_overlap': yes, 'without_overlap': no,
                'rejected_tasks':rejected_yes+rejected_no,
                'suggested_overlap': suggestion, 'support': posterior,
                'scope': 'recent_distinct_approved_overlap_choices', 'requires_confirmation': True}

    def descriptor(self, user, source, evidence, *, verified):
        if verified is not True or source not in ('verified_text_count', 'verified_calculation'):
            return None
        row = evidence[0] if source == 'verified_text_count' and len(evidence) == 1 and isinstance(evidence[0], dict) else {}
        if source == 'verified_text_count' and (row.get('scope') != 'explicit_literal_only'
                or type(row.get('value')) is not int or row['value'] < 0 or row.get('operation') not in OPERATIONS-{'calculation'}
                or not re.fullmatch(r'[a-f0-9]{64}', str(row.get('input_sha256','')))
                or (row.get('operation') == 'occurrences' and not re.fullmatch(r'[a-f0-9]{64}', str(row.get('needle_sha256',''))))):
            return None
        operation = row.get('operation', 'calculation')
        signature = fingerprint(operation + ':' + str(row.get('input_sha256','')) + ':' + str(row.get('needle_sha256','')))
        # A prompted/suggested choice is not an independent training example.
        independent = (operation == 'occurrences' and row.get('clarification_resolved') is True
                       and row.get('choice_origin') == 'explicit_user_choice' and type(row.get('overlapping')) is bool)
        return {'event': uuid.uuid4().hex, 'owner': fingerprint(user), 'operation': operation, 'signature': signature,
                'epoch': self.view(user)['epoch'], 'verifier': 'host_exact_v1',
                'choice': row.get('overlapping') if operation == 'occurrences' and row.get('clarification_resolved') is True else None,
                'independent_choice': independent}

    def observe(self, user, descriptor, *, delivery_sequence=None):
        if not self.valid_descriptor(descriptor) or descriptor['owner'] != fingerprint(user):
            return {'status': 'not_verified'}
        result = {}
        def update(raw):
            state = self.valid(raw, fingerprint(user))
            if descriptor['epoch'] != state['epoch']:
                result['status'] = 'stale';return state
            if delivery_sequence is not None:
                if type(delivery_sequence) is not int or not 0 < delivery_sequence < 2**53:
                    raise ValueError('Invalid tool delivery checkpoint')
                if delivery_sequence <= state['checkpoint']:
                    result['status'] = 'duplicate';return state
            event = descriptor['event']
            if event in state['events']:
                if any(state['events'][event].get(k) != v for k,v in descriptor.items() if k != 'event'):
                    raise ValueError('Conflicting tool event')
                result['status'] = 'duplicate';return state
            record = {k:v for k,v in descriptor.items() if k != 'event'}
            record['feedback'] = None
            state['events'][event] = record
            if delivery_sequence is not None:state['checkpoint']=delivery_sequence
            op = descriptor['operation']
            state['executions'][op] = min(2**53-1, state['executions'].get(op,0)+1)
            while len(state['events']) > LIMIT:
                state['events'].pop(next(iter(state['events'])))
            result['status'] = 'observed'
            return state
        self.store.transact_state(self.key(user), update)
        return result

    def feedback(self, user, descriptor, positive):
        if not self.valid_descriptor(descriptor) or descriptor['owner'] != fingerprint(user) or type(positive) is not bool:
            return {'status': 'not_saved'}
        result = {}
        def update(raw):
            state = self.valid(raw, fingerprint(user))
            event = descriptor['event']
            record = state['events'].get(event)
            if descriptor['epoch'] != state['epoch'] or record is None:
                result['status'] = 'stale';return state
            if any(record.get(k) != v for k,v in descriptor.items() if k != 'event'):
                raise ValueError('Conflicting feedback target')
            if record['feedback'] is positive:
                result['status'] = 'duplicate_feedback';return state
            record['feedback'] = positive
            signature = record['signature']
            if type(record['choice']) is bool:
                if positive and record['independent_choice']:
                    state['votes'].pop(signature, None)
                    state['votes'][signature] = {'choice': record['choice'], 'event': event, 'approved':True}
                elif not positive:
                    state['votes'].pop(signature, None)
                    state['votes'][signature] = {'choice': record['choice'], 'event': event, 'approved':False}
                elif state['votes'].get(signature, {}).get('event') == event:
                    state['votes'].pop(signature)
            while len(state['votes']) > LIMIT:
                state['votes'].pop(next(iter(state['votes'])))
            result['status'] = 'feedback_recorded'
            return state
        self.store.transact_state(self.key(user), update)
        return result

    def reset(self, user):
        def update(raw):
            state = self.valid(raw, fingerprint(user))
            if state['epoch'] >= 2**53-1:
                raise ValueError('Tool epoch exhausted')
            return self.empty(state['epoch']+1)
        self.store.transact_state(self.key(user), update)
        return {'status': 'reset'}


def feedback_target(history):
    if not history:
        return None
    last = history[-1]
    if getattr(last, 'role', None) != 'assistant':
        return None
    meta = getattr(last, 'metadata', {}) or {}
    if meta.get('source') in ('verified_text_count', 'verified_calculation') and meta.get('knowledge_verified') is True:
        target = meta.get('tool_experience')
    elif meta.get('source') == 'tool_learning_feedback':
        target = meta.get('tool_feedback_target')
    else:
        return None
    return deepcopy(target) if ToolStrategyLearning.valid_descriptor(target) else None


def feedback_signal(message):
    from .answer_recall import feedback_kind, normalize
    kind = feedback_kind(message)
    if kind == 'negative' and normalize(message) not in {
        'risposta sbagliata','la risposta è sbagliata','sbagliato','non è corretto',
        'wrong answer','hai sbagliato','ti sbagli'}:
        return None  # Corrections containing new facts remain ordinary user input.
    return kind


def control(message):
    text = re.sub(r'\s+', ' ', message.strip().casefold()).rstrip('.!?')
    if text in {'cosa hai imparato sui conteggi', 'quali strategie di conteggio hai imparato'}:
        return 'view'
    if text in {'dimentica le strategie di conteggio apprese', 'azzera le strategie di conteggio apprese'}:
        return 'reset'
    return None
