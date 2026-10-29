"""Literal navigation of the user's available turns, without model inference.

Only explicit requests to quote a question are handled. General follow-ups and
questions about its meaning stay with the normal dialogue pipeline.
"""
from dataclasses import dataclass
import hashlib
import re

from allma_model.core.autobiographical_identity import normalized


@dataclass(frozen=True)
class QuestionReference:
    grounded: tuple
    target: dict | None = None


def _key(turn):
    return {'timestamp': turn.timestamp.isoformat(),
            'sha256': hashlib.sha256(turn.content.encode()).hexdigest()}


def question_reply(message, history, user_id, conversation_id):
    query = normalized(message)
    previous = bool(re.fullmatch(
        r'(?:che cosa|cosa|che domanda|quale domanda) ti (?:ho|avevo) (?:chiesto|domandato|fatto)'
        r'(?: (?:prima|poco fa|(?:nella |con la )?(?:precedente|ultima) domanda))', query))
    previous = previous or query in {
        'qual era la mia domanda precedente', 'qual e stata la mia ultima domanda',
        'qual era la domanda precedente', 'ricordi la mia ultima domanda'}
    anchor = re.fullmatch(
        r'(?:che|quale) domanda ti ho fatto (?:subito )?(dopo|prima) '
        r'(?:la domanda\s*:\s*|(?:la domanda\s+)?[«“"])(.+?)[»”"]?', message.strip().rstrip('?!.'), re.I)
    followup = query in {'e in quella dopo di domanda', 'e la domanda dopo',
                        'e quella dopo', 'e quella prima', 'e la domanda prima'}
    if not (previous or anchor or followup):
        return None
    turns = [turn for turn in history if turn.conversation_id == conversation_id
             and (turn.user_id or turn.metadata.get('user_id')) == user_id]
    users = [turn for turn in turns if turn.role == 'user' and turn.metadata.get('is_valid') is not False]
    index = None
    if previous:
        index = len(users)-1
    elif anchor:
        text = normalized(anchor[2].strip(' «»“”"'))
        matches = [i for i, turn in enumerate(users) if normalized(turn.content) == text]
        if len(matches) > 1:
            return QuestionReference(('Trovo più occorrenze di quella domanda. A quale ti riferisci?',
                                      'conversation_question_clarification', []))
        if matches:
            index = matches[0] + (1 if anchor[1].casefold() == 'dopo' else -1)
    else:
        last = turns[-1] if turns else None
        if last is None or last.role != 'assistant' or last.metadata.get('source') != 'conversation_question_recall':
            return None
        key = last.metadata.get('conversation_reference')
        matches = [i for i, turn in enumerate(users) if _key(turn) == key]
        if len(matches) == 1:
            index = matches[0] + (-1 if 'prima' in query else 1)
    if index is None or not 0 <= index < len(users):
        return QuestionReference(('Non trovo quella domanda nella parte di conversazione disponibile.',
                                  'conversation_question_absent', []))
    target = users[index]
    return QuestionReference((f'Mi hai chiesto: «{target.content}».',
                              'conversation_question_recall', [target.content]), _key(target))
