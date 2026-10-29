"""Opt-in public reference reads. Nothing here searches personal memory.

An obtained extract proves what that page says, not universal factual truth.
The default is local-only. Only a bounded public topic goes to one fixed API;
model-generated URLs, page instructions and full conversations are never used.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import math
import re
import sqlite3
import threading
import time
import unicodedata
from urllib.parse import urlparse, parse_qs

from .persistence import atomic_write_json
from .generation_control import check_cancelled

USER_AGENT = 'ALLMA/0.9.1 (https://github.com/jokenji19/ALLMA)'
LANGUAGES = frozenset(('it', 'en'))
MAX_RESPONSE = 96 * 1024
TTL = 24 * 60 * 60


def research_followup(message):
    return bool(re.fullmatch(r'\s*(?:cerca(?:lo|la)?(?: su internet| online| sul web)|'
        r'verifica(?:lo|la)?(?: su internet| online| sul web)|search (?:online|the web)|look it up)[\s.!?]*',message or '',re.I))


def local_only_request(message):
    """A turn may restrict a grant, never create one. Ambiguous vetoes stay local."""
    text = unicodedata.normalize('NFKC', message or '').casefold().replace('’', "'")
    text = re.sub(r"\bdon't\b", 'do not', text)
    return bool(re.search(
        r'\b(?:offline|solo (?:in )?locale|local only|nessuna ricerca|no (?:internet|browsing|web search))\b|'
        r'\b(?:senza|without)\b[^.!?;\n]{0,60}\b(?:internet|online|web|rete|browsing|search)\b|'
        r'\b(?:non|evita|do not|never)\b[^.!?;\n]{0,90}'
        r'\b(?:internet|online|web|rete|brows\w*|search\w*)\b', text))


def subject_reference(message):
    """Resolve only an explicitly replaced subject; '' means unresolved correction.

    This is a disposable task reference, never a new user memory or fact.
    """
    match = re.match(r'^\s*(?:no[,!]?[ \t]+)?(?:intendevo|mi riferivo(?: a)?|'
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
    return subject if public_topic(subject) else "Cos'è " + subject + '?'


def public_topic(message, anchor=''):
    """Conservative topic nomination; no LLM/private-archive query arguments.

    Unknown forms stay local. An explicit search command still cannot bypass
    sensitive-data filtering or the app's separate permission.
    """
    if anchor:
        corrected = subject_reference(message)
        if corrected is not None:
            return public_topic(corrected) if corrected else None
        current = public_topic(message)
        if current is not None:
            return current
    if not anchor and research_followup(message):
        return None
    if anchor and public_topic(message) is None and re.search(
            r'\b(?:mio|mia|miei|mie|nostr\w*|tuo|tua|your|my|our|codice|password|'
            r'telefono|indirizzo|farmac\w*|diagnos\w*|sintom\w*|depress\w*)\b|[@\n]|https?://',message or '',re.I):
        return None
    text = anchor or message or ''
    if not isinstance(text,str) or len(text)>300:
        return None
    text=text.strip()
    # Only formatting after the public question is removed, never private
    # clauses from an otherwise sensitive question.
    text = re.split(r'(?<=[?.!])\s*(?:rispondi|rispondimi|answer|respond)\b',text,flags=re.I)[0].strip()
    if (re.search(r'[\n@\d`{}<>]|https?://', text, re.I)
            or re.search(r'\b(?:io|mio|mia|miei|mie|nostr\w*|mi chiamo|ti ho|ti avevo|'
                r'noi|tuo|tua|tuoi|tue|questo|questa|quello|quella|'
                r'my|mine|our|your|this|that|password|codice|token|chiave|indirizzo|telefono|email|'
                r'farmac\w*|diagnos\w*|sintom\w*|depress\w*|suicid\w*|'
                r'inventa\w*|immagina\w*|poesia|racconto|fantasia|imagine|fiction|story)\b',text,re.I)):
        return None
    text = re.split(r'\b(?:rispondi|rispondimi|answer|respond)\b',text,flags=re.I)[0].strip()
    pattern = (r'^(?:cerca(?: su internet| online| sul web)?|verifica(?: online)?|'
        r'chi (?:era|fu|è)|che cos[’\']è|cos[’\']è|cosa (?:è|sono)|'
        r'(?:come (?:funziona(?:no)?|si forma(?:no)?))|'
        r'(?:spiega(?:mi)?|descrivi(?:mi)?)(?: il funzionamento)?(?: come| perché| perche)?|'
        r'what (?:is|are|was)|who (?:is|was)|how (?:does|do)|search(?: online)?|explain)\s+')
    match = re.match(pattern,text,re.I)
    if not match:
        return None
    topic = text[match.end():].strip(' ?!.:;«»“”"')
    topic = re.sub(r'^(?:di una? |di |una? |il |lo |la |i |gli |le |the |an? )+', '',topic,flags=re.I)
    topic = re.sub(r'\s+in (?:una|due|tre|quattro|\d+) frasi\s*$', '',topic,flags=re.I)
    if (not 2 <= len(topic) <= 90 or not re.fullmatch(r'[\wÀ-ž ’\'-]+',topic)
            or len(topic.split()) > 9):
        return None
    return ' '.join(topic.split())


def _url_allowed(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and parsed.hostname in {lang+'.wikipedia.org' for lang in LANGUAGES}
            and parsed.username is None and parsed.password is None and parsed.port in (None,443)
            and parsed.path.startswith('/wiki/') and not parsed.fragment and not parsed.query)
    except (ValueError,TypeError):
        return False


def reference_link_allowed(url):
    if url=='https://creativecommons.org/licenses/by-sa/4.0/':
        return True
    try:
        parsed=urlparse(url)
        query=parse_qs(parsed.query,strict_parsing=True)
        return (_url_allowed(parsed._replace(query='').geturl()) and set(query)=={'oldid'}
            and len(query['oldid'])==1 and query['oldid'][0].isdigit() and 0<int(query['oldid'][0])<10**12)
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

    @property
    def identifier(self):
        return hashlib.sha256((self.url+'\n'+str(self.revision)+'\n'+self.text).encode()).hexdigest()

    def citation(self):
        return {key:getattr(self,key) for key in ('title','url','revision','fetched_at','license_url','provider')}


def _valid_reference(reference):
    return (isinstance(reference,Reference) and isinstance(reference.title,str)
        and 1<=len(reference.title)<=200 and isinstance(reference.text,str)
        and 30<=len(reference.text)<=6000 and _url_allowed(reference.url)
        and type(reference.revision) is int and reference.revision>0
        and type(reference.fetched_at) in (int,float) and math.isfinite(reference.fetched_at)
        and 0<=time.time()-reference.fetched_at<=TTL
        and isinstance(reference.matched_title,str) and len(reference.matched_title)<=200
        and reference.provider=='wikipedia'
        and reference.license_url=='https://creativecommons.org/licenses/by-sa/4.0/')


def _relevant(reference, topic):
    """Search ranking alone does not establish that an extract is about a topic."""
    if reference.matched_title and _title_key(reference.matched_title)==_title_key(topic):
        return True
    stop=set('il lo la gli le un una di del della funzionamento formazione the a an of does do work works'.split())
    def words(value):
        value=''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))
        return {word for word in re.findall(r'\w+',value) if word not in stop and len(word)>1}
    requested=words(topic)
    title=words(reference.title)
    shared=requested & title
    return bool(requested and title) and len(shared)/len(requested)>=.6 and len(shared)/len(title)>=.6


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

    def fetch(self, topic, language, cancelled, allowed):
        from .bounded_io import reference_io
        return reference_io(lambda stop: self._fetch(topic, language, stop, allowed),
                            cancelled, allowed)

    def _fetch(self, topic, language, cancelled, allowed):
        import requests
        if language not in LANGUAGES or not allowed():
            return []
        session=self.session or requests.Session()
        owned=self.session is None
        if owned:session.trust_env=False
        base={'action':'query','format':'json','formatversion':2,
            'prop':'extracts|info|revisions|pageprops','ppprop':'disambiguation',
            'exintro':1,'explaintext':1,'exchars':1200,'exlimit':2,'inprop':'url','rvprop':'ids|timestamp'}
        attempts=({'titles':topic,'redirects':1},
            {'generator':'search','gsrsearch':topic,'gsrnamespace':0,'gsrlimit':2})
        started=time.monotonic()
        try:
            for attempt in attempts:
                check_cancelled(cancelled)
                if not allowed() or time.monotonic()-started>8:return []
                with session.get('https://'+language+'.wikipedia.org/w/api.php',params={**base,**attempt},
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
                for page in sorted(pages,key=lambda p:p.get('index',99) if type(p.get('index')) is int else 99)[:2]:
                    text,title,url=page.get('extract'),page.get('title'),page.get('fullurl')
                    revision=(page.get('revisions') or [{}])[0].get('revid')
                    if (page.get('ns')!=0 or 'disambiguation' in page.get('pageprops',{})
                            or not isinstance(text,str) or not 30<=len(text)<=6000
                            or not isinstance(title,str) or not 1<=len(title)<=200
                            or not _url_allowed(url) or type(revision) is not int or revision<1):continue
                    matched=topic if resolved==_title_key(title) else ''
                    reference=Reference(title,text,url,revision,time.time(),matched_title=matched)
                    if _valid_reference(reference) and _relevant(reference,topic):result.append(reference)
                if result:return result
            return []
        finally:
            if owned:session.close()


class PublicReferences:
    def __init__(self, db_path, preference_path, reader=None):
        self.db_path, self.preference_path = str(db_path), Path(preference_path)
        self.reader = reader or WikipediaReader()
        self.lock = threading.RLock()
        self._enabled, self._revision, self._error = False, 0, None
        if self.preference_path.exists():
            try:
                if self.preference_path.stat().st_size > 4096:
                    raise ValueError('Preference size')
                data = json.loads(self.preference_path.read_text())
                if set(data) != {'version','enabled'} or type(data['version']) is not int or data['version'] != 1 or type(data['enabled']) is not bool:
                    raise ValueError('Invalid preference')
                self._enabled = data['enabled']
            except Exception:
                self._error = 'Non riesco a leggere il consenso: le ricerche online restano disattivate.'

    def status(self):
        with self.lock:
            return {'enabled':self._enabled,'default_local':True,'error':self._error,
                    'provider':'Wikipedia','query_scope':'current_public_topic'}

    def configure(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Invalid web preference')
        with self.lock:
            # Revoke before disk I/O so a failed save cannot keep an in-flight
            # operation authorized. A failed enable never grants access.
            if not enabled:
                self._enabled=False
            self._revision += 1
            try:
                atomic_write_json(self.preference_path,{'version':1,'enabled':enabled})
            except OSError:
                self._error='Non riesco a salvare la preferenza. Le ricerche sono disattivate in questa sessione.'
                self._enabled=False
                try:
                    self.preference_path.unlink(missing_ok=True)
                except OSError:
                    self._error+=' Al prossimo avvio controlla nuovamente questa impostazione.'
                return self.status()
            self._enabled, self._error = enabled, None
            return self.status()

    @staticmethod
    def _key(topic, language):
        return hashlib.sha256((language+'\n'+unicodedata.normalize('NFKC',topic).casefold()).encode()).hexdigest()

    def _cache(self, key, references=None):
        with sqlite3.connect(self.db_path,timeout=2) as db:
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

    def lookup(self, message, anchor='', language='it', cancel_event=None, activity=None):
        def emit(payload):
            if activity is not None:
                activity({'provider':'Wikipedia',**payload})
        try:
            result=self._lookup(message,anchor,language,cancel_event,emit)
        except Exception:
            emit({'state':'finished','network_used':False})
            raise
        emit({'state':result['status'],'network_used':result['network_used']})
        return result

    def _lookup(self, message, anchor, language, cancel_event, emit):
        topic = public_topic(message,anchor)
        result = {'status':'not_applicable','references':[], 'network_used':False}
        if topic is None:
            return result
        language = language if language in LANGUAGES else 'it'
        key = self._key(topic,language)
        check_cancelled(cancel_event)
        try:
            cached=self._cache(key)
        except (sqlite3.Error,ValueError,TypeError):
            cached=[]
        cached=[r for r in cached if _relevant(r,topic)]
        if cached:
            return dict(result,status='cached',references=cached)
        with self.lock:
            revision=self._revision
            if not self._enabled or local_only_request(message):
                return dict(result,status='local_only')
        def allowed():
            with self.lock:
                return self._enabled and self._revision==revision
        try:
            result['network_used']=True
            emit({'state':'searching','network_used':True})
            references=self.reader.fetch(topic,language,cancel_event,allowed)
            if not isinstance(references,list) or len(references)>2:
                raise ValueError('Invalid reference collection')
            references=[r for r in references if _valid_reference(r) and _relevant(r,topic)]
            check_cancelled(cancel_event)
            with self.lock:
                if not allowed():
                    return dict(result,status='consent_revoked')
                if references:
                    try:self._cache(key,references)
                    except sqlite3.Error:pass
            return dict(result,status='obtained' if references else 'not_found',references=references)
        except Exception as error:
            from .generation_control import GenerationCancelled
            if isinstance(error,GenerationCancelled):raise
            return dict(result,status='unavailable',error=type(error).__name__)
