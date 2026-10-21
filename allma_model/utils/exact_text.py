"""Bounded, literal text operations. No model, history lookup or reference answers.

Parsing consumes the entire request. Quotes delimit data, never instructions;
unsupported/multiple operations stay on the ordinary conversation path.
"""
from dataclasses import dataclass, replace
import hashlib
import json
import re
import unicodedata
from .exact_request import split_exact_request

MAX_TEXT = 8192
MAX_REQUEST = MAX_TEXT + 1024
_QUOTES = {'"': '"', "'": "'", '«': '»', '“': '”', '‘': '’', '`': '`'}
_LITERAL = r'(?:@\d+@|[\w]+(?:[-’\x27][\w]+)*)'
_ARTICLE = r'(?:(?:il testo|la parola|la stringa|il termine)\s+)?'
_IN = r'(?:in|nel testo|nella parola|nella stringa|nel termine)\s+'
_OF = r'(?:di|del testo|della parola|della stringa|del termine|in|nel testo|nella parola|nella stringa|:)\s*'
_NUMBERS = dict(zip(('zero uno due tre quattro cinque sei sette otto nove dieci undici dodici '
                     'tredici quattordici quindici sedici diciassette diciotto diciannove venti').split(), range(21)))
_NUMBERS.update(ventuno=21, ventidue=22, ventitré=23, ventitre=23, ventiquattro=24,
                venticinque=25, ventisei=26, ventisette=27, ventotto=28, ventinove=29, trenta=30)
_NUMBERS.update(un=1, una=1)


@dataclass(frozen=True)
class TextCount:
    operation: str
    text: str
    needle: str = ''
    expected: object = None
    overlap: object = None  # None: caller has not selected a matching policy.
    output: str = 'prose'
    choice_origin: str = 'explicit_request'


def _literals(message):
    """Replace delimited literals before parsing; never unescape/strip payloads."""
    pieces, values, i = [], [], 0
    while i < len(message):
        char = message[i]
        if char in _QUOTES and not (char == "'" and i and message[i-1].isalnum()):
            end = message.find(_QUOTES[char], i+1)
            # In Italian, an apostrophe between letters belongs to the word,
            # including inside a single-quoted operand such as 'l'acqua'.
            while (char in ("'", '‘') and end > 0 and end+1 < len(message)
                   and message[end-1].isalnum() and message[end+1].isalnum()):
                end = message.find(_QUOTES[char], end+1)
            if end < 0 or (char == '`' and message[i:i+3] == '```'):
                return None
            # Escaped delimiters are deliberately unsupported, not reinterpreted.
            value = message[i+1:end]
            if '\\' in value or len(value) > MAX_TEXT:
                return None
            pieces.append('@' + str(len(values)) + '@')
            values.append(value)
            i = end+1
        else:
            if char in '@«»“”‘’`"' and char != '’':
                return None  # A placeholder cannot be supplied by the user.
            pieces.append(char)
            i += 1
    return ''.join(pieces), values


def parse_text_count(message):
    if not isinstance(message, str) or len(message) > MAX_REQUEST or any(0xD800 <= ord(c) <= 0xDFFF for c in message):
        return None
    masked = _literals(message)
    if masked is None:
        return None
    plain, values = masked
    plain, output = split_exact_request(plain)
    plain = re.sub(r'[?.!]\s*$', '', plain).strip()
    overlap = None
    modifier = re.search(r',?\s+(?P<mode>(?:includendo|contando anche) le sovrapposizioni|senza sovrapposizioni)$', plain, re.I)
    if modifier:
        overlap = not modifier['mode'].casefold().startswith('senza')
        plain = plain[:modifier.start()].strip()
    lit = lambda name: '(?P<' + name + '>' + _LITERAL + ')'
    expected = None
    needle = None
    match = re.fullmatch(r'(?:quante (?P<letters>lettere)|quanti (?P<chars>caratteri|punti di codice Unicode))\s+'
                         r'(?:contiene|ha)\s+' + _ARTICLE + lit('text'), plain, re.I)
    if not match:
        match = re.fullmatch(r'conta\s+(?:le (?P<letters>lettere)|i (?P<chars>caratteri|punti di codice Unicode))(?=\s|:)\s*'
                             + _OF + _ARTICLE + lit('text'), plain, re.I)
    if not match:
        match = re.fullmatch(r'(?:quante (?P<letters>lettere)|quanti (?P<chars>caratteri|punti di codice Unicode))\s+'
                             r'(?:ci sono|sono presenti)\s+' + _IN + _ARTICLE + lit('text'), plain, re.I)
    if not match:
        match = re.fullmatch(_ARTICLE + lit('text') + r'\s+(?:contiene|ha)\s+'
                             r'(?P<expected>\d{1,6}|[a-zàé]+)\s+'
                             r'(?:(?P<letters>letter[ae])|(?P<chars>caratter[ei]|punt[oi] di codice Unicode))', plain, re.I)
        if match:
            spelling = match['expected'].casefold()
            expected = int(spelling) if spelling.isdigit() else _NUMBERS.get(spelling)
            if expected is None:
                return None
            if spelling == 'una' and (match['letters'] or '').casefold() != 'lettera':
                return None
            if spelling == 'un' and (match['chars'] or '').casefold() not in ('carattere', 'punto di codice unicode'):
                return None
    if match:
        operation = ('letters' if match['letters'] else
                     'codepoints' if match['chars'].casefold().startswith('punt') else 'characters')
        if overlap is not None:
            return None
    else:
        subject = r'(?:(?:la lettera|il carattere|la sequenza|la parola|il termine)\s+)?'
        of_needle = r'(?:di\s+' + subject + r'|della (?:lettera|sequenza|parola)\s+|del (?:carattere|termine)\s+)'
        tail = lit('needle') + r'\s+' + _IN + _ARTICLE + lit('text')
        patterns = [
            r'quante volte (?:compare|appare|è presente)\s+' + subject + tail,
            r'conta le occorrenze\s+' + of_needle + tail,
            r'quante occorrenze\s+' + of_needle + lit('needle') + r'\s+(?:ci sono|sono presenti)\s+' + _IN + _ARTICLE + lit('text'),
        ]
        match = next((matched for pattern in patterns if (matched := re.fullmatch(pattern, plain, re.I))), None)
        if not match:
            return None
        operation = 'occurrences'
        needle = match['needle']

    # Bare one-token references like "questo" are not explicit text operands.
    ambiguous = {'questo', 'quello', 'questa', 'quella', 'questi', 'quelli', 'queste', 'quelle',
                 'sopra', 'prima', 'qui', 'mio', 'tuo', 'tutto', 'tutta', 'tutte', 'tutti', 'esso', 'essa'}
    used = []
    def operand(token):
        if token.startswith('@'):
            index = int(token[1:-1])
            used.append(index)
            return values[index]
        return None if token.casefold() in ambiguous or len(token) > MAX_TEXT else token
    text = operand(match['text'])
    needle = operand(needle) if needle is not None else ''
    if text is None or needle is None or sorted(used) != list(range(len(values))):
        return None
    if (expected is None and output == 'yes_no') or (expected is not None and output == 'number'):
        return None  # Contradictory operation and output shape.
    return TextCount(operation, text, needle, expected, overlap, output)


def _android_graphemes(text):
    # Built into Android API 24+, matching this app's minimum API; no extra model/library.
    from jnius import autoclass
    iterator = autoclass('android.icu.text.BreakIterator').getCharacterInstance(autoclass('java.util.Locale').ROOT)
    iterator.setText(text)
    iterator.first()
    count = 0
    while iterator.next() != -1:
        count += 1
    return count


def _characters(text):
    # The cheap path is intentionally limited to Latin without remaining marks.
    # Complex emoji/scripts go through the platform grapheme segmenter, never len().
    normalized = unicodedata.normalize('NFC', text)
    if all(ord(c) < 0x250 and not unicodedata.category(c).startswith('M') for c in normalized):
        return len(normalized) - normalized.count('\r\n'), 'unicode-latin-graphemes'
    return _android_graphemes(text), 'android-icu-graphemes'


def count_request(request):
    """Evaluate a parsed literal request, returning grounded-answer provenance."""
    evidence = {'operation': request.operation,
                'input_sha256': hashlib.sha256(request.text.encode('utf-8')).hexdigest(),
                'input_codepoints': len(request.text), 'scope': 'explicit_literal_only'}
    if request.operation == 'letters':
        value = sum(c.isalpha() for c in unicodedata.normalize('NFC', request.text))
        evidence.update(engine='python-unicode', policy='NFC_alphabetic_codepoints', unicode_version=unicodedata.unidata_version)
    elif request.operation == 'codepoints':
        value = len(request.text)
        evidence.update(engine='python-unicode', policy='raw_Unicode_codepoints')
    elif request.operation == 'characters':
        try:
            value, engine = _characters(request.text)
        except Exception:
            # A missing/failing platform service is not a verified count.
            return ('Non riesco a verificare il numero di caratteri di questo testo su questo dispositivo.',
                    'text_count_unavailable', [evidence])
        evidence.update(engine=engine, policy='grapheme_clusters_including_spaces')
    else:
        if not request.needle:
            return ('Indica almeno un carattere da cercare: una sequenza vuota non ha un conteggio univoco.',
                    'text_count_clarification', [evidence])
        evidence.update(engine='python-literal', policy='case_sensitive_raw_literal', overlapping=request.overlap,
                        needle_sha256=hashlib.sha256(request.needle.encode('utf-8')).hexdigest(), choice_origin=request.choice_origin)
        disjoint = request.text.count(request.needle)
        overlapping = disjoint
        # Only repeated, bordered needles can overlap themselves. Compute the
        # alternate policy when necessary, without regex or a second model call.
        if request.overlap is not False and disjoint and len(request.needle) > 1:
            overlapping = 0
            position = request.text.find(request.needle)
            while position != -1:
                overlapping += 1
                position = request.text.find(request.needle, position+1)
        if request.overlap is None and disjoint != overlapping:
            evidence.update(engine='python-literal', policy='overlap_unspecified',
                            candidates={'without_overlap': disjoint, 'with_overlap': overlapping})
            return (f'Trovo {disjoint} occorrenze senza sovrapposizioni e {overlapping} includendo le sovrapposizioni. Quale criterio vuoi usare?',
                    'text_count_clarification', [evidence])
        value = overlapping if request.overlap else disjoint
    evidence['value'] = value
    verified = None if request.expected is None else value == request.expected
    if verified is not None:
        evidence.update(expected=request.expected, proposition_true=verified)
    if request.output == 'json':
        payload = {'conteggio': value}
        if verified is not None:
            payload['esito'] = verified
        answer = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    elif request.output == 'number':
        answer = str(value)
    elif verified is not None:
        answer = ('sì' if verified else 'no') if request.output == 'yes_no' else (
            ('Sì' if verified else 'No') + ', il conteggio è ' + str(value) + '.')
    else:
        units = {'letters': ('lettera', 'lettere'), 'characters': ('carattere (spazi inclusi)', 'caratteri (spazi inclusi)'),
                 'codepoints': ('punto di codice Unicode', 'punti di codice Unicode'), 'occurrences': ('occorrenza', 'occorrenze')}
        unit = units[request.operation][0 if value == 1 else 1]
        answer = str(value) + ' ' + unit + '.'
        if request.operation == 'occurrences':
            answer += (' Contando anche le sovrapposizioni.' if request.overlap else
                       ' Senza sovrapposizioni.' if request.overlap is False else ' Le occorrenze non si sovrappongono.')
            answer += ' Distinguo maiuscole e minuscole.'
    return answer, 'verified_text_count', [evidence]


def _clarification_choice(message, history):
    """Resolve only the immediately pending tool question in caller-scoped history."""
    if not isinstance(message, str) or len(message) > MAX_REQUEST or len(history) < 2:
        return None
    masked = _literals(message)
    if masked is None or masked[1]:
        return None
    body, output = split_exact_request(masked[0])
    body = re.sub(r'[?.!]\s*$', '', body).strip()
    assistant = history[-1]
    metadata = getattr(assistant, 'metadata', None)
    if (getattr(assistant, 'role', None) != 'assistant'
            or not isinstance(metadata, dict) or metadata.get('source') != 'text_count_clarification'):
        return None
    records = metadata.get('evidence')
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        return None
    evidence = records[0]
    if evidence.get('policy') != 'overlap_unspecified' or evidence.get('scope') != 'explicit_literal_only':
        return None
    original = None
    # One declined proposal may add a clarification pair. Bind back to the
    # explicit operands using both digests, never generic conversation text.
    for candidate in reversed(history[-8:-1]):
        if getattr(candidate, 'role', None) != 'user':
            continue
        parsed = parse_text_count(getattr(candidate, 'content', None))
        if (parsed is not None and parsed.operation == 'occurrences' and parsed.overlap is None
                and parsed.expected is None
                and evidence.get('input_sha256') == hashlib.sha256(parsed.text.encode('utf-8')).hexdigest()
                and evidence.get('needle_sha256') == hashlib.sha256(parsed.needle.encode('utf-8')).hexdigest()):
            original = parsed;break
    if original is None or output == 'yes_no':
        return None
    proposed = evidence.get('suggested_overlap')
    if re.fullmatch(r'(?:con(?: le)? sovrapposizioni|(?:conta|contando|includi|includendo) (?:anche )?(?:le )?sovrapposizioni)', body, re.I):
        overlap = True
    elif re.fullmatch(r'(?:senza(?: le)? sovrapposizioni|(?:escludi|non contare) (?:le )?sovrapposizioni)', body, re.I):
        overlap = False
    elif type(proposed) is bool and body.casefold() in ('sì', 'si', 'sì grazie', 'si grazie', 'va bene', 'confermo'):
        overlap = proposed
    elif type(proposed) is bool and body.casefold() in ('no', 'no grazie'):
        return replace(original, choice_origin='declined_suggestion', output=original.output if output == 'prose' else output)
    else:
        return None
    return replace(original, overlap=overlap, output=original.output if output == 'prose' else output,
                   choice_origin='learned_suggestion_response' if type(proposed) is bool or evidence.get('choice_origin') in ('declined_suggestion','learned_suggestion_response') else 'explicit_user_choice')


def text_count_reply(message, *, execute=None, history=(), suggestion=None):
    """History, when provided, must already be scoped to the current user and chat."""
    request = parse_text_count(message)
    continued = request is None
    if continued:
        request = _clarification_choice(message, history)
    if request is None:
        return None
    result = (execute or count_request)(request)
    if continued and result[1] == 'verified_text_count':
        result[2][0]['clarification_resolved'] = True
    if result[1] == 'text_count_clarification' and result[2][0].get('policy') == 'overlap_unspecified' and request.choice_origin != 'declined_suggestion':
        try:
            suggestion = suggestion() if callable(suggestion) else suggestion
        except Exception:
            suggestion = None
    if (result[1] == 'text_count_clarification' and result[2][0].get('policy') == 'overlap_unspecified'
            and request.choice_origin != 'declined_suggestion' and isinstance(suggestion, dict)
            and type(suggestion.get('suggested_overlap')) is bool
            and type(suggestion.get('confirmed_tasks')) is int and suggestion['confirmed_tasks'] >= 3):
        choice = suggestion['suggested_overlap']
        result[2][0].update(suggested_overlap=choice, suggestion_support_count=suggestion['confirmed_tasks'], strategy_source='meta_learning')
        wording = 'includere le sovrapposizioni' if choice else 'escludere le sovrapposizioni'
        answer = result[0].split(' Quale criterio vuoi usare?')[0]
        answer += f' Negli esempi che hai confermato hai scelto spesso di {wording}. Vuoi usare questo criterio anche qui?'
        result = answer, result[1], result[2]
    return result
