"""Offer a choice of focus for a broad, explicit public search."""

import re

from .public_references import freshness_requested, local_only_request, public_query_text
from .public_language import private_identity_topic
from .web_search import _plain, search_query


_COMMAND = re.compile(
    r"^\s*(?:(?P<it>cercami|cerca)|(?P<en>search for|find information on)|"
    r"(?P<es>búscame|buscame|busca)|(?P<fr>cherche-moi|cherche)|"
    r"(?P<de>such(?:e)? nach)|(?P<pt>procura|procure|pesquisa|pesquise))\s+(?P<topic>.+)$", re.I)
_UNSCOPED = re.compile(r"^(?:di|de|to|in|su|sul|sui|sur|en|im|na|online|offline)\b", re.I)
_FOCUSED = re.compile(
    r"^(?:chi|che cosa|cosa|come|quando|dove|quanto|quale|quali|perche|whether|who|what|"
    r"when|where|why|how|quien|que|como|cuando|donde|cuanto|qui|ou|pourquoi|comment|"
    r"quand|wer|was|wie|wann|warum|quem|onde|qual)\b|"
    r"\b(?:battaglie|battles?|batallas?|batailles?|schlachten|batalhas?|"
    r"prezz\w*|prices?|precios?|prix|preise?|precos?|orari|opening hours|"
    r"documentazione|documentation|manuale|manual|ricetta|recipe|rispondi|answer|"
    r"studi|papers?|articoli scientifici|confront\w*|versus)\b")
_ARTICLE = re.compile(r"^(?:(?:il|lo|la|le|gli|i|the|el|los|las|les|der|die|das|o|os|as) |l['’])", re.I)
_IT_TOPIC_PREFIX = {'il ': 'sul ', 'lo ': 'sullo ', 'la ': 'sulla ', 'i ': 'sui ',
                    'gli ': 'sugli ', 'le ': 'sulle ', "l'": "sull'", 'l’': 'sull’'}
_RELATION = re.compile(r"\b(?:di|del|della|of|de|du|von|do|da)\b")
_DETAIL = re.compile(
    r"^(?:vita|biografia|carriera|storia|origine|opere|life|biography|history|works|career|"
    r"vida|biografia|historia|obras|vie|biographie|histoire|oeuvres|œuvres|"
    r"leben|geschichte|werke|trajetoria|origem)\b")
_DEFINITION = re.compile(r'\b(?:e stato|e stata|e|fu|is|was|est|etait|es|fue|ist|war|foi)\b')
_MEDIA_TITLE = re.compile(
    r'\((?:film|movie|pellicola|pelicula|romanzo|novel|serie|television|videogioco|video game)\b', re.I)
_NONFICTION = frozenset({'person', 'military', 'place', 'event', 'organization', 'concept', 'natural'})

_COMMAND_PREFIX = {
    'it': 'Cerca su Internet', 'en': 'Search online', 'es': 'Busca en internet',
    'fr': 'Cherche sur Internet', 'de': 'Suche im Internet', 'pt': 'Pesquisa na internet',
}
_PROMPTS = {
    'it': ('Cosa vuoi approfondire su {topic}?', 'Attiva Internet dal globo per avviare la ricerca.'),
    'en': ('What would you like to explore about {topic}?', 'Turn on Internet with the globe to search.'),
    'es': ('¿Qué quieres explorar sobre {topic}?', 'Activa Internet con el globo para buscar.'),
    'fr': ('Quel aspect de {topic} veux-tu explorer ?', 'Active Internet avec le globe pour lancer la recherche.'),
    'de': ('Was möchtest du über {topic} erfahren?', 'Aktiviere Internet über das Globus-Symbol, um zu suchen.'),
    'pt': ('O que queres explorar sobre {topic}?', 'Ativa a Internet no globo para pesquisar.'),
}
_FACETS = ('overview', 'biography', 'campaigns', 'works', 'history', 'mechanism',
           'applications', 'geography', 'culture', 'causes', 'context', 'activities', 'highlights',
           'structure', 'origin')
_LABELS = {
    'it': ('Panoramica', 'Biografia', 'Battaglie e campagne', 'Opere e contributi', 'Storia', 'Come funziona',
           'Applicazioni', 'Geografia', 'Cultura', 'Cause e conseguenze', 'Contesto', 'Attività e ruolo', 'Aspetti principali',
           'Struttura', 'Origine'),
    'en': ('Overview', 'Biography', 'Battles and campaigns', 'Works and contributions', 'History', 'How it works',
           'Applications', 'Geography', 'Culture', 'Causes and consequences', 'Context', 'Activities and role', 'Key points',
           'Structure', 'Origins'),
    'es': ('Panorama general', 'Biografía', 'Batallas y campañas', 'Obras y aportaciones', 'Historia', 'Cómo funciona',
           'Aplicaciones', 'Geografía', 'Cultura', 'Causas y consecuencias', 'Contexto', 'Actividades y función', 'Aspectos clave',
           'Estructura', 'Origen'),
    'fr': ('Vue d’ensemble', 'Biographie', 'Batailles et campagnes', 'Œuvres et contributions', 'Histoire',
           'Fonctionnement', 'Applications', 'Géographie', 'Culture', 'Causes et conséquences', 'Contexte', 'Rôle et activités', 'Points clés',
           'Structure', 'Origine'),
    'de': ('Überblick', 'Biografie', 'Schlachten und Feldzüge', 'Werke und Beiträge', 'Geschichte',
           'Funktionsweise', 'Anwendungen', 'Geografie', 'Kultur', 'Ursachen und Folgen', 'Kontext', 'Rolle und Aktivitäten', 'Kernpunkte',
           'Aufbau', 'Ursprung'),
    'pt': ('Visão geral', 'Biografia', 'Batalhas e campanhas', 'Obras e contribuições', 'História', 'Como funciona',
           'Aplicações', 'Geografia', 'Cultura', 'Causas e consequências', 'Contexto', 'Atividades e função', 'Pontos principais',
           'Estrutura', 'Origem'),
}
_PROFILES = {
    'military': ('biography', 'campaigns', 'context'),
    'person': ('biography', 'works', 'context'),
    'place': ('geography', 'history', 'culture'),
    'natural': ('structure', 'mechanism', 'origin'),
    'concept': ('mechanism', 'applications', 'history'),
    'event': ('history', 'causes', 'context'),
    'work': ('works', 'history', 'context'),
    'organization': ('history', 'activities', 'context'),
    'general': ('history', 'context', 'highlights'),
}
_SEARCH_DETAILS = {
    'it': {'campaigns': 'battaglie', 'works': 'opere', 'mechanism': 'funzionamento',
           'causes': 'cause', 'activities': 'attività', 'highlights': 'caratteristiche'},
    'en': {'campaigns': 'battles', 'works': 'works', 'mechanism': 'mechanism',
           'causes': 'causes', 'activities': 'activities', 'highlights': 'overview'},
    'es': {'campaigns': 'batallas', 'works': 'obras', 'mechanism': 'funcionamiento',
           'causes': 'causas', 'activities': 'actividades', 'highlights': 'características'},
    'fr': {'campaigns': 'batailles', 'works': 'œuvres', 'causes': 'causes',
           'activities': 'activités', 'highlights': 'caractéristiques'},
    'de': {'campaigns': 'Schlachten', 'works': 'Werke', 'causes': 'Ursachen', 'activities': 'Aktivitäten'},
    'pt': {'campaigns': 'batalhas', 'works': 'obras', 'mechanism': 'funcionamento',
           'causes': 'causas', 'activities': 'atividades', 'highlights': 'características'},
}
_NAMED_CAMPAIGN = {
    'it': r"(?:battaglia|campagna) (?:di |del |della |dell['’]|a |in |d['’])",
    'en': r'(?:battle|campaign) (?:of |at |in |for )',
    'es': r'(?:batalla|campaña) (?:de |del |en |por )',
    'fr': r"(?:bataille|campagne) (?:de |du |des |d['’]|en |à )",
    'de': r'(?:schlacht|feldzug) (?:bei |von |um |in )',
    'pt': r'(?:batalha|campanha) (?:de |do |da |em |por )',
}
_MILITARY_ACTION = {
    'it': r'combatt\w*|vin[st]\w*|sconfitt\w*|sconfis\w*|batt[eé]\w*|attacc\w*|disfatta|truppe|armata|esercito',
    'en': r'fought|won|lost|defeat\w*|attack\w*|troops|army|armies|forces',
    'es': r'libr\w*|derrot\w*|venci\w*|perdi\w*|atac\w*|combat\w*|tropas|ejército',
    'fr': r'combatt\w*|batt\w*|remport\w*|vainc\w*|défait\w*|attaqu\w*|troupes|armée',
    'de': r'kämpf\w*|sieg\w*|besieg\w*|niederlag\w*|angriff\w*|truppen|armee|heer',
    'pt': r'combat\w*|lut\w*|derrot\w*|ven[çc]\w*|atac\w*|perd\w*|tropas|exército',
}
_CAMPAIGN_PASSAGES = {
    language: re.compile(
        r'(?=.*\b(?i:' + _MILITARY_ACTION[language] + r')\b)'
        r'.*\b(?i:' + name + r')(?P<engagement>[A-ZÀ-ÖØ-Þ][^\W\d_]+)')
    for language, name in _NAMED_CAMPAIGN.items()
}
_DESCRIPTION = (
    ('military', r'\b(?:imperator[ei]|imperatrice|emperor|empereur|emperador|imperador|condottier\w*|'
                 r'general(?:e)?|feldherr|commandant)\b'),
    ('person', r'\b(?:politic[oa]|politician|politiker|pol[ií]tico|ecrivain|scrittor\w*|writer|'
               r'compositor\w*|komponist|compositeur|scientist|scienziat\w*|fisic[oa]|physicist|'
               r'astronaut\w*|pittor\w*|painter|artist\w*|athlet\w*|nacque|born|nacio|nasceu)\b'),
    ('place', r'\b(?:citta|comune|capitale|capital|city|ville|stadt|ciudad|cidade|paese|'
              r'country|pays|pais|continente?|isola|island|insel|montagna|mountain|fiume|river|ocean\w*)\b'),
    ('organization', r'\b(?:organizzazion\w*|organization|organisation|organizaci\w*|associa\w*|'
                     r'azienda|company|entreprise|universit\w*|agenz\w*)\b'),
    ('work', r'\b(?:romanzo|racconto|novel|novela|roman|conte|ballet\w*|opera musicale|sinfon\w*|'
             r'symphon\w*|film|dipinto|danza|danse|dance|dança|tanz)\b'),
    ('event', r'\b(?:guerra|war|krieg|guerre|battagli\w*|battle|schlacht|rivoluzion\w*|revoluci\w*|'
              r'revolution|revolucao|evento|event)\b'),
    ('natural', r'\b(?:sistem[ae] (?:sola\w*|planeta\w*|nervos\w*|digestiv\w*)|'
                r'(?:solar|planetary|nervous|digestive) system|sonnensystem|nervensystem|'
                r'ecosistem\w*|ecosystem\w*|okosystem\w*)\b'),
    ('concept', r'\b(?:process\w*|sistem\w*|system\w*|tecnologi\w*|technolog\w*|teori\w*|theor\w*|'
                r'fenomen\w*|phenomen\w*|algoritm\w*|algorithm\w*|metod\w*|method\w*)\b'),
)


def search_command(message):
    """Recognize bare search imperatives while keeping the existing online forms."""
    match = _COMMAND.match(message or '')
    if not match or _UNSCOPED.match(match['topic']):
        return None
    language = next(code for code in _COMMAND_PREFIX if match[code])
    topic = match['topic'].strip(' ¿¡?!.')
    if (local_only_request(message) or not public_query_text(message)
            or private_identity_topic(language, topic)):
        return language, ''
    # Preserve the established routing of focused Italian "Cerca" requests.
    if language == 'it' and match['it'].casefold() == 'cerca' and broad_topic(topic) is None:
        return None
    return language, topic


def broad_topic(topic):
    topic = _ARTICLE.sub('', topic or '').strip()
    if not 2 <= len(topic) <= 85 or len(topic.split()) > 7 or freshness_requested(topic):
        return None
    if search_query(topic, min_length=2) != topic or _FOCUSED.search(_plain(topic)):
        return None
    if _DETAIL.match(_plain(topic)) and _RELATION.search(_plain(topic)):
        return None
    return topic


def focus_choices(topic, language, reference=None, *, original_topic=''):
    search_topic = topic
    description = ''
    if reference is not None:
        description = _plain(reference.text[:240])
        definition = _DEFINITION.search(description)
        if definition:
            description = description[definition.end():]
        title = reference.title
        if (search_query(title, min_length=2) == title
                and re.search(r'(?<!\w)' + re.escape(_plain(topic)) + r'(?!\w)', _plain(title))):
            search_topic = title
    # Search only the opening description. Distant mentions can describe a
    # different entity. With no description, use the words of the topic.
    matches = [(match.start(), name) for name, pattern in _DESCRIPTION
               if (match := re.search(pattern, description or _plain(topic)))]
    kind = min(matches, key=lambda match: match[0], default=(0, 'general'))[1]
    if kind in ('general', 'concept') and any(name == 'natural' for _, name in matches):
        kind = 'natural'
    if kind == 'person' and any(name == 'military' and position < 65 for position, name in matches):
        kind = 'military'
    prompt, offline = _PROMPTS[language]
    labels = dict(zip(_FACETS, _LABELS[language], strict=True))
    choices = []
    for facet in ('overview', *_PROFILES[kind]):
        label = labels[facet]
        detail = _SEARCH_DETAILS[language].get(facet, label.lower())
        query = search_topic if facet == 'overview' else f'{search_topic} {detail}'
        if search_query(query, min_length=2) == query:
            choices.append({'label': label, 'query': f'{_COMMAND_PREFIX[language]} {query}', 'facet': facet})
    article = _ARTICLE.match(original_topic) if language == 'it' else None
    italian_prefix = _IT_TOPIC_PREFIX.get(article[0].casefold()) if article else None
    question = ('Cosa vuoi approfondire ' + italian_prefix + search_topic + '?' if italian_prefix
                else prompt.format(topic=search_topic))
    return question, {'choices': choices, 'offline': offline, 'kind': kind}


def selected_research_focus(message, topic, history):
    """Recover the intended subject and facet, including older saved choices."""
    for row in reversed(history):
        if row.role != 'assistant' or row.metadata.get('source') != 'research_choices':
            continue
        focus = (row.metadata.get('reference_review') or {}).get('choices') or {}
        for index, choice in enumerate(focus.get('choices', ())):
            if choice.get('query') != message:
                continue
            overview = topic if choice.get('facet', 'overview' if index == 0 else '') == 'overview' else None
            return overview, focus.get('kind') in _NONFICTION
    return None, False


def matches_overview(topic, title):
    return bool(title and _plain(title).replace('_', ' ').strip() == _plain(topic).strip())


def adaptation_title(title):
    return isinstance(title, str) and bool(_MEDIA_TITLE.search(_plain(title)))


def campaign_scope(query, language):
    """Recognize the campaign focus and require a named military engagement."""
    detail = _SEARCH_DETAILS.get(language, {}).get('campaigns')
    if detail and query.casefold().endswith(' ' + detail.casefold()):
        return query[:-(len(detail) + 1)].strip(), _CAMPAIGN_PASSAGES[language]
    return None
