"""Resume a withheld turn from scoped history, never from the rejected prose.

The history projection is disposable: notices remain in the actual transcript.
Only a content-free conversational opening can receive a local clarification;
substantive questions, emotions and output instructions still need the pipeline.
"""
import re
import unicodedata

EXPLANATION_SOURCE = 'runtime_recovery_explanation'
GUARD_FAILURES = frozenset({
    'subject_mismatch', 'dialogue_repetition', 'unsupported_personal_claim',
    'identity_conflict', 'format_mismatch', 'unbacked_source_claim',
    'instruction_echo', 'repetition', 'internal_commentary',
})


def _plain(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', str(text or '')).casefold()))


def clarification_question(message):
    return _plain(message) in {
        'cosa intendi', 'che significa', 'cosa significa',
        'perché hai bloccato la risposta', 'perche hai bloccato la risposta',
        'what do you mean', 'why was the answer blocked',
    }


def technical_notice(record):
    metadata = record.get('metadata', {}) if isinstance(record, dict) else getattr(record, 'metadata', {})
    return (metadata or {}).get('source') == EXPLANATION_SOURCE


def opening_recovery(message):
    if (not isinstance(message, str) or len(message) > 220
            or re.search(r'[\n«»“”"`]', message) or message.strip().startswith("'")):
        return None
    query = _plain(message)
    prefix = r'(?:(?:bene|sto bene|tutto bene|grazie|ok|va bene)(?: grazie)? (?:ma |però |e )?)?'
    italian = re.fullmatch(prefix + r'(?:(?:io )?ho (?:un dubbio|una domanda|un problema)|'
        r'(?:vorrei|volevo|voglio|posso) (?:farti|porti) (?:una domanda|un quesito)|'
        r'(?:vorrei|volevo|voglio) (?:chiederti|dirti) (?:una cosa|qualcosa)|'
        r'posso (?:chiederti|dirti) (?:una cosa|qualcosa))', query)
    english = re.fullmatch(r'(?:(?:i m fine|i am fine|thanks|okay)(?: but| and)? )?'
        r'(?:i have a (?:question|doubt|concern)|(?:can|may) i ask you (?:a question|something)|'
        r'i (?:would like|want) to ask you (?:a question|something))', query)
    if not italian and not english:
        return None
    if english:
        answer = 'What would you like to ask?' if 'question' in query or 'ask' in query else 'What is on your mind?'
    else:
        answer = 'Dimmi pure: qual è il dubbio?' if 'dubbio' in query else 'Dimmi pure: di che cosa si tratta?'
    return {'content': answer, 'source': 'grounded_dialogue_recovery',
            'evidence': [{'kind': 'dialogue_opening', 'text': message}],
            'language': 'it' if italian else 'en'}


def unanswered_attempt(history):
    """Only the latest failure, across adjacent host explanations, is pending.

    Callers must scope history by user and conversation. A new substantive turn,
    a successful answer, or cancellation ends this chain; no archive is created.
    """
    index = len(history) - 1
    while index >= 1:
        reply, request = history[index], history[index - 1]
        metadata = getattr(reply, 'metadata', {}) or {}
        if reply.role != 'assistant' or request.role != 'user':
            return None
        if (metadata.get('source') == EXPLANATION_SOURCE
                and clarification_question(request.content)):
            index -= 2
            continue
        reason = (metadata.get('generation') or {}).get('status')
        if metadata.get('is_valid') is False and reason in GUARD_FAILURES:
            return {'request': request, 'reason': reason}
        return None
    return None


def dialogue_history(history):
    """Exclude host error explanations and their questions from model context.

    Keep the unanswered request, genuine answers, and every durable event.
    In particular a user asking to explain an actual answer is not removed.
    """
    projected = []
    for turn in history:
        if turn.role == 'assistant' and technical_notice(turn):
            if projected and projected[-1].role == 'user' and clarification_question(projected[-1].content):
                projected.pop()
            continue
        projected.append(turn)
    return projected
