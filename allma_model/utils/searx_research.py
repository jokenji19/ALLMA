"""Discover pages through the companion index and read evidence on device."""
from datetime import date
from html import unescape
from http.client import HTTPException, HTTPSConnection
from ipaddress import ip_address, ip_network
from itertools import takewhile
import logging
import re
import socket
import ssl
from sys import stdlib_module_names
import time
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .bounded_io import reference_io
from .fact_search import fact_question
from .generation_control import check_cancelled
from .online_article import ArticleParagraphs
from .online_transport import ProviderError, request_json
from .research_choices import adaptation_title, campaign_scope
from .research_intent import primacy_question
from .research_scopes import documented_record, historical_facets, localized_statement, source_passage
from .science_search import science_question
from .technical_search import technical_reference


COMPANION_PORT = 18767
COMPANION_URL = f'http://127.0.0.1:{COMPANION_PORT}/search'
MWMBL_SEARCH = 'https://api.mwmbl.org/api/v2/search/'
EUROPE_PMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
CROSSREF_WORKS = 'https://api.crossref.org/works'
_BODY_LIMIT = 768 * 1024
_PUBLIC_V6 = ip_network('2000::/3')
_V6_TRANSITION = (ip_network('2002::/16'), ip_network('2001::/32'))
_REQUEST_WORDS = frozenset(
    'find search cerca ricerca dimmi spiegami puoi please tell explain how what when which '
    'pourquoi comment quel quelle chercher busca donde como que cuando cual cuales quien wie welche was '
    'pesquisa qual quais sobre information informazioni info documentazione documentation docs official ufficiale '
    'papers paper scientific scientifici research studi studies guide guida '
    'estudios articles etudes studien el los las una unos unas en por para entre et des aux dans sur les der die das und mit ein '
    'uma dos das nos nas com un une es son se does did fue era ne hoy actualidad actualmente ultimas noticias '
    'aujourd hui dernieres nouvelles heute neueste nachrichten hoje'.split())
_SCHOLARLY = re.compile(r'\b(?:studi|studi scientifici|articoli scientifici|letteratura scientifica|'
                        r'research papers?|scientific papers?|meta-analysis|systematic review|'
                        r'estudios|artículos científicos|études|articles scientifiques|studien)\b', re.I)
_SCHOLARLY_HOSTS = {'arxiv.org', 'export.arxiv.org', 'europepmc.org'}
_DOCUMENTATION = re.compile(r'\b(?:documentation|documentazione|manuale|manual|reference guide)\b', re.I)
_DISCUSSION_URL = re.compile(r'(?:^https://(?:forum|forums|community|users|internals|discuss|bugzilla)\.|'
                             r'/(?:issues|discussions|tickets?|questions|forum|forums)/)', re.I)
_ANECDOTE = re.compile(r'^(?:I (?:keep|tried|have|had|hit|ran|think|guess|need|wonder|am|remember)|'
                        r'my|ho (?:provato|avuto|notato)|mi capita|he probado|me pasa|'
                        r'this (?:document|page|article) (?:covers|describes|introduces|explains))\b', re.I)
_VERSION_NOTE = re.compile(r'^(?:added in|(?:changed|deprecated) (?:in|since) version|'
                            r'(?:distinto|añadido|obsoleto) en la versión|'
                            r'(?:modifié|ajouté) (?:dans|en) la version)\b', re.I)
_BODY_LANGUAGE = {
    'en': set('the for with and to of is are will this can by from was were'.split()),
    'es': set('el los las que se es su una en para del como con'.split()),
    'it': set('il gli la lo una suo alla della che sono con anche gli per'.split()),
    'fr': set('le les des une aux est sont dans pour par avec que cette'.split()),
}
_UNDERSCORE = re.compile(r'(?<!\w)[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z][A-Za-z0-9]*)+(?!\w)')
_API_SYMBOL = re.compile(r'[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z][A-Za-z0-9]*)+|[A-Z]?[a-z]+(?:[A-Z][A-Za-z0-9]*)+|'
                         r'[A-Z][a-z]+(?:[A-Z][A-Za-z0-9]*)+')
_SHORT_COMMAND = re.compile(r'[a-z][a-z0-9-]{1,23}')
_HEADING_LEVEL = {f'h{level}': level for level in range(1, 7)} | {'dt': 7}
_CAUSAL_QUESTION = re.compile(r'^(?:perch[eé]|why|por qu[eé]|pourquoi|warum|por que)\b', re.I)
_CAUSAL_PASSAGE = re.compile(r'\b(?:perch[eé]|caus\w*|a causa di|dipend\w*|dovut\w*|in quanto|'
                             r'because|due to|results? from|leads? to|arises? from|caus\w*|provoc\w*|'
                             r'debido a|porque|parce que|car|weil|aufgrund)\b', re.I)
_DATE_QUESTION = re.compile(r'^(?:quando|in che anno|when|in what year|cu[aá]ndo|en qu[eé] a[ñn]o|quand)\b', re.I)
_DATE_IN_PASSAGE = re.compile(r'\b(?:[12]\d{3}|\d{1,2}º? (?:secolo|century|siglo)|'
                             r'[MDCLXVI]{1,9} (?:secolo|siglo|siècle))\b', re.I)
_COMPARATIVE_MENTION = re.compile(r'\b(?:compared (?:to|with)|in comparison with|unlike|'
                                  r'paragonat\w* a|rispetto a|confrontat\w* con|'
                                  r'comparad\w* con|a diferencia d(?:e|el))\b', re.I)
_RELATIVE_FOUNDING = re.compile(r'^(?:founded|established|opened|inaugurated|fondat[oa]|inaugurat[oa]|'
                                r'fundad[oa]|inaugurad[oa])\b[^.!?]{0,75}\b(?:after|before|dopo|prima|después|antes)\b', re.I)
_ENTITY_TYPES = frozenset(('school', 'scuola', 'escuela', 'museum', 'museo', 'institute', 'istituto', 'instituto'))
_FICTIONAL_SUBJECT = re.compile(
    r"\b(?:is (?:an? |the )?(?:[a-z0-9-]+ ){0,5}(?:film|novel|television series|video game)|"
    r"e un(?:a)? (?:[a-z0-9-]+ ){0,4}(?:film|romanzo|serie televisiva|videogioco)|"
    r"es (?:una?|la) (?:[a-z0-9-]+ ){0,4}(?:pelicula|novela|serie de television|videojuego))\b")
_UNNAMED_ACTOR = re.compile(r'^(?:(?:in|nel|en) \d{4},? )?(?:he|she|fu|fue)\b', re.I)
_ABBREVIATION = re.compile(r"(?<!\w)(?:[ap]\.[mM]\.|St\.|[A-Z]\.)(?=\s+[^\W\d_])")
_PERSON_TITLE = re.compile(r"[^\W\d_]+(?:[ ’'-][^\W\d_]+){1,5}")


def _vocabulary(text):
    from .web_search import _plain, _terms

    symbols = {_plain(match[0]) for match in _UNDERSCORE.finditer(text)}
    return _terms(_UNDERSCORE.sub(' ', text)) | symbols


def _official_documents(query, language):
    """Resolve project manuals before sending a query to the external index."""
    words = query.split()
    terms = _vocabulary(query)
    if 'python' in terms:
        if 'requests' in terms and language == 'en':
            yield 'https://requests.readthedocs.io/en/latest/user/quickstart/', {'python'}, 'Requests'
        code_language = 'es/' if language == 'es' else 'fr/' if language == 'fr' else ''
        if language in ('en', 'es', 'fr'):
            modules = dict.fromkeys(word.casefold() for word in words if word.casefold() in stdlib_module_names
                                    and not word.startswith('_'))
            for module in list(modules)[:2]:
                yield f'https://docs.python.org/{code_language}3/library/{module}.html', {'python'}, module
    if language == 'en':
        lowered = [word.casefold() for word in words]
        if 'cargo' in lowered and 'rust' in terms:
            command = next(iter(lowered[lowered.index('cargo') + 1:]), '')
            if _SHORT_COMMAND.fullmatch(command) and command not in _REQUEST_WORDS:
                yield f'https://doc.rust-lang.org/cargo/commands/cargo-{command}.html', {'rust'}, f'cargo {command}'
        if 'golang' in lowered or 'go' in lowered:
            name = 'golang' if 'golang' in lowered else 'go'
            package = list(takewhile(lambda word: word == word.lower() and _SHORT_COMMAND.fullmatch(word)
                                     and word not in _REQUEST_WORDS, words[lowered.index(name) + 1:]))[:2]
            if package:
                yield 'https://pkg.go.dev/' + '/'.join(package), {name}, 'Go ' + '/'.join(package)
    if 'sqlite' in terms:
        yield 'https://sqlite.org/docs.html', {'sqlite'}, 'SQLite'


def _safe_address(value):
    address = ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    return address.version == 4 or (address in _PUBLIC_V6 and not any(address in prefix for prefix in _V6_TRANSITION))


def _remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError('Page deadline exceeded')
    return min(seconds, 2.5)


def _open_public_socket(host, deadline, cancelled, allowed):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or not all(_safe_address(item[4][0]) for item in addresses):
        raise ValueError('Page address is not public')
    for family, kind, proto, _, address in addresses[:2]:
        check_cancelled(cancelled)
        if not allowed():
            raise ValueError('Search permission revoked')
        connected = socket.socket(family, kind, proto)
        try:
            connected.settimeout(_remaining(deadline))
            connected.connect(address)
            return connected
        except OSError:
            connected.close()
    raise OSError('Page connection unavailable')


def read_public_page(url, deadline, cancelled, allowed, tls):
    """Pinned TLS connection. Every redirect undergoes the same public-IP check."""
    from .public_references import USER_AGENT
    from .web_search import public_url

    for _ in range(3):
        check_cancelled(cancelled)
        if not allowed() or not public_url(url):
            return None
        target = urlsplit(url)
        path = urlunsplit(('', '', quote(target.path or '/', safe="/%:@!$&'()*+,;=-._~"),
                           quote(target.query, safe="/%=:@!$&'()*+,;-._~?"), ''))
        connection = HTTPSConnection(target.hostname, timeout=_remaining(deadline), context=tls)
        try:
            raw = _open_public_socket(target.hostname, deadline, cancelled, allowed)
            try:
                raw.settimeout(_remaining(deadline))
                page_socket = tls.wrap_socket(raw, server_hostname=target.hostname)
                connection.sock = page_socket
            except BaseException:
                raw.close()
                raise
            check_cancelled(cancelled)
            if not allowed():
                return None
            connection.request('GET', path, headers={'User-Agent': USER_AGENT,
                'Accept': 'text/html, text/plain', 'Accept-Encoding': 'identity'})
            with connection.getresponse() as reply:
                if reply.status in (301, 302, 303, 307, 308):
                    target_url = reply.getheader('Location')
                    if not target_url:
                        return None
                    url = urljoin(url, target_url)
                    continue
                content_type = reply.headers.get_content_type()
                if reply.status != 200 or content_type not in ('text/html', 'text/plain'):
                    return None
                if reply.getheader('Content-Encoding', 'identity').lower() != 'identity':
                    return None
                body = bytearray()
                while len(body) < _BODY_LIMIT:
                    check_cancelled(cancelled)
                    if not allowed():
                        return None
                    page_socket.settimeout(_remaining(deadline))
                    chunk = reply.read1(min(16384, _BODY_LIMIT - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                try:
                    charset = reply.headers.get_content_charset() or 'utf-8'
                    decoded = body.decode(charset, errors='replace')
                except LookupError:
                    decoded = body.decode('utf-8', errors='replace')
                return url, content_type, decoded
        finally:
            connection.close()
    return None


class _Page(ArticleParagraphs):
    _SKIP = ArticleParagraphs._SKIP | {'header', 'footer', 'aside', 'form'}

    def __init__(self):
        super().__init__()
        self.published = None
        self.language = None
        self.sections = []
        self.links = []
        self._headings = {}
        self._heading = None
        self._link = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'html':
            self.language = (values.get('lang') or '').lower().split('-', 1)[0] or None
        if tag == 'meta':
            label = (values.get('property') or values.get('name') or '').lower()
            if label in ('article:published_time', 'datepublished', 'publication_date', 'citation_publication_date'):
                try:
                    self.published = date.fromisoformat((values.get('content') or '')[:10]).isoformat()
                except ValueError:
                    pass
        if not self._blocked:
            if tag in _HEADING_LEVEL:
                self._heading = (tag, [])
            elif tag == 'a' and values.get('href'):
                self._link = (values['href'], [])
        if tag == 'blockquote' and 'abstract' in (values.get('class') or '').split():
            self._headings[7] = 'Abstract'
            tag = 'p'
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self._heading and self._heading[0] == tag:
            level = _HEADING_LEVEL[tag]
            heading = ' '.join(''.join(self._heading[1]).split())
            self._headings = {key: value for key, value in self._headings.items() if key < level}
            if heading:
                self._headings[level] = heading
            self._heading = None
        if tag == 'dd':
            self._headings.pop(_HEADING_LEVEL['dt'], None)
        if tag == 'a' and self._link:
            url, text = self._link
            self.links.append((url, ''.join(text)))
            self._link = None
        before = len(self.paragraphs)
        super().handle_endtag('p' if tag == 'blockquote' else tag)
        if len(self.paragraphs) != before:
            self.sections.append((' '.join(self._headings.values()), self.paragraphs[-1]))
        if tag == 'blockquote' and self._headings.get(7) == 'Abstract':
            self._headings.pop(7)

    def handle_data(self, data):
        super().handle_data(data)
        if not self._blocked:
            if self._heading:
                self._heading[1].append(data)
            if self._link:
                self._link[1].append(data)


def _focus_terms(value):
    # Recognize a few grammatical variants without treating adjacent subjects
    # or different API symbols as interchangeable.
    return {_ACTION_VARIANTS.get(word, word) for word in _vocabulary(value)}


_ACTION_VARIANTS = {**dict.fromkeys(('creacion', 'crea', 'crean', 'creado', 'creada', 'creados', 'creadas'), 'crear'),
                    **dict.fromkeys(('origine', 'origini', 'origins', 'origen', 'fondazione', 'founded',
                                     'fondato', 'fondata', 'fundacion', 'fundado', 'fundada'), 'origin'),
                    **dict.fromkeys(('inaugurazione', 'inaugurato', 'inaugurata', 'inauguro',
                                     'inauguracion', 'inaugurado', 'inaugurada', 'inaugurated',
                                     'opened', 'apertura', 'abrio', 'aprio'), 'inauguration'),
                    'virtuales': 'virtual', 'vapor': 'vapour'}


def _index_links(body, url, query):
    from .web_search import public_url

    page = _Page()
    page.feed(body)
    page.close()
    focus = _focus_terms(query) - _REQUEST_WORDS - {'sqlite'}
    ranked = []
    for path, label in page.links:
        link = urljoin(url, path)
        hits = focus & _focus_terms(label)
        if (public_url(link) and link != url and urlsplit(link).hostname == urlsplit(url).hostname
                and len(hits) >= min(2, len(focus)) and hits):
            ranked.append((len(hits), link, label))
    links = {}
    for _, link, label in sorted(ranked, key=lambda item: -item[0]):
        links.setdefault(link, label)
    return list(links.items())[:2]


def _scoped_passage(paragraphs, supports, excluded, *, compact_definition=False):
    from .contribution_review import statements
    from .web_search import _plain, _safe_text

    pair = None
    for _, paragraph in paragraphs:
        previous = ''
        protected = _ABBREVIATION.sub(lambda match: match[0].replace('.', '\u2024'), paragraph.replace('\u200b', ''))
        protected = re.sub(r'(?<=\.)\((?=[A-Z])', ' (', protected)
        for sentence in statements(protected, limit=30):
            sentence = _safe_text(sentence.replace('\u2024', '.'), 425)
            if compact_definition and sentence and not sentence.endswith(('.', '?', '!')):
                # A colon can introduce a code example after a complete definition.
                sentence = sentence.rstrip(':').rstrip() + '.'
            if (not sentence.endswith('.') or len(sentence) > 420 or sentence.endswith('...')
                    or _plain(sentence) in excluded or _ANECDOTE.search(sentence)):
                previous = ''
                continue
            if len(sentence) >= 35 and supports(sentence):
                return True, sentence
            if pair is None and previous:
                joined = previous + ' ' + sentence
                if 35 <= len(joined) <= 420 and _plain(joined) not in excluded and supports(joined):
                    pair = (False, joined)
            previous = sentence
    return pair


def _read_passages(decoded, content_type, query, language, *, official_title='', project_words=(),
                   abstract_only=False, exclude=(), primacy=None, fact=None, science=None, technical=None):
    from .contribution_review import statements
    from .web_search import _safe_text, _plain

    page = _Page()
    if content_type == 'text/html':
        page.feed(decoded)
        page.close()
        if language and page.language and language != page.language:
            return None
        paragraphs = page.sections
    elif technical:
        # RFC text wraps each paragraph across physical lines.
        paragraphs = [('', ' '.join(block.split())) for block in re.split(r'\n\s*\n', decoded, maxsplit=1000)]
    else:
        paragraphs = [('', line) for line in decoded.splitlines()[:1000]]
    if technical:
        matching = [(heading, text) for heading, text in paragraphs if technical.matches_section(heading)]
        match = _scoped_passage(matching, technical.supports, exclude,
                                compact_definition=technical.compact_definition)
        if not match and not matching and technical.definition:
            match = _scoped_passage(paragraphs, lambda text: bool(
                re.match(technical.definition, _plain(text)) and technical.supports(text)), exclude)
        if not match:
            return None
        direct, excerpt = match
        if technical.introduction and not re.search(technical.introduction, _plain(excerpt)):
            lead = _scoped_passage(matching, lambda text: bool(
                re.search(technical.introduction, _plain(text))), exclude)
            if lead and len(lead[1]) + len(excerpt) + 5 <= 500:
                excerpt = lead[1] + ' […] ' + excerpt
        return (direct,), excerpt, page.published
    if science:
        match = _scoped_passage(paragraphs, science.supports, exclude)
        return ((match[0],), match[1], page.published) if match else None
    if primacy and any(_FICTIONAL_SUBJECT.search(_plain(text)) for _, text in paragraphs[:3]):
        return None
    campaign = campaign_scope(query, language) if fact is None and primacy is None else None
    required = _focus_terms(campaign[0] if campaign else query) - _REQUEST_WORDS - set(project_words)
    if not required:
        return None
    # A result title from the index may be stale or describe the wrong page.
    # Only a known official document may lend its topic to a body sentence.
    official_terms = _focus_terms(official_title)
    detail = required - official_terms
    symbols = {word.casefold() for word in query.split() if _API_SYMBOL.fullmatch(word)}
    required_relation = (_CAUSAL_PASSAGE if _CAUSAL_QUESTION.search(query)
                         else _DATE_IN_PASSAGE if _DATE_QUESTION.search(query) else None)
    historical_fact = 'origin' in required or required_relation is _DATE_IN_PASSAGE
    if historical_fact and official_terms and official_terms <= required:
        required -= _ENTITY_TYPES - official_terms
        detail = required - official_terms
    matches = []
    biography_lead = ''
    surname = ''
    if (primacy and official_title and _PERSON_TITLE.fullmatch(official_title)
            and paragraphs and not paragraphs[0][0]):
        opening = _plain(paragraphs[0][1])
        surname = _plain(official_title.rsplit(' ', 1)[-1])
        if surname in re.findall(r'[^\W\d_]+', opening[:120]) and re.search(r'\([^)]*\b\d{4}\b', opening[:220]):
            biography_lead = official_title
    for position, (heading, paragraph) in enumerate(paragraphs):
        if abstract_only and 'abstract' not in heading.casefold():
            continue
        section_terms = _focus_terms(heading)
        lead = bool(re.search(r'\b(?:description|overview|descrizione|descripci[oó]n)\b', heading, re.I))
        symbol_definition = bool(official_title and symbols & section_terms and detail <= section_terms)
        protected = _ABBREVIATION.sub(lambda match: match[0].replace('.', '\u2024'), paragraph.replace('\u200b', ''))
        for sentence in statements(protected, limit=30):
            sentence = sentence.replace('\u2024', '.')
            if len(sentence) > (420 if fact else 320):
                continue
            sentence = _safe_text(sentence, 425)
            if (not 35 <= len(sentence) or not sentence.endswith(('.', '!', '。', '！'))
                    or sentence.endswith(('...', '…')) or _ANECDOTE.search(sentence) or _VERSION_NOTE.search(sentence)):
                continue
            if _plain(sentence) in exclude:
                continue
            if campaign and not campaign[1].match(sentence):
                continue
            if not fact and required_relation is not None and not required_relation.search(sentence):
                continue
            if historical_fact and _RELATIVE_FOUNDING.search(sentence):
                continue
            if language in _BODY_LANGUAGE and language != 'en':
                words = set(re.findall(r'[^\W\d_]+', sentence.casefold()))
                if len(words & _BODY_LANGUAGE['en']) >= max(2, len(words & _BODY_LANGUAGE[language]) + 2):
                    continue
            body = _focus_terms(sentence)
            if official_terms and historical_fact:
                comparison = _COMPARATIVE_MENTION.search(sentence)
                if comparison and official_terms & _focus_terms(sentence[comparison.end():]) and not (
                        official_terms & _focus_terms(sentence[:comparison.start()])):
                    continue
            if fact is not None:
                if not fact.supports(sentence, article_title=official_title, opening=not heading):
                    continue
            elif primacy is not None:
                if not primacy.supports(sentence, article_topic=official_title if not heading else ''):
                    continue
                if _UNNAMED_ACTOR.match(sentence):
                    context, found, _ = paragraph.partition(sentence)
                    named_here = bool(official_title and found and _plain(official_title) in _plain(context))
                    continued_lead = position == 1 and not context.strip() and biography_lead
                    lead_sentence = (position == 1 and found and biography_lead
                                     and re.fullmatch(r'(?:in \d{4},? )?' + re.escape(surname)
                                                      + r' [^.!?]+\.', _plain(context).strip()))
                    if (heading or not (named_here or continued_lead or lead_sentence)
                            or len(sentence) + len(official_title) > 315):
                        continue
                    sentence = f'{official_title} — {sentence}'
            elif official_title:
                if not required <= body | official_terms | section_terms:
                    continue
                if not (symbol_definition or (detail or required) & body or (campaign and not detail)
                        or (lead and not detail and required <= section_terms)):
                    continue
            elif not required <= body:
                continue
            if 'crear' in detail and 'crear' not in body:
                continue
            # Prefer a passage that explains the feature or answers the query
            # directly. Repeated query words alone do not improve its rank.
            if _plain(sentence).rstrip('.!') == _plain(query):
                continue
            identifiers = list(_API_SYMBOL.finditer(sentence[:120])) if symbols else []
            first_symbol = next((item for item in identifiers if sentence[item.end():].startswith('(')),
                                identifiers[0] if identifiers else None)
            defines_symbol = first_symbol is not None and first_symbol[0].casefold() in symbols
            scoped_overview = bool(official_title) and lead and not detail
            topic_heading = bool(detail and detail <= section_terms)
            overview_for_origin = 'origin' in required and bool(official_title) and not heading
            score = (bool(fact and not heading), defines_symbol, symbol_definition, scoped_overview, overview_for_origin, topic_heading,
                     0 if scoped_overview or symbol_definition else len(detail & body),
                     0 if scoped_overview or symbol_definition else len(required & body))
            matches.append((score, sentence, page.published))
    if not matches and fact and fact.kind in ('connection', 'countries', 'city'):
        def supports_continuation(passage):
            pair = statements(passage, limit=2)
            return len(pair) == 2 and fact.supports_place_continuation(*pair, official_title)

        if match := _scoped_passage(paragraphs, supports_continuation, exclude):
            return (False,), match[1], page.published
    if campaign and matches:
        ranked = sorted(matches, key=lambda row: row[0], reverse=True)
        score, first, published = ranked[0]
        engagement = _plain(campaign[1].match(first)['engagement'])
        for _, passage, _ in ranked[1:]:
            candidate = _plain(campaign[1].match(passage)['engagement'])
            if candidate != engagement and len(first) + len(passage) + 5 <= 420:
                return score, first + ' […] ' + passage, published
        return score, first, published
    return max(matches, key=lambda row: row[0], default=None)


def _encyclopedia_pages(session, query, language, stop, allowed, deadline, *, fact=None,
                        seen=None, refine=False):
    """Use exact Wikipedia revisions and inspect their bodies on device."""
    import requests
    from .contribution_review import statements
    from .public_references import LANGUAGES, USER_AGENT
    from .web_search import encyclopedic_results

    if language not in LANGUAGES:
        return
    documents = encyclopedic_results(session, query, language, stop, allowed)
    seen = set() if seen is None else seen
    documents = [row for row in documents if row['url'] not in seen]
    if fact:
        documents = [row for row in documents if fact.accepts_document_title(row.get('title') or '')]

        def relevance(row):
            title = row.get('title') or ''
            extract = row.get('snippet')
            mentions_relation = refine and any(fact.supports(text, article_title=title, opening=True)
                                               for text in statements(extract, limit=6))
            terms = set(fact.words) & _vocabulary(title)
            return mentions_relation, len(terms), '(' not in title

        documents.sort(key=relevance, reverse=True)
    failure = None
    for row in documents[:3]:
        check_cancelled(stop)
        if time.monotonic() >= deadline or not allowed():
            return
        seen.add(row['url'])
        revision = urlsplit(row['url']).query.removeprefix('oldid=')
        endpoint = f'https://{language}.wikipedia.org/w/api.php'
        params = {'action': 'parse', 'oldid': revision, 'prop': 'text', 'disabletoc': 1,
                  'format': 'json', 'formatversion': 2}
        try:
            try:
                payload = request_json(session, endpoint, stop, allowed, params=params,
                                       headers={'User-Agent': USER_AGENT}, limit=_BODY_LIMIT)
            except ValueError:
                if time.monotonic() >= deadline or not allowed():
                    raise
                # An oversized page may still have a readable introduction
                # at the same revision, including for unclassified questions.
                payload = request_json(session, endpoint, stop, allowed, params={**params, 'section': 0},
                                       headers={'User-Agent': USER_AGENT}, limit=_BODY_LIMIT)
        except (requests.RequestException, ProviderError, OSError, ValueError) as error:
            failure = error
            if isinstance(error, ProviderError) and error.status == 429:
                break
            continue
        raw = (payload or {}).get('parse')
        if isinstance(raw, dict) and str(raw.get('revid')) == revision and isinstance(raw.get('text'), str):
            yield (row['url'], 'text/html', raw['text']), raw.get('title')
    if failure is not None:
        raise failure


def _abstract_body(abstract):
    paragraphs = re.sub(r'</?(?:[\w-]+:)?(?:p|sec)\b[^>]*>', '\n', abstract[:18000], flags=re.I)
    return unescape(re.sub(r'<[^>]{1,250}>', ' ', paragraphs))


def _publication_abstracts(session, query, stop, allowed):
    """Read the publication abstract from the research catalog, not index snippets."""
    from .public_references import USER_AGENT

    data = request_json(session, EUROPE_PMC, stop, allowed, params={
        'query': query, 'pageSize': 5, 'resultType': 'core', 'format': 'json',
    }, headers={'User-Agent': USER_AGENT}, limit=192 * 1024)
    rows = (data or {}).get('resultList')
    rows = rows.get('result') if isinstance(rows, dict) else None
    for row in rows[:5] if isinstance(rows, list) else ():
        if not isinstance(row, dict):
            continue
        origin, identifier, abstract = (row.get(key) for key in ('source', 'id', 'abstractText'))
        if (origin not in ('MED', 'PMC', 'PPR') or not isinstance(identifier, str)
                or not re.fullmatch(r'(?:PMC|PPR)?[0-9]{1,12}', identifier)
                or not isinstance(abstract, str) or not abstract):
            continue
        yield (f'https://europepmc.org/article/{origin}/{identifier}', 'text/plain', _abstract_body(abstract)), row.get('title')


def _crossref_abstracts(session, query, stop, allowed):
    """Read abstracts deposited by publishers with Crossref."""
    from .public_references import USER_AGENT
    from .web_search import _plain

    payload = request_json(session, CROSSREF_WORKS, stop, allowed, params={
        'query.bibliographic': query, 'filter': 'has-abstract:true',
        'rows': 5, 'select': 'DOI,title,abstract',
    }, headers={'User-Agent': USER_AGENT}, limit=192 * 1024)
    message = (payload or {}).get('message')
    rows = message.get('items') if isinstance(message, dict) else None
    works = {}
    for row in rows[:5] if isinstance(rows, list) else ():
        if not isinstance(row, dict):
            continue
        doi, titles, abstract = (row.get(key) for key in ('DOI', 'title', 'abstract'))
        if (not isinstance(doi, str) or not re.fullmatch(r'10\.\d{4,9}/[-A-Za-z0-9._();/+]{1,180}', doi)
                or not isinstance(titles, list) or not titles or not isinstance(titles[0], str)
                or not isinstance(abstract, str) or not abstract):
            continue
        title = titles[0]
        numbered = re.fullmatch(r'(.+)/v([0-9]{1,5})', doi, flags=re.I)
        family, edition = numbered.groups() if numbered else (doi, '0')
        key = (family.casefold(), _plain(title))
        version = int(edition)
        if key not in works or version > works[key][0]:
            works[key] = version, doi, title, abstract
    for _, doi, title, abstract in works.values():
        link = 'https://doi.org/' + quote(doi, safe='/-._')
        yield (link, 'text/plain', _abstract_body(abstract)), title


class SearxResearch:
    name = 'Ricerca web generale'

    def __init__(self, *, use_companion=True):
        self._use_companion = use_companion
        self._next_mwmbl_request = 0.0

    def fetch(self, query, language, fresh, cancelled, allowed, *, previous=(), exclude_adaptations=False):
        return reference_io(lambda stop: self._fetch(query, language, fresh, stop, allowed, previous, exclude_adaptations),
                            cancelled, allowed, seconds=11)

    def _fetch(self, query, language, fresh, cancelled, allowed, previous, exclude_adaptations=False):
        import certifi
        import requests
        from .public_references import LANGUAGES, USER_AGENT
        from .web_search import _plain, _safe_text, public_url, public_web_question, recent_publication

        deadline = time.monotonic() + 10.5
        params = {'q': query, 'format': 'json', 'language': language if language in LANGUAGES else 'all'}
        scholarly = bool(_SCHOLARLY.search(query))
        documentation = bool(_DOCUMENTATION.search(query))
        primacy = None if fresh or scholarly or documentation else primacy_question(query, language)
        fact = None if primacy or fresh or scholarly or documentation else fact_question(query, language)
        science = None if primacy or fact or fresh or scholarly or documentation else science_question(query, language)
        technical = technical_reference(query) if not (fresh or scholarly or primacy or fact or science) else None
        campaign = campaign_scope(query, language) if not (fresh or scholarly or technical) else None
        if scholarly:
            params['categories'] = 'science,general'
        elif fresh:
            # General engines can discover articles as well. Validate the
            # publication date of each page locally before choosing a result.
            params['categories'] = 'news,general'
        rephrased = ' '.join(word for word in query.split() if _focus_terms(word) - _REQUEST_WORDS)
        variants = tuple(dict.fromkeys((rephrased, query))) if rephrased else (query,)
        if primacy:
            from .web_search import search_query
            alternatives = (value for value in primacy.discovery_queries()
                            if search_query(value, allow_symbols=True) == value)
            variants = tuple(dict.fromkeys((*alternatives, query)))[:3]
        elif fact or science:
            from .web_search import search_query
            topics = fact.discovery_queries() if fact else science.topics
            alternatives = (value for value in topics
                            if search_query(value, min_length=2) == value)
            variants = tuple(dict.fromkeys((*alternatives, *variants)))[:3]
        elif campaign:
            variants = tuple(dict.fromkeys((campaign[0], *variants)))
        seen = set()
        seen_revisions = set()
        excluded = {_plain(item) for item in previous}
        tls = ssl.create_default_context(cafile=certifi.where())

        def read(url, until=deadline, *, seconds=2.2):
            check_cancelled(cancelled)
            if url in seen or not allowed() or time.monotonic() >= until:
                return None
            seen.add(url)
            try:
                return read_public_page(url, min(until, time.monotonic() + seconds), cancelled, allowed, tls)
            except (HTTPException, OSError, ValueError, ProviderError):
                return None

        def evidence(page, title, *, official_title='', project_words=(), from_catalog=False, technical_scope=None):
            url, content_type, body = page
            target = urlsplit(url)
            host = target.hostname
            if exclude_adaptations and (adaptation_title(title)
                                        or adaptation_title(unquote(target.path).replace('_', ' '))):
                return None
            if fact and host.endswith('.wikipedia.org') and target.path.startswith('/wiki/'):
                article = unquote(target.path.removeprefix('/wiki/')).replace('_', ' ')
                if not fact.accepts_document_title(article):
                    return None
            if scholarly and host not in _SCHOLARLY_HOSTS and not (from_catalog and host == 'doi.org'):
                return None
            if host == 'support.mozilla.org' and _vocabulary(query) & {'mozilla', 'firefox'}:
                official_title = 'Firefox'
                project_words = {'mozilla'}
            match = _read_passages(body, content_type, query, technical_scope.language if technical_scope else language,
                                   official_title=official_title,
                                   project_words=project_words,
                                   abstract_only=scholarly and host in ('arxiv.org', 'export.arxiv.org'),
                                   exclude=excluded, primacy=primacy, fact=fact, science=science, technical=technical_scope)
            if match is None:
                return None
            score, text, published = match
            if fresh and not recent_publication(published, query):
                return None
            return score, {'url': url, 'title': title, 'snippet': text,
                           'publisher': host, 'date': published, 'page_read': True,
                           **({'fact_relation': (fact.kind if fact else 'science' if science else
                                                 'technical' if technical_scope else 'campaign')}
                              if fact or science or technical_scope or campaign else {})}

        if technical:
            opened = False
            for source in (technical, *technical.alternatives):
                page = read(source.url, seconds=3.5)
                if not page:
                    continue
                target, final = urlsplit(source.url), urlsplit(page[0])
                if (final.hostname != target.hostname
                        or final.path.rstrip('/').rsplit('/', 1)[-1] != target.path.rstrip('/').rsplit('/', 1)[-1]):
                    continue
                opened = True
                if match := evidence(page, source.title, technical_scope=source):
                    return {'status': 'obtained', 'results': [match[1]]}
            return {'status': 'insufficient_evidence' if opened else 'unavailable', 'results': []}

        facets = historical_facets(primacy) if primacy else ()
        record = documented_record(primacy) if primacy and not facets else None
        if facets or record:
            scope = facets or (record,)
            verified = 0
            results = []
            documents = {}
            with requests.Session() as session:
                session.trust_env = False
                for facet in scope:
                    for source in facet.sources:
                        check_cancelled(cancelled)
                        if not allowed() or time.monotonic() >= deadline:
                            break
                        if source.url not in documents:
                            documents[source.url] = self._read_scope_source(
                                session, source.url, read, deadline, cancelled, allowed)
                        opened = documents[source.url]
                        if opened is None:
                            continue
                        url, paragraphs = opened
                        if not source_passage(paragraphs, source.markers, adjacent=source.adjacent):
                            continue
                        verified += 1
                        answer = localized_statement(facet, language)
                        if _plain(answer) not in excluded:
                            results.append({'url': url, 'title': source.title, 'snippet': answer,
                                            'publisher': urlsplit(url).hostname, 'facet': facet.key,
                                            'page_read': True})
                        break
            if results:
                return {'status': 'obtained', 'results': results,
                        'coverage': 'full_scope' if verified == len(scope) else 'partial_scope'}
            if facets or verified:
                return {'status': 'no_new_evidence' if verified else 'insufficient_evidence', 'results': []}

        if not scholarly and not fresh:
            if science:
                for title, url in science.official:
                    page = read(url)
                    if page and urlsplit(page[0]).hostname == urlsplit(url).hostname and (match := evidence(page, title)):
                        return {'status': 'obtained', 'results': [match[1]]}
            for url, project, title in _official_documents(query, language):
                page = read(url)
                if not page or urlsplit(page[0]).hostname != urlsplit(url).hostname:
                    continue
                if url == 'https://sqlite.org/docs.html':
                    for link, label in _index_links(page[2], page[0], query):
                        document = read(link)
                        if document and urlsplit(document[0]).hostname == 'sqlite.org':
                            match = evidence(document, label, official_title=label, project_words=project)
                            if match:
                                return {'status': 'obtained', 'results': [match[1]]}
                else:
                    match = evidence(page, title, official_title=title, project_words=project)
                    if match:
                        return {'status': 'obtained', 'results': [match[1]]}

        ranked = []
        indexed_pages = 0
        search_partial = False
        search_completed = False
        found_candidates = False
        wiki_limited = False
        encyclopedia = not (fresh or scholarly or documentation)
        encyclopedia_first = encyclopedia and (fact or science or primacy or public_web_question(query, None) or bool(
            re.match(r'^[A-Z][\w-]+ [A-Z][\w-]+\b', query)))
        scope_timeout = deadline - 2.5 if encyclopedia and not encyclopedia_first else deadline
        transport_errors = (requests.RequestException, ProviderError, OSError, ValueError)

        def encyclopedia_results(session, until, variant=variants[0], *, refine=False):
            nonlocal search_completed, search_partial, found_candidates, wiki_limited
            found = []
            try:
                for page, title in _encyclopedia_pages(session, variant, language, cancelled, allowed, until,
                                                       fact=fact, seen=seen_revisions, refine=refine):
                    found_candidates = True
                    title = _safe_text(title, 160)
                    if title and (match := evidence(page, title, official_title=title)):
                        found.append(match)
                    if len(found) >= (1 if fact or science else 2):
                        break
            except transport_errors as error:
                search_partial = True
                wiki_limited = isinstance(error, ProviderError) and error.status == 429
            else:
                search_completed = True
            return [row for _, row in sorted(found, key=lambda item: item[0], reverse=True)]

        def read_candidates(rows, until, page_limit):
            nonlocal indexed_pages, found_candidates
            candidates = [row for row in rows[:12] if isinstance(row, dict) and public_url(row.get('url'))
                          and (not scholarly or urlsplit(row['url']).hostname in _SCHOLARLY_HOSTS)
                          and (not documentation or not _DISCUSSION_URL.search(row['url']))]
            found_candidates |= bool(candidates)
            for row in candidates:
                check_cancelled(cancelled)
                if not allowed() or time.monotonic() >= until or indexed_pages >= page_limit:
                    break
                url = row['url']
                if scholarly and urlsplit(url).hostname == 'arxiv.org':
                    url = url.replace('https://arxiv.org/html/', 'https://arxiv.org/abs/', 1)
                if url in seen:
                    continue
                title = _safe_text(unescape(row['title']), 160) if isinstance(row.get('title'), str) else ''
                if not title:
                    continue
                indexed_pages += 1
                page = read(url, until)
                if page and not (documentation and _DISCUSSION_URL.search(page[0])):
                    match = evidence(page, title)
                    if match:
                        ranked.append(match)
                if len(ranked) >= 2:
                    break
            return [row for _, row in sorted(ranked, key=lambda item: item[0], reverse=True)]

        with requests.Session() as session:
            session.trust_env = False
            if scholarly and language == 'en' and not fresh:
                for catalog in (_publication_abstracts, _crossref_abstracts):
                    check_cancelled(cancelled)
                    if not allowed() or time.monotonic() >= deadline:
                        break
                    try:
                        for page, title in catalog(session, variants[0], cancelled, allowed):
                            check_cancelled(cancelled)
                            title = _safe_text(title, 160)
                            if title and (match := evidence(page, title, from_catalog=True)):
                                ranked.append(match)
                            if len(ranked) == 2:
                                break
                    except transport_errors:
                        search_partial = True
                    else:
                        search_completed = True
                    if ranked:
                        return {'status': 'obtained', 'results': [row for _, row in ranked]}
            if encyclopedia_first:
                until = min(deadline, time.monotonic() + (5 if primacy or fact or science else 3.5))
                for attempt, variant in enumerate(variants[:2]):
                    check_cancelled(cancelled)
                    if wiki_limited or time.monotonic() >= until or not allowed():
                        break
                    if results := encyclopedia_results(session, until, variant, refine=bool(attempt)):
                        return {'status': 'obtained', 'results': results}
            companion_answered = False
            for variant_index, variant in enumerate(variants if self._use_companion else ()):
                check_cancelled(cancelled)
                if not allowed() or time.monotonic() >= scope_timeout:
                    break
                try:
                    payload = request_json(session, COMPANION_URL, cancelled, allowed, params={**params, 'q': variant},
                                           headers={'User-Agent': USER_AGENT}, limit=192 * 1024)
                except transport_errors:
                    break
                rows = (payload or {}).get('results')
                if not isinstance(rows, list):
                    break
                companion_answered = True
                search_completed = True
                if isinstance(payload.get('unresponsive_engines'), list) and payload['unresponsive_engines']:
                    search_partial = True
                page_limit = min(5, 5 - (len(variants) - 1 - variant_index))
                if results := read_candidates(rows, scope_timeout, page_limit):
                    return {'status': 'obtained', 'results': results}
            if encyclopedia and not encyclopedia_first and allowed() and time.monotonic() < deadline:
                if results := encyclopedia_results(session, deadline):
                    return {'status': 'obtained', 'results': results}
            if not scholarly and not (fresh and companion_answered) and allowed() and time.monotonic() < deadline:
                # A responsive companion may return no usable evidence.
                # The public index can offer another route to the same fact.
                direct_query = variants[1] if (encyclopedia_first or companion_answered) and len(variants) > 1 else variants[0]
                try:
                    rows = self._search_mwmbl(session, direct_query, cancelled, allowed)
                    if rows is not None:
                        search_completed = True
                        if results := read_candidates(rows, deadline, indexed_pages + 3):
                            return {'status': 'obtained', 'results': results}
                except transport_errors:
                    search_partial = True

        status = ('index_unavailable' if not search_completed else 'search_partial' if search_partial else
                  'insufficient_evidence' if found_candidates else 'not_found')
        return {'status': status, 'results': []}

    def _search_mwmbl(self, session, query, stop, allowed):
        from .public_references import USER_AGENT

        check_cancelled(stop)
        if not allowed() or time.monotonic() < self._next_mwmbl_request:
            return None
        try:
            data = request_json(session, MWMBL_SEARCH, stop, allowed, params={'q': query},
                                headers={'User-Agent': USER_AGENT}, limit=192 * 1024)
        except ProviderError as error:
            if error.status == 429:
                self._next_mwmbl_request = time.monotonic() + 60
                logging.info('[PublicReference] index=mwmbl status=rate_limited')
            raise
        finally:
            self._next_mwmbl_request = max(self._next_mwmbl_request, time.monotonic() + 1)
        if data is None:
            return None
        rows = data.get('results')
        if not isinstance(rows, list):
            raise ValueError('Invalid Mwmbl results')
        logging.info('[PublicReference] index=mwmbl status=obtained candidates=%s', len(rows))
        return rows

    @staticmethod
    def _read_scope_source(session, url, read, deadline, stop, allowed):
        import requests
        from .public_references import LANGUAGES, USER_AGENT
        from .web_search import _plain

        parsed = urlsplit(url)
        wiki_language = parsed.hostname.split('.')[0] if parsed.hostname.endswith('.wikipedia.org') else None
        if wiki_language in LANGUAGES:
            title = unquote(parsed.path.removeprefix('/wiki/')).replace('_', ' ')
            try:
                payload = request_json(session, f'https://{parsed.hostname}/w/api.php', stop, allowed,
                    params={'action': 'parse', 'page': title, 'prop': 'text|revid', 'format': 'json',
                            'formatversion': 2, 'disabletoc': 1}, headers={'User-Agent': USER_AGENT},
                    limit=_BODY_LIMIT)
            except (requests.RequestException, ProviderError, OSError, ValueError):
                return None
            page = (payload or {}).get('parse')
            revision = page.get('revid') if isinstance(page, dict) else None
            if (type(revision) is not int or revision <= 0 or not isinstance(page.get('title'), str)
                    or _plain(page['title']) != _plain(title) or not isinstance(page.get('text'), str)):
                return None
            body = page['text']
            url += '?oldid=' + str(revision)
        else:
            opened = read(url, min(deadline, time.monotonic() + 1.8))
            if not opened or opened[0] != url or opened[1] != 'text/html':
                return None
            body = opened[2]
        document = _Page()
        document.feed(body)
        document.close()
        return url, document.paragraphs
