from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import sqlite3
import pytest
from allma_model.core.dream_system.review_store import DreamReviewStore, ReviewConflict


def store(tmp_path):
    s = DreamReviewStore(tmp_path / 'reviews.db')
    s.ingest([{'text': 'Il mare può favorire il rilassamento', 'timestamp': '2026-10-06T12:00:00',
               'user_id': 'u', 'evidence': {'text': 'Oggi sono stato al mare', 'role': 'user'}}])
    return s


def test_legacy_import_is_idempotent_and_does_not_grant_knowledge(tmp_path):
    s = store(tmp_path)
    row = s.list('u')[0]
    s.ingest([{'text': row['original_text'], 'timestamp': row['created_at'], 'user_id': 'u'}])
    assert len(s.list('u')) == 1
    assert row['status'] == 'unverified'
    assert row['knowledge_verified'] is False
    assert s.relevant('u', 'Come mi aiuta il mare?') == []
    assert s.version('u') == 0


def test_confirmation_correction_and_retraction_survive_restart(tmp_path):
    s = store(tmp_path)
    identifier = s.list('u')[0]['id']
    confirmed = s.review('u', identifier, 'confirm', note='Corrisponde alla mia esperienza')
    assert confirmed['user_confirmed'] and not confirmed['knowledge_verified']
    assert s.relevant('u', 'Il mare mi rilassa?')[0]['id'] == identifier
    corrected = s.review('u', identifier, 'correct', correction='Il mare mi agita quando è affollato', expected_revision=1)
    assert corrected['original_text'] == confirmed['original_text']
    assert corrected['text'] == 'Il mare mi agita quando è affollato'
    s = DreamReviewStore(tmp_path / 'reviews.db')
    assert s.relevant('u', 'Come vivo il mare?')[0]['status'] == 'user_corrected'
    rejected = s.review('u', identifier, 'reject', expected_revision=2)
    assert rejected['status'] == 'rejected'
    assert s.relevant('u', 'Come vivo il mare?') == []
    assert s.version('u') == 3
    assert [event['decision'] for event in s.list('u')[0]['review_history']] == ['reject', 'correct', 'confirm']
    with sqlite3.connect(s.path) as db:
        assert db.execute('SELECT decision FROM dream_review_events ORDER BY revision').fetchall() == [('confirm',), ('correct',), ('reject',)]


def test_other_user_cannot_see_review_or_retrieve_hypothesis(tmp_path):
    s = store(tmp_path)
    identifier = s.list('u')[0]['id']
    assert s.list('other') == []
    with pytest.raises(ValueError):
        s.review('other', identifier, 'confirm')
    s.review('u', identifier, 'confirm')
    assert s.relevant('other', 'Il mare') == []
    assert s.version('other') == 0


def test_duplicate_acknowledgement_is_idempotent_and_stale_conflict_is_rejected(tmp_path):
    s = store(tmp_path)
    identifier = s.list('u')[0]['id']
    first = s.review('u', identifier, 'confirm')
    assert s.review('u', identifier, 'confirm') == first
    assert s.version('u') == 1
    with pytest.raises(ReviewConflict):
        s.review('u', identifier, 'reject')
    assert s.list('u')[0]['status'] == 'user_confirmed'


def test_concurrent_conflicting_reviews_have_only_one_winner(tmp_path):
    s = store(tmp_path)
    identifier = s.list('u')[0]['id']
    def review(decision):
        try:
            return s.review('u', identifier, decision)['status']
        except ReviewConflict:
            return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(review, ['confirm', 'reject']))
    assert results.count('conflict') == 1
    assert s.version('u') == 1


@pytest.mark.parametrize('kwargs', [{'decision': 'approve'}, {'decision': 'correct', 'correction': '  '},
    {'decision': 'correct', 'correction': 'x'*2001}, {'decision': 'confirm', 'expected_revision': True}])
def test_invalid_review_leaves_state_unchanged(tmp_path, kwargs):
    s = store(tmp_path)
    with pytest.raises(ValueError):
        s.review('u', s.list('u')[0]['id'], **kwargs)
    assert s.version('u') == 0
    assert s.list('u')[0]['status'] == 'unverified'


def test_sqlite_transaction_failure_does_not_partially_promote(tmp_path):
    s = store(tmp_path)
    identifier = s.list('u')[0]['id']
    with sqlite3.connect(s.path) as db:
        db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON dream_review_events BEGIN SELECT RAISE(ABORT,'disk failure'); END")
    with pytest.raises(sqlite3.DatabaseError):
        s.review('u', identifier, 'confirm')
    assert s.list('u')[0]['status'] == 'unverified'
    assert s.version('u') == 0
    with sqlite3.connect(s.path) as db:
        db.execute('DROP TRIGGER reject_event')
    assert s.review('u', identifier, 'confirm')['revision'] == 1


def test_retrieval_is_bounded_relevant_and_excludes_unreviewed_records(tmp_path):
    s = store(tmp_path)
    s.review('u', s.list('u')[0]['id'], 'confirm')
    s.ingest([{'text': 'Il cielo è blu', 'timestamp': 'later', 'user_id': 'u'}])
    assert s.relevant('u', 'Mi racconti il cielo?') == []
    assert s.relevant('u', 'ciao') == []
    assert len(s.relevant('u', 'mare rilassamento', limit=999)) == 1
