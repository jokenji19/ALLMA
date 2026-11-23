"""Adversarial checks for attributed feedback and public evidence."""
from itertools import permutations
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from allma_model.core.autobiographical_identity import POLICY_VERSION
from allma_model.core.response_feedback import _source_check, latest_correction
from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.utils.public_references import Reference
from allma_model.utils.saved_references import SavedReferences


QUESTION = 'Quando fu firmato il Patto tripartito?'
TOPIC = 'Patto tripartito'
TERMS = ('firmato', 'sottoscritto', 'siglato')
USER = 'synthetic'
CONVERSATION = 'feedback-stress'


@pytest.fixture
def core(tmp_path, monkeypatch):
    from allma_model.core.allma_core import ALLMACore

    monkeypatch.chdir(tmp_path)
    brain = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'test.db'))
    brain._ensure_mobile_llm = lambda: None
    brain._llm = Mock()
    brain._llm.generate.side_effect = AssertionError('Il feedback deve usare una fonte o uno strumento')
    brain.public_references.reader = Mock(fetch=Mock(return_value=[]))
    brain.public_references.configure(True)
    yield brain
    brain.close()


def store_answer(core, text, question=QUESTION, **metadata):
    cid = core.start_conversation(USER)
    identifier = uuid4().hex
    core.conversational_memory.store_message(cid, question, {}, 'user', USER)
    core.conversational_memory.store_message(cid, text, {
        'response_feedback_id': identifier, 'is_valid': True, 'identity_policy': POLICY_VERSION,
        'source': 'model_generated', **metadata}, 'assistant', USER)
    return cid, identifier


def page(text, suffix='', revision=101):
    return Reference(TOPIC, text, 'https://it.wikipedia.org/wiki/Patto_tripartito' + suffix,
                     revision, time.time())


@pytest.mark.parametrize('original', ['1941', 'Nel 1941.', 'Il Patto tripartito fu firmato nel 1941.'])
@pytest.mark.parametrize('passage', [
    'Il Patto tripartito non fu firmato nel 1940.',
    'Il Patto tripartito forse fu firmato nel 1940.',
    'Il Patto tripartito sarebbe stato firmato nel 1940.',
    'Il Patto tripartito fu firmato prima del 1940.',
    'Il Patto tripartito fu firmato dopo il 1940.',
    'Il Patto tripartito fu firmato entro il 1940.',
    'Il Patto tripartito fu firmato verso il 1940.',
    'Il Patto tripartito fu firmato prima della conferenza del 1940.',
    'Il Patto tripartito fu discusso; la Francia firmò nel 1940.',
    'Il Patto tripartito cita il trattato firmato nel 1940 dalla Francia.',
    'Il Patto tripartito fu firmato nel 1940 a.C.',
    'Il Patto tripartito fu firmato il 27 settembre 1940 e ratificato nel 1941.',
])
def test_uncertain_or_unrelated_dates_are_not_promoted_to_corrections(original, passage):
    result = _source_check(original, passage, {}, True, TOPIC, TERMS)
    assert result['status'] == 'evidence'


@pytest.mark.parametrize('phrase', [
    'Il Patto tripartito fu firmato nel 1940.',
    'Il Patto tripartito fu un accordo sottoscritto a Berlino il 27 settembre 1940.',
    'Il Patto tripartito venne siglato il 27 settembre 1940 a Berlino.',
])
@pytest.mark.parametrize(('original', 'status'), [('1940', 'supported'), ('1941', 'corrected')])
def test_affirmative_dated_event_can_be_checked(phrase, original, status):
    assert _source_check(original, phrase, {}, True, TOPIC, TERMS)['status'] == status


@pytest.mark.parametrize('order', list(permutations([0, 1])))
def test_conflicting_dates_remain_visible_in_both_orders(core, order):
    pages = [page(f'Il Patto tripartito fu firmato nel {year} da Germania, Italia e Giappone.', suffix, revision)
             for year, suffix, revision in [(1940, '', 101), (1941, '_(studio)', 102)]]
    core.public_references.reader.fetch.return_value = [pages[index] for index in order]
    cid, identifier = store_answer(core, '1942')
    state = core.give_response_feedback(USER, cid, identifier, 'down')
    assert state['check']['status'] == 'conflicting'
    assert {row['origin']['citation']['revision'] for row in state['check']['alternatives']} == {101, 102}
    with pytest.raises(ValueError):
        core.give_response_feedback(USER, cid, identifier, 'review_up')
    assert core.saved_references.entries(USER) == []


def test_a_late_click_cannot_approve_or_revoke_a_different_revision(core):
    cid, identifier = store_answer(core, '41', 'Quanto fa 18 + 24?')
    give = lambda vote: core.give_response_feedback(USER, cid, identifier, vote)
    assert give('down')['status'] == 'reviewed'
    with pytest.raises(ValueError):
        give('up')
    assert give('review_up')['status'] == 'review_approved'
    assert give('down')['status'] == 'review_approved'
    assert give('review_down')['status'] == 'review_disputed'
    assert give('review_down')['status'] == 'review_disputed'
    with pytest.raises(ValueError):
        give('review_up')


@pytest.mark.parametrize('incremental', [False, True])
def test_corrections_survive_restart_and_more_than_64_messages(tmp_path, incremental):
    from allma_model.core.response_feedback import apply_feedback

    memory = ConversationalMemory(storage_dir=str(tmp_path), incremental=incremental)
    core = SimpleNamespace(conversational_memory=memory, answer_recall=Mock(),
                           saved_references=SavedReferences(str(tmp_path / 'app.db')))
    identifier = 'a' * 32
    question = 'E domani?'
    memory.store_message(CONVERSATION, question, {}, 'user', USER)
    memory.store_message(CONVERSATION, 'Una risposta.', {'response_feedback_id': identifier,
        'is_valid': True, 'response_feedback': {'vote': 'down', 'status': 'reviewed'}}, 'assistant', USER)
    apply_feedback(core, USER, CONVERSATION, identifier, 'correction', 'Intendevo il museo, non il ristorante.')
    for index in range(72):
        memory.store_message('other-thread', f'Messaggio sintetico {index}', {}, 'user', USER)
    reloaded = ConversationalMemory(storage_dir=str(tmp_path), incremental=incremental)
    assert latest_correction(reloaded, USER, question, CONVERSATION) == 'Intendevo il museo, non il ristorante.'
    assert latest_correction(reloaded, USER, question, 'other-thread') is None
    assert latest_correction(reloaded, 'other-user', question, CONVERSATION) is None


def test_disputing_a_recalled_bookmark_retires_the_original_entry(core):
    core.public_references.reader.fetch.return_value = [
        page('Il Patto tripartito fu firmato nel 1940 dalla Germania, dall’Italia e dal Giappone.')]
    cid = core.start_conversation(USER)
    first = core.process_message(USER, cid, QUESTION)
    original_id = first.metadata['response_feedback_id']
    assert core.give_response_feedback(USER, cid, original_id, 'up')['saved']
    recalled = core.process_message(USER, cid, 'Cosa hai salvato sul Patto tripartito?')
    assert recalled.metadata['source'] == 'saved_reference_recall'
    core.give_response_feedback(USER, cid, recalled.metadata['response_feedback_id'], 'down')
    assert core.saved_references.entries(USER) == []


@pytest.mark.parametrize('question', [
    'Cerca sul web il mio indirizzo personale',
    'Cerca online il referto medico di un paziente',
    'Puoi controllare online la mia password?',
    'Chi era il mio vicino?',
    'Quando fu firmato il Patto tripartito? Rispondi senza internet.',
    'Cerca sul web la mia storia clinica',
    'Cerca sul web https://127.0.0.1/private',
    'Che tempo fa a casa mia?',
])
def test_feedback_never_researches_private_or_explicitly_local_questions(core, question):
    core.public_references.search = Mock()
    core.public_references.weather = Mock()
    cid, identifier = store_answer(core, 'Una risposta sintetica.', question)
    state = core.give_response_feedback(USER, cid, identifier, 'down')
    assert state['check']['status'] in ('offline', 'unresolved')
    core.public_references.reader.fetch.assert_not_called()
    core.public_references.search.fetch.assert_not_called()
    core.public_references.weather.fetch.assert_not_called()


@pytest.mark.parametrize('reenable', [False, True])
def test_consent_change_during_check_rejects_the_returned_passage(core, reenable):
    service = core.public_references

    def fetch(*args):
        service.configure(False)
        if reenable:
            service.configure(True)
        return [page('Il Patto tripartito fu firmato nel 1940 da Germania, Italia e Giappone.')]

    service.reader.fetch.side_effect = fetch
    cid, identifier = store_answer(core, '1941')
    reply = core.give_response_feedback(USER, cid, identifier, 'down')
    assert reply['check']['status'] == 'offline'
    assert not reply['check']['text']
    assert core.saved_references.entries(USER) == []
    assert core.give_response_feedback(USER, cid, identifier, 'down') == reply
    service.reader.fetch.assert_called_once()


def test_concurrent_clicks_do_not_duplicate_public_check(core):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()
    found = page('Il Patto tripartito fu firmato nel 1940 da Germania, Italia e Giappone.')

    def fetch(*args):
        entered.set()
        assert release.wait(3)
        return [found]

    core.public_references.reader.fetch.side_effect = fetch
    cid, identifier = store_answer(core, '1941')
    with ThreadPoolExecutor(2) as workers:
        future = workers.submit(core.give_response_feedback, USER, cid, identifier, 'down')
        try:
            assert entered.wait(3)
            with pytest.raises(ValueError, match='occupata'):
                core.give_response_feedback(USER, cid, identifier, 'down')
        finally:
            release.set()
        verified = future.result(timeout=3)
    assert verified['check']['status'] == 'corrected'
    assert core.give_response_feedback(USER, cid, identifier, 'down') == verified
    core.public_references.reader.fetch.assert_called_once()
