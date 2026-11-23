"""Opt-in public reference reads. Nothing here searches personal memory.

An obtained extract proves what that page says, not universal factual truth.
The default is local-only. Only a bounded public topic goes to one fixed API;
model-generated URLs, page instructions and full conversations are never used.
"""
from contextlib import closing, contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import logging
import math
import re
import sqlite3
import threading
import time
import unicodedata
from urllib.parse import urlparse, parse_qs, unquote

from .persistence import atomic_write_json
from .generation_control import check_cancelled
from .nasa_references import ESA_PAGES, NASA_LICENSE, NASA_PAGES, NOAA_PAGES, EsaReader, NasaReader, NoaaReader, astronomy_topic, evidence_terms
from .public_language import WIKIPEDIA_EDITIONS, identity_question, multilingual_local_only, private_identity_topic
from .reference_comparison import AGENCY_PROVIDERS, agency_topic, comparison_subject, source_comparison_followup, source_comparison_request

USER_AGENT = 'ALLMA/0.9.1 (https://github.com/jokenji19/ALLMA)'
LANGUAGES = WIKIPEDIA_EDITIONS
MAX_RESPONSE = 96 * 1024
TTL = 24 * 60 * 60


_RESEARCH = re.compile(r'^\s*(?:(?:puoi|riesci a|can you)\s+)?(?:'
    r'(?P<es>(?:busca|busque) (?:en internet|en línea|online)|verifica (?:en internet|en línea))|'
    r'(?P<fr>(?:cherche|recherche|vérifie) (?:sur internet|en ligne))|'
    r'(?P<de>(?:suche|recherchiere) (?:im internet|online))|'
    r'(?P<pt>(?:pesquisa|pesquise|procura|procure) (?:na internet|online))|'
    r'(?P<it>(?:cerc\w*|verific\w*|controll\w*)(?:\s+\w+){0,3}\s+(?:sui? internet|online|sul web|in rete))|'
    r'(?P<en>search (?:online|the web|the internet)|(?:check|verify) online|look (?:it )?up)|'
    r'(?P<ru>(?:найди|поищи|проверь) (?:в интернете|онлайн))|'
    r'(?P<ar>ابحث (?:في الإنترنت|على الإنترنت)))\b', re.I)
_REUSE_QUESTION = re.compile(
    r'(?:quest[ao]|quell[ao]|l[’\']ultima|la precedente) domanda(?: precedente| successiva)?|'
    r'la domanda (?:precedente|che ti ho (?:fatto|appena fatto))|'
    r'(?:that|the previous|my last) question|(?:esa|la pregunta anterior)|'
    r'(?:cette question|la question précédente)|(?:diese|die vorige) frage|(?:essa pergunta|a pergunta anterior)', re.I)
_FRESH = re.compile(r'\b(?:oggi|attualmente|attual[ei]|today|latest|right now|notizie (?:su|sul|dal)|'
                    r'hoy|actualmente|últimas noticias|aujourd[’\']hui|dernières nouvelles|'
                    r'heute|aktuell|neueste nachrichten|hoje|últimas notícias|'
                    r'(?:ultim[oaie]|recent[ei])\s+(?:notizi\w*|dati|statistic\w*|aggiornament\w*|version\w*|risultat\w*)|'
                    r'(?:notizi\w*|dati|aggiornament\w*|risultat\w*)\s+recent[ei])\b', re.I)
_PUBLIC_QUESTION = re.compile(r'^(?:perch[eé]|come (?:si|avviene|nasce|è nato)|'
    r'dove (?:si trova(?:no)?|è situat[oa])|quando (?:è|sono|fu|avvenne)|'
    r'qual(?:e|i)? (?:è|sono) (?:la|le|i|il) (?:caus[ae]|conseguenz[ae]|origine|effett[oi]) (?:di|del(?:l[aoe])?)|'
    r'(?:parlami|mi parli) di|(?:why|when|where) (?:is|was|were|does|did|are))\s+', re.I)
_PROPERTY_QUESTION = re.compile(r'^perch[eé]\s+([^?.!,]{2,80}?)\s+è\s+([\wà-ž-]{2,30})[\s?!.]*$', re.I)
_YEAR_QUESTION = re.compile(r'^(?:in che anno|quando) (?:è stat[oa]|fu|venne)\s+'
                            r'(firmat[oa]|inaugurat[oa]|fondat[oa]|pubblicat[oa])\b', re.I)
_WORK_QUESTION = re.compile(r'^(?:chi ha (scritto|dipinto|composto)|who (wrote|painted|composed))\b', re.I)
_WORK_TYPES = {
    'dipinto': ('dipinto', 'quadro', 'opera pittorica'), 'painted': ('painting',),
    'scritto': ('romanzo', 'libro', 'poema', 'opera letteraria', 'testo teatrale', 'opera poetica'),
    'wrote': ('novel', 'book', 'poem', 'play', 'literary work'),
    'composto': ('composizione', 'opera musicale', 'sinfonia', 'concerto', 'brano'),
    'composed': ('composition', 'opera', 'symphony', 'concerto', 'song'),
}
_FACT_QUESTION = re.compile(r'^(?:che cosa (?:significa|sono|si intende per)|mi (?:spieghi|descrivi)|'
    r'(?:dimmi qualcosa su|raccontami di)|'
    r'chi ha (?:scritto|dipinto|composto|inventato|scoperto)|'
    r'(?:could you |can you )?explain|tell me about|who (?:wrote|painted|composed|invented|discovered))\s+', re.I)
_PRIVATE_OR_LOCAL = re.compile(r'\b(?:io|mio|mia|miei|mie|nostr\w*|mi chiamo|ti ho|ti avevo|'
    r'noi|tuo|tua|tuoi|tue|questo|questa|quello|quella|my|mine|our|your|this|that|'
    r'password|codice|token|chiave|indirizzo|telefono|email|credenzial\w*|segreto|privat\w*|'
    r'cellulare|nome utente|username|account|numero di carta|pin|foto intim\w*|quanto guadagna|'
    r'prescrizion\w*|refert\w*|ricetta medica|esami di laboratorio|gruppo sanguigno|tessera sanitaria|'
    r'storia clinica|certificato vaccinale|nominativo del cliente|paziente|dove lavora|cv|'
    r'la su[ao] (?:casa|abitazione|residenza)|home address|medical records?|patient|social security number|'
    r'stipend\w*|salario|retribuzion\w*|iban|conto corrente|cartella clinica|'
    r'(?:dove|where)\s+(?:abita\w*|vive\w*|does)|come contattare|residenza di|casa di|'
    r'curriculum di|mi sento|farmac\w*|diagnos\w*|sintom\w*|depress\w*|suicid\w*|'
    r'immagin\w*|poesia|racconto|fantasia|imagine|fiction|story|'
    r'come scrivere|scena ambientata)\b', re.I)
_INVENTION_WORD = re.compile(r'\binvent\w*\b', re.I)
_DEPENDENT_RESEARCH = re.compile(r'^\s*(?:(?:dimmi|tell me) (?:anche )?(?:altro|di pi[uù]|more)|'
    r'(?:puoi )?(?:spiega(?:mi)? meglio|approfondisci)|altri dettagli|what else)\b|'
    r'^\s*(?:why|perch[eé]|come mai)[\s?!.,]*$', re.I)
_DEPENDENT_TAIL = re.compile(r"(?:su di (?:esso|essa|lui|lei)|sull[’']argomento|sullo stesso argomento|about it)", re.I)
_CAUSAL_TERMS = ('perché', 'perche', 'causa', 'causato', 'causata', 'causate', 'causati', 'dovuto',
                 'dovuta', 'dovute', 'dovuti', 'dipende', 'provoca', 'because', 'caused', 'due', 'results')
_TITLE_ALIASES = {'pelle rossa': 'Nativi americani', 'pellerossa': 'Nativi americani',
                  'mao tse tung': 'Mao Zedong', 'mao tse-tung': 'Mao Zedong',
                  "ettore nell'iliade": 'Ettore (mitologia)', 'ettore nell’iliade': 'Ettore (mitologia)'}
_NAME_ENTRY = re.compile(
    r'\b(?:un nome proprio|un prenome|a given name|a surname|un nombre de pila|un apellido|'
    r'un prénom|un nom de famille|ein (?:männlicher |weiblicher )?vorname|ein familienname|'
    r'um prenome|um sobrenome|мужское имя|женское имя|личное имя|фамилия)\b|'
    r'اسم شخصي|(?:是|の)(?:姓氏|個人名|人名)', re.I)


def person_or_group_question(message):
    return identity_question(message) is not None


def _identity_document(text):
    from .contribution_review import statements

    lead = statements(text, limit=1)
    return bool(lead and not _NAME_ENTRY.search(lead[0]))


def research_followup(message):
    match = _RESEARCH.match(message or '')
    remainder = message[match.end():].strip(' \t:,.!?') if match else None
    return remainder is not None and (not remainder or _REUSE_QUESTION.fullmatch(remainder) is not None)


def research_language(message):
    match = _RESEARCH.match(message or '')
    return match.lastgroup if match else None


def research_subject(message, history):
    """Resolve an explicit online command to one user-authored public query."""
    match = _RESEARCH.match(message or '')
    if not match:
        return None
    if local_only_request(message) or not public_query_text(message[:match.end()]):
        return ''
    if research_followup(message):
        # A generic imperative has no query of its own. Use the latest
        # substantive user turn, even if the assistant asked for clarity.
        for row in reversed(history):
            if row.role != 'user' or research_followup(row.content):
                continue
            if (local_only_request(row.content) or not public_query_text(row.content)
                    or private_identity_topic(match.lastgroup, row.content)):
                return ''
            prior = _RESEARCH.match(row.content)
            if prior and private_identity_topic(prior.lastgroup, row.content):
                return ''
            return row.content[prior.end():].lstrip(' :,-') if prior else row.content
        return ''
    subject = message[match.end():].lstrip(' :,-')
    return subject if public_query_text(message) and not private_identity_topic(match.lastgroup, subject) else ''


def explicit_research(message):
    return not local_only_request(message) and bool(_RESEARCH.match(message or '') or re.match(
        r'^\s*(?:cerca|verifica|search)\b', message or '', re.I))


def local_only_request(message):
    """A turn may restrict a grant, never create one. Ambiguous vetoes stay local."""
    text = unicodedata.normalize('NFKC', message or '').casefold().replace('’', "'")
    text = re.sub(r"\bdon't\b", 'do not', text)
    return multilingual_local_only(text) or bool(re.search(
        r'\b(?:offline|solo (?:in )?locale|local only|nessuna ricerca|no (?:internet|browsing|web search))\b|'
        r'\b(?:(?:rispondi|vai) a memoria|(?:usa|use) solo (?:quello|ciò) che sai|'
        r'(?:senza|without)\s+(?:consultare\s+)?fonti esterne)\b|'
        r'\b(?:senza|without)\b[^.!?;\n]{0,60}\b(?:internet|online|web|rete|browsing|search)\b|'
        r'\b(?:non|evita|do not|never)\b[^.!?;\n]{0,90}'
        r'\b(?:internet|online|web|rete|brows\w*|search\w*)\b', text))


def subject_reference(message):
    """Resolve only an explicitly replaced subject; '' means unresolved correction.

    This is a disposable task reference, never a new user memory or fact.
    """
    match = re.match(r'^\s*(?:no[,!]?[ \t]+)?(?:intendo|intendevo|mi riferivo(?: a)?|'
        r'parlavo di|volevo dire|i meant|i was referring to)\s+([^.!?\n]{1,150})', message or '', re.I)
    if not match:
        if re.match(r'^\s*(?:no[,!]?\s*)?non intendevo\b', message or '', re.I):
            match = re.search(r'\bma\s+([^.!?\n]{1,150})', message, re.I)
            if not match:
                return ''
        else:
            return None
    subject = re.split(r',?\s+\b(?:non|not|cerca|verifica|search)\b', match[1], maxsplit=1, flags=re.I)[0].strip(' ,;:')
    if (not subject or re.search(r'\b(?:contrario|precedente|altro|altra|quello|quella|questo|questa|'
            r'opposite|previous|other|that|this)\b', subject, re.I)):
        return ''
    subject = re.sub(r'\b(nell|dell|sull|all|dall|l)"(?=[^\W\d_])', r"\1'", subject, flags=re.I)
    return subject if public_topic(subject) else "Cos'è " + subject + '?'


def public_query_text(value):
    """Normalize compatibility forms before admitting a string to the router."""
    if not isinstance(value, str) or len(value) > 300:
        return ''
    text = unicodedata.normalize('NFKC', value)
    if (len(text) > 300 or any(unicodedata.category(char).startswith('C') for char in text)
            or re.search(r'[@`{}<>]|https?://', text, re.I) or private_or_creative(text)):
        return ''
    return text.strip()


def private_or_creative(text):
    if _PRIVATE_OR_LOCAL.search(text):
        if re.search(r'\b(?:ipv6|http)\b', text, re.I):
            from .technical_search import public_protocol_question

            explicit = _RESEARCH.match(text)
            question = text[explicit.end():].lstrip(' :,-') if explicit else text
            if public_protocol_question(question):
                return False
        return True
    if not _INVENTION_WORD.search(text):
        return False
    from .research_intent import primacy_question

    command = _RESEARCH.match(text)
    subject = (text[command.end():] if command else text).strip(' :,-')
    return not any(
        plan.action == 'invent' and not _INVENTION_WORD.search(plan.topic)
        for language in ('it', 'en', 'es') if (plan := primacy_question(subject, language))
    )


def dependent_research(message):
    match = _DEPENDENT_RESEARCH.match(message)
    if not match:
        return False
    tail = message[match.end():].strip(' ?!.,')
    tail = re.sub(r"(?:^|[,;]\s*)senza ripetere (?:i punti già detti|quanto già detto)[.!?]*$", '', tail, flags=re.I)
    return not tail or bool(_DEPENDENT_TAIL.fullmatch(tail))


def freshness_requested(message):
    return bool(_FRESH.search(unicodedata.normalize('NFKC', message)))


def public_topic(message, anchor=''):
    """Conservative topic nomination; no LLM/private-archive query arguments.

    Unknown forms stay local. An explicit search command still cannot bypass
    sensitive-data filtering or the app's separate permission.
    """
    message = public_query_text(message)
    if not message:
        return None
    corrected = subject_reference(message)
    if corrected is not None:
        # An explicit catalog entry can resolve a qualified correction even
        # without an anchor. Otherwise retain the dialogue requirement.
        topic = public_topic(corrected) if corrected else None
        return topic if anchor or topic in _TITLE_ALIASES.values() else None
    if anchor:
        current = public_topic(message)
        if current is not None:
            return current
        without_offline = re.sub(
            r'(?:[.,;]\s*|\s+)(?:ma\s+)?(?:non cercare (?:su internet|online)|'
            r'senza internet|rimani offline|offline|do not search online)[.!?\s]*$', '', message, flags=re.I)
        if not (research_followup(message) or dependent_research(without_offline)):
            return None
    if not anchor and research_followup(message):
        return None
    text = public_query_text(anchor) if anchor else message
    if not text:
        return None
    text=text.strip()
    # Only formatting after the public question is removed, never private
    # clauses from an otherwise sensitive question.
    text = re.split(r'(?<=[?.!])\s*(?:rispondi|rispondimi|answer|respond)\b',text,flags=re.I)[0].strip()
    if re.search(r'[\n@\d`{}<>]|https?://', text, re.I) or private_or_creative(text):
        return None
    text = re.split(r'\b(?:rispondi|rispondimi|answer|respond)\b',text,flags=re.I)[0].strip()
    # Accept an optional polite request and separators after a web-search verb.
    online = _RESEARCH.match(text)
    if online:
        remainder = text[online.end():].lstrip(' :,-')
        nested_topic = public_topic(remainder)
        if nested_topic is not None:
            return nested_topic
        text = 'Cerca ' + remainder
    if official := astronomy_topic(text):
        return official
    if (text.startswith('Cerca ') or re.match(r'^perch[eé]\s|^why\s', text, re.I)) and agency_topic(text, True) == 'Global sea level':
        return 'Global sea level'
    identity = identity_question(text)
    pattern = (r'^(?:cerca(?: su internet| online| sul web)?|verifica(?: online)?|'
        r'che cos[’\']è|cos[’\']è|cosa (?:è|sono)|'
        r'(?:come (?:funziona(?:no)?|si forma(?:no)?))|'
        r'(?:spiega(?:mi)?|descrivi(?:mi)?)(?: il funzionamento)?(?: come| perché| perche)?|'
        r'what (?:is|are|was)|how (?:does|do)|search(?: online)?|explain)\s+')
    match = _YEAR_QUESTION.match(text) or _FACT_QUESTION.match(text) or re.match(pattern,text,re.I) or _PUBLIC_QUESTION.match(text)
    if not identity and not match:
        return None
    topic = (identity[1] if identity else text[match.end():]).strip(' ?؟!.:;«»“”"')
    if property_question := _PROPERTY_QUESTION.fullmatch(text):
        topic = property_question[1]
    if text.casefold().startswith('come si '):
        topic = re.sub(r'^(?:produce|fabbrica|ottiene|forma)\s+', '', topic, flags=re.I)
    topic = re.sub(r'\s+in (?:una|due|tre|quattro|\d+) frasi\s*$', '',topic,flags=re.I)
    topic = re.sub(r'^(?:in dettaglio|brevemente|in detail|briefly)\s+|\s+(?:in dettaglio|brevemente|in detail|briefly)$',
                   '', topic, flags=re.I)
    topic = re.sub(r'^(?:di una? |di |una? |il |lo |la |i |gli |le |the |an? )+', '',topic,flags=re.I)
    if re.match(r'^(?:qual è|cosa|quale|the latest|dato più recente)\b', topic, re.I):
        return None
    if (not 2 <= len(topic) <= 104 or len(topic.split()) > 13
            or any(not (char.isalpha() or unicodedata.category(char).startswith('M')
                        or char in " ’'-·・") for char in topic)
            or (identity and (private_identity_topic(identity[0], topic) or multilingual_local_only(topic)))):
        return None
    topic = ' '.join(topic.split())
    alias = _TITLE_ALIASES.get(topic.casefold())
    if alias and (person_or_group_question(text) or text.casefold().startswith(('cerca ', "cos'è ", 'cos’è '))):
        return alias
    return topic


def _url_allowed(url):
    try:
        if (not isinstance(url, str) or len(url) > 2048
                or '\\' in url or any(ord(char) <= 32 or ord(char) == 127 for char in url)):
            return False
        parsed = urlparse(url)
        decoded = unquote(parsed.path, errors='strict')
        if ('\\' in decoded or re.search(r'%[\da-fA-F]{2}', decoded)
                or any(part in {'.', '..'} for part in decoded.split('/'))
                or any(unicodedata.category(char).startswith('C') for char in decoded)):
            return False
        return (parsed.scheme == 'https' and parsed.hostname in {lang+'.wikipedia.org' for lang in LANGUAGES}
            and parsed.username is None and parsed.password is None and parsed.port in (None,443)
            and parsed.path.startswith('/wiki/') and len(parsed.path) > len('/wiki/')
            and not parsed.fragment and not parsed.query)
    except (ValueError,TypeError):
        return False


def reference_link_allowed(url):
    if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        return False
    if url in (*NASA_PAGES.values(), *ESA_PAGES.values(), *NOAA_PAGES.values(), NASA_LICENSE, 'https://creativecommons.org/licenses/by-sa/4.0/'):
        return True
    try:
        parsed=urlparse(url)
        query=parse_qs(parsed.query,strict_parsing=True)
        return (_url_allowed(parsed._replace(query='').geturl()) and set(query)=={'oldid'}
            and len(query['oldid'])==1 and re.fullmatch(r'[1-9][0-9]{0,11}', query['oldid'][0]) is not None)
    except (ValueError,TypeError,AttributeError):
        return False


@dataclass(frozen=True)
class Reference:
    title: str
    text: str
    url: str
    revision: int
    fetched_at: float
    license_url: str = 'https://creativecommons.org/licenses/by-sa/4.0/'
    provider: str = 'wikipedia'
    matched_title: str = ''
    entity_id: str = ''
    alternate_title: str = ''
    full_article: bool = False

    @property
    def identifier(self):
        return hashlib.sha256((self.url+'\n'+str(self.revision)+'\n'+self.text).encode()).hexdigest()

    def citation(self):
        return {key:getattr(self,key) for key in ('title','url','revision','fetched_at','license_url','provider')}


def _valid_reference(reference):
    return (isinstance(reference,Reference) and isinstance(reference.title,str)
        and 1<=len(reference.title)<=200 and _valid_extract(reference.text, reference.url)
        and type(reference.revision) is int
        and type(reference.fetched_at) in (int,float) and math.isfinite(reference.fetched_at)
        and 0<=time.time()-reference.fetched_at<=TTL
        and isinstance(reference.matched_title,str) and len(reference.matched_title)<=200
        and isinstance(reference.entity_id,str) and (not reference.entity_id or re.fullmatch(r'Q[1-9]\d{0,14}',reference.entity_id))
        and isinstance(reference.alternate_title,str) and len(reference.alternate_title)<=200
        and type(reference.full_article) is bool
        and ((reference.provider=='wikipedia' and _url_allowed(reference.url)
              and 0<reference.revision<10**12 and reference.license_url=='https://creativecommons.org/licenses/by-sa/4.0/')
             or (reference.provider=='nasa' and NASA_PAGES.get(reference.title)==reference.url
                 and reference.revision==0 and reference.license_url==NASA_LICENSE)
             or (reference.provider=='esa' and ESA_PAGES.get(reference.title)==reference.url
                 and reference.revision==0 and reference.license_url=='')
             or (reference.provider=='noaa' and NOAA_PAGES.get(reference.title)==reference.url
                 and reference.revision==0 and reference.license_url=='')))


def _valid_extract(text, url):
    # A complete sentence in Chinese or Japanese often needs fewer characters.
    short_edition = isinstance(url, str) and url.startswith(
        ('https://zh.wikipedia.org/wiki/', 'https://ja.wikipedia.org/wiki/'))
    return isinstance(text, str) and (18 if short_edition else 30) <= len(text) <= 6000


def _relevant(reference, topic):
    """Search ranking alone does not establish that an extract is about a topic."""
    if reference.matched_title and _title_key(reference.matched_title)==_title_key(topic):
        return True
    stop=set('il lo la gli le un una di del della da al alla nel nella si fu sono viene funzionamento formazione '
             'the a an of does do did was were is are in and work works'.split())
    def words(value):
        value=''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))
        return {word[:-1] if len(word)>4 and word[-1] in 'aeio' else word
                for word in re.findall(r'\w+',value) if word not in stop and len(word)>1}
    requested=words(topic)
    title=words(reference.title)
    shared=requested & title
    if not requested or not title:
        return False
    if len(shared)/len(requested)>=.6 and len(shared)/len(title)>=.6 and (len(requested)<=2 or requested<=title|words(reference.text)):
        return True
    # A longer public question may include an aspect absent from the title.
    # Require a title match and all other meaningful terms in the extract.
    return (len(requested)>=2 and title < requested and len(requested-shared)<=2
            and requested <= title | words(reference.text))


def _title_key(value):
    return ' '.join(unicodedata.normalize('NFKC',value).replace('_',' ').casefold().split())


def _resolved_title(query, topic):
    # Only redirects/normalizations returned by the fixed API can establish an
    # alias. Search ranking or a surname overlap alone is insufficient.
    current=_title_key(topic)
    for key in ('normalized','redirects'):
        rows=query.get(key,[])
        if not isinstance(rows,list) or len(rows)>8:
            return None
        for _ in range(len(rows)):
            row=next((r for r in rows if isinstance(r,dict) and isinstance(r.get('from'),str)
                and _title_key(r['from'])==current and isinstance(r.get('to'),str)),None)
            if row is None:break
            target=_title_key(row['to'])
            if target==current:break
            current=target
    return current


class WikipediaReader:
    """Resolve a public title first; at most one bounded search fallback."""
    def __init__(self, session=None):
        self.session = session

    def fetch(self, topic, language, cancelled, allowed, work_types=(), *, accept_document=None):
        from .bounded_io import reference_io
        return reference_io(lambda stop: self._fetch(topic, language, stop, allowed, work_types,
                                                     accept_document=accept_document), cancelled, allowed)

    def fetch_article(self, focus, language, cancelled, allowed):
        from .bounded_io import reference_io
        from .online_article import find_passage
        from .online_transport import request_json
        import requests

        citation = focus.article_citation
        url, title, revision = citation['url'], citation['title'], citation['revision']
        if (language not in LANGUAGES or not _url_allowed(url)
                or urlparse(url).hostname != f'{language}.wikipedia.org'
                or type(revision) is not int or not 0 < revision < 10**12):
            return []

        def fetch(stop):
            with requests.Session() as session:
                session.trust_env = False
                result = request_json(session, f'https://{language}.wikipedia.org/w/api.php', stop, allowed,
                    params={'action': 'parse', 'oldid': revision, 'prop': 'text|revid', 'format': 'json',
                            'formatversion': 2, 'disableeditsection': 1},
                    headers={'User-Agent': USER_AGENT}, limit=2 * 1024 * 1024)
            parsed = (result or {}).get('parse')
            if not isinstance(parsed, dict) or parsed.get('title') != title or parsed.get('revid') != revision:
                return []
            passage = find_passage(parsed.get('text'), focus)
            check_cancelled(stop)
            return [Reference(title, passage, url, revision, time.time(), full_article=True)] if passage else []

        return reference_io(fetch, cancelled, allowed)

    def _fetch(self, topic, language, cancelled, allowed, work_types=(), *, accept_document=None):
        import requests
        if language not in LANGUAGES or not allowed():
            return []
        session=self.session or requests.Session()
        owned=self.session is None
        if owned:session.trust_env=False
        base = {'action':'query','format':'json','formatversion':2,
            'prop':'extracts|info|revisions|pageprops|langlinks','ppprop':'disambiguation|wikibase_item',
            'lllang':'en' if language=='it' else 'it','lllimit':1,
            'explaintext':1,'exsectionformat':'plain','inprop':'url','rvprop':'ids|timestamp'}
        search_topic = f'intitle:"{topic}" "{work_types[0]}"' if work_types else topic
        attempts=({'titles':topic,'redirects':1},
            {'generator':'search','gsrsearch':search_topic,'gsrnamespace':0,'gsrlimit':4})
        started=time.monotonic()
        try:
            for attempt in attempts:
                check_cancelled(cancelled)
                if not allowed() or time.monotonic()-started>8:return []
                extract = ({'exsentences':10, 'exlimit':1} if accept_document is not None and 'titles' in attempt
                           else {'exintro':1,'exsentences':8,'exlimit':4})
                with session.get('https://'+language+'.wikipedia.org/w/api.php',params={**base,**extract,**attempt},
                        headers={'User-Agent':USER_AGENT,'Accept':'application/json'},
                        timeout=(3,3),stream=True,allow_redirects=False) as response:
                    if response.status_code!=200:raise ValueError('Reference service unavailable')
                    chunks,size=[],0
                    # read1 returns available bytes without waiting to fill a
                    # whole chunk. The fallback also checks a trickling body.
                    raw = getattr(response, 'raw', None)
                    read1 = getattr(raw, 'read1', None)
                    if callable(read1) and hasattr(type(raw), 'read1'):
                        chunks_iter = iter(lambda: read1(4096, decode_content=True), b'')
                    else:
                        chunks_iter = response.iter_content(1)
                    for chunk in chunks_iter:
                        check_cancelled(cancelled)
                        if not allowed():return []
                        size+=len(chunk)
                        if size>MAX_RESPONSE or time.monotonic()-started>8:raise ValueError('Reference response limit')
                        chunks.append(chunk)
                    data=json.loads(b''.join(chunks))
                query=data.get('query',{});pages=query.get('pages',[])
                if not isinstance(pages,list) or 'error' in data or any(not isinstance(p,dict) for p in pages):
                    raise ValueError('Invalid reference response')
                resolved=_resolved_title(query,topic) if 'titles' in attempt else None
                result=[]
                for page in sorted(pages,key=lambda p:p.get('index',99) if type(p.get('index')) is int else 99)[:4]:
                    text,title,url=page.get('extract'),page.get('title'),page.get('fullurl')
                    revision=(page.get('revisions') or [{}])[0].get('revid')
                    if (page.get('ns')!=0 or 'disambiguation' in page.get('pageprops',{})
                            or not _valid_extract(text, url)
                            or not isinstance(title,str) or not 1<=len(title)<=200
                            or not _url_allowed(url) or urlparse(url).hostname != f'{language}.wikipedia.org'
                            or type(revision) is not int or revision<1):continue
                    matched=topic if resolved==_title_key(title) else ''
                    props=page.get('pageprops') or {}
                    if work_types:
                        lead = text.split('\n', 1)[0][:320]
                        if not any(re.search(r'\b'+re.escape(kind)+r'\b', lead, re.I) for kind in work_types):
                            continue
                        if _title_key(title.split(' (', 1)[0]) == _title_key(topic):
                            matched = topic
                    entity=props.get('wikibase_item','')
                    links=page.get('langlinks') or []
                    alternate=next((link.get('title','') for link in links if isinstance(link,dict)
                                    and link.get('lang')==base['lllang']), '')
                    reference=Reference(title,text,url,revision,time.time(),matched_title=matched,
                                        entity_id=entity,alternate_title=alternate)
                    if (_valid_reference(reference) and _relevant(reference,topic)
                            and (accept_document is None or accept_document(text))):
                        result.append(reference)
                    if len(result)==2:
                        break
                if result:return result
            return []
        finally:
            if owned:session.close()


class PublicReferences:
    def __init__(self, db_path, preference_path, reader=None):
        self.db_path, self.preference_path = str(db_path), Path(preference_path)
        self.reader = reader or WikipediaReader()
        self.nasa_reader = NasaReader()
        self.esa_reader = EsaReader()
        self.noaa_reader = NoaaReader()
        from .online_weather import OpenMeteo
        from .searx_research import SearxResearch
        from .web_search import NativeWebSearch
        self.weather = OpenMeteo()
        self.search = NativeWebSearch()
        self.general_search = SearxResearch()
        self._web_links = {}
        self.lock = threading.RLock()
        self._enabled, self._revision, self._error = False, 0, None
        self._expanded = False
        if self.preference_path.exists():
            try:
                if self.preference_path.stat().st_size > 4096:
                    raise ValueError('Preference size')
                data = json.loads(self.preference_path.read_text())
                if (set(data) - {'version','enabled','expanded'} or type(data['version']) is not int
                        or data['version'] != 1 or type(data['enabled']) is not bool
                        or type(data.get('expanded', False)) is not bool):
                    raise ValueError('Invalid preference')
                self._enabled = data['enabled']
                self._expanded = data.get('expanded', False)
            except Exception:
                self._error = 'Non riesco a leggere il consenso: le ricerche online restano disattivate.'

    def status(self):
        with self.lock:
            return {'enabled':self._enabled,'default_local':True,'error':self._error,
                    'provider':'Wikipedia, fonti ufficiali e Open-Meteo','query_scope':'current_public_topic',
                    'expanded':self._expanded}

    def register_web_links(self, sources):
        from .web_search import public_url
        with self.lock:
            for row in sources:
                url = row.get('url')
                if public_url(url):
                    self._web_links.pop(url, None)
                    self._web_links[url] = None
            while len(self._web_links) > 600:
                del self._web_links[next(iter(self._web_links))]

    def web_link_allowed(self, url):
        from .web_search import public_url
        with self.lock:
            return public_url(url) and url in self._web_links

    def live_lookup(self, reader, message, args, cancel_event=None, activity=None, *, requires_expanded=False,
                    reader_options=None, expected_revision=None):
        result = {'status':'local_only', 'network_used':False}
        check_cancelled(cancel_event)
        with self.lock:
            if expected_revision is not None and expected_revision != self._revision:
                return {'status': 'consent_revoked', 'network_used': False}
            if not self._enabled or (requires_expanded and not self._expanded) or local_only_request(message):
                return result
            revision = self._revision
        def allowed():
            with self.delivery_authorized(revision) as current:
                return current

        started = time.monotonic()
        error_type = None
        try:
            if activity:
                activity({'state':'searching', 'network_used':True, 'provider':reader.name})
            result.update(network_used=True, authorization_revision=revision)
            payload = reader.fetch(*args, cancel_event, allowed, **(reader_options or {}))
            if allowed():
                if not isinstance(payload, dict):
                    result['status'] = 'unavailable'
                else:
                    result.update(payload)
            else:
                result['status'] = 'consent_revoked'
        except Exception as error:
            from .generation_control import GenerationCancelled
            if isinstance(error, GenerationCancelled):
                result['status'] = 'cancelled'
                raise
            error_type = type(error).__name__
            result['status'] = 'unavailable'
        finally:
            logging.info('[PublicReference] provider=%s status=%s elapsed_ms=%.0f error=%s',
                         reader.name, result['status'], (time.monotonic() - started) * 1000, error_type or '-')
            if activity:
                activity({'state':'finished', 'network_used':result['network_used'], 'provider':reader.name})
        check_cancelled(cancel_event)
        if not allowed():
            return {'status':'consent_revoked', 'network_used':result['network_used']}
        return result

    def search_web(self, message, query, language, fresh, cancel_event=None, activity=None):
        from .web_search import search_query, feed_plan
        if search_query(query) != query or private_identity_topic(language, query):
            return {'status':'not_applicable', 'network_used':False}
        if not self.status()['enabled'] or local_only_request(message):
            return {'status':'local_only', 'network_used':False}
        if fresh and not feed_plan(query):
            return {'status':'freshness_unsupported', 'network_used':False}
        return self.live_lookup(self.search, message, (query, language if language in LANGUAGES else 'it', fresh),
                                cancel_event, activity)

    def search_public_pages(self, message, query, language, fresh, cancel_event=None, activity=None, *,
                            previous=(), expected_revision=None, exclude_adaptations=False):
        from .web_search import search_query
        if search_query(query, allow_symbols=True) != query or private_identity_topic(language, query.replace('_', ' ')):
            return {'status':'not_applicable', 'network_used':False}
        options = {'previous': tuple(previous)} if previous else {}
        if exclude_adaptations:
            options['exclude_adaptations'] = True
        return self.live_lookup(self.general_search, message, (query, language, fresh), cancel_event, activity,
                                requires_expanded=True, reader_options=options,
                                expected_revision=expected_revision)

    def configure_expanded(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Invalid search preference')
        with self.lock:
            return self.configure(self._enabled, expanded=enabled)

    def configure(self, enabled, *, expanded=None):
        if type(enabled) is not bool:
            raise ValueError('Invalid web preference')
        with self.lock:
            # Revoke before disk I/O so a failed save cannot keep an in-flight
            # operation authorized. A failed enable never grants access.
            if not enabled:
                self._enabled=False
                self.weather.clear_locations()
            self._revision += 1
            expanded = self._expanded if expanded is None else expanded
            preference = {'version':1,'enabled':enabled}
            if expanded:
                preference['expanded'] = True
            try:
                atomic_write_json(self.preference_path, preference)
            except OSError:
                self._error='Non riesco a salvare la preferenza. Le ricerche sono disattivate in questa sessione.'
                self._enabled=False
                self._expanded=False
                try:
                    self.preference_path.unlink(missing_ok=True)
                except OSError:
                    self._error+=' Al prossimo avvio controlla nuovamente questa impostazione.'
                return self.status()
            self._enabled, self._error = enabled, None
            self._expanded = expanded
            return self.status()

    @staticmethod
    def _key(topic, language):
        if language in LANGUAGES:
            language = 'wiki-v2:'+language
        return hashlib.sha256((language+'\n'+unicodedata.normalize('NFKC',topic).casefold()).encode()).hexdigest()

    def _cache(self, key, references=None):
        with closing(sqlite3.connect(self.db_path, timeout=2)) as db, db:
            if references is None:
                exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='public_reference_cache'").fetchone()
                if not exists:
                    return []
                row=db.execute('SELECT payload,created FROM public_reference_cache WHERE key=?',(key,)).fetchone()
                if not row or not isinstance(row[0],str) or len(row[0])>MAX_RESPONSE or not 0 <= time.time()-row[1] <= TTL:
                    return []
                data=json.loads(row[0])
                if not isinstance(data,list) or len(data)>2:
                    return []
                refs=[Reference(**item) for item in data]
                return refs if all(_valid_reference(r) for r in refs) else []
            db.execute('CREATE TABLE IF NOT EXISTS public_reference_cache (key TEXT PRIMARY KEY,payload TEXT NOT NULL,created REAL NOT NULL)')
            db.execute('INSERT OR REPLACE INTO public_reference_cache VALUES(?,?,?)',
                (key,json.dumps([asdict(r) for r in references],ensure_ascii=False),time.time()))
            db.execute('DELETE FROM public_reference_cache WHERE key NOT IN (SELECT key FROM public_reference_cache ORDER BY created DESC LIMIT 32)')
            return references

    @contextmanager
    def delivery_authorized(self, revision):
        """Linearize durable publication against changes to the online grant."""
        if revision is None:
            yield True
            return
        with self.lock:
            yield self._enabled and revision == self._revision

    def lookup(self, message, anchor='', language='it', cancel_event=None, activity=None, *, focused=None):
        def emit(payload):
            if activity is not None:
                activity(payload)
        safe_message = public_query_text(message)
        fresh = {}
        check_cancelled(cancel_event)
        try:
            if not safe_message:
                result = {'status': 'not_applicable', 'references': [], 'network_used': False}
                if isinstance(message, str) and source_comparison_request(message):
                    result.update(status='comparison_unsupported', comparison=True)
            elif source_comparison_request(safe_message):
                subject = comparison_subject(anchor if source_comparison_followup(safe_message) else safe_message)
                result = self._compare_sources(subject, safe_message, language, cancel_event, emit, fresh)
            else:
                result = self._lookup(safe_message, anchor, language, cancel_event, emit, fresh, focused)
        except Exception:
            emit({'state':'finished','network_used':False})
            raise
        with self.delivery_authorized(result.get('authorization_revision')) as allowed:
            if not allowed:
                result = dict(result, status='consent_revoked', references=[], source_states={})
        emit({'state':result['status'],'network_used':result['network_used'],
              'provider':result.get('provider')})
        with self.delivery_authorized(result.get('authorization_revision')) as allowed:
            check_cancelled(cancel_event)
            if not allowed:
                return dict(result, status='consent_revoked', references=[], source_states={})
            for key, references in fresh.items():
                try:
                    self._cache(key, references)
                except sqlite3.Error:
                    pass
            return result

    def _cached_source(self, key, provider, topic):
        try:
            references = self._cache(key)
        except (sqlite3.Error, ValueError, TypeError):
            return []
        return [r for r in references if r.provider == provider and _relevant(r, topic)]

    @staticmethod
    def _fetch_source(reader, provider, topic, language, cancelled, allowed, **options):
        references = reader.fetch(topic, language, cancelled, allowed, **options)
        if not isinstance(references, list) or len(references) > 2:
            raise ValueError('Invalid reference collection')
        return [r for r in references if _valid_reference(r) and r.provider == provider and _relevant(r, topic)]

    def _compare_sources(self, subject, message, language, cancel_event, emit, fresh):
        from .generation_control import GenerationCancelled

        result = {'status': 'comparison_unsupported', 'comparison': True, 'references': [],
                  'source_states': {}, 'network_used': False}
        topic = public_topic(subject)
        if not topic or _FRESH.search(subject) or _FRESH.search(message):
            return result
        agency = agency_topic(subject, topic)
        requested = set(re.findall(r'\b(?:nasa|esa|noaa)\b', message.casefold()))
        if requested - set(AGENCY_PROVIDERS.get(agency, ())):
            return result
        if not agency and re.search(r'\b(?:indipendent\w*|independent|editori diversi|siti diversi)\b', message, re.I):
            return result
        language = language if language in ('it', 'en') else 'it'
        result.update(comparison='agencies' if agency else 'editions', agency_topic=agency,
                      provider=('NASA Science e NOAA' if agency == 'Global sea level' else 'NASA Science ed ESA')
                      if agency else 'Wikipedia')
        check_cancelled(cancel_event)
        with self.lock:
            revision = self._revision
            online = self._enabled and not local_only_request(message)

        def allowed():
            with self.lock:
                return online and self._enabled and self._revision == revision

        def read_source(slot, provider, label, reader, query, edition, accept=lambda ref: True):
            check_cancelled(cancel_event)
            key = self._key(query, slot)
            references = [ref for ref in self._cached_source(key, provider, query) if accept(ref)]
            state = 'cached' if references else 'local_only'
            if not references and allowed():
                result['network_used'] = True
                result['authorization_revision'] = revision
                emit({'state': 'searching', 'network_used': True, 'provider': label})
                try:
                    references = [ref for ref in self._fetch_source(reader, provider, query, edition, cancel_event, allowed)
                                  if accept(ref)]
                    state = 'obtained' if references else 'not_found'
                    if references:
                        fresh[key] = references
                except GenerationCancelled:
                    raise
                except Exception:
                    state = 'unavailable'
            result['source_states'][slot] = state
            result['references'].extend(references[:1])
            return references[0] if references else None

        if agency:
            read_source('nasa', 'nasa', 'NASA Science', self.nasa_reader, agency, language)
            if agency == 'Global sea level':
                read_source('noaa', 'noaa', 'NOAA', self.noaa_reader, agency, language)
            else:
                read_source('esa', 'esa', 'ESA', self.esa_reader, agency, language)
        else:
            def in_edition(ref, edition):
                return ref.url.startswith(f'https://{edition}.wikipedia.org/')

            primary = read_source(language, 'wikipedia', 'Wikipedia', self.reader, topic, language,
                                  lambda ref: in_edition(ref, language))
            alternate = 'en' if language == 'it' else 'it'
            if primary and primary.alternate_title and primary.entity_id:
                read_source(alternate, 'wikipedia', 'Wikipedia', self.reader, primary.alternate_title, alternate,
                            lambda ref: in_edition(ref, alternate) and ref.entity_id == primary.entity_id)

        check_cancelled(cancel_event)
        with self.lock:
            # Revocation while reading either source invalidates the whole
            # turn and prevents publishing or caching the first result alone.
            if result['network_used'] and not allowed():
                return dict(result, status='consent_revoked', references=[], source_states={})
        status = ('obtained' if result['network_used'] else 'cached') if result['references'] else (
            'unavailable' if result['network_used'] else 'local_only')
        return dict(result, status=status)

    def _lookup(self, message, anchor, language, cancel_event, emit, fresh, focused):
        candidate = focused.candidate_question if focused is not None else message
        topic = public_topic(candidate, anchor if focused is None else '')
        result = {'status':'not_applicable','references':[], 'network_used':False}
        if _FRESH.search(message) and (topic or explicit_research(message)
                or (anchor and public_topic(anchor) and _DEPENDENT_RESEARCH.match(message))):
            return dict(result, status='freshness_unsupported')
        if topic is None:
            return dict(result, status='local_only') if local_only_request(message) else result
        language = language if language in LANGUAGES else 'it'
        # The proper name "Europa" alone is also the continent. Only the
        # catalog route from the current public question or its user anchor
        # may select NASA. Distinct cache keys keep those meanings apart.
        subject = (subject_reference(message) if focused is None else None) or (
            candidate if public_topic(candidate) is not None else anchor)
        subject = re.split(r'(?<=[?.!])\s*(?:rispondi|rispondimi|answer|respond)\b', subject, flags=re.I)[0].strip()
        online = _RESEARCH.match(subject)
        if online:
            remainder = subject[online.end():].lstrip(' :,-')
            subject = remainder if public_topic(remainder) else 'Cerca ' + remainder
        official = topic in NASA_PAGES and astronomy_topic(subject)==topic
        provider = 'NASA Science' if official else 'Wikipedia'
        expected_provider = 'nasa' if official else 'wikipedia'
        result['provider'] = provider
        if _FRESH.search(subject):
            return dict(result, status='freshness_unsupported')
        if official:
            result['evidence_terms'] = evidence_terms(subject)
            if re.search(r'\b(?:differenz\w*|confront\w*|compar\w*|difference\w*|versus)\b', subject, re.I):
                result['partial_coverage'] = True
        elif re.search(r'^(?:perch[eé]|why|qual è la causa)\b', subject.strip(), re.I):
            result['evidence_terms'] = (_CAUSAL_TERMS,)
            result['focus_evidence'] = True
            if property_question := _PROPERTY_QUESTION.fullmatch(subject.strip()):
                attribute = property_question[2].casefold()
                color_terms = ('blu', 'azzurro', 'azzurra')
                result['evidence_terms'] += (color_terms if attribute in color_terms else (attribute,),)
        elif year_question := _YEAR_QUESTION.match(subject):
            event = year_question[1].casefold()[:-1]
            terms = (event+'o', event+'a', event+'i', event+'e')
            if event == 'firmat':
                terms += ('accettato', 'accettata', 'siglato', 'siglata', 'sottoscritto', 'sottoscritta')
            result.update(evidence_terms=(terms,), focus_evidence=True, year_terms=terms)
        work_question = _WORK_QUESTION.match(subject) if not official else None
        work_verb = next((group.casefold() for group in work_question.groups() if group), '') if work_question else ''
        work_types = _WORK_TYPES.get(work_verb, ())
        identity = not official and person_or_group_question(subject)
        accept_document = focused.matches_document if focused is not None else _identity_document if identity else None
        cache_scope = 'nasa' if official else f'{language}:work:{work_types[0]}' if work_types else language
        key = self._key(topic, cache_scope)
        check_cancelled(cancel_event)
        cached = self._cached_source(key, expected_provider, topic)
        if focused is None:
            if identity:
                cached = [ref for ref in cached if accept_document(ref.text)]
            if cached:
                return dict(result, status='cached', references=cached)
        else:
            focus_scope = (f'wiki-article-v1:{language}:{focused.answer_type}:{focused.departure_target.casefold()}'
                           if focused.article_citation else f'wiki-focus-v1:{language}')
            focus_key = self._key(topic, focus_scope) if not official else key
            expanded = self._cached_source(focus_key, expected_provider, topic) if focus_key != key else []
            relevant = [ref for ref in cached + expanded
                        if focused.matches_document(ref.text, full_article=ref.full_article)]
            if relevant:
                return dict(result, status='cached', references=relevant[:2])
        with self.lock:
            revision=self._revision
            if not self._enabled or local_only_request(message):
                return dict(result,status='local_only')
        def allowed():
            with self.lock:
                return self._enabled and self._revision==revision
        try:
            result['network_used']=True
            result['authorization_revision'] = revision
            emit({'state':'searching','network_used':True,'provider':provider})
            reader = self.nasa_reader if official else self.reader
            options = {'work_types': work_types} if work_types else {}
            if accept_document is not None and isinstance(reader, WikipediaReader):
                options['accept_document'] = accept_document
                if focused is not None:
                    key = focus_key
            if (focused is not None and focused.article_citation and isinstance(reader, WikipediaReader)
                    and urlparse(focused.article_citation['url']).hostname == f'{language}.wikipedia.org'):
                references = [ref for ref in reader.fetch_article(focused, language, cancel_event, allowed)
                              if _valid_reference(ref) and _relevant(ref, topic)]
            else:
                references = self._fetch_source(reader, expected_provider, topic, language, cancel_event, allowed, **options)
            if focused is not None:
                references = [ref for ref in references
                              if focused.matches_document(ref.text, full_article=ref.full_article)]
            elif accept_document is not None:
                references = [ref for ref in references if accept_document(ref.text)]
            check_cancelled(cancel_event)
            with self.lock:
                if not allowed():
                    return dict(result,status='consent_revoked')
                if references:
                    fresh[key] = references
            return dict(result,status='obtained' if references else 'not_found',references=references)
        except Exception as error:
            from .generation_control import GenerationCancelled
            if isinstance(error,GenerationCancelled):raise
            return dict(result,status='unavailable',error=type(error).__name__)
