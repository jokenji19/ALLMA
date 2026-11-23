"""Bounded comparison and source-span receipts, without another model call.

Similarity nominates possible repetition; it cannot prove entailment or truth.
Support is claimed only for a complete extract present in an obtained source,
or a literal attributed user report. Numbers, negation and role order survive.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re
import unicodedata

VERSION = 1
_CJK = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
_STOP = set('il lo la i gli le un uno una di del della dello dei delle a al alla da dal dalla '
    'in nel nella con su per tra fra e o ma che come cui si ci ne l d ed alla anche inoltre '
    'questo questa questi queste tale tali proprio propria grazie presenza meccanismo '
    'the a an of to from on in with and or but that which as it its this these those '
    'also furthermore thanks presence mechanism'.split())
_NEG = {'non','mai','nessuno','nessuna','senza','not','never','without','no'}
_FUNCTION = {'funziona','funzionano','funzionare','permette','permettono','permettendo',
    'consente','consentono','fornisce','fornendo','serve','sono','era','stato','essere',
    'works','allows','allow','provides','is','are','was','be','been'}


def _plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))


def _features(text):
    words=re.findall(r'\w+',_plain(text))
    content=[w for w in words if w not in _STOP and w not in _FUNCTION and len(w)>1]
    # Prefix morphology is only a lexical feature, never a semantic alias.
    return [w[:6] if len(w)>6 and w not in _NEG else w for w in content]


def _protected(text):
    words=re.findall(r'\w+',_plain(text))
    return (tuple(re.findall(r'(?<!\w)[+-]?\d+(?:[.,]\d+)?',text)),
            tuple(w for w in words if w in _NEG))


def statements(text, limit=12):
    if not isinstance(text,str) or '```' in text or text.lstrip().startswith(('{','[')):
        return []
    safe=text[:6000]
    # Mask whitespace inside balanced annotations so a pronunciation like
    # «…? ; …» cannot break the lead sentence. Slice the original text.
    masked = re.sub(r'\([^()\n]*\)|\[[^\[\]\n]*\]',
                    lambda match: re.sub(r'\s', '\0', match[0]), safe)
    parts, start = [], 0
    for boundary in re.finditer(r'(?<=[.!?؟])\s+|(?<=[。！？])\s*|\n+', masked):
        parts.append(safe[start:boundary.start()])
        start = boundary.end()
    parts.append(safe[start:])
    return [p.strip(' \t-*') for p in parts if len(_features(p))>=3 or len(_CJK.findall(p))>=8][:limit]


def novelty(text, previous):
    old=statements(previous,limit=48);new=statements(text)
    if not old or not new:
        return {'status':'not_assessed','clauses':[], 'semantic_certainty':False}
    old_features=[_features(s) for s in old]
    union=set(w for row in old_features for w in row)
    rows=[]
    for sentence in new:
        features=_features(sentence);terms=set(features)
        exact=next((i for i,s in enumerate(old) if _plain(s)==_plain(sentence)),None)
        covered=len(terms & union)/max(1,len(terms))
        compatible=[(i,row) for i,row in enumerate(old_features) if _protected(old[i])==_protected(sentence)]
        best=max(((SequenceMatcher(None,row,features,autojunk=False).ratio(),i) for i,row in compatible),default=(0,None))
        if exact is not None:
            status='repeated';reference=exact
        elif (len(terms)>=4 and covered>=.8 and best[0]>=.65
              and [w for w in old_features[best[1]] if w in terms]
                  == [w for w in features if w in set(old_features[best[1]])]):
            status='possible_paraphrase';reference=best[1]
        else:
            status='candidate_new';reference=None
        rows.append({'sha256':hashlib.sha256(sentence.encode()).hexdigest(),'status':status,
            'previous_clause':reference,'lexical_coverage':round(covered,3),
            'order_similarity':round(best[0],3)})
    all_repeated=bool(rows) and all(r['status'] in ('repeated','possible_paraphrase') for r in rows)
    return {'version':VERSION,'status':'no_demonstrated_progress' if all_repeated else 'candidate_progress',
            'clauses':rows,'semantic_certainty':False}


def support_review(text, references=(), user_reports=()):
    rows=[]
    for statement in statements(text):
        # Exact source text only. Similarity must never certify a fact, changed
        # numbers, an inverted relation or a different person/place.
        reference=next((r for r in references if statement in statements(r.text)),None)
        report=next((r for r in user_reports if statement in statements(r)),None)
        rows.append({'sha256':hashlib.sha256(statement.encode()).hexdigest(),
            'basis':'reference_text' if reference else 'user_report' if report else 'not_established',
            'source_id':reference.identifier if reference else None,
            'truth_verified':False})
    return {'version':VERSION,'claims':rows,'truth_verified':False,
            'unsupported':sum(row['basis']=='not_established' for row in rows)}


@dataclass(frozen=True)
class SourcedContribution:
    text: str
    reference: object
    spans: tuple

    def audit(self):
        return {'version':VERSION,'basis':'reference_text','truth_verified':False,
            'source_id':self.reference.identifier,'spans':[list(span) for span in self.spans],
            'citation':self.reference.citation(),
            'excerpt_sha256':hashlib.sha256(self.text.encode()).hexdigest()}


def history_contribution(history, request, count):
    """Recover a precise span from the contiguous run of attributed extracts."""
    from .saved_references import saved_topic

    if count not in (None, 1):
        return None
    for row in reversed(history[-12:]):
        if row.role == 'user':
            continue
        source = row.metadata.get('source')
        if source not in ('reference_excerpt', 'saved_reference_recall'):
            break
        audit = row.metadata.get('reference_review')
        if (not isinstance(audit, dict) or audit.get('basis') != 'reference_text'
                or row.metadata.get('is_valid') is not True or not saved_topic('reference_excerpt', audit)):
            break
        spans = audit.get('spans')
        if (audit.get('excerpt_sha256') != hashlib.sha256(row.content.encode()).hexdigest()
                or not isinstance(spans, list) or not 1 <= len(spans) <= 5
                or not all(isinstance(pair, list) and len(pair) == 2
                           and all(type(n) is int for n in pair) and 0 <= pair[0] < pair[1] <= 6000 for pair in spans)):
            continue
        offset = 0
        chunks = []
        for start, end in spans:
            length = end - start
            chunks.append(row.content[offset:offset + length])
            offset += length + 1
        if ' '.join(chunks) != row.content or offset != len(row.content) + 1:
            continue
        for index, (span, sentence) in enumerate(zip(spans, chunks)):
            if request.matches_at(chunks, index):
                return sentence, dict(audit, spans=[span], retrieval_status='history',
                    network_used=False, excerpt_sha256=hashlib.sha256(sentence.encode()).hexdigest())
    return None


def select_contribution(references, previous='', count=None, evidence_terms=(),
                        default_count=1, reserve_followup=True, focus_evidence=False, year_terms=(), focused=None):
    """Extract complete new source sentences; never fuse different documents."""
    year_pattern = None
    if year_terms:
        event = r'\b(?:' + '|'.join(map(re.escape, year_terms)) + r')\b'
        year_pattern = re.compile(event + r"[^,;.!?]{0,50}(?<![\w.,])[1-9]\d{2,3}(?!\w|[.,]\d)", re.I)
    for reference in references[:2]:
        candidates=[]
        sentences = statements(reference.text, limit=48 if evidence_terms or focused else 12)
        for index, sentence in enumerate(sentences):
            body = re.sub(r'\([^()\n]*\)|\[[^\[\]\n]*\]', '', sentence)
            if (re.search(r'[?？؟]', body) or len(sentence)>900
                    or not sentence.endswith(('.', '!', '。', '！')) or sentence.endswith(('...', '…'))):
                continue
            if focused is not None and not focused.matches_at(
                    sentences, index, full_article=getattr(reference, 'full_article', False)):
                continue
            if previous:
                comparison=novelty(sentence,previous)
                if comparison['status']=='no_demonstrated_progress':
                    continue
            start=reference.text.find(sentence)
            if start<0:
                continue
            candidates.append((sentence,(start,start+len(sentence))))
        max_sentences = min(default_count, max(1, len(candidates) - int(reserve_followup)))
        sizes = (count,) if count is not None else range(max_sentences, 0, -1)
        for needed in sizes:
            if not 1 <= needed <= 5:
                continue
            for index in range(len(candidates) - needed + 1):
                chosen=candidates[index:index + needed]
                if any(reference.text[left[1][1]:right[1][0]].strip()
                       for left,right in zip(chosen,chosen[1:])):
                    continue
                text=' '.join(s for s,_ in chosen)
                if len(text) > (1800 if count or default_count > 3 else 1100):
                    continue
                evidence_text = chosen[0][0] if focus_evidence else text
                words = set(re.findall(r'\w+', evidence_text.casefold()))
                if evidence_terms and not all(words.intersection(group) for group in evidence_terms):
                    continue
                if year_pattern and not year_pattern.search(evidence_text):
                    continue
                from .output_contract import valid_sentence_count
                if count and not valid_sentence_count(text,count):
                    continue
                if (evidence_terms and count is None and index > 0
                        and re.match(r'^(?:the measurement|these observations|from these samples)\b', text, re.I)):
                    prior = candidates[index - 1]
                    gap = reference.text[prior[1][1]:chosen[0][1][0]]
                    if not gap.strip() and '\n' not in gap and len(prior[0]) + len(text) <= 900:
                        chosen = [prior, *chosen]
                        text = prior[0]+' '+text
                if (focused is not None and count is None and getattr(reference, 'full_article', False)
                        and focused.answer_type == 'date' and focused.date_context(sentences[0])
                        and sentences[0] != chosen[0][0]):
                    context = sentences[0]
                    offset = reference.text.find(context)
                    chosen = [(context, (offset, offset + len(context))), *chosen]
                    text = context + ' ' + text
                return SourcedContribution(text,reference,tuple(span for _,span in chosen))
    return None
