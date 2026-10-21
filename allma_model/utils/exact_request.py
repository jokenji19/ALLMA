"""Small shared envelope for exact tools, consuming rather than ignoring format.

Text tools must mask literals before calling this; arithmetic operands are
validated separately. Extra commands remain in the body and fail full matching.
"""
import re

MAX_TOOL_REQUEST = 9216
_COURTESY = re.compile(r'^(?:per\s+(?:favore|cortesia)|gentilmente)\s*,?\s+', re.I)
_DIRECTIVE = re.compile(
    r'(?:(?:rispondi(?:mi)?|scrivi(?:mi)?|restituisci(?:mi)?)|'
    r'(?:puoi|potresti)\s+(?:risponder(?:e|mi)|scriver(?:e|mi)|restituir(?:e|mi)))\s+'
    r'(?:(?:solo|soltanto|esclusivamente)\s+|(?:con|in)\s+un\s+(?:solo|unico)\s+)'
    r'(?P<kind>(?:(?:con|in)\s+)?(?:(?:un|il)\s+)?'
    r'(?:numero|risultato numerico|JSON(?:\s+valido)?|s[iì]\s*(?:o|oppure|/)\s*no))', re.I)
_SUFFIX = re.compile(r'(?:[?.;:]\s*|\s+(?:e\s+)?)' + _DIRECTIVE.pattern + r'\s*[.!?]?\s*$', re.I)


def split_exact_request(message):
    if not isinstance(message, str) or len(message) > MAX_TOOL_REQUEST:
        return None
    # Only masked data may pass here from a text tool: whitespace inside a
    # literal must not be collapsed. Arithmetic whitespace is not a digit.
    body = re.sub(r'\s+', ' ', message).strip()
    body = _COURTESY.sub('', body, count=1)
    kind = 'prose'
    prefix = _DIRECTIVE.match(body)
    separator = re.match(r'\s*[:.?!]\s*', body[prefix.end():]) if prefix else None
    if separator:
        kind = prefix['kind']
        body = body[prefix.end()+separator.end():]
    else:
        suffix = _SUFFIX.search(body)
        if suffix:
            kind = suffix['kind']
            body = body[:suffix.start()]
    kind = ('json' if 'json' in kind.casefold() else
            'number' if re.search(r'numero|risultato numerico', kind, re.I) else
            'yes_no' if kind != 'prose' else 'prose')
    body = _COURTESY.sub('', body.strip(), count=1)
    body = re.sub(r'^(?:(?:puoi|potresti)\s+dirmi|dimmi)\s+(?=(?:quante|quanti|quanto|qual)\b)',
                  '', body, count=1, flags=re.I)
    body = re.sub(r'^(?:puoi|potresti)\s+(contare|calcolare)\s+',
                  lambda m: 'conta ' if m[1].casefold() == 'contare' else 'calcola ', body, count=1, flags=re.I)
    return body, kind
