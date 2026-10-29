"""Remove standalone execution commentary, never rewrite factual sentences.

This is deliberately narrower than a relevance or truth classifier. Requested
analysis of a user/draft/system, quotations, code and structured data are kept.
Every edit is auditable and disqualifies the candidate from automatic learning.
"""
from dataclasses import dataclass
import hashlib
import re

from .output_contract import requested_contract, requested_sentence_count, sentence_count

VERSION = 2
_REQUESTS_ANALYSIS = re.compile(
    r'\b(?:prompt|istruzioni|controll[oi]|validazion\w*|verifiche|ragionamento|'
    r'come ragioni|come rispondi|perché hai|perche hai|why did you|how do you|'
    r'utente|user|paziente|personaggio|traduci|translate|riscrivi|riformula|'
    r'cita|citazione|quote|frase|testo|dialogo|racconto|poesia)\b', re.I)
_COMMENTARY = re.compile(
    r'^(?:(?:non\s+)?ho\s+(?:verificato|accertato|confermato)\s+se\s+l[’\']utente\b'
    r'|(?:devo|dovrei)\s+(?:rispondere|rispettare|distinguere|evitare)\b.*'
    r'\b(?:utente|formato|istruzioni|esperienz\w*)\b'
    r'|i (?:have not verified whether the user|(?:need|should|must) (?:respond|answer) to the user)\b)', re.I)


@dataclass(frozen=True)
class Projection:
    text: str
    removed: tuple = ()
    reasons: tuple = ()

    @property
    def reason(self):
        return self.reasons[0] if self.reasons else 'internal_commentary'

    def audit(self):
        return {'version': VERSION, 'removed_sentences': len(self.removed),
                'removed_sha256': list(self.removed), 'reasons':list(self.reasons),
                'factual_verification': False}


def project_answer(text, request, continuity=None):
    if (not text or _REQUESTS_ANALYSIS.search(request) or requested_contract(request) == 'json'
            or sentence_count(text) is None):
        return Projection(text)
    # Only complete sentences with conventional boundaries are eligible. Mixed
    # factual/technical clauses remain intact for normal output validation.
    removed, spans = [], []
    for match in re.finditer(r'(?:^\s*|(?<=[.!?])\s+)(?P<sentence>[^.!?\n]+[.!?]?)(?=\s|$)', text):
        sentence = match['sentence'].strip()
        if (not _COMMENTARY.search(sentence)
                or re.search(r'[,;:]|\b(?:ma|però|tuttavia|quindi|perciò|perché|poiché|but|however|because|therefore)\b', sentence, re.I)
                or re.search(r'[«»“”"`]', sentence)):
            continue
        spans.append(match.span())
        removed.append(hashlib.sha256(sentence.encode('utf-8')).hexdigest())
    result, start = [], 0
    for begin, end in spans:
        result.append(text[start:begin]); start = end
    result.append(text[start:])
    projection = Projection(''.join(result).strip(), tuple(removed),
                            ('internal_commentary',) if removed else ())
    return _remove_reasked_checkin(projection,request,continuity)


def _remove_reasked_checkin(projection, request, continuity):
    # An arbitrary response being received does not prove it answered the
    # question. Only the closed, explicit check-in task authorizes deletion.
    if (continuity is None or continuity.checkin_task is None or continuity.allow_repeat
            or continuity.factual_correction or continuity.correction or requested_contract(request) is not None
            or requested_sentence_count(request) is not None
            or re.search(r'[«»“”"`]',projection.text)):
        return projection
    # Only a complete, standalone equivalent of the satisfied question can go.
    # Mixed/substantive questions are preserved for normal validation.
    from .conversation_reply import reasked
    spans=[];hashes=[]
    for match in re.finditer(r'(?:^\s*|(?<=[.!?])\s+)(?P<sentence>[^.!?\n]+[.!?]?)(?=\s|$)',projection.text):
        sentence=match['sentence'].strip()
        if reasked(sentence,continuity.preceding_questions):
            spans.append(match.span());hashes.append(hashlib.sha256(sentence.encode()).hexdigest())
    if not spans:
        return projection
    parts=[];start=0
    for begin,end in spans:
        parts.append(projection.text[start:begin]);start=end
    parts.append(projection.text[start:]);remaining=''.join(parts).strip()
    # No canned replacement, empty answer or cosmetic "Certo!" is promoted.
    if len(re.findall(r'\w+',remaining))<3:
        return projection
    from .dialogue_continuity import normalized
    if (continuity.duplicate(remaining) or (len(normalized(remaining).split())>=6
            and normalized(remaining) in normalized(continuity.previous_answer))):
        return projection
    return Projection(remaining,projection.removed+tuple(hashes),
        projection.reasons+(('repeated_checkin' if continuity.checkin_task is not None else 'repeated_question'),))
