"""A bounded acknowledgement from attributed user evidence, never model prose.

This recovers mixed-emotion support after a rejected model answer. It does
not solve a factual task, diagnose feelings, or train/confirm an answer.
"""
from allma_model.emotional_system.emotion_analysis import analyze
from allma_model.utils.output_contract import (
    requested_contract, requested_sentence_count, valid_sentence_count,
    borrowed_user_experience,
)
import re
import unicodedata


def emotional_recovery(message, learned_aliases=None, consolidated_labels=None):
    message = unicodedata.normalize('NFKC', message)
    if requested_contract(message) is not None:
        return None
    count = requested_sentence_count(message)
    if count not in (None, 1, 2):
        return None
    state = analyze(message, learned_aliases=learned_aliases)
    analysis = state['analysis']
    if analysis['uncertain'] or analysis['truncated']:
        return None
    # Multiple clear current self-attributed emotions; uncertain, negated,
    # quoted, historical and other-person evidence are excluded by analyze.
    labels = {key for key, score in state['nuances'].items() if score >= .8}
    learned_single = len(labels) == 1 and (labels & set(consolidated_labels or []) or
        any(item.get('learned_alias') for item in analysis['evidence']))
    if (len(labels) < 2 and not learned_single) or len(labels) > 4:
        return None
    fragments, evidence = [], []
    for item in analysis['evidence']:
        if item['label'] not in labels:
            continue
        fragment = message[item['start']:item['end']]
        if fragment not in fragments:
            fragments.append(fragment)
            evidence.append(dict(item, text=fragment))
    if len(fragments) < 2 and not learned_single:
        return None
    # Exact user words prevent escalating "preoccupata" into "panico".
    if learned_single:
        # Context is copied from the user's current clause, not inferred from
        # the failed candidate. Keep it distinct from a previous episode.
        clause = re.split(r'[.!?](?=\s|$)|\n', message, maxsplit=1)[0].strip()[:240]
        if '«' in clause or '»' in clause:
            return None
        answer = f'Mi dici come ti senti: «{clause}».'
    else:
        quoted = [f'«{fragment}»' for fragment in fragments]
        joined = ', '.join(quoted[:-1]) + ' e ' + quoted[-1]
        answer = f'Hai descritto emozioni diverse: {joined}.'
    if count != 1:
        answer += ' Se ti va, possiamo approfondire cosa accompagna queste sensazioni, una alla volta.'
    if not valid_sentence_count(answer, count) or borrowed_user_experience(answer, message):
        return None
    return {'content': answer, 'evidence': evidence, 'source': 'grounded_emotional_recovery'}
