"""Read a small catalog of NASA Science pages without sending a search query."""
from html.parser import HTMLParser
import re
import time

from .bounded_io import reference_io
from .generation_control import check_cancelled

NASA_PAGES = {
    'Europa': 'https://science.nasa.gov/mission/europa-clipper/why-europa-europa-up-close/',
    'Enceladus': 'https://science.nasa.gov/saturn/moons/enceladus/',
    'Global sea level': 'https://science.nasa.gov/earth/explore/earth-indicators/sea-leve/',
}
NASA_LICENSE = 'https://www.nasa.gov/nasa-brand-center/images-and-media/'
ESA_PAGES = {
    'Europa': 'https://www.esa.int/articles/about-us/directorates/science/juice/juice-factsheet',
    'Enceladus': 'https://www.esa.int/articles/about-us/meet-us/sites-and-establishments/esa-esac/sampling-the-ocean-on-enceladus',
}
NOAA_PAGES = {'Global sea level': 'https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level'}
MAX_PAGE_RESPONSE = 512 * 1024


def astronomy_topic(text):
    """Recognize catalog entries in public questions, including Italian names."""
    if not re.search(r'\?|^\s*(?:cerca|verifica|spieg\w*|descriv\w*|search|explain|'
                     r'tell me|approfondisci|confront\w*|compar\w*)\b', text, re.I):
        return None
    europa = re.search(r'\beuropa\b', text, re.I) and re.search(
        r'\b(?:giove|jupiter|luna|moon|satellite|ghiacci\w*|ice|ocean\w*|clipper)\b', text, re.I)
    enceladus = re.search(r'\b(?:encelado|enceladus)\b', text, re.I)
    if bool(europa) == bool(enceladus):
        return None
    return 'Europa' if europa else 'Enceladus'


def evidence_terms(question):
    groups = (
        (r'\b(?:magnetic\w*|magnetism\w*)\b', ('magnetic', 'magnetometer')),
        (r'\b(?:sismic\w*|seismic\w*|seismomet\w*)\b', ('seismic', 'seismometer', 'seismometers')),
        (r'\b(?:prove|prova|indizi|evidenz\w*|evidence|misur\w*|measurement\w*)\b',
         ('measurement', 'measurements', 'observations', 'detected', 'doppler', 'magnetometer')),
        (r'\b(?:prove|prova|indizi|evidenz\w*|evidence|misur\w*|measurement\w*)\b',
         ('showed', 'implied', 'inferred', 'found', 'discovered', 'determined', 'detected', 'suggest', 'suggests')),
        (r'\b(?:oceano|oceani|ocean\w*|acqua|water|ghiacci\w*|ice)\b',
         ('ocean', 'water', 'saltwater', 'ice')),
        (r'\b(?:vita|life|abitab\w*|habitab\w*)\b', ('life', 'habitable', 'habitability')),
        (r'\b(?:mission\w*|clipper|cassini)\b', ('mission', 'clipper', 'cassini')),
        (r'\b(?:orbita|orbit\w*|rotazione|rotation)\b', ('orbit', 'rotation')),
    )
    return tuple(terms for pattern, terms in groups if re.search(pattern, question, re.I))


class MainParagraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.inactive = []
        self.paragraph = None
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.in_main = True
        if not self.in_main:
            return
        if tag in {'script', 'style', 'noscript', 'template', 'nav', 'aside', 'footer'}:
            self.inactive.append(tag)
        if self.inactive:
            return
        if tag == 'p':
            self.paragraph = []
        elif tag == 'br' and self.paragraph is not None:
            self.paragraph.append(' ')

    def handle_endtag(self, tag):
        if self.inactive:
            if tag == self.inactive[-1]:
                self.inactive.pop()
            return
        if tag == 'p' and self.paragraph is not None:
            text = ' '.join(''.join(self.paragraph).split())
            if 40 <= len(text) <= 1800:
                self.paragraphs.append(text)
            self.paragraph = None
        elif tag == 'main':
            self.in_main = False
            self.paragraph = None

    def handle_data(self, data):
        if self.in_main and not self.inactive and self.paragraph is not None:
            self.paragraph.append(data)


class AstronomyReader:
    pages = {}
    provider = ''
    license_url = ''

    def __init__(self, session=None):
        self.session = session

    def fetch(self, topic, language, cancelled, allowed):
        if topic not in self.pages:
            return []
        return reference_io(lambda stop: self._fetch(topic, stop, allowed), cancelled, allowed)

    def _fetch(self, topic, cancelled, allowed):
        import requests
        from .public_references import Reference, USER_AGENT

        session = self.session or requests.Session()
        if self.session is None:
            session.trust_env = False
        url = self.pages[topic]
        parser = MainParagraphs()
        try:
            check_cancelled(cancelled)
            if not allowed():
                return []
            with session.get(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'},
                             timeout=(3, 3), stream=True, allow_redirects=False) as response:
                content_type = response.headers.get('Content-Type', '').partition(';')[0].strip().lower()
                if response.status_code != 200 or content_type != 'text/html':
                    raise ValueError('Astronomy source unavailable')
                chunks = bytearray()
                for chunk in response.iter_content(4096):
                    check_cancelled(cancelled)
                    if not allowed():
                        return []
                    chunks.extend(chunk)
                    if len(chunks) > MAX_PAGE_RESPONSE:
                        raise ValueError('Astronomy source response limit')
            parser.feed(chunks.decode('utf-8'))
            parser.close()
        finally:
            if self.session is None:
                session.close()
        selected = []
        size = 0
        for paragraph in parser.paragraphs:
            if (topic == 'Global sea level' and not re.search(r'\b(?:global (?:mean )?sea level|thermal expansion)\b',
                                                              paragraph, re.I)):
                continue
            if self.provider == 'esa' and topic == 'Europa' and topic.casefold() not in paragraph.casefold():
                continue
            if size + len(paragraph) <= 6000 and paragraph not in selected:
                selected.append(paragraph)
                size += len(paragraph) + 1
        subject = r'\bglobal (?:mean )?sea level\b' if topic == 'Global sea level' else re.escape(topic)
        if not any(re.search(subject, p, re.I) for p in selected):
            return []
        return [Reference(topic, '\n'.join(selected), url, 0, time.time(),
                          license_url=self.license_url, provider=self.provider)]


class NasaReader(AstronomyReader):
    pages = NASA_PAGES
    provider = 'nasa'
    license_url = NASA_LICENSE


class EsaReader(AstronomyReader):
    pages = ESA_PAGES
    provider = 'esa'


class NoaaReader(AstronomyReader):
    pages = NOAA_PAGES
    provider = 'noaa'
