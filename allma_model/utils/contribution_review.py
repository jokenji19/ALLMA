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
    # No splitting decimals. Preserve exact spans so source excerpts can be
    # selected without manufacturing a connective or changing an assertion.
    parts=re.split(r'(?<!\d)(?<=[.!?])\s+|\n+',safe)
    return [p.strip(' \t-*') for p in parts if len(_features(p))>=3][:limit]


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
            'citation':self.reference.citation()}


def select_contribution(references, previous='', count=None):
    """Extract complete new source sentences; never fuse different documents."""
    for reference in references[:2]:
        candidates=[]
        for sentence in statements(reference.text):
            if '?' in sentence or len(sentence)>900 or not sentence.endswith(('.', '!')) or sentence.endswith(('...', '…')):
                continue
            if previous:
                comparison=novelty(sentence,previous)
                if comparison['status']=='no_demonstrated_progress':
                    continue
            start=reference.text.find(sentence)
            if start<0:
                continue
            candidates.append((sentence,(start,start+len(sentence))))
        needed=count or 1
        if not 1 <= needed <= 3 or len(candidates)<needed:
            continue
        chosen=candidates[:needed]
        # Avoid silently stitching distant passages into a newly constructed
        # assertion. Multi-sentence answers must remain one contiguous extract.
        if any(reference.text[left[1][1]:right[1][0]].strip()
               for left,right in zip(chosen,chosen[1:])):
            continue
        text=' '.join(s for s,_ in chosen)
        # Exact output requirements are checked through the existing parser.
        from .output_contract import valid_sentence_count
        if count and not valid_sentence_count(text,count):
            continue
        return SourcedContribution(text,reference,tuple(span for _,span in chosen))
    return None
