"""Explicitly bookmarked public evidence, independent of the search cache."""
from contextlib import closing
import json
import re
import sqlite3
import time
import unicodedata

from .public_references import ESA_PAGES, NASA_PAGES, NOAA_PAGES, reference_link_allowed


_IDENTIFIER = re.compile(r'[0-9a-f]{32}')
_QUESTION = re.compile(
    r"(?:cosa (?:hai|ho|abbiamo) salvato|mostra(?:mi)? le (?:informazioni|fonti) salvate)"
    r" (?:su(?:l|lla|llo|lle|i|gli)?\b|sull[’']|riguardo a\b)\s*(.{1,140}?)\s*[?.!]*",
    re.I,
)
_TOPICS = {
    'europa_subsurface_ocean': 'Oceano sotto il ghiaccio di Europa',
    'enceladus_global_ocean': 'Oceano sotto il ghiaccio di Encelado',
    'global_sea_level_causes': 'Cause dell’innalzamento del livello del mare',
}
_AGENCY_PAGES = {'nasa': NASA_PAGES, 'esa': ESA_PAGES, 'noaa': NOAA_PAGES}


def valid_id(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _valid_citation(citation):
    if not isinstance(citation, dict) or not isinstance(citation.get('title'), str) or not citation['title'].strip():
        return False
    url, revision, provider = citation.get('url'), citation.get('revision'), citation.get('provider')
    if not isinstance(url, str) or type(revision) is not int or not isinstance(provider, str):
        return False
    if provider == 'wikipedia':
        return '?' not in url and 0 < revision < 10**12 and reference_link_allowed(f'{url}?oldid={revision}')
    return provider in _AGENCY_PAGES and revision == 0 and url in _AGENCY_PAGES[provider].values()


def saved_topic(source, review):
    if not isinstance(review, dict) or review.get('truth_verified') is not False:
        return None
    if source == 'reference_excerpt' and review.get('basis') == 'reference_text':
        citation = review.get('citation')
        return citation['title'] if _valid_citation(citation) else None
    if source == 'web_search' and review.get('basis') == 'web_passages':
        from .web_search import public_url, search_query

        topic = search_query(review.get('public_topic'))
        sources = review.get('sources')
        if (topic and isinstance(sources, list) and 1 <= len(sources) <= 3 and all(
                isinstance(row, dict) and public_url(row.get('url')) and
                isinstance(row.get('title'), str) and isinstance(row.get('excerpt'), str) for row in sources)):
            return topic
    if source == 'reference_comparison' and review.get('basis') == 'source_comparison':
        sources = review.get('sources')
        if not isinstance(sources, list):
            return None
        citations = [row.get('citation') for row in sources
                     if isinstance(row, dict) and isinstance(row.get('excerpt'), str) and row['excerpt'].strip()]
        if (review.get('outcome') in {'agreement', 'disagreement', 'parallel_reading'}
                and len(citations) == 2 and all(_valid_citation(citation) for citation in citations)
                and citations[0]['url'] != citations[1]['url']):
            return _TOPICS.get(review.get('scope'), citations[0]['title'])
    return None


def requested_topic(message):
    if len(message) <= 240:
        match = _QUESTION.fullmatch(message.strip())
        if match:
            return match[1]
    return None


def _terms(value):
    normalized = unicodedata.normalize('NFKD', value.casefold())
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    return set(re.findall(r'[^\W_]+', normalized)) - {
        'un', 'una', 'uno', 'il', 'lo', 'la', 'l', 'i', 'le', 'gli', 'del', 'dello',
        'della', 'dell', 'dei', 'delle', 'di', 'da', 'per', 'su', 'sul', 'sui', 'in',
        'e', 'the', 'a', 'of', 'on', 'about',
    }


class SavedReferences:
    LIMIT = 200
    PAGE_SIZE = 10

    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    @staticmethod
    def _ensure_table(db):
        db.execute('''CREATE TABLE IF NOT EXISTS saved_public_knowledge (
            owner TEXT NOT NULL, id TEXT NOT NULL, saved_at REAL NOT NULL,
            source TEXT NOT NULL, answer TEXT NOT NULL, review TEXT NOT NULL,
            PRIMARY KEY (owner, id)
        )''')

    def remember(self, owner, event):
        from allma_model.core.autobiographical_identity import response_disputed

        metadata = event.metadata
        identifier = metadata.get('reference_save_id')
        source, review = metadata.get('source'), metadata.get('reference_review')
        if (event.role != 'assistant' or event.user_id != owner or metadata.get('is_valid') is not True
                or response_disputed(metadata)
                or not valid_id(identifier) or not saved_topic(source, review)
                or not isinstance(event.content, str) or not event.content.strip()
                or len(event.content) > 12000):
            raise ValueError('Questa risposta non è disponibile per il salvataggio.')
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._ensure_table(db)
            if db.execute('SELECT 1 FROM saved_public_knowledge WHERE owner=? AND id=?',
                          (owner, identifier)).fetchone():
                return
            if db.execute('SELECT COUNT(*) FROM saved_public_knowledge WHERE owner=?',
                          (owner,)).fetchone()[0] >= self.LIMIT:
                raise ValueError('Archivio pieno. Rimuovi una voce da Cosa imparo.')
            db.execute('INSERT INTO saved_public_knowledge VALUES (?,?,?,?,?,?)',
                       (owner, identifier, time.time(), source, event.content, json.dumps(review)))

    def forget(self, owner, identifier):
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if self._exists(db):
                db.execute('DELETE FROM saved_public_knowledge WHERE owner=? AND id=?', (owner, identifier))

    @staticmethod
    def _exists(db):
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='saved_public_knowledge'").fetchone()

    def entries(self, owner, *, offset=0, limit=None):
        with closing(self._connect()) as db:
            if not self._exists(db):
                return []
            rows = db.execute('''SELECT id,saved_at,source,answer,review FROM saved_public_knowledge
                WHERE owner=? ORDER BY saved_at DESC, rowid DESC LIMIT ? OFFSET ?''',
                (owner, self.LIMIT if limit is None else limit, offset)).fetchall()
        result = []
        for identifier, saved_at, source, answer, payload in rows:
            review = json.loads(payload)
            title = saved_topic(source, review)
            if not valid_id(identifier) or not title:
                raise ValueError('Archivio delle fonti non disponibile.')
            result.append({'id': identifier, 'saved_at': saved_at, 'source': source,
                           'title': title, 'answer': answer, 'review': review})
        return result

    def find(self, owner, topic):
        terms = _terms(topic)
        if not terms:
            return []
        rows = self.entries(owner)
        exact = [row for row in rows if terms == _terms(row['title'])]
        return exact or [row for row in rows if terms <= _terms(row['title'])]
