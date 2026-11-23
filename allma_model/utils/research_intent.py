"""Interpret requests for historical and other firsts before querying an index."""

from dataclasses import dataclass
import re

from .web_search import _plain, _terms


_FIRST_QUESTION = {
    'it': re.compile(
        r"^chi (?:(?:e stato|e stata|fu) )?(?:il |la )?prim[oa]"
        r"(?: (?P<role>uomo|donna|persona|essere umano|europe[oa]))? (?:a |ad )?"
        r"(?P<action>[a-z]+) (?:di |a |in |su |sulla |sul )?(?P<topic>.+)$"),
    'en': re.compile(
        r"^who (?:was the first(?: (?P<role>person|man|woman|human|european))? to |first )"
        r"(?P<action>[a-z]+) (?:on |in |into |onto |to )?(?P<topic>.+)$"),
    'es': re.compile(
        r"^quien (?:fue )?(?:el |la )?primer[oa]?"
        r"(?: (?P<role>hombre|mujer|persona|ser humano|europe[oa]))? (?:en |a )?"
        r"(?P<action>[a-z]+) (?:en |a )?(?P<topic>.+)$"),
}
_DISCOVERY_QUESTION = {
    'it': re.compile(r'^chi (?:ha |aveva )?(?P<action>scoperto|scopri|inventato|invento)(?: per prim[oa])? (?P<topic>.+)$'),
    'en': re.compile(r'^who (?P<action>discovered|invented) (?P<topic>.+)$'),
    'es': re.compile(r'^quien (?P<action>descubrio|invento) (?P<topic>.+)$'),
}
_FIRST = re.compile(r'\b(?:first|earliest|prim[oaie]|primer[oa]?)\b')
_FIRST_ACTOR = re.compile(
    r'\b(?:first (?:(?:known|documented) )?'
    r'(?:(?:person|people|man|woman|men|women|human|humans|astronauts?|climbers?|team|europeans?) )?'
    r'(?:(?:ever|confirmed) )?(?:to|who) |'
    r'prim[oaie] (?:(?:uom(?:o|ini)|donn[ae]|person[ae]|astronaut[ai]|alpinist[ai]|europe[oaie]) )?'
    r'(?:a|ad|che) |primer[oa]? (?:(?:personas?|hombres?|mujer(?:es)?|astronautas?|alpinistas?|europe[oa]s?) )?'
    r'(?:en|que) )')
_FIRST_IN_SPACE = re.compile(r'\b(?:first (?:woman|man|human|person) in space|'
                             r'prim[oa] (?:uomo|donna|essere umano|persona) nello spazio|'
                             r'primer[oa]? (?:mujer|hombre|persona) en el espacio)\b')
_OWN_FIRST = re.compile(r"\b(?:his|her|their|suo|sua|su|prop(rio|ria)) (?:first|prim[oa]|primer[oa]?)\b")
_QUALIFIED_GROUP = re.compile(
    r'\b(?:first woman|prima donna|primera mujer) (?:of |from |from the |di origine |del |'
    r'dalla |nella |de ascendencia |de origen |del pais )')
_RECORD_MEDIUM = re.compile(r'\b(?:film(?:ed|at[ao]|ad[ao])|televised|televisiv[ao]|'
                            r'trasmess[ao] (?:in tv|in televisione)|emitid[ao])\b')
_CLIMB_QUALIFIERS = re.compile(r"\b(?:in winter|winter ascent|winter climb|"
                              r"in inverno|d'inverno|invernal[ei]?|invierno|sin oxigeno|"
                              r"senza ossigeno|without (?:supplemental )?oxygen)\b")
_ATLANTIC = re.compile(r'\b(?:atlantic|atlantico|transatlantic[oa]?)\b')
_SOLO = re.compile(r'\b(?:solo|alone|in solitaria|en solitario)\b')
_NONSTOP = re.compile(r'\b(?:non[ -]?stop|senza scal[oi]|sin escalas?)\b')
_FLIGHT_SCOPE = re.compile(r'\b(?:balloon|pallone|globo|helicopter|elicottero|helicoptero|'
                           r'westbound|eastbound|west to east|east to west)\b')
_SOLO_CROSSING = re.compile(
    r'\b(?:first (?:non[ -]?stop[, ]+)?solo[, ]+(?:non[ -]?stop )?(?:transatlantic )?(?:flight|crossing)|'
    r'prim[oa] (?:volo|traversata|vuelo|cruce)\b[^.!?]{0,70}\b(?:in solitaria|en solitario))\b')
_SOLO_FEMALE_PILOT = re.compile(
    r'\bfirst woman to (?:make|complete) (?:a|the) (?:non[ -]?stop[, ]+)?solo[, ]+'
    r'(?:non[ -]?stop )?(?:transatlantic )?flight\b')
_AIR_TRAVEL = re.compile(r'\b(?:flight|flying|fly|flew|landing|piloted|airplane|'
                         r'volo|aereo|atterraggio|vuelo|avion|aterrizaje)\b')
_NEAR_FIRST = re.compile(
    r'\b(?:one of the|among the|amongst the|uno dei|una delle|fra i|tra i|tra le|'
    r'uno de los|una de las|entre los|entre las|(?:not|never) the|non (?:fu|e stato)|no fue)\s+'
    r'(?:the |[iu]l |la )?(?:first|earliest|prim[oaie]|primer[oa]?)\b')
_NARROWER_FIRST = re.compile(
    r'\b(?:first|prim[oa]|primer[oa]?) (?:american[oa]?|british|ingles[ea]?|frances[ea]?|'
    r'french|russian|soviet|sovietic[oa]|german|tedesc[oa]|european|europe[oa]|woman|mujer|donna)\b')
_WOMAN = re.compile(r'\b(?:woman|female|donna|mujer)\b')
_EUROPEAN = re.compile(r'\b(?:european[os]?|europe[oaie]s?)\b')
_TOPIC_PREFIX = re.compile(r"^(?:l['’ ]|el |la |il |lo |un |una |the |an? )")
_RELATION_ADVERBS = r'(?:(?:successfully|ever|effettivamente|riuscir\w* a|con exito) )?'
_ACTIONS = {
    'discover': ('scoprire scoperto scopri discover discovered descubrir descubrio', r'scopr\w*|scopert\w*|discover\w*|descubr\w*'),
    'reach': ('raggiungere raggiunto reach reached arrive arrivare llegar llego alcanzar',
              r'raggiun\w*|arriv\w*|reach\w*|arriv\w*|lleg\w*|alcanz\w*'),
    'walk': ('camminare cammino walk walked andar caminar camino',
             r'cammin\w*|walk\w*|set foot|mise piede|mettere piede|pis\w*|camin\w*'),
    'fly': ('volare volo fly flew volar volo', r'vol\w*|fl(?:ew|y|ight|own)\w*|vuelo\w*'),
    'invent': ('inventare inventato invento invent invented inventar invento', r'invent\w*'),
    'climb': ('scalare scalo climb climbed escalar escalo',
              r'scal\w*|climb\w*|ascen\w*|escal\w*|summit|'
              r'(?:reach|stand on) the summit|raggiung\w* (?:la vetta|la cima)|alcanz\w* la cima'),
    'win': ('vincere vinse win won ganar gano', r'vinc\w*|vins\w*|vint\w*|won|win\w*|gan\w*|receive'),
    'launch': ('lanciare lancio launch launched lanzar lanzo', r'lanci\w*|launch\w*|lanz\w*'),
    'orbit': ('orbitare orbito orbit orbited orbitar orbito', r'orb[íi]t\w*'),
}
_ACTION_BY_WORD = {word: action for action, (words, _) in _ACTIONS.items() for word in words.split()}
_DISCOVERY_TERM = {
    'it': {'discover': 'scoperta', 'reach': 'arrivo', 'walk': 'camminare', 'fly': 'volo',
           'invent': 'invenzione', 'climb': 'ascensione', 'win': 'vittoria', 'launch': 'lancio', 'orbit': 'orbita'},
    'en': {'discover': 'discovery', 'reach': 'reach', 'walk': 'walk', 'fly': 'flight', 'invent': 'invention',
           'climb': 'ascent', 'win': 'win', 'launch': 'launch', 'orbit': 'orbit'},
    'es': {'discover': 'descubrimiento', 'reach': 'llegada', 'walk': 'caminar', 'fly': 'vuelo',
           'invent': 'invención', 'climb': 'ascenso', 'win': 'victoria', 'launch': 'lanzamiento', 'orbit': 'órbita'},
}
_FIRST_TERM = {'it': 'primo', 'en': 'first', 'es': 'primero'}
_EVENT_SEARCH_TERMS = {
    ('it', 'luna', 'walk'): 'primo passo astronauta allunaggio',
    ('en', 'moon', 'walk'): 'first astronaut on the lunar surface',
    ('es', 'luna', 'walk'): 'primer astronauta superficie lunar',
}


@dataclass(frozen=True)
class PrimacyQuestion:
    topic: str
    action: str
    language: str
    role: str = ''

    def discovery_queries(self):
        if event := _EVENT_SEARCH_TERMS.get((self.language, self.topic, self.action)):
            return (event, f'{self.topic} {_DISCOVERY_TERM[self.language][self.action]}')
        action = _DISCOVERY_TERM.get(self.language, {}).get(self.action, self.action)
        first = _FIRST_TERM[self.language]
        if self.role in ('donna', 'mujer'):
            first = 'prima' if self.language == 'it' else 'primera'
        if self.action == 'fly' and _ATLANTIC.search(self.topic) and _SOLO.search(self.topic):
            crossing = {'it': 'volo transatlantico in solitaria', 'en': 'solo transatlantic flight',
                        'es': 'vuelo transatlántico en solitario'}[self.language]
            return (' '.join(filter(None, (first, self.role, crossing))), f'{self.topic} {action}')
        ranked = ' '.join((self.topic, first, self.role or action))
        return (ranked, f'{self.topic} {action}')

    def supports(self, passage, *, article_topic=''):
        text = _plain(passage)
        solo_atlantic = self.action == 'fly' and _ATLANTIC.search(self.topic) and _SOLO.search(self.topic)
        if solo_atlantic:
            required = _terms(_NONSTOP.sub('', _SOLO.sub('', _ATLANTIC.sub('', self.topic)))) - {
                'across', 'over', 'ocean', 'oceano', 'attraverso', 'sobre'}
            if (not _ATLANTIC.search(text) or not _SOLO.search(text)
                    or not required <= _terms(text)
                    or (_FLIGHT_SCOPE.search(text) and not _FLIGHT_SCOPE.search(self.topic))
                    or (_NONSTOP.search(self.topic) and not _NONSTOP.search(text))):
                return False
        elif not _terms(self.topic) <= _terms(text):
            return False
        # A lead that names who discovered the exact topic can support an
        # attribution even when its wording omits the ordinal.
        target = re.escape(self.topic)
        if self.action == 'discover' and not self.role and self.topic == _plain(article_topic):
            attribution = (r'(?: was discovered in \d{4} by | fu scopert[ao] nel \d{4} da |'
                           r' fue descubiert[ao] en \d{4} por )')
            if re.match(target + attribution + r'\w+', _TOPIC_PREFIX.sub('', text)):
                return True
        if not _FIRST.search(text) or _NEAR_FIRST.search(text) or _OWN_FIRST.search(text):
            return False
        if self.role in ('donna', 'woman', 'mujer'):
            if not _WOMAN.search(text) or _QUALIFIED_GROUP.search(text):
                return False
        elif self.role.startswith('europ'):
            if not _EUROPEAN.search(text):
                return False
        elif _NARROWER_FIRST.search(text):
            return False
        if _RECORD_MEDIUM.search(text) and not _RECORD_MEDIUM.search(self.topic):
            return False
        if self.action == 'climb' and _CLIMB_QUALIFIERS.search(text) and not _CLIMB_QUALIFIERS.search(self.topic):
            return False
        if solo_atlantic:
            if not self.role and _SOLO_CROSSING.search(text) and _AIR_TRAVEL.search(text):
                return True
            if self.role == 'woman' and _SOLO_FEMALE_PILOT.search(text):
                return True
        _, predicate = _ACTIONS[self.action]
        action = r'\b(?:' + predicate + r')\b'
        if self.action in ('discover', 'invent', 'launch'):
            # Do not accept an ordinal attached to a related object, e.g.
            # "discovered mechanism of penicillin resistance".
            object_phrase = r'(?:(?:the|il|la|el) )?' + target + r'\b(?=[,.;:!?”"’]|$| (?:in|en|nel|by|da|por)\b)'
            first = r'\b(?:first|prim[oa]|primer[oa]?)\b'
            return bool(re.search(
                first + r' ' + _RELATION_ADVERBS + action + ' ' + object_phrase + '|'
                + first + r' (?:practical )?' + target + r' (?:was|fu|fue) ' + action + r'\b|'
                + r'\b' + target + r' (?:was|fu|fue) ' + first + ' ' + action + r'\b', text)
                or any(re.match(_RELATION_ADVERBS + action + ' ' + object_phrase, text[mark.end():])
                       for mark in _FIRST_ACTOR.finditer(text)))
        if self.action == 'win':
            title = r'(?:(?:the|a|il|un|el) )?' + target + r'\b(?=$|[.!?,;:]| (?:in|en|nel) \d{4}\b)'
            if any(re.match(_RELATION_ADVERBS + action + ' ' + title, text[mark.end():])
                   for mark in _FIRST_ACTOR.finditer(text)):
                return True
            award = r'\b(?:prima donna insignita del|first woman awarded|primera mujer galardonada con) '
            return self.role in ('woman', 'donna', 'mujer') and bool(re.search(award + title, text))
        for first in _FIRST_ACTOR.finditer(text):
            if re.match(_RELATION_ADVERBS + action, text[first.end():]):
                return True
        return self.action == 'fly' and bool(_FIRST_IN_SPACE.search(text)) and bool(re.search(action, text))


def primacy_question(query, language):
    """Keep the relation and target independently from the wording of the request."""
    if language not in _FIRST_QUESTION or not isinstance(query, str):
        return None
    text = _plain(query).strip(' ¿¡?!.。？！')
    match = _FIRST_QUESTION[language].fullmatch(text) or _DISCOVERY_QUESTION[language].fullmatch(text)
    if not match:
        return None
    action = _ACTION_BY_WORD.get(match['action'], match['action'])
    # Unspecified verbs are too ambiguous to verify as a world first.
    if action not in _ACTIONS:
        return None
    topic = _TOPIC_PREFIX.sub('', match['topic'])
    role = match.groupdict().get('role') or ''
    if role in ('uomo', 'hombre', 'man', 'persona', 'person', 'essere umano', 'ser humano', 'human'):
        role = ''
    if not _terms(topic):
        return None
    return PrimacyQuestion(topic, action, language, role)
