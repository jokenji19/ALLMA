"""Small, explicit semantic features for retrieval, never autobiographical facts.

This is a bounded concept lexicon, not a neural embedding or a truth checker.
Descriptions of an object's function can nominate several matching memories;
only the original, attributed records may supply an answer.
"""
import re
import unicodedata


def words(text):
    return re.findall(r"[^\W_]+(?:[-_][^\W_]+)*", unicodedata.normalize('NFKC', text).casefold())


# General language capabilities; none of these entries describes a user's life.
CONCEPTS = {
    'rain_cover': (r'ombrell[oi]|impermeabil[ei]|umbrella|raincoat',
        r'(?:riparar\w*|protegg\w*|protezion\w*|riparo|shelter|protect\w*).{0,45}(?:pioggia|rain)|(?:non bagnarm\w*|restare asciutt\w*)'),
    'writing_tool': (r'penn[ae]|matit[ae]|pen|pencil',
        r'(?:strument\w*|oggett\w*|qualcosa|quello|uso|usavo|serve|tool).{0,40}(?:scriver\w*|writing|write)'),
    'cutting_tool': (r'forbic[ei]|scissors',
        r'(?:tagliar\w*|ritagliar\w*|cutting|cut).{0,25}(?:cart[ae]|fogli\w*|tessut\w*|paper|fabric)'),
    'portable_light': (r'torci[ae]|torcia|flashlight',
        r'(?:illumin\w*|vedere|luce|see|light).{0,35}(?:buio|oscur\w*|dark)|(?:buio|dark).{0,35}(?:illumin\w*|luce|light)'),
    'portable_power': (r'powerbank|power bank|batteria portatile|caricatore portatile',
        r'(?:ricaric\w*|caric\w*|charge).{0,30}(?:telefon\w*|cellular\w*|smartphone|phone)'),
    'screw_tool': (r'cacciavit[ei]|screwdriver',
        r'(?:avvitar\w*|svitar\w*|stringer\w*|allentar\w*|tighten|loosen).{0,25}(?:vit[ei]|screws?)'),
    'temperature_tool': (r'termometr\w*|thermometer',
        r'(?:misurar\w*|controllar\w*|measure|check).{0,25}(?:febbre|temperatura|fever|temperature)'),
    'vision_aid': (r'occhiali|spectacles|eyeglasses',
        r'(?:veder\w*|legger\w*|see|read).{0,15}(?:meglio|better)'),
    'bicycle': (r'bici|biciclett[ae]|bicycle|bike', r'(?:mezzo|veicolo).{0,20}pedali'),
    'car': (r'auto|automobil[ei]|vettur[ae]|car', r''),
    'physician_visit': (r'visita medica|appuntamento medico|dottor\w*|medic[oa]|physician|doctor', r''),
    'veterinary_visit': (r'veterinari\w*|veterinary|vet', r''),
    'movie': (r'film|pellicol[ae]|movie|cinema', r''),
    'book': (r'libr[oi]|romanz[oi]|book|novel', r''),
}


_PATTERNS = {name: tuple(re.compile(r'\b(?:'+pattern+r')\b', re.I)
                         for pattern in patterns if pattern)
             for name, patterns in CONCEPTS.items()}


def concepts(text):
    # Sentence boundaries prevent unrelated clauses forming a false function.
    normalized = unicodedata.normalize('NFKC', text).casefold()
    clauses = re.split(r'[.!?;\n]', normalized)
    return frozenset(name for name, patterns in _PATTERNS.items()
                     if any(pattern.search(clause) for clause in clauses for pattern in patterns))
