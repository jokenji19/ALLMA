"""Compare attributed claims within the scope of each supported topic."""
import re
import unicodedata

from .contribution_review import statements


_POLITE = r'(?:(?:puoi|potresti|riesci a|can you|could you)\s+)?'
_ACTION = (r'(?:confronta(?:re)?|incrocia(?:re)?|compara(?:re)?|verifica(?:re)?|'
           r'mett(?:i|ere) a confronto|(?:fai|fare) un confronto tra|compare|cross[- ]check|verify)')
_SOURCES = (r'(?:(?:le|the)\s+)?(?:(?:due|two)\s+)?(?:independent\s+)?'
            r'(?:fonti|sources)(?:\s+(?:indipendenti|di editori diversi|di siti diversi))?')
_JOIN = r'\s+(?:e|ed|and)\s+'
_AGENCIES = rf'(?:nasa{_JOIN}(?:esa|noaa)|(?:esa|noaa){_JOIN}nasa)'
_AGREEMENT = (r'(?:le\s+(?:due\s+)?fonti\s+(?:concordano|divergono|sono concordi|sono divergenti)'
              r'|do\s+(?:the\s+)?(?:two\s+)?sources\s+(?:agree|disagree))')
_HEAD = rf'(?:{_POLITE}{_ACTION}\s+(?:{_SOURCES}|{_AGENCIES})|{_AGREEMENT})'
_SCOPE_SEPARATOR = r"(?:\s*:\s*|\s+sull[’']\s*|\s+(?:sull[aoei]|sul|su|sugli|sui|about|on)\s+)"
_COMPARISON = re.compile(
    rf'\s*{_HEAD}(?:\s+tra loro)?(?:{_SCOPE_SEPARATOR}(?P<subject>\S.*?)\s*|[\s.!?]*)',
    re.I,
)


def _comparison_match(message):
    if not isinstance(message, str) or len(message) > 300:
        return None
    text = unicodedata.normalize('NFKC', message)
    if any(unicodedata.category(char) in {'Cc', 'Cf'} for char in text):
        return None
    return _COMPARISON.fullmatch(text)


def source_comparison_request(message):
    return _comparison_match(message) is not None


def source_comparison_followup(message):
    match = _comparison_match(message)
    return bool(match and match['subject'] is None)


def comparison_subject(message):
    match = _comparison_match(message)
    return 'Cerca ' + match['subject'] if match and match['subject'] else message


def clarify_comparison(message, previous):
    """Explain the preceding evidence grade using its recorded comparison."""
    if not re.fullmatch(r"\s*(?:cosa (?:intendi(?: dire)?|vuoi dire)|in che senso|what do you mean)[?.!\s]*", message, re.I):
        return None
    if previous is None or previous.role != 'assistant' or previous.metadata.get('is_valid') is not True:
        return None
    review = previous.metadata.get('reference_review') or {}
    if (previous.metadata.get('source') != 'reference_comparison' or review.get('basis') != 'source_comparison'
            or review.get('outcome') != 'agreement' or review.get('scope') not in
            {'europa_subsurface_ocean', 'enceladus_global_ocean'}):
        return None
    states = [row.get('state') for row in review.get('sources', ()) if isinstance(row, dict)]
    if len(states) != 2 or not set(states) <= {'strong_inference', 'inferred'}:
        return None
    subject = 'Europa' if review['scope'] == 'europa_subsurface_ocean' else 'Encelado'
    answer = (f'Gli indizi riportati dalle due fonti sostengono l’ipotesi di un oceano sotto il ghiaccio di {subject}. '
              'Per «inferenza» intendo che i ricercatori arrivano a questa conclusione interpretando misurazioni indirette.')
    return answer, dict(review, retrieval_status='history', network_used=False)


# Each rule is scoped to Europa and to an ocean beneath its surface. A generic
# mention of water, another moon, a future measurement, or a shared keyword
# cannot establish what the publisher says about this claim.
_OCEAN = r'(?:an? )?(?:global )?oceans? of (?:salty )?liquid water beneath (?:its|their) icy crusts?'
_CLAIM_PATTERNS = tuple((state, re.compile(pattern, re.I)) for state, pattern in (
    ('strong_inference', r"^jupiter's moon europa shows strong evidence for " + _OCEAN + r'\.$'),
    ('strong_inference', r'^several independent lines of evidence have led scientists to conclude that europa almost certainly has '
                          + _OCEAN + r'\.$'),
    ('inferred', r"^(?:the four largest of jupiter's moons are known as the 'galilean moons'; of these, )?"
                 r'three are thought to have ' + _OCEAN + r' \(ganymede, europa and callisto\)\.$'),
    ('inferred', r'^europa is thought to have ' + _OCEAN + r'\.$'),
    ('direct_observation', r'^direct observations confirmed that europa has ' + _OCEAN + r'\.$'),
    ('denied', r'^europa has no ocean of (?:salty )?liquid water beneath its icy crust\.$'),
    ('no_direct_observation', r'^no direct observations have confirmed an ocean of (?:salty )?liquid water '
                              r'beneath the icy crust of europa\.$'),
))

_LABELS = {'strong_inference': 'riporta forti indizi', 'inferred': 'descrive l’oceano come ipotesi',
           'direct_observation': 'riporta una conferma da osservazioni dirette',
           'denied': 'afferma che l’oceano è assente'}
_PUBLISHERS = {'nasa': 'NASA Science', 'esa': 'ESA', 'noaa': 'NOAA'}
AGENCY_PROVIDERS = {'Europa': ('nasa', 'esa'), 'Enceladus': ('nasa', 'esa'),
                    'Global sea level': ('nasa', 'noaa')}

_ENCELADUS_PATTERNS = (
    ('strong_inference', re.compile(r'^from gravity measurements based on the doppler effect[^.!?]{0,200}, scientists determined that the jets were being supplied by a global ocean inside the moon\.$', re.I)),
    ('strong_inference', re.compile(r"^studies with cassini have shown that beneath the moon's icy exterior lies a global ocean heated in part by tidal forces from saturn and its moon dione\.$", re.I)),
    ('denied', re.compile(r'^enceladus has no global ocean beneath its icy crust\.$', re.I)),
)
_SEA_LEVEL = re.compile(r'^(?:global sea level rise is caused primarily by two factors:|'
                        r'the rising water level is mostly due to a combination of) (.+)\.$', re.I)
_EXPANSION = re.compile(r'\bexpansion of (?:seawater|ocean water) as it warms\b', re.I)
_LAND_ICE = re.compile(r'\b(?:melting ice sheets and glaciers|melt water from glaciers and ice sheets)\b', re.I)


def agency_topic(subject, public_topic):
    if public_topic in ('Europa', 'Enceladus') and re.search(r'\b(?:ocean\w*|oceano)\b', subject, re.I):
        if re.search(r'\b(?:profond\w*|deep|depth|salinit\w*|salinity|vita|life|temperature|temperatura|'
                     r'sismic\w*|seismic\w*|spessore|thickness|quanto|how (?:big|large|deep))\b', subject, re.I):
            return None
        return public_topic
    sea_level = re.search(r'\b(?:livello (?:globale )?(?:del mare|dei mari|degli oceani)|sea[- ]level)\b', subject, re.I)
    causes = re.search(r'\b(?:caus\w*|perch[eé]|why|riscaldament\w*|warming|sciogliment\w*|melting)\b', subject, re.I)
    rise = re.search(r'\b(?:aument\w*|innalzament\w*|sal[ei]|alz\w*|ris(?:e|ing))\b', subject, re.I)
    if public_topic and sea_level and causes and rise and not re.search(r'\b(?:locale|local|regional\w*|quanto|how much)\b', subject, re.I):
        return 'Global sea level'
    return None


def _source_claim(reference, topic):
    patterns = _ENCELADUS_PATTERNS if topic == 'Enceladus' else _CLAIM_PATTERNS
    matches = {}
    for sentence in statements(reference.text, limit=64):
        # Preserve the original wording and offsets for the source panel.
        canonical = sentence.replace('’', "'").replace('‘', "'")
        if topic == 'Global sea level':
            causal = _SEA_LEVEL.fullmatch(canonical)
            if causal and _EXPANSION.search(causal[1]) and _LAND_ICE.search(causal[1]):
                start = reference.text.index(sentence)
                # NOAA refers to the global measurement in the preceding
                # sentence. Keep the attribution tied to that same paragraph.
                if canonical.lower().startswith('the rising water level'):
                    begin = reference.text.rfind('\n', 0, start) + 1
                    prior = reference.text[begin:start]
                    if not re.search(r'^global mean sea level has risen\b', prior, re.I):
                        continue
                    sentence = prior + sentence
                matches.setdefault('strong_inference', sentence)
            continue
        for state, pattern in patterns:
            if pattern.search(canonical):
                matches.setdefault(state, sentence)
    # Multiple positive formulations can differ in certainty. An internal
    # disagreement, however, is not a usable vote in the comparison.
    if ('denied' in matches and any(state in matches for state in ('direct_observation', 'strong_inference', 'inferred'))
            or 'direct_observation' in matches and 'no_direct_observation' in matches):
        return None
    for state in ('direct_observation', 'strong_inference', 'inferred', 'denied', 'no_direct_observation'):
        if state in matches:
            excerpt = matches[state]
            start = reference.text.index(excerpt)
            return {'state': state, 'excerpt': excerpt, 'span': [start, start + len(excerpt)],
                    'source_id': reference.identifier, 'citation': reference.citation()}
    return None


def compare_agencies(topic, references, source_states):
    providers = AGENCY_PROVIDERS[topic]
    sources = {r.provider: r for r in references if r.title == topic and r.provider in providers}
    claim = {'Europa': 'la presenza dell’oceano sotto il ghiaccio di Europa',
             'Enceladus': 'la presenza di un oceano globale sotto il ghiaccio di Encelado',
             'Global sea level': 'le cause principali dell’innalzamento globale del mare'}[topic]
    support = {'Europa': 'un oceano sotto il ghiaccio di Europa',
               'Enceladus': 'un oceano globale sotto il ghiaccio di Encelado'}
    rows = []
    for provider in providers:
        publisher = _PUBLISHERS[provider]
        reference = sources.get(provider)
        evidence = _source_claim(reference, topic) if reference else None
        rows.append({'publisher': publisher, 'provider': provider, 'via': source_states.get(provider),
                     **(evidence or {'state': 'not_addressed' if reference else 'unavailable',
                                 'citation': reference.citation() if reference else None})})

    first, second = (row['state'] for row in rows)
    statements_present = [row for row in rows if row['state'] in _LABELS]
    if len(statements_present) < 2:
        outcome = 'insufficient'
        conclusion = f'Il confronto su {claim} resta aperto. Servono due passaggi pertinenti.'
    elif (first == 'denied') != (second == 'denied'):
        outcome = 'disagreement'
        conclusion = f'Le fonti divergono su {claim}. Il confronto lascia la questione aperta.'
    else:
        outcome = 'agreement'
        if topic == 'Global sea level':
            conclusion = ('Le due fonti indicano le stesse cause principali: l’acqua oceanica si espande '
                          'quando si scalda e lo scioglimento dei ghiacci sulla terraferma aggiunge acqua al mare.')
        elif first == second == 'denied':
            conclusion = 'I due documenti affermano che l’oceano è assente.'
        elif first == second == 'direct_observation':
            conclusion = 'I due documenti riportano osservazioni dirette a sostegno della presenza dell’oceano.'
        else:
            conclusion = f'Entrambe le fonti riportano elementi a favore di {support[topic]}.'
            if first != second:
                conclusion += ' La formulazione e il grado di certezza differiscono.'
            if 'direct_observation' not in (first, second):
                conclusion += ' Nei passaggi citati la presenza dell’oceano è un’inferenza.'

    lines = []
    for row in rows:
        state = row['state']
        detail = _LABELS.get(state) or {
            'not_addressed': 'passaggio pertinente assente',
            'no_direct_observation': 'segnala che mancano osservazioni dirette',
        }.get(state, 'nessuna copia locale disponibile' if row['via'] == 'local_only' else 'fonte non disponibile')
        if topic == 'Global sea level' and state == 'strong_inference':
            detail = 'attribuisce l’innalzamento soprattutto a questi due fattori'
        lines.append(f"**{row['publisher']}** — {detail}.")
        if row.get('excerpt'):
            lines.append('> '+row['excerpt'])
    limit = {
        'Europa': 'Le fonti possono basarsi sulle stesse osservazioni.',
        'Enceladus': 'Le due fonti si basano su dati della missione congiunta Cassini–Huygens.',
        'Global sea level': 'Il confronto riguarda le cause globali. Il contributo dei due fattori varia nel tempo e il livello locale dipende anche da altri fenomeni.',
    }[topic]
    return '\n\n'.join([conclusion, *lines, limit]), {
        'basis': 'source_comparison', 'truth_verified': False, 'outcome': outcome,
        'scope': {'Europa': 'europa_subsurface_ocean', 'Enceladus': 'enceladus_global_ocean',
                  'Global sea level': 'global_sea_level_causes'}[topic], 'sources': rows,
    }


def compare_europa(references, source_states):
    return compare_agencies('Europa', references, source_states)


def compare_editions(references, source_states, count=3):
    """Show two verified editions side by side without asserting entailment."""
    from .contribution_review import select_contribution

    rows, sections = [], []
    for reference in references[:2]:
        lang = 'it' if reference.url.startswith('https://it.wikipedia.org/') else 'en'
        selected = select_contribution([reference], default_count=count, reserve_followup=False)
        if selected is None:
            continue
        label = 'Wikipedia in italiano' if lang == 'it' else 'Wikipedia in inglese'
        rows.append({'publisher': label, 'provider': 'wikipedia', 'via': source_states.get(lang),
                     'state': 'excerpt', 'excerpt': selected.text, 'spans': selected.audit()['spans'],
                     'source_id': reference.identifier, 'citation': reference.citation()})
        sections.append(f'**{label}**\n\n{selected.text}')
    if not sections:
        return '', {}
    paired = len(sections) == 2
    intro = ('Le due voci trattano lo stesso argomento. Appartengono entrambe a Wikipedia e possono condividere fonti.'
             if paired else 'Ho trovato un solo passaggio utilizzabile. Il confronto resta aperto.')
    return '\n\n'.join([intro, *sections]), {
        'basis': 'source_comparison', 'truth_verified': False, 'outcome': 'parallel_reading' if paired else 'insufficient',
        'scope': 'linked_wikipedia_editions', 'sources': rows,
    }
