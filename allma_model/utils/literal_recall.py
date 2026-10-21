"""Source-bound recall for a deliberately small class of literal declarations.

Not a factual verifier or a semantic memory engine. Never take assistant prose,
quoted examples, hypothetical values or similarity scores as a declaration.
"""
import re

_QUERY = re.compile(
    r'(?:quale|qual è|qual e|ricordi|ti ricordi|ricordi qual è|ti ricordi qual è|dimmi|ricordami|mi dici|mi ricordi|puoi dirmi|puoi ricordarmi)\s+'
    r'(?:il\s+)?(?:mio\s+)?codice(?:\s+di\s+(?P<kind>prova|accesso|riferimento))?'
    r'(?:\s+(?:attuale|valido))?(?:\s+(?:che\s+)?ti\s+(?:ho|avevo)\s+(?:già\s+)?(?:indicato|detto|comunicato|scritto))?', re.I)
_DECLARATION = re.compile(
    r'(?:(?P<update>ora|rettifico|correzione)\s*[:,]?\s*)?'
    r'(?P<scope>per\s+[A-Za-zÀ-ÿ ]{1,60}\s+)?'
    r'(?:(?:il\s+)?mio|il)\s+(?P<new>nuovo\s+)?codice(?:\s+(?:di\s+(?P<kind>prova|accesso|riferimento)|dichiarato))?'
    r'(?:\s+(?P<now>ora))?\s*(?:è|e|:)\s*(?:(?P<now_after>ora)\s+)?(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{0,63})[.!]?', re.I)
_REVOCATION = re.compile(
    r'(?:non usare(?:\s+(?:più|piu))?|revoco|annullo)\s+'
    r'(?:(?:il\s+)?mio|il)\s+codice(?:\s+di\s+(?P<kind>prova|accesso|riferimento))?'
    r'(?:\s+(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{0,63}))?[.!]?', re.I)
_EXAMPLE = re.compile(r'\b(?:se|non|forse|esempio|ipotizziamo|ipotizza|immagina|fingi|sarebbe|potrebbe|supponi)\b', re.I)


def _uncertain_scopes(text):
    """Ambiguous identifier reports, scoped without treating programming as one.

    An unnamed assignment can affect any category. Merely discussing source
    code or its quality is not a new identifier declaration or revocation.
    """
    scopes=[]
    for match in re.finditer(r'\bcodic[ei]\b(?:\s+di\s+(prova|accesso|riferimento))?',text,re.I):
        if match[1]:
            scopes.append(match[1].casefold())
        elif re.match(r'\s*(?:(?:è|e|era|non|potrebbe|sarebbe|vale|diventa|cambia|scaduto)\b|:|'
                      r'[A-Za-z0-9_-]*[0-9][A-Za-z0-9_-]*)',text[match.end():],re.I):
            scopes.append('')
    return scopes


def _request(message):
    parts = re.split(r'[?!.]\s*', message.strip(), maxsplit=1)
    question = parts[0].strip()
    suffix = parts[1].strip() if len(parts) > 1 else ''
    match = _QUERY.fullmatch(question)
    if not match:
        return None
    code_only = bool(re.fullmatch(
        r'Rispondi solo con il codice(?: oppure NON_DISPONIBILE se non è nei ricordi)?[.!]?', suffix, re.I))
    return (code_only, (match['kind'] or '').casefold()) if not suffix or code_only else None



def literal_statement_reply(message):
    """Acknowledge the user statement itself, never regenerate a stored value.

    The caller persists the actual input before delivering this acknowledgement.
    No independent claim of truth, deletion or successful disk durability is made.
    """
    text = message.strip()
    revocation = _REVOCATION.fullmatch(text)
    declaration = _DECLARATION.fullmatch(text)
    match = revocation or declaration
    if match is None or (declaration and _EXAMPLE.search(text)):
        return None
    value = match['value']
    if value and not any(char.isdigit() for char in value):
        return None
    kind = (match['kind'] or '').casefold()
    if declaration and not kind and match['scope']:
        scope = re.search(r'\b(prova|accesso|riferimento)\b', match['scope'], re.I)
        kind = scope[1].casefold() if scope else ''
    label = 'codice'+(' di '+kind if kind else '')
    if revocation:
        label = 'codice indicato' if value else label
        return f'Ho ricevuto la revoca del {label}.', 'literal_user_revocation_ack', [message]
    update = any(match[name] for name in ('update','new','now','now_after'))
    if update:
        return f'Ho ricevuto la correzione del {label}: {value}.', 'literal_user_update_ack', [message]
    return f'Hai indicato il {label}: {value}.', 'literal_user_declaration_ack', [message]

def literal_code_reply(message, events):
    """Return (answer, source, evidence texts) or None to use normal reasoning.

    events must already be scoped to the authenticated user by the caller.
    The caller supplies available user statements, not a top-k search.
    Missing data always falls through to the full retrieval pipeline.
    """
    request = _request(message)
    if request is None:
        return None
    code_only, kind = request
    events = events() if callable(events) else events
    active, revoked, blocked = {}, set(), {}
    uncertainties, last_updates = [], {}
    last_unscoped = -1
    control_evidence = []
    for event_index, event in enumerate(events):
        text = event.content.strip()
        if _request(text) is not None:
            continue
        declaration = _DECLARATION.fullmatch(text)
        revocation = _REVOCATION.fullmatch(text)
        match = declaration or revocation
        if match is None or (declaration and _EXAMPLE.search(text)):
            uncertainties.extend((event_index,scope) for scope in _uncertain_scopes(text))
            continue
        origin_kind = (match['kind'] or '').casefold()
        if declaration and not origin_kind and match['scope']:
            scope_kind = re.search(r'\b(prova|accesso|riferimento)\b', match['scope'], re.I)
            origin_kind = scope_kind[1].casefold() if scope_kind else ''
        # A generic update/revocation can target one known category, never many.
        known = set(active) | revoked | set(blocked)
        is_update = bool(declaration and any(match[name] for name in ('update','new','now','now_after')))
        if not origin_kind and (is_update or revocation):
            if len(known) == 1:
                origin_kind = next(iter(known))
            elif len(known) > 1:
                uncertainties.append((event_index,''))
                control_evidence.append(('', text))
                continue
        if not origin_kind:
            last_unscoped = event_index
        value = match['value']
        if value and not any(char.isdigit() for char in value):
            uncertainties.append((event_index,origin_kind))
            continue
        if revocation:
            control_evidence.append((origin_kind, text))
            if value is None:
                active[origin_kind] = {}
                revoked.add(origin_kind)
            else:
                current = active.setdefault(origin_kind, {})
                if any(old.casefold() == value.casefold() and old != value for old in current):
                    uncertainties.append((event_index,origin_kind))
                current.pop(value, None)
                blocked.setdefault(origin_kind, set()).add(value)
            continue
        values = active.setdefault(origin_kind, {})
        if is_update:
            last_updates[origin_kind] = event_index
            active[origin_kind] = {value:text}
            revoked.discard(origin_kind)
            blocked[origin_kind] = {old for old in blocked.get(origin_kind, set()) if old.casefold() != value.casefold()}
        elif origin_kind not in revoked and value not in blocked.get(origin_kind, set()):
            if any(old.casefold() == value.casefold() for old in blocked.get(origin_kind, set())):
                uncertainties.append((event_index,origin_kind))
            else:
                values.setdefault(value, text)
    relevant = {kind} if kind else set(active) | revoked | set(blocked)
    # An explicit update resolves older ambiguity for its named category only.
    # Generic questions still require identifying the category without guessing.
    cutoff = last_updates.get(kind, -1) if kind else -1
    uncertain = any(index > cutoff and (not kind or scope in ('',kind)) for index,scope in uncertainties)
    if kind and last_unscoped > cutoff and (active.get('') or '' in revoked or blocked.get('')):
        uncertain = True  # An unscoped declaration cannot answer a specific category.
    values = [(value, text) for key, group in active.items() if key in relevant
              for value, text in group.items()]
    has_revocation = bool(revoked & relevant or any(blocked.get(key) for key in relevant))
    control_evidence = [text for key, text in control_evidence if not kind or key in relevant or not key]
    if uncertain:
        if values or has_revocation or control_evidence:
            return ('Non riesco a individuare un codice attuale univoco nelle tue dichiarazioni. Quale intendi?',
                    'memory_clarification', [text for _, text in values][-8:] + control_evidence[-1:])
        return None
    if len(values) > 1:
        # A code-only instruction cannot justify choosing an arbitrary value.
        return ('Trovo più codici nelle tue dichiarazioni. A quale ti riferisci?',
                'memory_clarification', [text for _, text in values][-8:])
    if not values:
        if has_revocation:
            fallback = re.search(r'\boppure (NON_DISPONIBILE) se non è nei ricordi[.!]?$', message, re.I)
            answer = fallback[1] if code_only and fallback else 'Il codice risulta revocato nelle tue dichiarazioni; non lo ripropongo.'
            return answer, 'literal_memory_revoked', control_evidence[-1:]
        return None
    value, evidence = values[0]
    return (value if code_only else f'Mi hai indicato il codice {value}.',
            'literal_user_memory', [evidence])


def is_literal_request(message):
    """A deterministic host intent; no model is needed to select a read action."""
    return _request(message) is not None


def literal_absence_reply(message, events, records, action):
    """Report a bounded absence only after a verified, successful scoped read.

    An empty top-k result alone cannot erase a known declaration, revocation or
    ambiguous mention in the available history. Backend errors never mean absent.
    """
    request = _request(message)
    if request is None or records != [] or not isinstance(action, dict):
        return None
    steps = action.get('steps')
    if (action.get('status') != 'observed' or type(action.get('record_count')) is not int
            or action['record_count'] != 0 or not isinstance(steps, list) or len(steps) != 1
            or not isinstance(steps[0], dict) or steps[0].get('action') != 'memory' or steps[0].get('verified') is not True):
        return None
    events = events() if callable(events) else events
    for event in events:
        if _request(event.content) is None and re.search(r'\bcodic[ei]\b', event.content, re.I):
            return None
    code_only, _ = request
    if code_only:
        if not re.search(r'\boppure NON_DISPONIBILE se non è nei ricordi[.!]?$', message, re.I):
            return None
        answer = 'NON_DISPONIBILE'
    else:
        answer = 'Non trovo un codice nelle dichiarazioni disponibili e nella ricerca dei tuoi ricordi.'
    return answer, 'literal_memory_absent', []
