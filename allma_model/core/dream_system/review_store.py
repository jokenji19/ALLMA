"""Durable human review of generated hypotheses, separate from factual/episodic memory."""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ReviewConflict(ValueError):
    pass


class DreamReviewStore:
    STATUSES = {'confirm': 'user_confirmed', 'correct': 'user_corrected', 'reject': 'rejected'}

    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS dream_hypotheses (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL, original_text TEXT NOT NULL,
                created_at TEXT NOT NULL, evidence_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unverified', reviewed_text TEXT,
                review_note TEXT NOT NULL DEFAULT '', reviewed_at TEXT,
                revision INTEGER NOT NULL DEFAULT 0)''')
            db.execute('CREATE INDEX IF NOT EXISTS dream_user_status ON dream_hypotheses(user_id,status)')
            db.execute('''CREATE TABLE IF NOT EXISTS dream_review_events (
                hypothesis_id TEXT NOT NULL, revision INTEGER NOT NULL, decision TEXT NOT NULL,
                text TEXT, note TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                PRIMARY KEY(hypothesis_id,revision))''')
            db.execute('CREATE TABLE IF NOT EXISTS dream_user_versions (user_id TEXT PRIMARY KEY, version INTEGER NOT NULL)')

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def identity(item):
        # Old pending JSON files have no ID. Deterministic import is retry-safe.
        return hashlib.sha256(json.dumps([item['user_id'], item.get('timestamp', ''), item['text']],
                                          ensure_ascii=False).encode()).hexdigest()

    def ingest(self, records):
        with self._connect() as db:
            for item in records:
                if (not isinstance(item, dict) or not isinstance(item.get('text'), str)
                        or not item['text'].strip() or not isinstance(item.get('user_id'), str)
                        or not item['user_id']):
                    continue
                evidence = item.get('evidence') if isinstance(item.get('evidence'), dict) else {}
                db.execute('''INSERT OR IGNORE INTO dream_hypotheses
                    (id,user_id,original_text,created_at,evidence_json) VALUES(?,?,?,?,?)''',
                    (self.identity(item), item['user_id'], item['text'], str(item.get('timestamp', '')),
                     json.dumps(evidence, ensure_ascii=False)))

    @staticmethod
    def _record(row):
        if row is None:
            return None
        record = dict(row)
        record['evidence'] = json.loads(record.pop('evidence_json'))
        record.update(source='dream_hypothesis', knowledge_verified=False,
                      user_confirmed=record['status'] in ('user_confirmed', 'user_corrected'))
        record['text'] = record['reviewed_text'] or record['original_text']
        return record

    def list(self, user_id, limit=100):
        if not user_id:
            return []
        with self._connect() as db:
            rows = db.execute('''SELECT * FROM dream_hypotheses WHERE user_id=?
                ORDER BY CASE WHEN status='unverified' THEN 0 ELSE 1 END,
                         COALESCE(reviewed_at,created_at) DESC, id LIMIT ?''',
                              (user_id, max(1, min(200, int(limit))))).fetchall()
            records = [self._record(row) for row in rows]
            for record in records:
                events = db.execute('''SELECT revision,decision,text,note,reviewed_at FROM dream_review_events
                    WHERE hypothesis_id=? ORDER BY revision DESC LIMIT 5''', (record['id'],)).fetchall()
                record['review_history'] = [{**dict(event), 'text': (event['text'] or '')[:240],
                                             'note': event['note'][:240]} for event in events]
        return records

    def pending_count(self, user_id):
        with self._connect() as db:
            return db.execute("SELECT COUNT(*) FROM dream_hypotheses WHERE user_id=? AND status='unverified'",
                              (user_id,)).fetchone()[0]

    def version(self, user_id):
        with self._connect() as db:
            row = db.execute('SELECT version FROM dream_user_versions WHERE user_id=?', (user_id,)).fetchone()
            return row[0] if row else 0

    def review(self, user_id, hypothesis_id, decision, *, correction='', note='', expected_revision=0):
        if decision not in self.STATUSES:
            raise ValueError('Decisione non valida')
        if (not isinstance(correction, str) or not isinstance(note, str) or len(correction) > 2000
                or len(note) > 2000 or not isinstance(expected_revision, int) or isinstance(expected_revision, bool)
                or expected_revision < 0):
            raise ValueError('Dati della revisione non validi')
        correction, note = correction.strip(), note.strip()
        if decision == 'correct' and not correction:
            raise ValueError('Scrivi la correzione prima di salvarla')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM dream_hypotheses WHERE id=? AND user_id=?',
                             (hypothesis_id, user_id)).fetchone()
            if row is None:
                raise ValueError('Ipotesi non disponibile')
            status = self.STATUSES[decision]
            text = correction if decision == 'correct' else row['original_text'] if decision == 'confirm' else None
            same = row['status'] == status and row['reviewed_text'] == text and row['review_note'] == note
            if row['revision'] != expected_revision:
                if same and row['revision'] == expected_revision + 1:
                    return self._record(row)  # Retransmission after an acknowledgement was lost.
                raise ReviewConflict('La revisione è cambiata: aggiorna l’elenco e riprova')
            if same:
                return self._record(row)
            now = datetime.now(timezone.utc).isoformat()
            revision = row['revision'] + 1
            db.execute('''UPDATE dream_hypotheses SET status=?,reviewed_text=?,review_note=?,
                reviewed_at=?,revision=? WHERE id=? AND user_id=?''',
                (status, text, note, now, revision, hypothesis_id, user_id))
            db.execute('INSERT INTO dream_review_events VALUES(?,?,?,?,?,?)',
                       (hypothesis_id, revision, decision, text, note, now))
            db.execute('''INSERT INTO dream_user_versions VALUES(?,1)
                ON CONFLICT(user_id) DO UPDATE SET version=version+1''', (user_id,))
            return self._record(db.execute('SELECT * FROM dream_hypotheses WHERE id=?', (hypothesis_id,)).fetchone())

    @staticmethod
    def _terms(text):
        stop = {'come','cosa','quale','quali','della','delle','degli','sono','questo','questa','perché',
                'allma','vorrei','dimmi','spiega','abbiamo','parlato'}
        return {word for word in re.findall(r'\w+', text.lower()) if len(word) >= 4 and word not in stop}

    def relevant(self, user_id, message, limit=2):
        terms = self._terms(message)
        if not terms:
            return []
        with self._connect() as db:
            # Bounded retrieval. No embeddings, native inference or background thread.
            rows = db.execute('''SELECT * FROM dream_hypotheses WHERE user_id=?
                AND status IN ('user_confirmed','user_corrected') ORDER BY reviewed_at DESC LIMIT 200''',
                              (user_id,)).fetchall()
        candidates = []
        for row in rows:
            item = self._record(row)
            overlap = len(terms & self._terms(item['text']))
            if overlap:
                candidates.append((overlap, item))
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in candidates[:max(0, min(2, limit))]]
