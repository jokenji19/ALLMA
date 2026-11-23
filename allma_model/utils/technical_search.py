"""Resolve public technical references to their manual and defining section."""

from dataclasses import dataclass
import re
from sys import stdlib_module_names

from .web_search import _plain


@dataclass(frozen=True)
class TechnicalReference:
    language: str
    title: str
    url: str
    section: str = ''
    evidence: tuple[str, ...] = ()
    compact_definition: bool = False
    definition: str = ''
    introduction: str = ''
    alternatives: tuple['TechnicalReference', ...] = ()

    def matches_section(self, heading):
        return not self.section or re.search(self.section, _plain(heading)) is not None

    def supports(self, passage):
        body = _plain(passage)
        return all(re.search(pattern, body) for pattern in self.evidence)


_MANUAL = r'(?:documentation|docs|reference|manual|documentazione|manuale)'
_GIT_COMMANDS = frozenset('add bisect branch checkout cherry-pick clone commit diff fetch log merge '
                          'pull rebase reflog reset restore revert show stash status switch tag worktree'.split())
_GIT = re.compile(rf'(?:git (?P<bare>[a-z][a-z-]*) {_MANUAL}|'
                  r'(?:what does|how does) git (?P<en>[a-z][a-z-]*) (?:work|do)|'
                  r'(?:come funziona|cosa fa|che cosa fa) git (?P<it>[a-z][a-z-]*))')
_PYTHON = re.compile(rf'python (?P<module>[a-z][a-z0-9_]{{1,29}})[ .](?P<name>[a-z][a-z0-9_]{{1,39}})'
                     rf'(?: {_MANUAL})?')
_CARGO = re.compile(rf'(?:rust )?cargo (?P<command>[a-z][a-z0-9-]{{1,23}}) {_MANUAL}')
_HTTP = re.compile(r'(?:(?:what does|what is|meaning of) (?:the )?http (?:status(?: code)? )?'
                   r'(?P<en>[1-5][0-9]{2})(?: (?:mean|not modified))?|'
                   r'(?:cosa significa|che cosa significa|cos[e\']+) (?:lo stato |il codice )?http '
                   r'(?P<it>[1-5][0-9]{2}))')
_IPV6 = re.compile(r'(?:quanti bit (?:ha|contiene|compongono) (?:un |gli )?indirizz[oi] ipv6|'
                   r'lunghezza (?:di un |degli )?indirizz[oi] ipv6(?: in bit)?)')
_DNS_FR = re.compile(r"(?:quel est le role du dns(?: sur internet)?|"
                     r"a quoi sert (?:le )?dns(?: sur internet)?|comment fonctionne (?:le )?dns)")
_FLEX_ES = re.compile(r'(?:(?:cual es la diferencia entre|diferencia entre) (?:el )?eje '
                      r'(?:principal y (?:el )?(?:eje )?(?:transversal|cruzado)|'
                      r'(?:transversal|cruzado) y (?:el )?(?:eje )?principal) (?:en|de) (?:css )?flexbox|'
                      r'(?:css )?flexbox eje principal y (?:eje )?(?:transversal|cruzado))')
_WAL = re.compile(rf'(?:sqlite (?:write[- ]ahead logging|wal) {_MANUAL}|'
                  r'(?:what is|how does) sqlite (?:write[- ]ahead logging|wal)(?: work)?)')


def public_protocol_question(query):
    """Admit closed questions about protocol definitions without admitting identifiers."""
    text = _plain(query).replace('’', "'").strip(' ¿¡?!.')
    return bool(_IPV6.fullmatch(text) or _HTTP.fullmatch(text))


def technical_reference(query):
    if not isinstance(query, str) or len(query) > 135:
        return None
    text = _plain(query).replace('’', "'").strip(' ¿¡?!.')
    if _IPV6.fullmatch(text):
        return TechnicalReference('it', 'IONOS · IPv6',
            'https://www.ionos.it/aiuto/infrastruttura-server-cloud/indirizzi-ip/ipv6-informazioni-di-base/',
            evidence=(r'\bindirizz[oi] ipv6\b', r'\b128\s*bit\b'),
            alternatives=(TechnicalReference('en', 'IETF · RFC 4291',
                'https://www.rfc-editor.org/rfc/rfc4291.txt',
                evidence=(r'\bipv6 addresses are 128[- ]bit identifiers\b',)),))
    if _WAL.fullmatch(text):
        return TechnicalReference('en', 'SQLite · Write-Ahead Logging', 'https://sqlite.org/wal.html',
            r'\bhow wal works\b',
            evidence=(r'\b(?:wal|write[- ]ahead log)\b', r'\bdatabase\b',
                      r'\b(?:append\w*|checkpoint\w*|journal file)\b'))
    if _DNS_FR.fullmatch(text):
        return TechnicalReference('fr', 'MDN · DNS', 'https://developer.mozilla.org/fr/docs/Glossary/DNS',
            evidence=(r'\bdns\b', r'\bnoms? de domaine\b', r'\badresses? ip\b',
                      r'\b(?:tradu\w*|convert\w*|resolution)\b'))
    if _FLEX_ES.fullmatch(text):
        return TechnicalReference('es', 'MDN · Los dos ejes de Flexbox',
            'https://developer.mozilla.org/es/docs/Web/CSS/Guides/Flexible_box_layout/Basic_concepts',
            evidence=(r'\beje principal\b', r'\beje (?:cruzado|transversal)\b',
                      r'\bflex-direction\b', r'\bperpendicular\b'))
    if match := _HTTP.fullmatch(text):
        status = match['en'] or match['it']
        # MDN's maintained HTTP reference for these statuses is in English.
        evidence = (r'\bconditional\b', r'\b(?:cach\w*|stored representation)\b') if status == '304' else (
            r'\b(?:response|status code)\b',)
        return TechnicalReference('en', f'MDN · HTTP {status}',
            f'https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/{status}',
            rf'^\s*{status}\b(?!.*\b(?:examples|specifications|see also|status)\b).*$',
            evidence, introduction=r'\b304 not modified\b' if status == '304' else '')
    if match := _GIT.fullmatch(text):
        command = match['bare'] or match['en'] or match['it']
        if command in _GIT_COMMANDS:
            return TechnicalReference('en', f'Git · git {command}',
                f'https://git-scm.com/docs/git-{command}',
                r'\bname\b', (rf'^git-{re.escape(command)}\s+[-–—]',), compact_definition=True)
    if match := _CARGO.fullmatch(text):
        command = match['command']
        return TechnicalReference('en', f'Cargo Book · cargo {command}',
            f'https://doc.rust-lang.org/cargo/commands/cargo-{command}.html', r'\bdescription\b')
    if (match := _PYTHON.fullmatch(text)) and match['module'] in stdlib_module_names:
        module, name = match['module'], match['name']
        evidence = ((r'\bgenerator\b', r'\b(?:with|context manager)\b')
                    if (module, name) == ('contextlib', 'contextmanager') else ())
        symbol = re.escape(name)
        return TechnicalReference('en', f'Python · {module}.{name}', f'https://docs.python.org/3/library/{module}.html',
            rf'(?<![\w.])(?:[a-z][a-z0-9_]*\.)*{symbol}(?:\(|\s|¶|$)', evidence,
            compact_definition=True,
            definition=rf'^the (?:[a-z][a-z0-9_]*\.)+{symbol}\([^)]*\) ',
            introduction=r'\bdecorator\b.*\bwith statement context managers\b' if evidence else '')
    return None
