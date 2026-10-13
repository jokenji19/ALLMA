"""Adversarial persistence tests with disposable archives, never device memories."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys

import pytest
from allma_model.core.dream_system.review_store import DreamReviewStore, ReviewConflict


def seeded(path, count=1):
    store = DreamReviewStore(path)
    store.ingest([{'text': f'Mare tranquillo ipotesi {i}', 'timestamp': str(i),
                   'user_id': 'u', 'evidence': {'text': f'Fonte {i}'}} for i in range(count)])
    return store


def test_many_revisions_with_restarts_preserve_full_audit_and_revocations(tmp_path):
    path = tmp_path / 'reviews.db'
    store = seeded(path, 12)
    states = {item['id']: {'revision': 0, 'status': 'unverified', 'text': item['original_text']}
              for item in store.list('u')}
    rng = random.Random(20261006)
    for step in range(300):
        identifier = rng.choice(list(states))
        previous = states[identifier]
        decision = rng.choice(['confirm', 'correct', 'reject'])
        kwargs = {'expected_revision': previous['revision'], 'note': f'Revisione {step}'}
        if decision == 'correct':
            kwargs['correction'] = f'Mare correzione {step} — tranquillità 🌊'
        result = store.review('u', identifier, decision, **kwargs)
        # Retransmissions, including after restart, must not add another event.
        store = DreamReviewStore(path)
        assert store.review('u', identifier, decision, **kwargs) == result
        states[identifier] = {'revision': result['revision'], 'status': result['status'], 'text': result['text']}
        assert store.version('u') == step + 1
        visible = {item['id']: item for item in store.list('u')}
        assert len(visible) == 12
        assert visible[identifier]['text'] == result['text']
        assert all(not item['knowledge_verified'] for item in visible.values())
        assert all(item['status'] in ('user_confirmed', 'user_corrected')
                   for item in store.relevant('u', 'mare tranquillo correzione'))
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT COUNT(*) FROM dream_review_events').fetchone()[0] == 300
        for identifier, state in states.items():
            revisions = [row[0] for row in db.execute(
                'SELECT revision FROM dream_review_events WHERE hypothesis_id=? ORDER BY revision', (identifier,))]
            assert revisions == list(range(1, state['revision'] + 1))
    for item in store.list('u'):
        assert len(item['review_history']) == min(5, item['revision'])
    assert store.list('other') == [] and store.version('other') == 0


def test_32_independent_clients_retransmit_one_confirmation_once(tmp_path):
    path = tmp_path / 'reviews.db'
    store = seeded(path)
    identifier = store.list('u')[0]['id']
    def confirm(_):
        return DreamReviewStore(path).review('u', identifier, 'confirm', expected_revision=0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(confirm, range(32)))
    assert all(response['revision'] == 1 for response in responses)
    assert store.version('u') == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM dream_review_events').fetchone()[0] == 1


def test_process_death_before_commit_rolls_back_and_can_retry(tmp_path):
    path = tmp_path / 'reviews.db'
    store = seeded(path)
    identifier = store.list('u')[0]['id']
    # The real review writes all three tables before calling _record on its result.
    # Killing at that point prevents the connection context from committing.
    code = '''
import os, sys
from allma_model.core.dream_system.review_store import DreamReviewStore
s = DreamReviewStore(sys.argv[1])
s._record = lambda row: os._exit(73)
s.review('u', sys.argv[2], 'confirm')
'''
    process = subprocess.run([sys.executable, '-c', code, str(path), identifier],
                             cwd=str(Path(__file__).resolve().parents[2]), timeout=10,
                             capture_output=True, text=True)
    assert process.returncode == 73, process.stderr
    store = DreamReviewStore(path)
    assert store.list('u')[0]['status'] == 'unverified'
    assert store.version('u') == 0
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT COUNT(*) FROM dream_review_events').fetchone()[0] == 0
    assert store.review('u', identifier, 'confirm')['revision'] == 1


def test_database_busy_does_not_acknowledge_or_change_state_and_retry_works(tmp_path, monkeypatch):
    store = seeded(tmp_path / 'reviews.db')
    identifier = store.list('u')[0]['id']
    original = store._connect
    def short_connection():
        connection = original()
        connection.execute('PRAGMA busy_timeout=20')
        return connection
    monkeypatch.setattr(store, '_connect', short_connection)
    lock = sqlite3.connect(store.path)
    try:
        lock.execute('BEGIN IMMEDIATE')
        with pytest.raises(sqlite3.OperationalError, match='locked'):
            store.review('u', identifier, 'confirm')
        assert store.version('u') == 0
        assert store.list('u')[0]['status'] == 'unverified'
    finally:
        lock.rollback()
        lock.close()
    assert store.review('u', identifier, 'confirm')['revision'] == 1


def test_corrected_text_replaces_old_retrieval_and_reconfirmation_restores_original(tmp_path):
    store = seeded(tmp_path / 'reviews.db')
    identifier = store.list('u')[0]['id']
    store.review('u', identifier, 'confirm')
    store.review('u', identifier, 'correct', correction='Montagna silenziosa', expected_revision=1)
    assert store.relevant('u', 'mare tranquillo') == []
    assert store.relevant('u', 'montagna')[0]['text'] == 'Montagna silenziosa'
    with pytest.raises(ReviewConflict):
        store.review('u', identifier, 'confirm', expected_revision=0)
    result = store.review('u', identifier, 'confirm', expected_revision=2)
    assert result['text'] == result['original_text']
    assert store.relevant('u', 'montagna') == []
    store.review('u', identifier, 'reject', expected_revision=3)
    assert store.relevant('u', 'mare tranquillo') == []


def test_pending_hypotheses_remain_visible_with_large_reviewed_archive(tmp_path):
    store = seeded(tmp_path / 'reviews.db', 230)
    rows = store.list('u', limit=200)
    for item in rows:
        store.review('u', item['id'], 'reject')
    remaining = store.list('u')
    assert store.pending_count('u') == 30
    assert all(item['status'] == 'unverified' for item in remaining[:30])
    assert len(store.list('u', limit=100000)) == 200
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM dream_hypotheses').fetchone()[0] == 230
