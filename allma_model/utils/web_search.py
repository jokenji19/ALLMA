"""Public search providers, evidence ranking and local answer construction."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
import re
import time
import unicodedata
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from .bounded_io import reference_io
from .generation_control import GenerationCancelled, check_cancelled
from .online_transport import ProviderError, request_bytes, request_json

_HOST = re.compile(r'(?:[a-z][a-z0-9-]{0,62}\.)+[a-z][a-z0-9-]{1,62}', re.I)
_STOP = frozenset('il lo la i gli le un una di del della dello dei delle a al alla da dal dalla in nel nella con su sul sulla per tra fra e o che chi come cosa quale quali quando dove perché perche the a an of to and for on is are who what when where why about from'.split())
_FRESH_WORDS = frozenset('oggi attuale attuali recenti recente ultimi ultime ultimo ultima aggiornamenti aggiornamento ora adesso now current today latest recent notizie news'.split())
_TODAY = re.compile(r"\b(?:oggi|today|hoy|aujourd[’']hui|heute|hoje)\b", re.I)
_PUBLIC_WEB_QUESTION = re.compile(
    r"^(?:che cos[’']è|che cosa (?:è|sono|significa)|cos[’']è|come (?:si |funziona|funzionano)|"
    r"perch[eé]|qual(?:e|i)? (?:è|sono)|quand[oa] (?:[èe]|fu|avvenne|si svolse)|"
    r"(?:quali|ci sono|trova) (?:studi|articoli scientifici|fonti pubbliche)|(?:che cosa|cosa) [èe] successo|"
    r"dove (?:si |[èe] |sono )|chi (?:ha |fu |era |[èe] )|quanti |quante |"
    r"what (?:is|are|was|were|causes|happened)|how (?:do|does|did|many|much)|why (?:is|are|does|do|did)|"
    r"find (?:studies|scientific papers|public sources)|"
    r"when (?:was|were|did)|where (?:is|are|did)|who (?:is|was|wrote|invented|founded)|"
    r"qu[eé] (?:es|son|significa)|cu[aá]l(?:es)? (?:es|son)|c[oó]mo (?:funciona|se)|"
    r"cu[aá]ndo (?:se|fue)|qui[eé]n (?:es|fue|escribi[oó])|por qu[eé]|"
    r"qu[’']est-ce que|(?:comment|pourquoi|quand) (?:fonctionne|se|a|est)|"
    r"was (?:ist|sind|bedeutet)|wie (?:funktioniert|entsteht)|"
    r"o que (?:é|são|significa)|como (?:funciona|se)|por que)\b", re.I)
_XML_TYPES = ('application/rss+xml', 'application/atom+xml', 'application/xml', 'text/xml')


@dataclass(frozen=True)
class Feed:
    publisher: str
    url: str
    hosts: tuple
    topics: frozenset
    overview_terms: frozenset = frozenset()


FEEDS = (
    Feed('NASA', 'https://www.nasa.gov/news-release/feed/', ('www.nasa.gov','science.nasa.gov'),
         frozenset('nasa spazio space luna moon artemis marte mars orbita astronauti astronaut stazione iss'.split())),
    Feed('ESA', 'https://www.esa.int/rss/news.rss', ('www.esa.int',),
         frozenset('esa spazio space luna moon artemis marte mars orbita astronauti astronaut stazione iss satelliti satellite copernicus'.split())),
    Feed('Android Developers', 'https://developer.android.com/static/blog/atom.xml', ('developer.android.com',),
         frozenset('android kotlin compose sdk quail play camera androidstudio'.split())),
    Feed('Android Studio', 'https://androidstudio.googleblog.com/feeds/posts/default?alt=rss',
         ('androidstudio.googleblog.com',), frozenset({'studio'}), frozenset({'android', 'studio', 'androidstudio'})),
    Feed('GitHub Changelog', 'https://github.blog/changelog/feed/', ('github.blog',),
         frozenset('github copilot actions git pull repository codespaces'.split())),
    Feed('Palazzo Chigi', 'https://www.governo.it/feed/rss', ('www.governo.it',),
         frozenset('politica politics parlamento parliament governo government chigi opposizione bilancio'.split()),
         frozenset('politica politics italiane italiana italiano italia italy italian governo government chigi nazionale'.split())),
    Feed('Istat', 'https://www.istat.it/feed/', ('www.istat.it',),
         frozenset('istat occupazione disoccupazione esportazioni importazioni demografia censimento'.split())),
)

_INFLATION_FEED = Feed('Istat', 'https://www.istat.it/tag/prezzi-al-consumo/feed/', ('www.istat.it',),
                       frozenset({'inflazione', 'prezzi', 'consumo'}))
_ANDROID_BULLETINS = 'https://source.android.com/docs/security/bulletin/asb-overview'
_ANDROID_BULLETIN_PATH = r'/docs/security/bulletin/\d{4}/\d{4}-\d{2}-\d{2}'
_ANDROID_SCOPE = {'android', 'sistema', 'operativo', 'sicurezza', 'security', 'patch',
                  'platform', 'operating', 'system', 'updates', 'update'}
_MONTHS = dict(zip('January February March April May June July August September October November December'.split(),
                   range(1, 13)))
_COMPARISON = re.compile(
    r"(?:qual [èe] |quali sono |what is |what are )?(?:la |le |the )?"
    r"(?:differenz[ae] (?:tra|fra)|differences? between) (.{2,55}?) (?:ed?|and) (.{2,55})", re.I)
_ENCYCLOPEDIA_ALIASES = {'it': {'memoria di archiviazione': 'memoria di massa',
                                'fotovoltaico': 'impianto fotovoltaico', 'eolico': 'energia eolica'},
                         'en': {'storage': 'computer data storage', 'storage memory': 'computer data storage'}}


def public_url(value):
    if not isinstance(value, str) or len(value) > 1500 or re.search(r'[\s\\<>]', value):
        return False
    try:
        url = urlsplit(value)
        host = url.hostname or ''
        return bool(url.scheme == 'https' and _HOST.fullmatch(host) and url.netloc.lower() == host
                    and not host.endswith(('.localhost', '.local', '.internal', '.test', '.onion', '.invalid', '.example'))
                    and not url.fragment and not any(unicodedata.category(ch).startswith('C') for ch in value))
    except ValueError:
        return False


def _plain(value):
    text = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def _terms(value):
    return {word for word in re.findall(r"[^\W_]+", _plain(value))
            if len(word) > 1 and word not in _STOP and word not in _FRESH_WORDS}


def search_query(message, topic=None, *, explicit=False, allow_symbols=False, min_length=4):
    """Only bounded public search text crosses the network boundary."""
    from .public_references import private_or_creative, public_query_text

    text = public_query_text(message)
    if not text:
        return None
    if explicit:
        text = re.sub(r'^(?:(?:puoi|riesci a|can you)\s+)?(?:cerca|ricerca|controlla|verifica|search|look up)'
                      r'(?: (?:su internet|sul web|in rete|online|the web|the internet))?\b', '', text, flags=re.I)
        text = text.lstrip(' :,-')
    elif topic and not re.search(r'\b(?:oggi|attual\w*|latest|today|recent\w*|ultim\w*)\b', text, re.I):
        text = topic
    # Accept a single public query, without a transcript, credentials, URLs,
    # delimiters for extra clauses, email, account handles or long identifiers.
    text = text.strip(' ¿¡?!.。？！')
    if explicit:
        text = re.sub(r'^(?:(?:quali sono|dimmi|ci sono|what are|what is) )?(?:le |gli |the )?', '', text, flags=re.I)
    if re.match(r'^python\s+', text, re.I) and re.search(r'[._]', text):
        from .technical_search import technical_reference

        if technical_reference(text):
            text = re.sub(r'(?<=\w)\.(?=\w)', ' ', text)
            allow_symbols = True
    # Allow short programming symbols inside explicit public queries. Repeated,
    # leading and trailing underscores are still rejected.
    symbols = re.findall(r'\w*_\w*', text)
    privacy_text = text.replace('_', ' ')
    if (not min_length <= len(text) <= 135 or len(text.split()) > 17 or len(_terms(text)) < 1
            or not re.fullmatch(r"[\wÀ-ž ’'\-]+", text)
            or any(not (explicit or allow_symbols) or not re.fullmatch(
                r'[A-Za-z][A-Za-z0-9]{0,23}(?:_[A-Za-z][A-Za-z0-9]{0,23}){1,2}', symbol) for symbol in symbols)
            or private_or_creative(privacy_text)
            or re.search(r'\b(?:\d{5,}|[a-f\d]{16,}|nome completo|indirizzo ip|storia personale|conversation|'
                         r'istruzioni|identità|numero|documento|cognome|miei|vuoi|per me|per noi)\b', privacy_text, re.I)):
        return None
    return ' '.join(text.split())


def web_followup(message, prior):
    """Reuse only the scoped public search topic already displayed as a source."""
    if not isinstance(prior, str):
        return None
    text = unicodedata.normalize('NFKC', message).strip(' ?!.')
    if re.fullmatch(r'(?:e |e invece )?(?:gli ultimi aggiornamenti|le ultime notizie|oggi|adesso|ora)', text, re.I):
        query = search_query(prior)
        return (query, True) if query else None
    from .public_references import dependent_research
    if dependent_research(text):
        query = search_query(prior)
        return (query, False) if query else None
    return None


def broad_web_request(message):
    text = unicodedata.normalize('NFKC', message.strip())
    return bool(re.match(r'^(?:(?:puoi|riesci a) )?(?:cerca|verifica|controlla) (?:sul web|in rete)\b|'
                         r'^(?:(?:quali sono|dimmi|ci sono|what are|what is) )?(?:le |gli |the )?(?:ultim[ei] (?:notizie|aggiornamenti|dati)|'
                         r'(?:notizie|aggiornamenti) (?:recenti|di oggi)|latest (?:news|updates))\b|'
                         r'^(?:qual è|quali sono|quanto costa) [^?.!]{0,85}\b(?:oggi|attual[ei]|attualmente)\b|'
                         r'^(?:notizi[ae] (?:su|di|dal|sul)|(?:las )?últimas noticias|'
                         r'(?:les )?dernières nouvelles|neueste nachrichten|(?:as )?últimas notícias)\b',
                         text, re.I))


def public_web_question(message, topic):
    """Admit a public information question after the dedicated readers."""
    text = unicodedata.normalize('NFKC', message).strip(' ¿¡')
    if topic:
        return True
    match = _PUBLIC_WEB_QUESTION.match(text)
    if match is None:
        return False
    return bool(search_query(text) and _terms(text[match.end():]))


def comparison_terms(query, language):
    match = _COMPARISON.fullmatch(query)
    if not match:
        return ()
    labels = [re.sub(r"^(?:il |la |le |gli |l['’]|the )", '', item, flags=re.I).strip() for item in match.groups()]
    aliases = _ENCYCLOPEDIA_ALIASES.get(language, {})
    subjects = [(label, aliases.get(_plain(label), label)) for label in labels if search_query(label, min_length=2) == label]
    return tuple(subjects) if len(subjects) == 2 and _plain(subjects[0][1]) != _plain(subjects[1][1]) else ()


def android_update_scope(query):
    terms = _terms(query)
    return 'android' in terms and terms <= _ANDROID_SCOPE


def inflation_scope(query):
    terms = _terms(query)
    return (('inflazione' in terms or {'prezzi', 'consumo'} <= terms)
            and bool(terms & {'italia', 'italiana', 'italiano', 'istat'}))


def feed_plan(query):
    terms = _terms(query)
    if {'android', 'studio'} <= terms or 'androidstudio' in terms:
        return [next(feed for feed in FEEDS if feed.publisher == 'Android Studio')]
    if inflation_scope(query):
        return [_INFLATION_FEED]
    eligible = (feed for feed in FEEDS if feed.publisher != 'Palazzo Chigi'
                or terms & {'italia', 'italiana', 'italiano', 'italiane', 'italy', 'italian', 'chigi'})
    ranked = sorted(((len(terms & feed.topics), feed) for feed in eligible), key=lambda item:item[0], reverse=True)
    return [feed for score, feed in ranked if score][:2]


class NativeWebSearch:
    """Read public catalogs and rank their evidence locally."""
    name = 'Ricerca ALLMA'

    def fetch(self, query, language, fresh, cancelled, allowed):
        return reference_io(lambda stop: self._fetch(query, language, fresh, stop, allowed),
                            cancelled, allowed, seconds=7)

    def _fetch(self, query, language, fresh, cancelled, allowed):
        import requests
        from .public_references import USER_AGENT

        plan = feed_plan(query)
        if fresh and not plan:
            return {'status':'freshness_unsupported'}
        results, contacted = [], 0
        deadline = time.monotonic() + 6.5
        with requests.Session() as session:
            session.trust_env = False
            if fresh and android_update_scope(query):
                try:
                    raw = request_bytes(session, _ANDROID_BULLETINS, cancelled, allowed,
                                        params={'hl':'en'}, headers={'User-Agent':USER_AGENT},
                                        types=('text/html',), limit=512 * 1024)
                    bulletins = android_bulletins(raw, language) if raw else []
                    return {'status':'obtained' if bulletins else 'not_found', 'results':bulletins}
                except (requests.RequestException, ProviderError, OSError, ValueError):
                    return {'status':'unavailable'}
            subjects = comparison_terms(query, language) if not fresh else ()
            if subjects:
                for _, subject in subjects:
                    if not allowed() or time.monotonic() >= deadline:
                        break
                    evidence = _read_encyclopedia(session, subject, language, cancelled, allowed)
                    if evidence is not None:
                        results.extend({**item, 'subject':subject} for item in evidence)
                        contacted += 1
                return {'status':'obtained' if results else 'not_found' if contacted else 'unavailable',
                        'results':results}
            for feed in plan:
                check_cancelled(cancelled)
                if not allowed() or time.monotonic() >= deadline:
                    break
                try:
                    raw = request_bytes(session, feed.url, cancelled, allowed, headers={'User-Agent':USER_AGENT},
                                        types=_XML_TYPES, limit=384 * 1024)
                    if raw is not None:
                        results.extend(feed_results(raw, feed))
                        contacted += 1
                except GenerationCancelled:
                    raise
                except (requests.RequestException, ProviderError, OSError, ValueError, ElementTree.ParseError):
                    continue
            if not fresh and allowed() and time.monotonic() < deadline:
                evidence = _read_encyclopedia(session, query, language, cancelled, allowed)
                if evidence is not None:
                    results.extend(evidence)
                    contacted += 1
        return {'status': 'obtained' if results else 'not_found' if contacted else 'unavailable',
                'results':results}


def android_bulletins(raw, language):
    """Read release and patch dates from official bulletin rows."""
    pattern = (r'<tr>\s*<td>\s*<a href="(' + _ANDROID_BULLETIN_PATH + r')">[^<]+</a>\s*</td>'
               r'\s*<td>(?:(?!</?t[dr]\b).){0,3500}</td>\s*<td>\s*([A-Za-z]+) (\d{1,2}), (\d{4})\s*</td>'
               r'\s*<td>\s*((?:\d{4}-\d{2}-\d{2}(?:\s*<br\s*/?>\s*)?)+)\s*</td>\s*</tr>')
    rows = []
    for path, month, day, year, levels in re.findall(pattern, raw.decode('utf-8'), re.S)[:3]:
        if month not in _MONTHS:
            continue
        try:
            published = date(int(year), _MONTHS[month], int(day))
            patches = [date.fromisoformat(value).isoformat() for value in re.findall(r'\d{4}-\d{2}-\d{2}', levels)]
        except ValueError:
            continue
        if language == 'en':
            title = f'Android Security Bulletin, {month} {year}'
            excerpt = f'The Android security bulletin of {published.isoformat()} lists these patch levels: '
        else:
            title = f'Bollettino di sicurezza Android, {published:%m/%Y}'
            excerpt = f'Il bollettino di sicurezza Android del {published:%d/%m/%Y} indica i livelli patch '
        rows.append({'title':title, 'url':urljoin(_ANDROID_BULLETINS, path), 'publisher':'AOSP',
                     'date':published.isoformat(), 'snippet':excerpt + ', '.join(patches) + '.'})
    return rows


def _read_encyclopedia(session, query, language, cancelled, allowed):
    import requests

    try:
        return encyclopedic_results(session, query, language, cancelled, allowed)
    except (requests.RequestException, ProviderError, ValueError, KeyError, IndexError, AttributeError, TypeError):
        return None


def feed_results(raw, feed):
    """Read a fixed RSS/Atom source as inert data, with no entity expansion."""
    # CDATA and comments cannot declare entities. Some publishers embed an
    # HTML doctype inside article CDATA; validate actual XML declarations.
    structural = re.sub(br'<!\[CDATA\[[\s\S]*?\]\]>|<!--[\s\S]*?-->', b'', raw)
    if b'\x00' in raw or re.search(br'<!\s*(?:DOCTYPE|ENTITY)', structural, re.I):
        raise ValueError('Unexpected feed declarations')
    root = ElementTree.fromstring(raw)
    ns = '{http://www.w3.org/2005/Atom}'
    atom = root.tag == ns + 'feed'
    if not atom and root.tag != 'rss':
        raise ValueError('Unsupported feed')
    rows = []
    for item in (root.findall(ns + 'entry') if atom else root.findall('./channel/item'))[:28]:
        title = item.findtext(ns + 'title' if atom else 'title')
        if atom:
            link = next((node.get('href') for node in item.findall(ns+'link')
                         if node.get('rel','alternate') == 'alternate'), None)
            time_text = item.findtext(ns+'published') or item.findtext(ns+'updated')
            desc = item.findtext(ns+'summary') or item.findtext(ns+'content')
        else:
            link, time_text, desc = (item.findtext(tag) for tag in ('link','pubDate','description'))
        if not public_url(link) or urlsplit(link).hostname not in feed.hosts or not title or not time_text:
            continue
        try:
            stamp = (datetime.fromisoformat(time_text.replace('Z','+00:00')) if atom
                     else parsedate_to_datetime(time_text))
            if stamp.tzinfo is None:
                continue
            published = stamp.astimezone(timezone.utc).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
        description = unescape(re.sub(r'<[^>]{0,500}>', ' ', desc or ''))
        rows.append({'title':unescape(title), 'url':link, 'snippet':description,
                     'date':published, 'publisher':feed.publisher})
    return rows


def encyclopedic_results(session, query, language, cancelled, allowed):
    from .public_references import LANGUAGES, USER_AGENT, _url_allowed

    language = language if language in LANGUAGES else 'it'
    data = request_json(session, f'https://{language}.wikipedia.org/w/api.php', cancelled, allowed,
                        params={'action':'query','format':'json','formatversion':2,'generator':'search',
                                'gsrsearch':query,'gsrnamespace':0,'gsrlimit':5,'prop':'extracts|info|revisions|pageprops',
                                'exintro':1,'explaintext':1,'exsentences':6,'exlimit':5,'inprop':'url',
                                'rvprop':'ids','ppprop':'disambiguation'}, headers={'User-Agent':USER_AGENT})
    pages = (data or {}).get('query', {}).get('pages', [])
    if not isinstance(pages, list):
        return []
    results = []
    pages = [page for page in pages[:5] if isinstance(page, dict)]
    for page in sorted(pages, key=lambda item: item.get('index') if type(item.get('index')) is int else 6):
        if not isinstance(page, dict) or page.get('ns') != 0 or 'disambiguation' in (page.get('pageprops') or {}):
            continue
        url, revision = page.get('fullurl'), (page.get('revisions') or [{}])[0].get('revid')
        if (_url_allowed(url) and urlsplit(url).hostname == f'{language}.wikipedia.org'
                and type(revision) is int and 0 < revision < 10**12):
            results.append({'title':page.get('title'), 'snippet':page.get('extract'),
                            'url':f'{url}?oldid={revision}', 'publisher':'Wikipedia'})
    return results


def _safe_text(value, limit):
    if not isinstance(value, str):
        return ''
    value = ' '.join(value[:limit].split())
    if (any(unicodedata.category(ch).startswith('C') for ch in value)
            or re.search(r'<[^>]+>|<\||https?://|\b(?:ignore (?:all|previous)|system prompt|ignora (?:tutte|le istruzioni))\b', value, re.I)):
        return ''
    return value


def recent_publication(value, query, *, today=None, window=7):
    today = today or datetime.now(timezone.utc).date()
    try:
        stamp = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    days = 0 if _TODAY.search(query) else window
    return stamp if today - timedelta(days=days) <= stamp <= today else None


def compose_web_answer(query, results, fresh=False, *, today=None, previous=(), previous_urls=(), accept=None,
                       read_pages=False, exclude_adaptations=False, overview_topic=None):
    """Select cited passages locally and avoid unsupported paraphrases."""
    if not isinstance(results, list):
        return []
    today = today or datetime.now(timezone.utc).date()
    requested = _terms(query) - ({'dati','data'} if fresh else set())
    if not requested:
        return []
    publishers = {feed.publisher:feed for feed in FEEDS}
    previous = {_plain(value) for value in previous}
    candidates = []
    for result in results[:64]:
        if not isinstance(result, dict) or not public_url(result.get('url')):
            continue
        target = urlsplit(result['url'])
        host = target.hostname
        label = result.get('publisher')
        if not isinstance(label, str):
            continue
        publisher = publishers.get(label)
        public_page = read_pages and label == host and result.get('page_read') is True
        bulletin = (label == 'AOSP' and host == 'source.android.com' and fresh and android_update_scope(query)
                    and re.fullmatch(_ANDROID_BULLETIN_PATH, target.path))
        if publisher and host not in publisher.hosts:
            continue
        if label == 'Wikipedia':
            from .public_references import reference_link_allowed
            if not reference_link_allowed(result['url']):
                continue
        elif publisher is None and not bulletin and not public_page:
            continue
        title = _safe_text(result.get('title'), 160)
        snippet = _safe_text(result.get('snippet'), 2000)
        if not title:
            continue
        if overview_topic:
            from .research_choices import matches_overview
            subject = (unquote(target.path.removeprefix('/wiki/'))
                       if host.endswith('.wikipedia.org') else title)
            if not matches_overview(overview_topic, subject):
                continue
        if exclude_adaptations:
            from .research_choices import adaptation_title
            if adaptation_title(title):
                continue
        prices = label == 'Istat' and inflation_scope(query)
        if prices and not {'prezzi','consumo'} <= _terms(title):
            continue
        if prices and 35 <= len(snippet) <= 320 and not snippet.endswith(('.', '!', '?', '…')):
            snippet += '.'
        dated = [stamp for value in (result.get('date'), result.get('last_updated'))
                 if (stamp := recent_publication(value, query, today=today, window=45 if bulletin or prices else 7))]
        if fresh and not dated:
            continue
        scored = []
        effective = ({'prezzi','consumo'} if prices else
                     requested - (_terms(publisher.publisher) if publisher else set()))
        title_terms = _terms(title)
        overview = bool(fresh and publisher and requested <= publisher.overview_terms)
        if bulletin or overview:
            headline = title.rstrip('.!?') + '.'
            excerpt = snippet if bulletin else headline
            if (excerpt and _plain(excerpt) not in previous and result['url'] not in previous_urls
                    and (accept is None or accept(excerpt))):
                scored.append((1, excerpt))
        # A body passage from general search was already checked against the
        # request and its document section. Rank it in the provider's order.
        passages = [snippet] if public_page else re.split(r'(?<=[.!?])\s+', snippet)
        limit = 320
        if public_page and result.get('fact_relation'):
            limit = 500 if result['fact_relation'] == 'technical' else 420
        for sentence in (() if bulletin or overview else passages):
            if (not 35 <= len(sentence) <= limit
                    or not sentence.endswith(('.', '!'))
                    or sentence.endswith(('...', '…')) or re.match(r'^\s*(?:[-*#>]|\d+[.)])', sentence)):
                continue
            if _plain(sentence) in previous or (accept is not None and not accept(sentence)):
                continue
            if public_page:
                scored.append((1, sentence))
                continue
            sentence_terms = _terms(sentence)
            overlap = effective & (title_terms | sentence_terms)
            if (effective and (len(overlap) < max(1, (len(effective)+1)//2) or not effective & sentence_terms)
                    or not effective and not publisher):
                continue
            rank = 1 if prices else len(overlap) * 2 + len(effective & sentence_terms)
            scored.append((rank, sentence))
        headline = title.rstrip('.!?') + '.'
        if (not scored and not overview and publisher and accept is None and result['url'] not in previous_urls and _plain(headline) not in previous
                and requested <= title_terms | _terms(publisher.publisher)):
            scored.append((len(requested), headline))
        if scored:
            rank, excerpt = max(scored, key=lambda row: row[0])
            url = urlsplit(result['url'])
            safe_url = urlunsplit((url.scheme, url.netloc.lower(), quote(url.path or '/', safe="/%=:@!$&'()*+,;-._~"),
                                  quote(url.query, safe="/%=:@!$&'()*+,;?-._~"), ''))
            row = {'title':title, 'url':safe_url, 'excerpt':excerpt, 'publisher':result.get('publisher'),
                   'date':max(dated).isoformat() if dated else None}
            if public_page and result.get('facet') in ('people', 'europe', 'voyage', 'east_asia', 'metal_type'):
                row['facet'] = result['facet']
            candidates.append((rank, row))
    note = set()
    domains = []
    facets = set()
    selected = []
    for _, source in sorted(candidates, key=lambda row:(row[0], row[1]['date'] or ''), reverse=True):
        host = urlsplit(source['url']).hostname.removeprefix('www.')
        excerpt = hashlib.sha256(' '.join(_plain(source['excerpt']).split()).encode()).digest()
        limit = 3 if fresh else 2
        facet = source.get('facet')
        if excerpt not in note and (facet not in facets if facet else domains.count(host) < limit):
            note.add(excerpt)
            domains.append(host)
            if facet:
                facets.add(facet)
            selected.append(source)
        if len(selected) >= (1 if fresh and (android_update_scope(query) or inflation_scope(query)) else 3):
            break
    return selected


def web_comparison(query, results, language, *, previous=()):
    """Keep coverage for both subjects and attach a source to each claim."""
    subjects = comparison_terms(query, language)
    if not subjects or not isinstance(results, list):
        return '', []
    sources = []
    for label, subject in subjects:
        # Require a title match. Mentions in unrelated pages aren't definitions.
        matching = [row for row in results if isinstance(row, dict) and row.get('subject') == subject
                    and _terms(subject) <= _terms(_safe_text(row.get('title'), 160))]
        ranked = compose_web_answer(subject, matching, previous=previous)
        if not ranked:
            return '', []
        sources.append({**ranked[0], 'subject':label})
    if sources[0]['url'] == sources[1]['url']:
        return '', []
    statuses = [_volatility(source['excerpt'], language) for source in sources]
    if set(statuses) == {'volatile','persistent'}:
        messages = ({'volatile':'holds data while powered', 'persistent':'keeps data after power is removed'}
                    if language == 'en' else {'volatile':'mantiene i dati mentre è alimentata',
                                               'persistent':'conserva i dati anche dopo lo spegnimento'})
        answer = '. '.join(f"**{row['subject']}** {messages[state]} [{i}]"
                           for i, (row, state) in enumerate(zip(sources, statuses), 1)) + '.'
    else:
        answer = '\n\n'.join(f"**{row['subject']}** · {row['excerpt']} [{i}]"
                             for i, row in enumerate(sources, 1))
    return answer, sources


def _volatility(excerpt, language):
    pattern = (r'\b(?:is|are)\s+(?:a (?:type of )?)?(non[- ]?volatile|volatile)\b' if language == 'en'
               else r'\b(?:e (?:un tipo di |una )?(?:memoria )?|(?:in )?maniera )(non volatile|volatile)\b')
    matches = {_plain(value).replace('-', '').replace(' ', '') for value in re.findall(pattern, _plain(excerpt))}
    persistence = re.search(r'\b(perde|mantiene) le informazioni quando non viene alimentata\b', _plain(excerpt))
    if persistence:
        matches.add('volatile' if persistence[1] == 'perde' else 'nonvolatile')
    return {'volatile':'volatile','nonvolatile':'persistent'}.get(next(iter(matches))) if len(matches) == 1 else None


def render_web_passages(sources, language, *, list_updates=False, partial_scope=False):
    publishers = {row['publisher'] for row in sources}
    if not list_updates or len(publishers) != 1 or not publishers <= {'Palazzo Chigi', 'Android Studio'}:
        blocks = []
        for i, row in enumerate(sources, 1):
            # Preserve the underscores in Python names when Markdown renders the citation.
            excerpt = re.sub(r'(?<![\w`])(__[A-Za-z]\w*__(?:\(\))?)(?![\w`])', r'`\1`', row['excerpt'])
            blocks.append(f'{excerpt} [{i}]')
        passages = '\n\n'.join(blocks)
        if partial_scope:
            note = {'it': 'Le fonti consultate coprono solo una parte della domanda.',
                    'en': 'The sources I could verify cover part of the question.',
                    'es': 'Las fuentes consultadas cubren solo una parte de la pregunta.'}.get(language)
            if note:
                passages += '\n\n' + note
        return passages
    if publishers == {'Palazzo Chigi'}:
        intro = ('**Palazzo Chigi** · Official Italian government releases' if language == 'en'
                 else '**Palazzo Chigi** · Comunicati ufficiali del Governo italiano')
    else:
        intro = ('**Android Studio** · Official release notes' if language == 'en'
                 else '**Android Studio** · Note di rilascio ufficiali')
    rows = [f"- {row['excerpt'].rstrip('.')} ({row['date']}) [{i}]" for i, row in enumerate(sources, 1)]
    return '\n\n'.join((intro, '\n'.join(rows)))
