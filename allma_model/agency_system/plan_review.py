"""Counterexamples to a plan's explicit count guarantees, not semantic certification.

A weaker lower bound is consistent with the goal but does not ensure it. We
show that gap without claiming the plan must fail or inventing physical facts.
Only narrowly parsed, positive user criteria participate; the rest is unknown.
"""
import hashlib
import re
import unicodedata

WORDS = dict(zip(('uno','una','un','due','tre','quattro','cinque','sei','sette','otto','nove','dieci',
                 'one','two','three','four','five','six','seven','eight','nine','ten'),
                (1,1,1,2,3,4,5,6,7,8,9,10,1,2,3,4,5,6,7,8,9,10)))
NUM = r'(?:\d{1,3}|'+'|'.join(WORDS)+r')'
CHECK = r'(?:controll\w*|verific\w*|esamin\w*|valid\w*|check\w*|review\w*|inspect\w*)'
_CHECK = re.compile(r'\b'+CHECK+r'\b',re.I)
_COUNT = re.compile(r'\b(?:(almeno|al massimo|at least|at most|esattamente|exactly|solo|only)\s+)?('+NUM+r')\s+([^\W\d_]+)\b',re.I)
_NEG = re.compile(r"\b(?:non|mai|senza|not|never|without|don['’]t)\b",re.I)
_QUOTED = re.compile(r'```.*?(?:```|$)|`[^`]*(?:`|$)|«[^»]*(?:»|$)|“[^”]*(?:”|$)|"[^"\n]*(?:"|$)',re.S)
_EMPHASIS = re.compile(r'(?<!\w)(\*\*|__|\*|_)(?=\S)([^\n]*?\S)\1(?!\w)')
_GENERIC = {'oggett','element','voc','item','object','element'}
_SKIP = {'volt','pass','minut','second','giorn','day','time','step','hour','esemp','example','person','student',
         'metr','gramm','litr','percent','eur','dollar','meter','minute','hour','liter'}


def plain(text):
    return unicodedata.normalize('NFKC',text).casefold()


def number(text):
    return int(text) if text.isdecimal() else WORDS.get(text)


def stem(word):
    word=plain(word)
    if len(word)>4 and word.endswith('s'):word=word[:-1]
    if len(word)>3 and word[-1] in 'aeio':return word[:-1]
    return word


def mask(text):
    text=_QUOTED.sub(lambda m:' '*len(m[0]),plain(text))
    for _ in range(2):text=_EMPHASIS.sub(lambda m:' '+m[2]+' ',text)
    return text


def requirements(criterion):
    """Extract at most four count obligations from short declarative clauses."""
    found=[]
    for clause in re.split(r'[;.!?\n]|\b(?:ma|but)\b',mask(criterion)):
        if _NEG.search(clause) or not _CHECK.search(clause):continue
        if re.search(r'\d\s*[+*/×÷-]\s*\d',clause):continue
        if re.search(r'\b(?:circa|forse|esempio|example|maybe|about)\b',clause):continue
        for match in _COUNT.finditer(clause):
            count=number(match[2]);subject=stem(match[3])
            if not count or subject in _SKIP or match[1] in {'al massimo','at most'}:continue
            if re.search(r'\b(?:in|nel|nella|con|per|inside|within)\s*$',clause[:match.start()]):continue
            if subject in {'dei','del','di','of','the'}:continue
            value={'kind':'checked_count','minimum':count,'subject':subject,'criterion_clause':clause.strip()}
            if value not in found:found.append(value)
    return found[:4]


def _coverage(clause, requirement, single):
    """A supported lower bound, or None when scope/polarity is ambiguous."""
    clean=mask(clause)
    if _NEG.search(clean) or re.search(r'\b(?:se|qualora|if|unless|esempio|example)\b',clean):return None
    action=_CHECK.search(clean)
    if not action:return None
    tail=clean[action.end():]
    words={stem(w) for w in re.findall(r'[^\W\d_]+',tail)}
    subject=requirement['subject']
    bound=subject in words or (single and subject in _GENERIC and bool(words & _GENERIC))
    # "uno dei tre" can refer to the unique user-specified collection.
    reference=re.search(r'\b('+NUM+r')\s+(?:dei|degli|delle|of(?: the)?)\s+('+NUM+r')\b',tail)
    if reference and single and number(reference[2])==requirement['minimum']:bound=True
    if not bound:return None
    if re.search(r'\b(?:ogni|ciascun\w*|tutt\w*|each|every|all)\b',tail):return requirement['minimum']
    if re.search(r'\b(?:uno|un|una|one)\s+(?:\w+\s+){0,2}(?:alla volta|at a time)\b',tail):return None
    if reference:return number(reference[1])
    values=[]
    for match in _COUNT.finditer(tail):
        noun=stem(match[3])
        if noun==subject or (single and noun in _GENERIC and subject in _GENERIC):
            if match[1] not in {'al massimo','at most'}:values.append(number(match[2]))
    return (sum(values) if re.search(r'\b(?:altri|altre|restanti|remaining|other)\b',tail) else max(values)) if values else None


def review(steps,criterion):
    obligations=requirements(criterion)
    findings=[];covered=[]
    for requirement in obligations:
        bounds=[]
        for index,step in enumerate(steps):
            for clause in re.split(r'[;.!?\n]|\b(?:poi|quindi|then|successivamente)\b',step):
                value=_coverage(clause,requirement,len(obligations)==1)
                if value is not None:bounds.append((value,index,clause.strip()))
        maximum=max((row[0] for row in bounds),default=0)
        terminal=[row for pos,row in enumerate(bounds) if row[0]<requirement['minimum']
                  and re.search(r'\b(?:final\w*|definitiv\w*|basta|sufficiente|sufficient|conclud\w*|finish\w*)\b',mask(row[2]))
                  and not re.search(r'\b(?:campione|sample|audit)\b',mask(row[2]))
                  and not any(later[0]>=requirement['minimum'] for later in bounds[pos+1:])]
        additive=sum(row[0] for row in bounds) if any(re.search(r'\b(?:altri|altre|restanti|remaining|other)\b',mask(row[2])) for row in bounds) else 0
        if not terminal and max(maximum,additive)>=requirement['minimum']:
            covered.append(requirement);continue
        if not bounds:continue  # Missing evidence is unknown, not a demonstrated gap.
        if len(bounds)>1 and not terminal:continue  # Ambiguous partition, not proof of a gap.
        value,index,clause=terminal[-1] if terminal else bounds[0]
        findings.append({'kind':'insufficient_guarantee','required':requirement['minimum'],
            'guaranteed':value,'uncovered':requirement['minimum']-value,
            'subject':requirement['subject'],'step_index':index,'step_excerpt':clause[:240],
            'criterion_excerpt':requirement['criterion_clause'][:240],
            'counterexample':f'{value} elementi controllati soddisferebbero questo controllo, ma non il minimo richiesto di {requirement["minimum"]}.'})
    return {'version':1,'source':'host_count_coverage_v1','criterion_sha256':hashlib.sha256(criterion.encode()).hexdigest(),
            'steps_sha256':hashlib.sha256('\n'.join(steps).encode()).hexdigest(),
            'status':'needs_review' if findings else 'no_known_gap' if obligations and len(covered)==len(obligations) else 'not_automatically_checkable',
            'requirements':obligations,'findings':findings,'semantic_correctness_verified':False}


def explanation(report):
    if report['status']!='needs_review':
        return 'Non ho rilevato un controllo numerico insufficiente nei requisiti che so esaminare. La correttezza generale del piano resta da valutare.'
    return ('Piano da rivedere prima dell’adozione. '+ ' '.join(
        f'Il passo {f["step_index"]+1} garantisce un controllo su {f["guaranteed"]} elementi, mentre il criterio ne richiede {f["required"]}. '
        +f['counterexample'] for f in report['findings'])+
        ' Chiedi una nuova proposta che copra il criterio completo.')


INSTRUCTION = ('Copri tutti i requisiti del criterio. Se servono N elementi controllati, '
    'un controllo limitato a un campione più piccolo non garantisce il risultato. '
    'Puoi controllarli uno alla volta, ma il piano deve coprire l’insieme richiesto. '
    'Le osservazioni locali di ALLMA segnalano solo lacune verificabili, non certificano il resto del piano.')
