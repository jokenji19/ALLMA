"""Bounded, offline emotion evidence. Scores are heuristics, not clinical probabilities.

Keep broad families compatible with voice/Soul consumers and retain finer nuances
separately. The response LLM can interpret context without a second inference.
"""
import math
import re
import unicodedata
from . import emotion_languages as languages

VERSION = 'emotion-evidence-v4'
# family, valence, arousal, perceived control, lexical evidence
LEXICON = {
    'joy': ('joy', .8, .6, .6, r'felic[ei]|content[oaie]|gioios[oaie]|happy|che bello|evviva|fantastico|ottimo|al settimo cielo|😊|😄'),
    'excitement': ('joy', .8, .9, .6, r'entusiast[ai]|eccitat[oaie]|esaltat[oaie]|excited|🥳'),
    'gratitude': ('joy', .7, .3, .6, r'grat[oaie]|gratitudine|ti ringrazio|grazie(?: mille| di cuore)?|thank(?:s|ful)'),
    'pride': ('joy', .7, .6, .8, r'orgoglios[oaie]|fier[oaie]|proud'),
    'love': ('joy', .8, .5, .6, r'innamorat[oaie]|ti voglio bene|ti amo|affetto|love'),
    'relief': ('joy', .6, .2, .6, r'sollevat[oaie]|sollievo|che sollievo|relieved'),
    'sadness': ('sadness', -.7, .3, .3, r'trist[ei]|infelic[ei]|sconfortat[oaie]|piango|piangere|a pezzi|gi[uù] di morale|sad|😢|😭|💔'),
    'loneliness': ('sadness', -.7, .3, .2, r'solitudine|mi sento sol[oa]|sono sol[oa](?!\s+(?:un|una))|nessuno mi (?:ascolta|capisce)|lonely'),
    'grief': ('sadness', -.9, .4, .2, r'lutto|ho perso (?:mia madre|mio padre|una persona cara)|grief|grieving'),
    'nostalgia': ('sadness', -.3, .3, .5, r'nostalgi[ac]\w*|malinconi[ac]\w*|nostalgic|mi manca(?:no)?'),
    'disappointment': ('sadness', -.6, .4, .4, r'delus[oaie]|delusione|amareggiat[oaie]|disappointed'),
    'helplessness': ('sadness', -.8, .4, .1, r'impotente|senza speranza|non ce la faccio pi[uù]|helpless|hopeless'),
    'guilt': ('sadness', -.6, .4, .3, r'senso di colpa|mi sento in colpa|colpevole|guilty|rimorso'),
    'shame': ('sadness', -.6, .5, .2, r'mi vergogno|vergogna|imbarazzat[oaie]|ashamed|embarrassed'),
    'anger': ('anger', -.7, .8, .6, r'arrabbiat[oaie]|rabbia|furios[oaie]|incazzat[oaie]|angry|furious|😡|🤬'),
    'frustration': ('anger', -.6, .6, .3, r'frustrat[oaie]|frustrazione|esasperat[oaie]|frustrated'),
    'annoyance': ('anger', -.4, .5, .6, r'irritat[oaie]|infastidit[oaie]|mi d[aà] fastidio|annoyed'),
    'jealousy': ('anger', -.5, .6, .3, r'gelos[oaie]|gelosia|invidios[oaie]|invidia|jealous|envious'),
    'fear': ('fear', -.8, .8, .2, r'paura|spaventat[oaie]|impaurit[oaie]|terrorizzat[oaie]|panico|cuore in gola|scared|afraid|terrified|😨'),
    'anxiety': ('fear', -.6, .7, .3, r'ansi[ao]|ansios[oaie]|preoccupat[oaie]|nervos[oaie]|anxious|worried|nervous'),
    'insecurity': ('fear', -.5, .5, .2, r'insicur[oaie]|insicurezza|non mi sento all.altezza|insecure'),
    'overwhelm': ('fear', -.6, .8, .2, r'sopraffatt[oaie]|sovraccaric[oa]|sotto pressione|overwhelmed'),
    'surprise': ('surprise', 0., .7, .4, r'sorpres[oaie]|sorpresa|wow|non ci credo|inaspettat[oaie]|surprised|😮'),
    'confusion': ('surprise', -.2, .5, .3, r'confus[oaie]|perpless[oaie]|disorientat[oaie]|non capisco|confused|🤔'),
    'disgust': ('disgust', -.7, .6, .5, r'disgustat[oaie]|disgusto|schif[oa]|ribrezzo|disgusted|🤢'),
    'trust': ('trust', .6, .3, .7, r'mi fido|fiducia|trust'),
    'calm': ('trust', .5, .15, .7, r'seren[oaie]|tranquill[oaie]|rilassat[oaie]|calm[oaie]?|in pace|relaxed'),
    'hope': ('anticipation', .5, .5, .5, r'speranzos[oaie]|spero|speranza|hopeful'),
    'curiosity': ('anticipation', .4, .5, .6, r'curios[oaie]|curiosit[aà]|curious'),
    'motivation': ('anticipation', .6, .7, .8, r'motivat[oaie]|determinat[oaie]|non vedo l.ora|motivated'),
    'fatigue': ('neutral', -.2, .1, .4, r'stanc[oaie]|esaust[oaie]|sfinito|sfinita|tired|exhausted|😴'),
    'numbness': ('neutral', -.3, .1, .3, r'mi sento vuot[oa]|non sento (?:pi[uù] )?niente|intorpidit[oaie]|numb'),
}
PATTERNS = [(label, values, re.compile(r'(?<!\w)(?:' + values[4] + '|' + languages.EXTRA_LEXICON.get(label, r'(?!)') + r')(?!\w)', re.I))
            for label, values in LEXICON.items()]
FAMILIES = {'neutral', 'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust', 'trust', 'anticipation'}
SELF = re.compile(r'\b(?:io|sono|ero|mi sento|mi sentivo|mi|ho|provo|sento|i am|i feel|i.m|' + languages.SELF_EXTRA + r')\b')
OTHER = re.compile(r'\b(?:tu|lui|lei|loro|sei|ti senti|si sente|si sentiva|mia madre|mio padre|mia sorella|mio fratello|il mio amico|la mia amica|il protagonista|il personaggio|il paziente|he|she|they|you|his|her|their|' + languages.OTHER_EXTRA + r')\b|\b(?!(?:io|i|je|yo|ich|mir|non|not|no|ne|nicht|oggi|questo)\b)\w+\s+(?:è|era|sembra|is|was|feels|est|était|se sent|está|se siente|ist|war|fühlt sich)\b')
GENERIC = re.compile(r'\b(?:spiega|definisci|traduci|tradurre|significa|significato|parola|frase|esempio|emozioni|le persone|nel romanzo|nel racconto|scrivi|disegna|mostra|aggiungi|translate|explain|' + languages.GENERIC_EXTRA + r')\b')
HYPOTHETICAL = re.compile(r'\b(?:se|quando|sarei|vorrei essere|potrei essere|immagina|if|whenever|wish i were|' + languages.HYPOTHETICAL_EXTRA + r')\b')
PAST = re.compile(r'\b(?:ieri|prima|ero|mi sentivo|l.anno scorso|una volta|yesterday|i was|' + languages.PAST_EXTRA + r')\b')
PRESENT = re.compile(r'\b(?:ora|adesso|oggi|mi sento|sono|i feel|i am|' + languages.PRESENT_EXTRA + r')\b')


def unit(value, default=0.):
    if type(value) not in (int, float) or not math.isfinite(value):
        return default
    return max(0., min(1., float(value)))


def analyze(text, learned_aliases=None):
    original = unicodedata.normalize('NFKC', text if isinstance(text, str) else '')[:12000]
    # Preserve offsets while excluding examples, quoted speech, and code.
    clean = re.sub(r'```.*?(?:```|$)|`[^`\n]*`|"[^"\n]*"|“[^”\n]*”|„[^“\n]*“|«[^»\n]*»|(?<!\w)\x27[^\x27\n]{2,}\x27(?!\w)',
                   lambda m: ' '*len(m[0]), original, flags=re.S).casefold()
    scores, evidence, other, negated, past = {}, [], [], [], []
    ambiguous = False
    unasserted = []
    patterns = list(PATTERNS)
    personal_patterns = {}
    if isinstance(learned_aliases, dict):
        for alias, label in learned_aliases.items():
            if (label in LEXICON and isinstance(alias, str) and len(alias) <= 32
                    and re.fullmatch(r'[\wÀ-ÿ -]+', alias) and alias.casefold() in clean):
                pattern = re.compile(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', re.I)
                patterns.append((label, LEXICON[label], pattern))
                personal_patterns[pattern.pattern] = alias
    for clause in re.finditer(r'[^.!?;\n]+', clean):
        chunk = clause[0]
        for label, values, pattern in patterns:
            for match in pattern.finditer(chunk):
                before = chunk[:match.start()]
                # Conjunctions bound negation and temporal changes; retain subject
                # attribution from the surrounding clause for fragments.
                scopes = re.split(r'\b(?:ma|però|invece|but|e|and|' + languages.SCOPE_EXTRA + r')\b|,|:(?=\s*(?:io\s+)?(?:sono|mi sento|provo|sento|i am|i feel)\b)', before)
                local = scopes[-1]
                self_hits, other_hits, generic_hits = list(SELF.finditer(before)), list(OTHER.finditer(before)), list(GENERIC.finditer(before))
                # End offsets distinguish Spanish "mi hermana" from Italian
                # first-person "mi": the longer attributed subject wins.
                self_pos = self_hits[-1].end() if self_hits else -1
                other_pos = other_hits[-1].end() if other_hits else -1
                generic_pos = generic_hits[-1].end() if generic_hits else -1
                first_person_phrase = bool(re.match(r'(?:mi |ho perso |non ce la faccio|non mi sento|non sento|ti (?:amo|voglio bene|ringrazio))', match[0]))
                if pattern.pattern in personal_patterns and self_pos < 0:
                    continue  # An object bearing the learned word is not the user.
                record = {'label': label, 'start': clause.start()+match.start(), 'end': clause.start()+match.end()}
                if pattern.pattern in personal_patterns:
                    record['learned_alias'] = personal_patterns[pattern.pattern]
                if languages.ambiguous_usage(match[0], local, self_pos >= 0 or other_pos >= 0):
                    ambiguous = True
                    continue
                # An emotion inside a feared/wished/reported belief is not an
                # assertion that the user experiences that emotion now.
                if re.search(r'\b(?:ho paura|temo|spero|vorrei|crede\w*|credi\w*|creda\w*|pensa\w*|pensi\w*)\b.*\bche\b|\b(?:espero|temo|souhaite|espère|crains)\b.*\bqu[e’\x27]|\b(?:hoffe|fürchte)\b.*\bdass\b', local):
                    unasserted.append(record)
                    continue
                if match[0].startswith('mi manca'):
                    # Require an object of attachment, rather than guessing
                    # sadness from every missing resource or bodily function.
                    attachment = chunk[match.end():].strip()
                    if not re.match(r"(?:(?:mio|mia|miei|mie)\s+(?:padre|madre|fratell\w*|sorell\w*|amic\w*|figli\w*|nonn\w*|famiglia)|casa\b|la mia famiglia\b)", attachment):
                        ambiguous = True
                        continue
                if not first_person_phrase and other_pos > self_pos:
                    other.append(record); continue
                if not first_person_phrase and generic_pos > self_pos:
                    continue
                if re.search(r'\b(?:traduci|tradurre|translate|parola|frase|scrivi|definisci|significato|' + languages.GENERIC_EXTRA + r')\b', local):
                    continue
                if match[0] == 'a pezzi' and not re.search(r'\b(?:sono|ero|mi sento|mi sentivo|mi ha lasciato)\b', local):
                    continue  # Broken objects are not evidence of distress.
                if match[0] == 'piangere' and not re.search(r'\b(?:mi|sto|ho|non riesco)\b', local):
                    continue  # Mentioning an action is not experiencing it.
                if HYPOTHETICAL.search(local):
                    ambiguous = True; continue
                # Negation removes the evidence, never invents the opposite feeling.
                window = ' '.join(local.split()[-6:])
                # Negation over a complement can exceed a short token window.
                # Preserve the operator across coordinated "né/nor" fragments.
                long_negation = bool(re.search(r'\bnon\b.*\b(?:niente|nulla|nessuno)\b.*\b(?:sentire|essere|provo|sento)\b', local))
                coordinated_negation = bool(re.search(r'\b(?:né|nemmeno|neanche|neppure|nor|neither|ni|weder|noch)\b', local)
                                            and re.search(r'\b(?:non|not|né|neither|no|ne|ni|pas|weder)\b', before))
                # Failure to inhibit an action is not negation of its emotion.
                inability = bool(re.search(r'\bnon riesco a\b.*\b(?:smettere di|trattenere|evitare di)\b', local))
                negatives = list(re.finditer(r'\b(?:non|not|senza|never|mai|no|' + languages.NEGATIVE_EXTRA + r')\b', window))
                non_only = re.search(r'\b(?:non (?:solo|soltanto)|no solo|pas seulement|nicht nur)\b', window)
                positive_mai = re.search(r'\bmai\b.*\bcos[iì]\b', window)
                if ((long_negation or coordinated_negation) and not non_only) or (negatives and len(negatives)%2 and not non_only and not positive_mai and not inability):
                    negated.append(record); continue
                if PAST.search(local) and not PRESENT.search(local):
                    past.append(record); continue
                strength = .62
                if self_pos >= 0 or first_person_phrase:
                    strength = .82
                if re.search(r'\b(?:forse|magari|credo|sembra|maybe|perhaps|' + languages.UNCERTAIN_EXTRA + r')\b', local):
                    strength = .48; ambiguous = True
                intensity = .55
                if re.search(r'\b(?:molto|tantissimo|estremamente|davvero|troppo|very|extremely|' + languages.INTENSE_EXTRA + r')\b', window):
                    intensity = .85
                if re.search(r'\b(?:poco|leggermente|appena|un po|slightly|a little|' + languages.MILD_EXTRA + r')\b', window):
                    intensity = .3
                # A negative continuation can make a positive interjection ironic.
                if label == 'joy' and re.search(r'che bello|fantastico|ottimo', match[0]) and re.search(r'rotto|fallit|perso|guasto|ritardo|multa|crash', chunk[match.end():]):
                    ambiguous = True; continue
                previous = scores.get(label)
                if previous is None or strength > previous[0]:
                    scores[label] = (strength, intensity)
                evidence.append(record)
    families = {}
    for label, (score, intensity) in scores.items():
        family = LEXICON[label][0]
        families[family] = max(families.get(family, 0.), score)
    family_strength = {f: max(score*.8+intensity*.2 for label,(score,intensity) in scores.items()
                             if LEXICON[label][0]==f) for f in families}
    ranked = sorted(families, key=lambda f: (-family_strength[f], f))
    primary = ranked[0] if ranked else 'neutral'
    confidence = families.get(primary, .35 if original.strip() else 0.)
    weights = {label: score*intensity for label, (score, intensity) in scores.items()}
    total = sum(weights.values())
    dims = [sum(LEXICON[label][index]*weight for label, weight in weights.items())/total if total else 0.
            for index in (1, 2, 3)]
    intensity = max((i for _, i in scores.values()), default=0.)
    return dict(primary_emotion=primary, confidence=confidence, intensity=intensity,
                secondary_emotions={f: families[f] for f in ranked[1:]},
                nuances={label: score for label, (score, _) in scores.items()},
                valence=dims[0], arousal=dims[1], dominance=dims[2],
                analysis={'version': VERSION, 'source': 'local_evidence', 'lexicon_languages': list(languages.LANGUAGES),
                          'uncertain': ambiguous or not scores or confidence < .6,
                          'mixed': len(scores)>1, 'evidence': evidence[:32], 'other_evidence': other[:16],
                          'negated': negated[:16], 'past_evidence': past[:16],
                          'unasserted_evidence': unasserted[:16],
                          'truncated': len(text or '') > 12000 if isinstance(text, str) else False})


# Language hints, not additional inferred feelings or autobiographical facts.
NUANCE_NAMES_IT = {
    'joy':'gioia', 'excitement':'entusiasmo', 'gratitude':'gratitudine', 'pride':'orgoglio',
    'love':'affetto', 'relief':'sollievo', 'sadness':'tristezza', 'loneliness':'solitudine',
    'grief':'dolore per una perdita', 'nostalgia':'nostalgia', 'disappointment':'delusione',
    'helplessness':'impotenza', 'guilt':'senso di colpa', 'shame':'vergogna',
    'anger':'rabbia', 'frustration':'frustrazione', 'annoyance':'fastidio', 'jealousy':'gelosia',
    'fear':'paura', 'anxiety':'ansia', 'insecurity':'insicurezza', 'overwhelm':'sopraffazione',
    'surprise':'sorpresa', 'confusion':'confusione', 'disgust':'disgusto', 'trust':'fiducia',
    'calm':'serenità', 'hope':'speranza', 'curiosity':'curiosità', 'motivation':'motivazione',
    'fatigue':'stanchezza', 'numbness':'vuoto emotivo',
}

def prompt_context(state):
    if state is None:
        return ''
    nuances = getattr(state, 'nuances', {})
    analysis = state.context.get('emotion_analysis', {})
    if not nuances and not analysis.get('other_evidence') and not analysis.get('uncertain'):
        return ''
    if not nuances and not analysis.get('other_evidence') and not analysis.get('evidence'):
        if not analysis.get('negated') and not analysis.get('past_evidence'):
            return ''
    labels = ', '.join(f'{label} ({NUANCE_NAMES_IT.get(label,label)})' for label in list(nuances)[:4]) or 'nessuna emozione attuale esplicita'
    detail = 'Possibile ambivalenza. ' if analysis.get('mixed') else ''
    detail += 'Interpretazione incerta. ' if analysis.get('uncertain') else ''
    if analysis.get('other_evidence'):
        others = list(dict.fromkeys(item.get('label') for item in analysis['other_evidence'] if item.get('label')))
        detail += 'Altre persone: '+', '.join(NUANCE_NAMES_IT.get(label,label) for label in others[:4])+'. '
    denied = list(dict.fromkeys(item.get('label') for item in analysis.get('negated', []) if item.get('label')))
    if denied:
        detail += 'Negate dall’utente: '+', '.join(NUANCE_NAMES_IT.get(label,label) for label in denied[:4])+'. '
    return 'Indizi emotivi dell’utente (ipotesi, non stato interno di ALLMA): '+labels+'. '+detail


def support_instruction(state):
    """One role-specific task, separate from the detector's attributed data."""
    if not prompt_context(state):
        return ''
    return ('Supporto: rivolgiti all’utente con il tu, nel formato richiesto. '
            'Riconosci le sue emozioni nella situazione descritta, distinguendo quelle altrui o negate. '
            'Offri un passo concreto solo se utile alla richiesta, oppure ascolta. '
            'Non attribuirtele: parla della sua esperienza, senza raccontare tuoi sentimenti o partecipazioni. '
            'Usa tatto nelle ipotesi, senza diagnosi o certezze inventate.')
