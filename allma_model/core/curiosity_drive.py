"""Grounded conversational curiosity, derived from the existing dialogue.

No second curiosity archive: admission receipts live with assistant messages.
The module can suggest a focus; it cannot invent experience or contact users.
"""
from __future__ import annotations
from hashlib import sha256
import re
from allma_model.learning_system.plan_experience import tokens
from allma_model.utils.output_contract import requested_contract, requested_sentence_count


DECLINE = re.compile(r"\b(?:non (?:farmi|fare|chiedermi|voglio) (?:altre )?domande|non (?:ne )?parliamo|cambiamo (?:argomento|discorso)|basta domande|don't ask|stop asking|change (?:the )?subject)\b", re.I)
EXPLORE = re.compile(r'\b(?:perché|come mai|spiegami|approfondisci|why|explain|tell me more)\b', re.I)


def followup_declined(text):
    return bool(DECLINE.search(text or ''))


def grounded_focus(text, history, user=None, conversation=None, goal=None):
    """Select at most one documented open thread; no model inference required."""
    if not isinstance(text, str) or not text.strip() or requested_contract(text) or requested_sentence_count(text):
        return None
    rows = [m for m in history[-24:] if (user is None or getattr(m,'user_id',None) == user)
            and (conversation is None or getattr(m,'conversation_id',None) == conversation)]
    # A closed topic stays closed in this conversation. Explicit exploration in
    # the current turn permits that turn's answer, not unsolicited follow-ups.
    closed = followup_declined(text) or any(followup_declined(m.content) for m in rows if m.role == 'user')
    if closed and not EXPLORE.search(text):
        return None
    if EXPLORE.search(text):
        return {'version':1,'kind':'requested_exploration','reference':sha256(text.encode()).hexdigest()[:16]}
    if closed:
        return None
    receipts = [m.metadata.get('curiosity_focus') for m in rows if m.role == 'assistant']
    if any(isinstance(r,dict) and r.get('kind') == 'open_question' for r in receipts[-4:]):
        return None
    features = tokens(text)
    # A failed answer is still an unresolved question. A later valid answer or
    # a user closing the topic prevents reopening it. Text never leaves history.
    for index in range(len(rows)-1, 0, -1):
        answer, question = rows[index], rows[index-1]
        if answer.role != 'assistant' or question.role != 'user' or answer.metadata.get('is_valid') is not False:
            continue
        reference = sha256(question.content.encode()).hexdigest()[:16]
        if any(isinstance(r,dict) and r.get('reference') == reference for r in receipts):
            continue
        if any(m.role == 'assistant' and m.metadata.get('is_valid') is True for m in rows[index+1:]):
            continue
        shared = features & tokens(question.content)
        if len(shared) >= 2:
            return {'version':1,'kind':'open_question','reference':reference,
                'topic_words':sorted(shared)[:6]}
    if isinstance(goal,dict) and goal.get('objective') and goal.get('next_step'):
        shared = features & tokens(goal['objective'])
        if len(shared) >= 2:
            return {'version':1,'kind':'goal','reference':str(goal.get('id','')),
                'revision':goal.get('revision'),'topic_words':sorted(shared)[:6]}
    return None


class CuriosityDrive:
    def __init__(self):
        self._trigger_count = self._total_processed = 0

    def process(self, user_input, context):
        self._total_processed += 1
        focus = grounded_focus(user_input, context.get('dialogue_history', []),
            context.get('user_id'), context.get('conversation_id'), context.get('goal_context'))
        result = {'user_prefix':[], 'system_instruction':[],
            'metadata':{'triggered':bool(focus),'score':1.0 if focus else 0.0,'focus':focus}}
        if focus:
            self._trigger_count += 1
            if focus['kind'] == 'requested_exploration':
                instruction = 'Approfondisci la domanda attuale con un collegamento pertinente, solo se aiuta a spiegarla. Distingui ciò che sai da ciò che resta incerto; non aggiungere domande personali per routine.'
            elif focus['kind'] == 'open_question':
                instruction = 'La domanda attuale riprende un tema rimasto senza risposta valida. Rispondi prima al contenuto attuale; se manca un dato indispensabile, chiedi un solo chiarimento pertinente, senza ripetere domande già risolte.'
            else:
                instruction = 'Il tema attuale è pertinente a un obiettivo già presente nel contesto. Se utile, collega la spiegazione al prossimo passo documentato, senza introdurre nuovi obiettivi né dichiarare azioni eseguite.'
            result['system_instruction'].append(instruction)
        return result

    def get_stats(self):
        return {'total_processed':self._total_processed,'trigger_count':self._trigger_count,
            'trigger_rate':round(self._trigger_count/max(self._total_processed,1),3)}
