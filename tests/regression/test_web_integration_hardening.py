"""Exercise the chat boundary with deterministic sources and no network."""
from contextlib import closing
import json
import re
import sqlite3
import time
from unittest.mock import Mock

import pytest

from allma_model.core.learning_insights import response_origin
from allma_model.utils.public_references import PublicReferences, Reference, WikipediaReader


OPENING = 'Chi era hitler?'
EXPANSION = 'Dimmi di più'
TARGETED = 'Contro chi ha fatto scoppiare la seconda guerra mondiale ?'
INVASION = 'In un susseguirsi di atti di sfida alla comunità internazionale, giunse a invadere la Polonia il 1º settembre 1939, provocando così lo scoppio della seconda guerra mondiale.'
BIOGRAPHY = ('Adolf Hitler fu cancelliere tedesco dal gennaio del 1933. '
             'Hitler guidò il Partito Nazionalsocialista. '
             'La dittatura perseguì gli oppositori politici. '
             'Nel 1934, dopo la morte di von Hindenburg, si attribuì il titolo di Führer e Cancelliere del Reich. '
             'La politica estera nazista mirava a espandersi a spese delle popolazioni dell’Europa orientale. ')


def page(title, excerpt, alias=''):
    return Reference(title, excerpt, 'https://it.wikipedia.org/wiki/' + title.replace(' ', '_'),
                     87654321, time.time(), matched_title=alias)


@pytest.fixture
def chat(tmp_path, monkeypatch):
    from allma_model.core.allma_core import ALLMACore

    monkeypatch.chdir(tmp_path)
    core = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'test.db'))
    core._ensure_mobile_llm = lambda: None
    core._llm = Mock()
    core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
    core._llm.generate.return_value = 'Non ho informazioni sufficienti per rispondere.'
    core.decision_runtime.route = Mock(return_value={'status': 'selected', 'choice': 'reason'})
    core.answer_recall.observe = Mock()
    core.public_references.reader = Mock(fetch=Mock(return_value=[]))
    core.public_references.configure(True)
    yield core
    core.close()


def turn(core, owner, conversation, question):
    events = []
    reply = core.process_message(owner, conversation, question,
                                 context={'disable_answer_recall': True, 'benchmark_seed': 42},
                                 stream_callback=events.append)
    return reply, [row['content'] for row in events if row['type'] == 'reference']


def prime_history(core, owner, conversation, document):
    core.public_references.reader.fetch.return_value = [document]
    first, first_activity = turn(core, owner, conversation, OPENING)
    expanded, second_activity = turn(core, owner, conversation, EXPANSION)
    assert first.is_valid and expanded.is_valid
    assert first.metadata['source'] == expanded.metadata['source'] == 'reference_excerpt'
    assert first.content != expanded.content
    assert any(event['state'] == 'searching' for event in first_activity)
    assert all(event['state'] != 'searching' for event in second_activity)
    assert core.public_references.reader.fetch.call_count == 1
    return expanded


@pytest.mark.parametrize('allow_online', [True, False])
def test_specific_followup_reuses_the_documented_fact_without_http_or_model(chat, allow_online):
    owner = 'route-history'
    conversation = chat.start_conversation(owner)
    document = page('Adolf Hitler', BIOGRAPHY + INVASION, 'hitler')
    expanded = prime_history(chat, owner, conversation, document)
    assert INVASION in expanded.content
    chat.public_references.configure(allow_online)
    # Let the transcript, and only the transcript, supply the evidence.
    with closing(sqlite3.connect(chat.db_path)) as db, db:
        db.execute('DELETE FROM public_reference_cache')
    reply, activity = turn(chat, owner, conversation, TARGETED)
    assert reply.is_valid and reply.metadata['source'] == 'reference_excerpt'
    audit = reply.metadata['reference_review']
    assert 'Polonia' in reply.content and '1939' in reply.content
    assert reply.content in expanded.content
    assert audit['citation'] == document.citation()
    assert audit['retrieval_status'] == 'history'
    assert audit['network_used'] is False and audit['truth_verified'] is False
    assert audit['source_id'] == document.identifier
    assert ' '.join(document.text[start:end] for start, end in audit['spans']) == reply.content
    origin = response_origin(reply.metadata, reply.is_valid)
    assert origin['citation']['revision'] == document.revision
    assert origin['via'] == 'history'
    assert all(event['state'] != 'searching' for event in activity)
    assert chat.public_references.reader.fetch.call_count == 1
    chat._llm.generate.assert_not_called()


@pytest.mark.parametrize('context_change', ['new_chat', 'other_profile', 'private_clause', 'subject_change'])
def test_targeted_fact_does_not_reuse_unrelated_or_private_history(chat, context_change):
    original_owner = 'route-history'
    original_conversation = chat.start_conversation(original_owner)
    document = page('Adolf Hitler', BIOGRAPHY + INVASION, 'hitler')
    prime_history(chat, original_owner, original_conversation, document)
    chat.public_references.reader.fetch.reset_mock(return_value=True)
    chat.public_references.reader.fetch.return_value = []

    owner, conversation, query = original_owner, original_conversation, TARGETED
    if context_change == 'new_chat':
        conversation = chat.start_conversation(owner)
    elif context_change == 'other_profile':
        owner = 'other-route-profile'
    elif context_change == 'private_clause':
        query += ' È un dato della mia cartella clinica.'
    else:
        turn(chat, owner, conversation, 'Ti piace il cioccolato?')
        query = 'Dove viene coltivato?'

    reply, activity = turn(chat, owner, conversation, query)
    audit = reply.metadata.get('reference_review', {})
    assert audit.get('retrieval_status') != 'history'
    assert 'invadere la Polonia' not in reply.content
    if context_change == 'private_clause':
        chat.public_references.reader.fetch.assert_not_called()
        assert not any(event['state'] == 'searching' for event in activity)
    for call in chat.public_references.reader.fetch.call_args_list:
        topic = call.args[0]
        assert re.fullmatch(r'[\wÀ-ž ’\'-]{2,104}', topic) and 'cartella clinica' not in topic


def test_missing_targeted_evidence_does_not_fall_back_to_an_invented_fact(chat):
    owner = 'route-history'
    conversation = chat.start_conversation(owner)
    prime_history(chat, owner, conversation, page('Adolf Hitler', BIOGRAPHY, 'hitler'))
    chat.public_references.reader.fetch.return_value = []
    reply, _ = turn(chat, owner, conversation, TARGETED)
    assert not reply.is_valid and reply.metadata['source'] == 'reference_unavailable'
    assert not reply.content
    assert response_origin(reply.metadata, reply.is_valid)['kind'] == 'incomplete'
    chat._llm.generate.assert_not_called()


@pytest.mark.parametrize('question', ['Quanti anni aveva quandp morì?', 'Quanti anni ha vissuto?'])
def test_lifespan_uses_the_cited_dates_across_a_wrong_model_turn(chat, question):
    owner = 'lifespan'
    conversation = chat.start_conversation(owner)
    document = page('Alessandro Magno',
        'Alessandro III di Macedonia (in greco antico Ἀλέξανδρος), conosciuto come Alessandro Magno '
        '(Μέγας Ἀλέξανδρος; Pella, 20 o 21 luglio 356 a.C. – Babilonia, 10 o 11 giugno 323 a.C.) '
        'è stato un condottiero macedone.', 'alessandro magno')
    chat.public_references.reader.fetch.return_value = [document]
    first, _ = turn(chat, owner, conversation, 'Chi era Alessandro Magno?')
    assert first.is_valid and first.metadata['source'] == 'reference_excerpt'
    meta = {'identity_policy': first.metadata['identity_policy'], 'is_valid': True}
    chat.conversational_memory.store_message(
        conversation, 'Quanti anni aveva quandp morì?', meta, 'user', owner)
    chat.conversational_memory.store_message(conversation, 'Morì nel 149 a.C. a 207 anni.',
        dict(meta, source='model_generated'), 'assistant', owner)
    chat.public_references.configure(False)
    with closing(sqlite3.connect(chat.db_path)) as db, db:
        db.execute('DELETE FROM public_reference_cache')
    reply, activity = turn(chat, owner, conversation, question)
    assert reply.is_valid and reply.content == 'Alessandro Magno morì a 32 anni.'
    assert reply.metadata['source'] == 'reference_calculation'
    audit = reply.metadata['reference_review']
    assert audit['source_excerpt'] in first.content and audit['citation'] == document.citation()
    assert audit['retrieval_status'] == 'history' and not audit['network_used']
    assert response_origin(reply.metadata)['label'] == 'Età calcolata dalla fonte'
    assert not activity and chat.public_references.reader.fetch.call_count == 1
    chat._llm.generate.assert_not_called()


def test_named_lifespan_with_year_only_returns_a_range(chat):
    chat.public_references.reader.fetch.return_value = [
        page('William Shakespeare', 'William Shakespeare (1564–1616) è stato un drammaturgo inglese.')]
    owner = 'lifespan'
    reply, _ = turn(chat, owner, chat.start_conversation(owner), 'Quanti anni ha vissuto William Shakespeare?')
    assert reply.is_valid and 'tra 51 e 52 anni' in reply.content
    assert reply.metadata['reference_review']['retrieval_status'] == 'obtained'
    chat._llm.generate.assert_not_called()


def test_unverified_age_requests_do_not_invite_a_model_guess(chat):
    owner = 'lifespan'
    conversation = chat.start_conversation(owner)
    unnamed, activity = turn(chat, owner, conversation, 'Quanti anni ha vissuto?')
    assert unnamed.metadata['source'] == 'clarification' and not activity
    named, _ = turn(chat, owner, conversation, 'Quanti anni ha vissuto Alessandro Magno?')
    assert not named.is_valid and named.metadata['reference_review']['retrieval_status'] == 'lifespan_unverified'
    chat._llm.generate.assert_not_called()


@pytest.mark.parametrize('followup', [True, False])
def test_eligible_fact_retrieves_evidence_under_the_public_event_title(chat, followup):
    owner = 'route-history'
    conversation = chat.start_conversation(owner)
    if followup:
        prime_history(chat, owner, conversation, page('Adolf Hitler', BIOGRAPHY, 'hitler'))
    war = page('Seconda guerra mondiale',
               'La seconda guerra mondiale coinvolse numerosi paesi e più continenti. '
               'La Germania invase la Polonia il 1º settembre 1939 dando inizio alla seconda guerra mondiale. '
               'Negli anni successivi la guerra coinvolse altri paesi.')
    chat.public_references.reader.fetch.reset_mock()
    chat.public_references.reader.fetch.return_value = [war]
    reply, activity = turn(chat, owner, conversation, TARGETED)
    assert reply.is_valid and reply.metadata['source'] == 'reference_excerpt'
    audit = reply.metadata['reference_review']
    assert audit['citation'] == war.citation()
    assert audit['retrieval_status'] == 'obtained' and audit['network_used'] is True
    assert audit['truth_verified'] is False
    assert 'invase la Polonia' in reply.content
    assert all(sentence not in reply.content for sentence in ('numerosi paesi', 'altri paesi'))
    assert any(event['state'] == 'searching' for event in activity)
    assert [call.args[0].casefold() for call in chat.public_references.reader.fetch.call_args_list] == [
        'seconda guerra mondiale']
    chat._llm.generate.assert_not_called()


def test_changed_transcript_cannot_borrow_a_source_receipt(chat):
    owner = 'route-history'
    conversation = chat.start_conversation(owner)
    document = page('Adolf Hitler', BIOGRAPHY + INVASION, 'hitler')
    expanded = prime_history(chat, owner, conversation, document)
    changed = 'La Germania invase i Paesi Bassi, provocando così lo scoppio della seconda guerra mondiale.'

    archive = chat.conversational_memory
    with archive.lock:
        assistant = next(row for row in reversed(archive.messages) if row.role == 'assistant'
                         and row.conversation_id == conversation)
        assert assistant.content == expanded.content
        assistant.content = changed
        archive.save_memory()
    with closing(sqlite3.connect(chat.db_path)) as db, db:
        db.execute('DELETE FROM public_reference_cache')
    chat.public_references.reader.fetch.return_value = []

    reply, _ = turn(chat, owner, conversation, TARGETED)
    assert not reply.is_valid and reply.metadata['source'] == 'reference_unavailable'
    assert 'Paesi Bassi' not in reply.content
    assert 'citation' not in reply.metadata.get('reference_review', {})
    chat._llm.generate.assert_not_called()


@pytest.mark.parametrize('opening,followup,title,lead,answer', [
    ('Che cos’è il Po?', 'Dove sfocia?', 'Po',
     'Il Po è il fiume più lungo d’Italia e attraversa la Pianura Padana.',
     'Il Po sfocia nel mare Adriatico attraverso un ampio delta.'),
    ('Che cos’è la fotosintesi?', 'Che cosa assorbe durante la fotosintesi?', 'Fotosintesi',
     'La fotosintesi è un processo che converte l’energia luminosa in energia chimica.',
     'Durante la fotosintesi le piante assorbono anidride carbonica dall’atmosfera.'),
    ('Chi era Mary Shelley?', 'Che romanzo ha scritto?', 'Mary Shelley',
     'Mary Shelley è stata una scrittrice inglese vissuta nel diciannovesimo secolo.',
     'Mary Shelley scrisse il romanzo Frankenstein, pubblicato nel 1818.'),
])
def test_targeted_followups_use_the_requested_relation(chat, opening, followup, title, lead, answer):
    owner = 'route-relations'
    conversation = chat.start_conversation(owner)
    # Include an unrelated lead before the passage. The follow-up may reuse the
    # answer span and must not simply repeat everything it already displayed.
    document = page(title, f'{lead} {answer}')
    chat.public_references.reader.fetch.return_value = [document]
    first, _ = turn(chat, owner, conversation, opening)
    assert first.is_valid and first.metadata['source'] == 'reference_excerpt'
    reply, activity = turn(chat, owner, conversation, followup)
    assert reply.is_valid and reply.metadata['source'] == 'reference_excerpt'
    assert reply.content == answer
    assert reply.metadata['reference_review']['citation'] == document.citation()
    assert all(event['state'] != 'searching' for event in activity)
    assert chat.public_references.reader.fetch.call_count == 1
    chat._llm.generate.assert_not_called()


def test_river_subject_can_continue_across_verified_adjacent_sentences(chat):
    owner = 'route-river'
    conversation = chat.start_conversation(owner)
    answer = ('Ha origine in Piemonte, bagna Piacenza e Ferrara e segna il confine tra due regioni, '
              'prima di sfociare nel mare Adriatico in un vasto delta.')
    chat.public_references.reader.fetch.return_value = [page('Po',
        'Il Po è un fiume dell’Italia settentrionale. La sua lunghezza, 652 chilometri, '
        'lo rende il più lungo fiume interamente italiano. ' + answer)]
    assert turn(chat, owner, conversation, 'Che cos’è il Po?')[0].is_valid
    response, _ = turn(chat, owner, conversation, 'Dove sfocia?')
    assert response.content == answer
    assert response.metadata['reference_review']['retrieval_status'] in {'history', 'cached'}
    chat.public_references.reader.fetch.assert_called_once()
    chat._llm.generate.assert_not_called()


def test_conflict_can_resolve_the_subject_from_a_source_opening(chat):
    owner = 'route-conflict'
    conversation = chat.start_conversation(owner)
    answer = ("Il conflitto ebbe inizio il 1º settembre 1939, con l'attacco della Germania nazista "
              "alla Polonia, e terminò nel 1945.")
    chat.public_references.reader.fetch.return_value = [page('Seconda guerra mondiale',
        'La seconda guerra mondiale vide contrapporsi le potenze dell’Asse e gli Alleati. ' + answer)]
    response, _ = turn(chat, owner, conversation, TARGETED)
    assert response.content == answer
    assert response.metadata['reference_review']['retrieval_status'] == 'obtained'
    chat._llm.generate.assert_not_called()

def test_location_followup_distinguishes_the_river_from_its_tributary(chat):
    owner = 'route-relations'
    conversation = chat.start_conversation(owner)
    document = page('Po', 'Il Po è il fiume più lungo d’Italia e attraversa la Pianura Padana. '
                    'Il Ticino sfocia nel Po vicino a Pavia. '
                    'Il Po sfocia nel mare Adriatico attraverso un ampio delta.')
    chat.public_references.reader.fetch.return_value = [document]
    initial, _ = turn(chat, owner, conversation, 'Che cos’è il Po?')
    assert initial.is_valid and 'Ticino' in initial.content
    reply, _ = turn(chat, owner, conversation, 'Dove sfocia?')
    assert reply.is_valid and reply.metadata['source'] == 'reference_excerpt'
    assert reply.content == 'Il Po sfocia nel mare Adriatico attraverso un ampio delta.'
    chat._llm.generate.assert_not_called()


def test_revocation_at_lookup_handoff_cannot_deliver_late_online_evidence(tmp_path):
    document = page('Po', 'Il Po è un fiume italiano che sfocia nel mare Adriatico.')
    reader = Mock(fetch=Mock(return_value=[document]))
    references = PublicReferences(tmp_path / 'reference.db', tmp_path / 'web_access.json', reader)
    references.configure(True)

    def activity(event):
        if event['state'] == 'obtained':
            references.configure(False)

    result = references.lookup('Che cos’è il Po?', activity=activity)
    assert not references.status()['enabled']
    reader.fetch.assert_called_once()
    assert result['status'] == 'consent_revoked'
    assert result['references'] == []
    assert references.lookup('Che cos’è il Po?')['status'] == 'local_only'


@pytest.mark.parametrize('reenable', [False, True])
def test_revocation_during_passage_selection_cannot_publish_or_stream_it(chat, monkeypatch, reenable):
    from allma_model.utils import contribution_review

    example = page('Po', 'Il Po è un fiume italiano che sfocia nel mare Adriatico.')
    chat.public_references.reader.fetch.return_value = [example]
    real_select = contribution_review.select_contribution

    def select_and_revoke(*args, **kwargs):
        result = real_select(*args, **kwargs)
        assert result is not None
        chat.public_references.configure(False)
        if reenable:
            chat.public_references.configure(True)
        return result

    monkeypatch.setattr(contribution_review, 'select_contribution', select_and_revoke)
    owner = 'route-revocation'
    conversation = chat.start_conversation(owner)
    events = []
    reply = chat.process_message(owner, conversation, 'Che cos’è il Po?', stream_callback=events.append)
    assert not reply.is_valid and reply.metadata['source'] == 'reference_unavailable'
    assert reply.metadata['reference_review']['retrieval_status'] == 'consent_revoked'
    assert not any(event['type'] == 'answer' and event['content'] for event in events)
    assert not any(row.conversation_id == conversation and example.text in row.content
                   for row in chat.conversational_memory.messages)
    chat._llm.generate.assert_not_called()


@pytest.mark.parametrize('message', [
    'Cerca online il nominativo del cliente',
    'Cerca online nome utente Francesca Rossi',
    'Chi è il paziente Mario Rossi?',
    'Cerca online Mario Rossi CV',
    'Cerca online dove lavora Mario Rossi',
])
def test_sensitive_identity_queries_do_not_leave_the_device(tmp_path, message):
    reader = Mock(fetch=Mock(return_value=[]))
    references = PublicReferences(tmp_path / 'reference.db', tmp_path / 'web_access.json', reader)
    references.configure(True)
    result = references.lookup(message, anchor='Chi era Alan Turing?')
    assert result['status'] == 'not_applicable'
    assert result['network_used'] is False
    reader.fetch.assert_not_called()


@pytest.mark.parametrize('match_found', [True, False])
def test_focused_transport_reads_a_bounded_passage_and_filters_the_fallback(tmp_path, match_found):
    from allma_model.utils.contextual_references import contextual_reference_request

    def response(rows):
        body = json.dumps({'query': {'pages': rows}}).encode()
        result = Mock(status_code=200, iter_content=Mock(return_value=[body]))
        result.__enter__ = Mock(return_value=result)
        result.__exit__ = Mock(return_value=False)
        return result

    def page_row(title, extract):
        return {'ns': 0, 'title': title, 'extract': extract, 'index': 1,
                'fullurl': 'https://it.wikipedia.org/wiki/' + title.replace(' ', '_'),
                'revisions': [{'revid': 123}]}

    title = 'Seconda guerra mondiale'
    vague = page_row(title, 'La seconda guerra mondiale fu un conflitto in cui furono coinvolti diversi paesi.')
    wrong_title = page_row('Invasione della Polonia',
                           'La Germania invase la Polonia dando inizio alla seconda guerra mondiale.')
    supported = page_row(title, wrong_title['extract'])
    session = Mock(get=Mock(side_effect=[response([vague]),
        response([wrong_title, supported] if match_found else [wrong_title, vague])]))
    reader = WikipediaReader(session)
    service = PublicReferences(tmp_path / 'reference.db', tmp_path / 'web_access.json', reader)
    service.configure(True)
    focused = contextual_reference_request(TARGETED)
    result = service.lookup(TARGETED, focused=focused)
    assert session.get.call_count == 2
    direct, fallback = session.get.call_args_list
    assert direct.args == fallback.args == ('https://it.wikipedia.org/w/api.php',)
    assert not direct.kwargs['allow_redirects'] and not fallback.kwargs['allow_redirects']
    direct_params = direct.kwargs['params']
    assert direct_params['titles'] == 'seconda guerra mondiale'
    assert direct_params['exsentences'] == 10 and direct_params['exlimit'] == 1
    assert 'exintro' not in direct_params
    fallback_params = fallback.kwargs['params']
    assert fallback_params['gsrsearch'] == 'seconda guerra mondiale'
    assert fallback_params['gsrlimit'] == 4 and fallback_params['exintro'] == 1
    assert result['status'] == ('obtained' if match_found else 'not_found')
    assert [reference.title for reference in result['references']] == ([title] if match_found else [])
    service.configure(False)
    cached = service.lookup(TARGETED, focused=focused)
    assert cached['status'] == ('cached' if match_found else 'local_only')
    assert cached['network_used'] is False
    assert session.get.call_count == 2
