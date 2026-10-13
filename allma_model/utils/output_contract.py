"""Explicit output shapes; no reference answers and no silent answer rewriting."""
import json
import re


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
    if '```' in text or re.search(r'["«»“”]|(?m:^\s*(?:[-*]|\d+[.)])\s)', text):
        return None
    if re.search(r'\b(?:dott|sig|prof|ecc|es|mr|dr)\.', text, re.I):
        return None
    plain = re.sub(r'(?<=\d)[.,](?=\d)', '_', text.strip())
    # A run of punctuation (?! or ...) closes one sentence.
    parts = re.split(r'[.!?]+(?=\s|$)', plain)
    return len([part for part in parts if part.strip()])


def valid_sentence_count(text, count):
    actual = sentence_count(text) if count else None
    return actual is None or actual == count


def requested_contract(request):
    # Examples/quoted instructions are not commands to the assistant.
    plain = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»', '', request or '', flags=re.S)
    if re.search(r'\b(?:non solo|non soltanto|not only|non rispondi|non scrivi)\b', plain, re.I):
        return None
    if not re.search(r'\b(?:rispondi|scrivi|restituisci|output|answer|return|respond)\b', plain, re.I):
        return None
    if not re.search(r'\b(?:solo|soltanto|esclusivamente|only)\b', plain, re.I):
        return None
    if re.search(r'\bjson\b', plain, re.I):
        return 'json'
    if re.search(r'\b(?:s[iì]\s*(?:o|/)\s*no|yes\s*(?:or|/)\s*no)\b', plain, re.I):
        return 'yes_no_en' if re.search(r'\byes\b', plain, re.I) else 'yes_no_it'
    if re.search(r'\b(?:numero|risultato numerico|number|numeric result)\b', plain, re.I):
        return 'number'
    return None


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


def borrowed_user_experience(response, request):
    if re.search(r'\b(?:riscrivi|riformula|ripeti|traduci|scrivi|inventa|racconta|rewrite|translate)\b', request, re.I):
        return False
    def clauses(text):
        text = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»\n]*»|“[^”\n]*”', '', text, flags=re.S)
        return re.findall(r'\b(?:sono|mi sento|ho|lavoro|studio|vivo)\s+([^.!?\n]+)', text, re.I)
    stop = {'e','ma','per','il','la','lo','i','le','un','una','di','del','della','al','a','che','mi','sono','molto','anche','non','con','te','tu','ti'}
    for answer in clauses(response):
        if re.search(r'\b(?:per te|aiutarti|ascoltarti|capirti|a disposizione|tuo|tua|tuoi|tue)\b', answer, re.I) or re.match(r'(?:capito|compreso|letto|ricevuto)\b', answer, re.I):
            continue
        tokens = set(re.findall(r'\w+', answer.casefold()))-stop
        for original in clauses(request):
            user_tokens = set(re.findall(r'\w+', original.casefold()))-stop
            shared = tokens & user_tokens
            if len(shared) >= 2 or (len(user_tokens) == 1 and tokens == user_tokens):
                return True
    return False
