"""Explicit output shapes; no reference answers and no silent answer rewriting."""
import json
import re


# Match a constraint attached to its command, never a format word anywhere in
# the question. These stay deliberately smaller than a natural-language parser.
_COMMAND = re.compile(
    r'\b(?:rispondi(?:mi)?|scrivi(?:mi)?|restituisci(?:mi)?|dammi|fornisci|usa|'
    r'output|answer|return|respond|write|provide|give|'
    r'(?:puoi|potresti|devi|riesci\s+a)\s+(?:risponder(?:e|mi)|scriver(?:e|mi)|restituir(?:e|mi))|'
    r'(?:can|could|would)\s+you\s+(?:please\s+)?(?:answer|respond|return)|'
    r'(?:anzi|invece|actually|instead),?)\s+', re.I)
_LEAD = r'(?:(?:con|in|with|using|usando|utilizzando)\s+)?'
_ONLY = r'(?:solo(?:\s+ed?\s+esclusivamente)?|soltanto|esclusivamente|only|un\s+(?:solo|unico))'
_FORMAT = (r'(?:(?:un|il|an?|the)\s+)?(?:(?:formato|format)\s+)?'
           r'(?:s[iì]\s*(?:o|oppure|/)\s*no\b|yes\s*(?:or|/)\s*no\b|'
           r'(?:(?:oggetto|object|documento|document)\s+)?(?:valid\s+)?json\b(?:\s+valido\b)?|'
           r'risultato\s+numerico\b|numeric\s+result\b|numero\b|number\b)')
_OBJECT = r'(?:(?:la\s+risposta|alla(?:\s+seguente)?\s+domanda|the\s+answer|per\s+favore|please)\s+)?'
_PREFIX_CONSTRAINT = re.compile(_OBJECT + _LEAD + _ONLY + r'\s+' + _LEAD + r'(?P<format>' + _FORMAT + r')', re.I)
_SUFFIX_CONSTRAINT = re.compile(
    _OBJECT + _LEAD + r'(?P<format>' + _FORMAT + r')\s*,?\s*'
    r'(?:solo|soltanto|only|senza\s+(?:aggiungere\s+)?altro|without\s+anything\s+else)\b', re.I)
_BARE_CONSTRAINT = re.compile(_LEAD + r'(?P<format>' + _FORMAT + r')', re.I)
_REVISION = re.compile(r'\b(?:anzi|invece|piuttosto|rettifico|actually|instead)\b', re.I)
_QUOTED = re.compile(
    r'```.*?(?:```|$)|`[^`]*(?:`|$)|"(?:\\.|[^"\\])*(?:"|$)|'
    r'«[^»]*(?:»|$)|“[^”]*(?:”|$)|'
    r"(?<!\w)'(?:\\.|[^'\\])*(?:'|$)", re.S)


def _contract_text(request):
    # Literal labels may be quoted in a real constraint: "sì" oppure "no".
    # Quoted instructions, code and examples remain data, not commands.
    labels = {'json', 'sì', 'si', 'no', 'yes'}
    def replace(match):
        value = match[0].strip('`"«»“”\'').strip()
        if match[0].startswith('```'):
            return ' ' * len(match[0])
        if value.casefold() == 'json' and not re.search(
                r'\b(?:con|in|with|using|formato|format)\s*$', (request or '')[max(0,match.start()-64):match.start()], re.I):
            return ' ' * len(match[0])
        return value if value.casefold() in labels else ' ' * len(match[0])
    return _QUOTED.sub(replace, request or '')


def requested_sentence_count(request):
    plain = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»|“[^”\n]*”', '', request or '', flags=re.S)
    if not re.search(r'\b(?:rispond\w*|spiega\w*|scrivi|restituisci|answer|respond|explain)\b', plain, re.I):
        return None
    match = re.search(r'\b(?:in|con|usa|using)\s+(?:(?:esattamente|exactly)\s+)?(\d+|una|due|tre|quattro|cinque|one|two|three|four|five)\s+(?:frasi|frase|sentences|sentence)\b', plain, re.I)
    if not match or re.search(r'\b(?:non in|non con|non rispond\w*|non scrivi|almeno|massimo|circa|at least|at most)\b', plain, re.I):
        return None
    numbers = {'una':1,'due':2,'tre':3,'quattro':4,'cinque':5,'one':1,'two':2,'three':3,'four':4,'five':5}
    count = int(match[1]) if match[1].isdigit() else numbers[match[1].lower()]
    return count if 1 <= count <= 5 else None


def sentence_count(text):
    # Do not guess sentence boundaries in code, lists or abbreviations.
    if '```' in text or re.search(r'(?m:^\s*(?:[-*]|\d+[.)])\s)', text):
        return None
    if re.search(r'\b(?:dott|sig|prof|ecc|es|mr|dr)\.', text, re.I):
        return None
    plain = re.sub(r'(?<=\d)[.,](?=\d)', '_', text.strip())
    # Quotation marks are not sentence boundaries; punctuation inside a
    # closing quote still closes a sentence.
    plain = re.sub(r'["«»“”]', '', plain)
    # A run of punctuation (?! or ...) closes one sentence.
    parts = re.split(r'[.!?]+(?=\s|$)', plain)
    return len([part for part in parts if part.strip()])


def valid_sentence_count(text, count):
    return not count or sentence_count(text) == count


def requested_contract(request):
    plain = _contract_text(request)
    selected, conflicting = None, False
    for command in _COMMAND.finditer(plain):
        # Inspect only the local command context; repeated commands in a large
        # pasted document must not trigger quadratic scans of all earlier text.
        prefix = re.split(r'[.!?;:\n]', plain[max(0,command.start()-160):command.start()])[-1].strip()
        if re.search(r"\b(?:non|not|never|don['’]t|do\s+not)(?:\s+\w+){0,2}\s*$", prefix, re.I):
            continue
        # Do not turn "che significa rispondi solo ..." into an instruction.
        arithmetic_boundary = bool(re.fullmatch(
            r'(?:quanto fa|calcola|qual [èe] il risultato di)\s+[\d\s,.()+*/^×÷−-]+', prefix, re.I))
        if prefix and not (arithmetic_boundary or prefix.endswith(',') or re.search(
                r'\b(?:e|and|ma|but|anzi|invece|piuttosto|rettifico|actually|instead|please|per\s+favore|you\s+(?:must|should))\s*$', prefix, re.I)):
            continue
        revision = bool(_REVISION.search(prefix) or _REVISION.match(command[0]))
        previously_selected = selected is not None
        if revision:
            selected, conflicting = None, False
        constraint = (_PREFIX_CONSTRAINT.match(plain, command.end())
                      or _SUFFIX_CONSTRAINT.match(plain, command.end())
                      or (_BARE_CONSTRAINT.match(plain, command.end()) if revision and previously_selected else None))
        if not constraint:
            continue
        tail = re.split(r'[.!?;:\n]', plain[constraint.end():constraint.end()+200], maxsplit=1)[0]
        if re.search(r'\b(?:e|and|ma|but)\s+(?:(?:poi|anche|also|then)\s+)?'
                     r'(?:spiega|scrivi|aggiungi|includi|una\s+spiegazione|un\s+commento|explain|add|include)\b', tail, re.I):
            conflicting = True
            continue
        label = constraint['format'].casefold()
        kind = ('json' if re.search(r'\bjson\b', label) else
                'yes_no_en' if re.search(r'\byes\b', label) else
                'yes_no_it' if re.search(r'\bs[iì]\b', label) else 'number')
        if selected is not None and selected != kind:
            conflicting = True
        selected = kind
    return None if conflicting else selected


def valid_contract(text, kind):
    if kind is None:
        return True
    if kind == 'json':
        try:
            json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            return True
        except (TypeError, ValueError):
            return False
    if kind == 'number':
        return bool(re.fullmatch(r'\s*[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?\s*', text))
    return text.strip().casefold() in ({'yes','no'} if kind == 'yes_no_en' else {'sì','si','no'})


def native_grammar(kind):
    from llama_cpp import LlamaGrammar
    if kind == 'json':
        return LlamaGrammar.from_json_schema('{}', verbose=False)
    rules = {
        'yes_no_it': 'root ::= "sì" | "si" | "no"',
        'yes_no_en': 'root ::= "yes" | "no"',
        'number': 'root ::= [+-]? [0-9]+ ([.,] [0-9]+)? ([eE] [+-]? [0-9]+)?',
    }
    return LlamaGrammar.from_string(rules[kind], verbose=False)


def invented_shared_experience(response, request):
    """Catch concrete co-participation claims, not ordinary conversational warmth.

    This deliberately bounded lexical gate is not a semantic truth verifier.
    Conversational acts remain allowed; quotations and requested fiction are data.
    """
    def unquoted(text):
        return re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»|“[^”\n]*”', '', text or '', flags=re.S)
    instruction = unquoted(request)
    if re.search(r'\b(?:scrivi|inventa|racconta|crea|riscrivi|riformula|traduci)\b.*\b(?:racconto|storia|dialogo|personaggio|poesia|prima persona)\b', instruction, re.I):
        return False
    plain = unquoted(response).replace('**', '').replace('__', '')
    shared = re.compile(
        r'\b(?:ho|abbiamo|aver|avere)\s+(?:davvero\s+)?(?:condiviso|vissuto|affrontato|attraversato|superato)\s+'
        r'(?P<object>[^.!?;\n]{1,110})', re.I)
    physical = re.compile(r'\b(?:trasloco|viaggio|vacanza|passeggiata|colloquio|esame|infanzia|malattia|lutto)\b', re.I)
    experiential = re.compile(r'\b(?:fase|esperienza|momento|percorso|avventura)\b', re.I)
    digital_object = re.compile(r'^(?:(?:un[ao]?|il|la|i|le|quest[oaie]|nostr[oaie]|dei|delle)\s+)?'
                                r'(?:messaggi?|conversazion[ei]|chat|informazioni|idee|testi?|risposte|riflessioni|file)\b', re.I)
    for match in shared.finditer(plain):
        # Exclude negated claims; do not suppress a later positive claim.
        before = plain[max(0, match.start()-18):match.start()]
        if re.search(r'\bnon\s+(?:l[’\']|lo\s+|la\s+)?$', before, re.I):
            continue
        obj = match['object'].strip()
        with_user = re.search(r'\b(?:con te|con voi|insieme a te|insieme a voi)\b', obj, re.I)
        if digital_object.match(obj):
            continue
        if physical.search(obj) and (with_user or match[0].lower().startswith('abbiamo')):
            return True
        if experiential.search(obj) and with_user:
            return True
    return False


def borrowed_user_experience(response, request):
    if invented_shared_experience(response, request):
        return True
    instruction = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»|“[^”\n]*”', '', request, flags=re.S)
    if re.search(r'\b(?:riscrivi|riformula|ripeti|traduci|rewrite|translate)\b', instruction, re.I) or re.search(
            r'\b(?:scrivi|inventa|racconta|crea)\b.*\b(?:racconto|storia|dialogo|personaggio|poesia|prima persona)\b', instruction, re.I):
        return False
    def clauses(text):
        text = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»|“[^”\n]*”', '', text, flags=re.S)
        # A helpful first clause cannot exempt a separate autobiographical one.
        pattern = r'\b(?:sono|mi sento|ho|lavoro|studio|vivo)\s+([^.!?\n]+?)(?=\b(?:sono|mi sento|ho|lavoro|studio|vivo)\b|[.!?\n]|$)'
        result = []
        for match in re.finditer(pattern, text, re.I):
            before = text[max(0, match.start()-20):match.start()]
            if re.search(r'\bnon\s+$', before, re.I):
                continue
            # "Ci sono / vi sono" is existential plural, not "io sono".
            # Scope this to the individual clause: a later personal claim
            # must still pass the normal attribution checks.
            if re.match(r'sono\b', match[0], re.I) and re.search(r'\b(?:ci|vi)\s+$', before, re.I):
                # Locative first person remains personal: "ci sono stata".
                personal = re.match(r'(?:(?:già|mai|sempre|ancora|appena)\s+)*(?:io\b|\w+(?:ato|ata|uto|uta|ito|ita)\b)', match[1], re.I)
                if not personal:
                    continue
            result.append(match[1])
        return result
    stop = {'e','ma','per','il','la','lo','i','le','un','una','di','del','della','al','a','che','mi','sono','molto','anche','non','con','te','tu','ti'}
    for answer in clauses(response):
        # First-person completed actions must be checked even when followed by
        # "tua" or "per te". Unlike "che tu abbia", "di aver" claims agency.
        action_verbs = r'(?:finito|completato|superato|terminato|vissuto|visitato|traslocato|affrontato|partecipato|frequentato|incontrato|iniziato|svolto)'
        own_action = (re.search(r'\b(?:di\s+)?aver(?:e)?\s+'+action_verbs+r'\b', answer, re.I)
                      or re.match(action_verbs+r'\b', answer, re.I))
        if not own_action and (re.search(r'\b(?:per te|aiutarti|ascoltarti|capirti|a disposizione|tuo|tua|tuoi|tue)\b', answer, re.I)
                or re.match(r'(?:capito|compreso|letto|ricevuto)\b', answer, re.I)):
            continue
        tokens = set(re.findall(r'\w+', answer.casefold()))-stop
        action_tokens = set(re.findall(r'\w+', answer[own_action.end():].casefold()))-stop if own_action else set()
        for original in clauses(request):
            user_tokens = set(re.findall(r'\w+', original.casefold()))-stop
            shared = tokens & user_tokens
            if len(shared) >= 2 or (own_action and action_tokens & user_tokens) or (len(user_tokens) == 1 and tokens == user_tokens):
                return True
    return False
