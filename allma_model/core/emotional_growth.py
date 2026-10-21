"""Pure, bounded updates for CoalescenceProcessor's persistent growth section.

User meanings remain user meanings. Learned response dispositions belong to
ALLMA's software policy, not to the user's biography or subjective feelings.
"""
import copy
import hashlib
import math
import re
import unicodedata
from allma_model.emotional_system.emotion_analysis import analyze, LEXICON, NUANCE_NAMES_IT, PATTERNS


def empty_state():
    return {'version': 1, 'profiles': {}}


def canonical(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def aliases(state, user_id):
    profile = state.get('profiles', {}).get(user_id, {})
    return {key: value['label'] for key, value in profile.get('meanings', {}).items()
            if value.get('label') in LEXICON}


def declared_meaning(text):
    match = re.fullmatch(
        r'(?:per me|quando dico)\s+["«“]?([\wÀ-ÿ -]{1,32})["»”]?\s+'
        r'(?:significa|intendo|vuol dire)\s+([^\n]{1,240})', text.strip(), re.I)
    if not match:
        return None
    term, definition = canonical(match[1]), match[2].strip()
    # A personal explanation is data, not a definition of everyone else's life.
    # Only an unambiguous named emotion permits a local lexical association.
    labels = [label for label, italian in NUANCE_NAMES_IT.items()
              if re.search(r'(?<!\w)' + re.escape(italian) + r'(?!\w)', definition, re.I)]
    if not labels and term not in LEXICON and term not in {canonical(v) for v in NUANCE_NAMES_IT.values()}:
        return None
    return term, {'definition': definition, 'label': labels[0] if len(labels) == 1 else None,
                  'source': 'explicit_user_definition'}


def _evidence_counts(association):
    """Migrate retained legacy evidence; never invent discarded observations.

    Counts outlive the small recent-context window. Grouping by lexical
    provenance lets a correction withdraw even older interpretations.
    """
    if 'evidence_counts' not in association:
        counts = {}
        for key in association.get('contexts', []):
            origin = '\x1f'.join(sorted(set(association.get('context_origins', {}).get(key, []))))
            counts[origin] = counts.get(origin, 0) + 1
        association['evidence_counts'] = counts
    return association['evidence_counts']


def evolve(state, user_id, event_id, text):
    """Copy-on-write; persistence/commit belongs to the coalescence owner."""
    if not user_id or not event_id or not isinstance(text, str):
        raise ValueError('Attributed experience required')
    candidate = copy.deepcopy(state)
    profile = candidate['profiles'].setdefault(user_id, {
        'meanings': {}, 'associations': {}, 'recent_events': [],
        'trait_deltas': {}, 'response_disposition': {}, 'recent_droplets': []})
    key = hashlib.sha256(event_id.encode()).hexdigest()
    if key in profile['recent_events']:
        return state, {'status': 'duplicate_event'}
    definition = declared_meaning(text)
    perception = analyze(text, learned_aliases=aliases(state, user_id))
    records = perception['analysis']
    labels = [label for label, strength in perception['nuances'].items() if strength >= .8]
    # A hypothetical second clause must not erase clear evidence from the
    # first. Uncertain labels themselves are below the required .8 strength.
    if definition is None and (not labels or records['truncated']):
        return state, {'status': 'no_clear_experience'}
    changed = []
    meaning_corrected = False
    if definition:
        term, meaning = definition
        # Never override linguistic baseline words with a personal redefinition.
        builtin = (term in LEXICON or term in {canonical(v) for v in NUANCE_NAMES_IT.values()}
                   or any(pattern.fullmatch(term) for _, _, pattern in PATTERNS))
        meaning['baseline_word'] = builtin
        if builtin:
            meaning['label'] = None
        previous = profile['meanings'].get(term)
        if previous and previous.get('label') != meaning['label']:
            meaning_corrected = True
            # Withdraw interpreted contexts tied to a corrected lexical meaning.
            for association in profile['associations'].values():
                counts = _evidence_counts(association)
                association['evidence_counts'] = {origin: count for origin, count in counts.items()
                                                  if term not in origin.split('\x1f')}
                provenance = association.get('context_origins', {})
                association['contexts'] = [key for key in association['contexts'] if term not in provenance.get(key, [])]
                association['context_origins'] = {key: provenance.get(key, []) for key in association['contexts']}
                association['observations'] = sum(association['evidence_counts'].values())
                association['stage'] = 'integrated' if association['observations'] >= 2 else 'suspended'
        profile['meanings'][term] = meaning
        changed.append('personal_meaning')
        labels = []  # Teaching a term is not experiencing its emotion right now.
    context_key = hashlib.sha256(canonical(text).encode()).hexdigest()
    integrated = []
    for label in labels:
        association = profile['associations'].setdefault(label, {'contexts': [], 'observations': 0, 'stage': 'suspended', 'context_origins': {}})
        if context_key in association['contexts']:
            continue
        counts = _evidence_counts(association)
        association['contexts'] = (association['contexts'] + [context_key])[-32:]
        origins = association.setdefault('context_origins', {})
        origins[context_key] = list({item['learned_alias'] for item in records['evidence'] if item['label'] == label and 'learned_alias' in item})
        origin = '\x1f'.join(sorted(origins[context_key]))
        counts[origin] = counts.get(origin, 0) + 1
        association['context_origins'] = {key: origins.get(key, []) for key in association['contexts']}
        association['observations'] = sum(counts.values())
        if association['observations'] >= 2:
            association['stage'] = 'integrated'
            integrated.append(label)
    # A reaction policy derived from repeated experience, not mood mirroring.
    trait = 'empathy' if any(LEXICON[label][0] in {'sadness', 'fear', 'anger'} for label in integrated) else 'curiosity' if integrated else None
    # Derive the small learned component from cumulative evidence. Corrections
    # therefore remove unsupported influences instead of leaving fake growth.
    for name, families in [('empathy', {'sadness', 'fear', 'anger'}),
                           ('curiosity', {values[0] for values in LEXICON.values()})]:
        amount = sum(max(0, item['observations'] - 1) for label, item in profile['associations'].items()
                     if LEXICON[label][0] in families)
        profile['trait_deltas'][name] = .1 * (1 - math.exp(-amount/64))
    if trait:
        profile['response_disposition'] = {
            'mode': 'care' if trait == 'empathy' else 'exploration',
            'basis': 'repeated_attributed_experience',
            'strength': profile['trait_deltas'][trait],
            'subject': 'ALLMA_response_policy', 'subjective_experience_verified': False}
        changed.append('response_disposition')
    elif meaning_corrected:
        profile['response_disposition'] = {}
    stage = 'integrated' if integrated else 'suspended' if labels else 'meaning_declared'
    profile['recent_events'] = (profile['recent_events'] + [key])[-256:]
    profile['recent_droplets'] = (profile['recent_droplets'] + [{
        'event': key, 'stage': stage, 'user_emotion_labels': labels,
        'owner': user_id, 'source': 'user_interaction', 'changes': changed}])[-48:]
    return candidate, {'status': stage, 'labels': labels, 'changes': changed,
                       'partial_uncertainty': records['uncertain'],
                       'own_response': copy.deepcopy(profile['response_disposition'])}


def view(state, user_id):
    profile = state.get('profiles', {}).get(user_id, {})
    return copy.deepcopy({'personal_meanings': profile.get('meanings', {}),
        'associations': profile.get('associations', {}), 'trait_deltas': profile.get('trait_deltas', {}),
        'response_disposition': profile.get('response_disposition', {}),
        'recent_droplets': profile.get('recent_droplets', [])})
