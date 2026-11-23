"""End-to-end research decisions with bounded simulated transports."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from allma_model.core.learning_insights import response_origin
from allma_model.utils.online_weather import _locations, weather_answer, weather_request
from allma_model.utils.web_search import FEEDS, NativeWebSearch, compose_web_answer, feed_results, public_url


@pytest.fixture
def core(tmp_path, monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    value = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'test.db'))
    value._ensure_mobile_llm = lambda: None
    value._llm = Mock()
    value._llm.generate.side_effect = AssertionError('Unexpected model generation')
    value.public_references.reader = Mock(fetch=Mock(return_value=[]))
    value.public_references.weather = Mock(name='Weather', fetch=Mock())
    value.public_references.weather.name = 'Open-Meteo'
    value.public_references.search = Mock(name='Search', fetch=Mock())
    value.public_references.search.name = 'Ricerca ALLMA'
    yield value
    value.close()


def turn(core, cid, text, stream=None):
    return core.process_message('synthetic', cid, text, stream_callback=stream)


def test_broad_search_offers_a_choice_and_the_selected_topic_uses_the_existing_search(core):
    from allma_model.utils.public_references import Reference

    source = Reference('Napoleone Bonaparte', 'Napoleone Bonaparte fu un politico e generale francese.',
                       'https://it.wikipedia.org/wiki/Napoleone_Bonaparte', 42,
                       datetime.now(timezone.utc).timestamp(), matched_title='Napoleone')
    service = core.public_references
    service.configure(True, expanded=True)
    url = 'https://example.edu/napoleone'
    service.reader.fetch.return_value = [source]
    service.general_search.fetch = Mock(return_value={'status': 'obtained', 'results': [
        {'title': 'Napoleon (film 2023)', 'url': 'https://example.org/film', 'publisher': 'example.org',
         'page_read': True, 'snippet': 'Nel film Napoleone Bonaparte sconfigge i prussiani nella battaglia di Jena.'},
        {'title': 'Il codice civile', 'url': 'https://example.org/codice', 'publisher': 'example.org',
         'page_read': True, 'snippet': 'Per Napoleone Bonaparte il codice civile contava più delle battaglie vinte.'},
        {'title': 'Campagne napoleoniche', 'url': url, 'publisher': 'example.edu', 'page_read': True,
         'snippet': 'Napoleone Bonaparte sconfisse i prussiani nella battaglia di Jena.'},
    ]})
    cid = core.start_conversation('synthetic')
    first = turn(core, cid, 'Cercami Napoleone')
    origin = response_origin(first.metadata, first.is_valid)
    assert first.metadata['source'] == 'research_choices'
    assert first.content == 'Cosa vuoi approfondire su Napoleone Bonaparte?'
    assert [item['label'] for item in origin['choices']] == [
        'Panoramica', 'Biografia', 'Battaglie e campagne', 'Contesto',
    ]
    service.general_search.fetch.assert_not_called()
    service.reader.fetch.assert_called_once()
    answer = turn(core, cid, origin['choices'][2]['query'])
    assert answer.metadata['source'] == 'web_search'
    assert answer.content.startswith('Napoleone Bonaparte sconfisse')
    assert [row['url'] for row in answer.metadata['reference_review']['sources']] == [url]
    assert service.general_search.fetch.call_args.args[0] == 'Napoleone Bonaparte battaglie'
    assert service.general_search.fetch.call_args.kwargs['exclude_adaptations'] is True
    core._llm.generate.assert_not_called()


def test_campaign_focus_selects_a_named_battle_instead_of_an_incidental_mention():
    from allma_model.utils.searx_research import _read_passages

    query = 'Napoleone Bonaparte battaglie'
    aside = 'Per Napoleone Bonaparte il codice civile contava più delle battaglie vinte.'
    battle = 'Napoleone sconfisse i prussiani nella battaglia di Jena.'
    body = f'<p>{aside}</p><p>{battle}</p>'
    assert _read_passages(body, 'text/html', query, 'it', official_title='Napoleone Bonaparte')[1] == battle


def test_campaign_focus_combines_distinct_battles_without_counting_repeated_mentions():
    from allma_model.utils.searx_research import _read_passages

    jena = 'Napoleone sconfisse i prussiani nella battaglia di Jena.'
    duplicate = 'Napoleone riportò una vittoria decisiva nella battaglia di Jena.'
    leipzig = 'Napoleone fu sconfitto dalla coalizione nella battaglia di Lipsia.'
    aside = 'Per Napoleone Bonaparte il codice civile contava più delle battaglie vinte.'
    body = ''.join(f'<p>{passage}</p>' for passage in (aside, jena, duplicate, leipzig))
    passage = _read_passages(body, 'text/html', 'Napoleone Bonaparte battaglie', 'it',
                             official_title='Napoleone Bonaparte')[1]
    assert passage.count('Jena') == 1 and 'Lipsia' in passage
    assert 'codice civile' not in passage


def test_overview_of_a_city_keeps_the_right_geographic_scope(core):
    from allma_model.utils.public_references import Reference

    city_url = 'https://es.wikipedia.org/wiki/Buenos_Aires'
    area_url = 'https://es.wikipedia.org/wiki/%C3%81rea_Metropolitana_de_Buenos_Aires'
    time = datetime.now(timezone.utc).timestamp()
    city = Reference('Buenos Aires', 'Buenos Aires es la capital de Argentina.', city_url, 42, time)
    area = Reference('Área Metropolitana de Buenos Aires',
                     'El Área Metropolitana de Buenos Aires reúne la capital y municipios vecinos.',
                     area_url, 62, time)
    service = core.public_references
    service.configure(True, expanded=True)
    service.reader.fetch.side_effect = [[city], [area, city]]
    service.general_search.fetch = Mock(return_value={'status': 'not_found', 'results': []})
    cid = core.start_conversation('synthetic')
    choices = response_origin(turn(core, cid, 'Búscame Buenos Aires').metadata)['choices']
    assert choices[0]['label'] == 'Panorama general'
    reply = turn(core, cid, choices[0]['query'])
    assert reply.metadata['source'] == 'reference_excerpt'
    assert reply.metadata['reference_review']['public_topic'] == 'Buenos Aires'
    assert 'municipios' not in reply.content
    assert city_url in str(reply.metadata['reference_review'])
    assert area_url not in str(reply.metadata['reference_review'])
    service.general_search.fetch.assert_not_called()


def test_overview_fallback_excludes_a_larger_area_from_any_publisher():
    pages = [
        {'title': 'Área Metropolitana de Buenos Aires', 'publisher': 'es.wikipedia.org',
         'url': 'https://es.wikipedia.org/wiki/%C3%81rea_Metropolitana_de_Buenos_Aires',
         'snippet': 'El Área Metropolitana de Buenos Aires reúne la capital y municipios vecinos.', 'page_read': True},
        {'title': 'Área Metropolitana de Buenos Aires', 'publisher': 'example.edu',
         'url': 'https://example.edu/area-metropolitana',
         'snippet': 'El Área Metropolitana de Buenos Aires reúne la capital y municipios vecinos.', 'page_read': True},
        {'title': 'Buenos Aires', 'publisher': 'example.org', 'url': 'https://example.org/ciudad',
         'snippet': 'Buenos Aires es la capital de Argentina y tiene un gobierno autónomo.', 'page_read': True},
    ]
    verified = compose_web_answer('Buenos Aires', pages, read_pages=True, overview_topic='Buenos Aires')
    assert [item['url'] for item in verified] == ['https://example.org/ciudad']


def test_broad_search_preserves_internet_consent_and_rejects_private_commands(core):
    service = core.public_references
    service.general_search.fetch = Mock()
    cid = core.start_conversation('synthetic')
    reply = turn(core, cid, 'Cercami il sistema solare')
    assert reply.metadata['source'] == 'research_choices'
    assert not reply.metadata['reference_review']['network_used']
    assert reply.content == 'Cosa vuoi approfondire sul sistema solare?'
    assert [choice['label'] for choice in response_origin(reply.metadata)['choices']] == [
        'Panoramica', 'Struttura', 'Come funziona', 'Origine',
    ]
    choice = response_origin(reply.metadata)['choices'][0]['query']
    assert turn(core, cid, choice).metadata['reference_review']['retrieval_status'] == 'local_only'
    service.configure(True, expanded=True)
    rejected = turn(core, cid, 'Cercami il mio indirizzo')
    assert rejected.metadata['source'] == 'reference_unavailable'
    assert not rejected.metadata['reference_review']['network_used']
    service.reader.fetch.assert_not_called()
    service.general_search.fetch.assert_not_called()


@pytest.mark.parametrize(('command', 'profile', 'expected'), [
    ('Búscame Buenos Aires', 'Buenos Aires es la capital de Argentina.', 'Geografía'),
    ('Cherche-moi le Boléro', 'Le Boléro est un ballet du compositeur Maurice Ravel.', 'Œuvres et contributions'),
    ('Search for quantum computing', 'Quantum computing uses systems with a quantum state.', 'How it works'),
])
def test_research_choices_adapt_the_facets_to_the_topic(command, profile, expected):
    from allma_model.utils.public_references import Reference
    from allma_model.utils.research_choices import broad_topic, focus_choices, search_command

    language, query = search_command(command)
    topic = broad_topic(query)
    assert topic
    _, origin = focus_choices(topic, language, Reference(topic, profile, '', 0, 0))
    assert expected in [item['label'] for item in origin['choices']]


def test_focused_command_does_not_offer_choices(core):
    service = core.public_references
    service.configure(True, expanded=True)
    service.general_search.fetch = Mock(return_value={'status': 'not_found', 'results': []})
    reply = turn(core, core.start_conversation('synthetic'), 'Cercami le battaglie di Napoleone')
    assert reply.metadata['source'] == 'reference_unavailable'
    assert service.general_search.fetch.call_args.args[0] == 'battaglie di Napoleone'
    core._llm.generate.assert_not_called()


def test_expanded_search_reads_pages_only_for_explicit_public_requests(core, monkeypatch):
    from allma_model.utils import searx_research

    query = 'modalità solo HTTPS Firefox Mozilla'
    url = 'https://support.mozilla.org/it/kb/modalita-solo-https-firefox'
    expected = 'La modalità solo HTTPS di Firefox prova a connettersi ai siti usando una connessione sicura.'
    discovery = Mock(return_value={'results': [
        {'title': 'Modalità solo HTTPS in Firefox', 'url': url, 'content': 'Testo di anteprima da non riportare.'},
        {'title': 'Pagina privata', 'url': 'http://127.0.0.1:8000/'},
    ]})
    page = Mock(return_value=(url, 'text/html', '<html lang="it"><p>' + expected + '</p></html>'))
    monkeypatch.setattr(searx_research, 'request_json', discovery)
    monkeypatch.setattr(searx_research, 'read_public_page', page)
    service = core.public_references
    service.configure_expanded(True)
    owner = 'synthetic'
    cid = core.start_conversation(owner)
    reply = turn(core, cid, 'Cerca su Internet ' + query)
    assert not reply.metadata['reference_review']['network_used']
    discovery.assert_not_called()
    service.configure(True)
    reply = turn(core, cid, 'Cerca su Internet ' + query)
    assert reply.metadata['source'] == 'web_search'
    assert reply.content == expected + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    assert service.web_link_allowed(url)
    assert discovery.call_args.kwargs['params']['q'] == query
    assert discovery.call_args.args[1] == searx_research.COMPANION_URL
    page.assert_called_once()
    core._llm.generate.assert_not_called()


def test_expanded_research_prefers_the_exact_official_command(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://doc.rust-lang.org/cargo/commands/cargo-check.html'
    description = 'Check a local package and all of its dependencies for errors.'
    page = '<html lang="en"><h1>cargo-check</h1><h2>Description</h2><p>' + description + '</p></html>'
    monkeypatch.setattr(searx_research, 'read_public_page', Mock(return_value=(url, 'text/html', page)))
    discovery = Mock(side_effect=AssertionError('Official manual already provided evidence'))
    monkeypatch.setattr(searx_research, 'request_json', discovery)
    core.public_references.configure(True)
    core.public_references.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search online Rust cargo check documentation')
    assert reply.content == description + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    discovery.assert_not_called()


def test_expanded_research_distinguishes_underscored_api_symbols(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.web_search import search_query

    url = 'https://docs.python.org/3/library/argparse.html'
    exact = 'The ArgumentParser.add_argument() method attaches individual argument specifications to the parser.'
    page = ('<html lang="en"><h1>argparse</h1><p>The add_argument_group() method also exposes an add_argument() '
            'method like a regular parser.</p><p>' + exact + '</p></html>')
    monkeypatch.setattr(searx_research, 'read_public_page', Mock(return_value=(url, 'text/html', page)))
    core.public_references.configure(True)
    core.public_references.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search online Python argparse add_argument documentation')
    assert reply.content == exact + ' [1]'
    assert search_query('Search online Python __private_token', explicit=True) is None
    assert search_query('Search online Python add_argument my login', explicit=True) is None


def test_technical_python_reference_parses_the_exact_decorator_section(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://docs.python.org/3/library/contextlib.html'
    definition = 'This decorator creates with statement context managers without defining __enter__().'
    behavior = 'The generator yields once and the with statement then runs its body.'
    page = ('<html lang="en"><h1>contextlib</h1>'
            '<dl><dt>@contextlib.asynccontextmanager¶</dt><dd>'
            '<p>An asynchronous generator can define an async with context manager.</p></dd></dl>'
            '<dl><dt>@contextlib.contextmanager¶</dt><dd><p>' + definition
            + '</p><p>' + behavior + '</p></dd></dl></html>')
    read = Mock(return_value=(url, 'text/html', page))
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    core.public_references.configure(True, expanded=True)
    answer = turn(core, core.start_conversation('synthetic'), 'Search online Python contextlib.contextmanager documentation')
    assert answer.content == definition.replace('__enter__()', '`__enter__()`') + ' […] ' + behavior + ' [1]'
    assert answer.metadata['reference_review']['sources'][0]['url'] == url
    assert answer.metadata['reference_review']['sources'][0]['excerpt'] == definition + ' […] ' + behavior
    read.assert_called_once()
    core._llm.generate.assert_not_called()


def test_technical_python_keeps_a_definition_ending_with_an_example_colon():
    from allma_model.utils.searx_research import _read_passages
    from allma_model.utils.technical_search import technical_reference

    query = 'Python pathlib.Path documentation'
    definition = 'This class represents concrete paths for the local operating system'
    page = ('<html lang="en"><dt>class pathlib.Path(*pathsegments)¶</dt><dd><p>'
            + definition + ':</p><pre>Path("example")</pre>'
            '<p>Arguments are specified as for the base class.</p></dd></html>')
    match = _read_passages(page, 'text/html', query, 'en', technical=technical_reference(query))
    assert match[1] == definition + '.'


def test_public_ipv6_standard_question_does_not_open_personal_address_searches(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.technical_search import technical_reference
    from allma_model.utils.web_search import search_query

    question = 'Quanti bit ha un indirizzo IPv6?'
    reference = technical_reference(question)
    excerpt = 'Gli indirizzi IPv6 hanno una lunghezza complessiva di 128 bit.'
    read = Mock(return_value=(reference.url, 'text/html', '<html lang="it"><p>' + excerpt + '</p></html>'))
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    core.public_references.configure(True, expanded=True)
    answer = turn(core, core.start_conversation('synthetic'), 'Cerca su Internet ' + question)
    assert answer.content == excerpt + ' [1]'
    for query in ('Qual è il mio indirizzo IPv6?', 'Quanti bit ha un indirizzo IPv6 2001:db8::1?',
                  'Quanti bit ha un indirizzo IPv6? Il mio è 2001:db8::1',
                  'Cerca il codice del mio account HTTP 304'):
        assert search_query(query) is None
    blocked = turn(core, core.start_conversation('synthetic'), 'Cerca su Internet il mio indirizzo IPv6')
    assert not blocked.metadata['reference_review']['network_used']
    core.public_references.configure(False)
    offline = turn(core, core.start_conversation('synthetic'), 'Cerca su Internet ' + question)
    assert not offline.metadata['reference_review']['network_used']
    read.assert_called_once()
    core._llm.generate.assert_not_called()


def test_technical_ipv6_can_use_the_wrapped_standard_when_localized_documentation_is_unreachable(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://www.rfc-editor.org/rfc/rfc4291.txt'
    excerpt = 'IPv6 addresses are 128-bit identifiers for interfaces and sets of interfaces.'
    read = Mock(side_effect=[None, (url, 'text/plain',
        '2. IPv6 Addressing\n\n   IPv6 addresses are 128-bit identifiers for interfaces and sets of\n   interfaces.\n\n')])
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    core.public_references.configure(True, expanded=True)
    answer = turn(core, core.start_conversation('synthetic'), 'Quanti bit ha un indirizzo IPv6?')
    assert answer.content == excerpt + ' [1]'
    assert answer.metadata['reference_review']['sources'][0]['url'] == url
    assert read.call_count == 2
    core._llm.generate.assert_not_called()


def test_expanded_research_cannot_use_a_search_title_to_supply_missing_evidence(monkeypatch):
    from allma_model.utils import searx_research

    unrelated = 'https://example.com/overview'
    relevant = 'https://example.org/manual'
    monkeypatch.setattr(searx_research, 'request_json', Mock(return_value={'results': [
        {'title': 'Configuring package timeouts', 'url': unrelated},
        {'title': 'Package guide', 'url': relevant},
    ]}))
    expected = 'Package timeouts can be configured independently for each mirror.'
    bodies = {
        unrelated: '<p>I have tried configuring package timeouts but cannot get the command to work.</p>'
                   '<p>Package download options are available from the toolbar in the application.</p>',
        relevant: '<p>' + expected + '</p>',
    }
    monkeypatch.setattr(searx_research, 'read_public_page',
                        lambda url, *_: (url, 'text/html', bodies[url]))
    result = searx_research.SearxResearch().fetch('package timeouts', 'en', False, None, lambda: True)
    assert [(row['url'], row['snippet']) for row in result['results']] == [(relevant, expected)]


def test_expanded_search_revocation_discards_pages_and_stops_fallback(core):
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    def revoke(*args):
        service.configure_expanded(False)
        return {'status': 'obtained', 'results': [{
            'url': 'https://support.mozilla.org/it/kb/modalita-solo-https-firefox',
            'publisher': 'support.mozilla.org', 'title': 'Solo HTTPS Firefox',
            'snippet': 'La modalità solo HTTPS di Firefox prova a usare una connessione sicura.',
            'page_read': True,
        }]}
    service.general_search.fetch = Mock(side_effect=revoke)
    reply = turn(core, core.start_conversation('synthetic'), 'Cerca su Internet modalità solo HTTPS Firefox')
    assert not reply.content and reply.metadata['reference_review']['retrieval_status'] == 'consent_revoked'
    service.search.fetch.assert_not_called()


def test_expanded_routes_a_natural_public_question_and_its_followup(core):
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    url = 'https://culture.example.org/venice'
    passages = [
        'L’origine del Carnevale di Venezia è documentata da testimonianze medievali.',
        'L’origine del Carnevale di Venezia rimane discussa tra gli studiosi della città.',
    ]
    service.general_search.fetch = Mock(side_effect=[{'status': 'obtained', 'results': [{
        'url': url, 'title': 'Carnevale di Venezia', 'publisher': 'culture.example.org',
        'snippet': passage, 'page_read': True,
    }]} for passage in passages])
    cid = core.start_conversation('synthetic')
    question = 'Qual è l’origine del Carnevale di Venezia?'
    reply = turn(core, cid, question)
    assert reply.is_valid and reply.content == passages[0] + ' [1]'
    service.general_search.fetch.assert_called_once()
    first_query = service.general_search.fetch.call_args.args[0]
    assert first_query == question.rstrip('?')
    reply = turn(core, cid, 'Dimmi di più')
    assert reply.is_valid and reply.content == passages[1] + ' [1]'
    assert service.general_search.fetch.call_args.args[0] == first_query
    assert service.general_search.fetch.call_args.kwargs['previous'] == (passages[0],)
    core._llm.generate.assert_not_called()


def test_expanded_uses_dated_articles_for_news_outside_the_known_feeds(core, monkeypatch):
    from allma_model.utils import searx_research

    old, new = 'https://science.example.org/archive', 'https://science.example.org/news/experiment'
    transport = Mock(return_value={'results': [
        {'url': old, 'title': 'Archival press release'},
        {'url': new, 'title': 'A new release'},
    ]})
    today = datetime.now(timezone.utc).date()
    body = '<p>Il CERN ha pubblicato una nuova analisi dei dati raccolti durante l’esperimento.</p>'
    def page(url, *_):
        stamp = today if url == new else today - timedelta(days=60)
        return url, 'text/html', f'<html lang="it"><meta property="article:published_time" content="{stamp}">' + body
    monkeypatch.setattr(searx_research, 'request_json', transport)
    monkeypatch.setattr(searx_research, 'read_public_page', page)
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Ultime notizie sul CERN')
    review = reply.metadata['reference_review']
    assert reply.is_valid and review['fresh']
    assert [row['url'] for row in review['sources']] == [new]
    assert transport.call_args.kwargs['params']['categories'] == 'news,general'


def test_public_article_body_remains_available_without_the_companion(core, monkeypatch):
    import requests
    from allma_model.utils import online_transport, searx_research, web_search

    first = 'https://es.wikipedia.org/wiki/Ada_Lovelace'
    expected = 'Lovelace examinó la máquina analítica y describió cómo la máquina podía ejecutar una secuencia de operaciones.'
    companion = Mock()

    def transport(session, url, cancelled, allowed, *, params, **kwargs):
        if url == searx_research.COMPANION_URL:
            companion()
            raise requests.ConnectionError()
        if params.get('generator') == 'search':
            return {'query': {'pages': [{'ns': 0, 'fullurl': first, 'title': 'Ada Lovelace',
                                         'revisions': [{'revid': 11}], 'extract': 'Texto introductorio.'}]}}
        assert params.get('oldid') == '11'
        return {'parse': {'revid': 11, 'title': 'Ada Lovelace', 'text': f'<p>{expected}</p>'}}

    for module in (searx_research, online_transport, web_search):
        monkeypatch.setattr(module, 'request_json', transport)
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Busca en internet Ada Lovelace máquina analítica')
    assert reply.is_valid and reply.content == expected + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == first + '?oldid=11'
    companion.assert_not_called()


def test_general_web_search_uses_direct_index_when_companion_is_missing(core, monkeypatch):
    import requests
    from allma_model.utils import searx_research

    url = 'https://support.mozilla.org/en-US/kb/https-only-prefs'
    excerpt = 'Firefox HTTPS-Only Mode tries to upgrade connections to secure HTTPS.'
    calls = []

    def discover(session, endpoint, cancelled, allowed, *, params, **kwargs):
        calls.append((endpoint, params['q']))
        if endpoint == searx_research.COMPANION_URL:
            raise requests.ConnectionError()
        assert endpoint == searx_research.MWMBL_SEARCH
        return {'results': [{'url': url, 'title': 'Firefox HTTPS-Only Mode',
                             'content': 'Unverified text from the index.'}]}

    index = Mock(side_effect=discover)
    page = Mock(return_value=(url, 'text/html', f'<html lang="en"><p>{excerpt}</p></html>'))
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', Mock(return_value=[]))
    monkeypatch.setattr(searx_research, 'request_json', index)
    monkeypatch.setattr(searx_research, 'read_public_page', page)
    service = core.public_references
    service.configure_expanded(True)
    cid = core.start_conversation('synthetic')
    question = 'Search online Firefox Mozilla HTTPS-Only Mode'
    reply = turn(core, cid, question)
    assert reply.metadata['reference_review']['retrieval_status'] == 'local_only'
    index.assert_not_called()
    page.assert_not_called()

    service.configure(True)
    reply = turn(core, cid, question)
    assert reply.is_valid and reply.content == excerpt + ' [1]'
    assert [endpoint for endpoint, _ in calls] == [searx_research.COMPANION_URL, searx_research.MWMBL_SEARCH]
    assert {query.casefold() for _, query in calls} == {'firefox mozilla https-only mode'}
    page.assert_called_once()
    core._llm.generate.assert_not_called()


def test_research_refines_a_failed_relation_and_does_not_read_a_revision_twice(core, monkeypatch):
    from allma_model.utils import searx_research, web_search

    question = 'When was the Meridian Museum opened?'
    failed = 'https://en.wikipedia.org/wiki/Meridian_Museum?oldid=21'
    related = 'https://en.wikipedia.org/wiki/Meridian_Museum_Annex?oldid=22'
    archive = 'https://en.wikipedia.org/wiki/Meridian_Museum_history?oldid=23'
    source = 'The Meridian Museum opened to the public in 1912.'
    rows = [
        {'url': failed, 'title': 'Meridian Museum', 'snippet': 'A search preview cannot prove the date.'},
        {'url': related, 'title': 'Meridian Museum Annex', 'snippet': 'The annex opened in 1962.'},
        {'url': archive, 'title': 'Meridian Museum history', 'snippet': source},
    ]
    discovery = Mock(side_effect=[rows[:2], [rows[0], rows[2]]])
    monkeypatch.setattr(web_search, 'encyclopedic_results', discovery)
    transport = Mock(side_effect=[
        searx_research.ProviderError(503),
        {'parse': {'revid': 22, 'title': rows[1]['title'], 'text': '<p>The annex to the museum opened to visitors in 1962.</p>'}},
        {'parse': {'revid': 23, 'title': rows[2]['title'], 'text': f'<p>{source}</p>'}},
    ])
    monkeypatch.setattr(searx_research, 'request_json', transport)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), question)
    assert reply.content == source + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == archive
    assert [call.args[1] for call in discovery.call_args_list] == ['meridian museum', 'meridian museum date']
    assert [call.kwargs['params']['oldid'] for call in transport.call_args_list] == ['21', '22', '23']
    core._llm.generate.assert_not_called()


def test_general_search_tries_another_index_after_a_companion_miss(core, monkeypatch):
    from allma_model.utils import searx_research

    source = 'https://example.edu/museum'
    passage = 'The Meridian Museum opened to the public in 1912.'
    discovery = Mock(side_effect=[
        {'results': []}, {'results': []}, {'results': []},
        {'results': [{'url': source, 'title': 'Museum archive', 'content': 'A different date in the preview.'}]},
    ])
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', Mock(return_value=[]))
    monkeypatch.setattr(searx_research, 'request_json', discovery)
    monkeypatch.setattr(searx_research, 'read_public_page',
                        Mock(return_value=(source, 'text/html', f'<p>{passage}</p>')))
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'When was the Meridian Museum opened?')
    assert reply.content == passage + ' [1]'
    assert discovery.call_args.args[1] == searx_research.MWMBL_SEARCH
    assert discovery.call_args.kwargs['params']['q'] == 'meridian museum date'


def test_geographic_recovery_requires_an_explicit_alias_in_the_same_paragraph():
    from allma_model.utils.fact_search import fact_question
    from allma_model.utils.searx_research import _read_passages

    query = 'Which seas does the Meridian Strait connect'
    scope = fact_question(query)
    alias = 'The East Channel or Meridian Strait is a natural strait along the coast.'
    passage = 'The East Channel connects the North Sea to the Baltic Sea.'
    unlinked = 'The Meridian Strait is near the East Channel and several other waterways.'

    def read(body):
        return _read_passages(body, 'text/html', query, 'en', fact=scope, official_title='East Channel')

    assert read(f'<p>{alias} {passage}</p>')[1] == alias + ' ' + passage
    assert read(f'<p>{alias}</p><p>{passage}</p>') is None
    assert read(f'<p>{unlinked} {passage}</p>') is None


def test_date_search_distinguishes_the_beginning_from_a_later_event():
    from allma_model.utils.fact_search import fact_question
    from allma_model.utils.searx_research import _read_passages

    query = 'Cuándo comenzó la independencia de México'
    scope = fact_question(query)
    previous = 'La colonia tuvo cambios políticos y económicos decisivos.'
    passage = 'La guerra por la independencia mexicana comenzó en 1810 y terminó en 1821.'
    assert not scope.supports('La guerra por la independencia mexicana terminó en 1821.')
    assert _read_passages(f'<p>{previous}\u200b {passage}</p>', 'text/html', query, 'es', fact=scope)[1] == passage


def test_city_search_keeps_an_explicit_location_in_the_article_lead():
    from allma_model.utils.fact_search import fact_question
    from allma_model.utils.searx_research import _read_passages

    query = 'En qué ciudad está el Museo del Meridian'
    scope = fact_question(query)
    heading = 'Museo del Meridian'
    lead = 'El Museo del Meridian conserva una extensa colección de pintura.'
    passage = 'Con sede en Sevilla, España, organiza también ciclos de música.'

    def read(body, title=heading):
        return _read_passages(body, 'text/html', query, 'es', fact=scope, official_title=title)

    assert read(f'<p>{lead}\u200b {passage}</p>')[1] == lead + ' ' + passage
    assert read(f'<p>{lead}</p><p>{passage}</p>') is None
    assert read(f'<p>{lead} {passage}</p>', 'Exposición Meridian') is None


def test_date_retry_rejects_an_older_homonym_even_from_the_alternate_index(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://en.wikipedia.org/wiki/Treaty_of_Meridian_(1843)'
    passage = 'The Treaty of Meridian was signed in 1843 by both countries.'
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', Mock(return_value=[]))
    monkeypatch.setattr(searx_research, 'request_json', Mock(return_value={
        'results': [{'url': url, 'title': 'Treaty of Meridian'}],
    }))
    monkeypatch.setattr(searx_research, 'read_public_page',
                        Mock(return_value=(url, 'text/html', f'<p>{passage}</p>')))
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'When was the Treaty of Meridian signed?')
    assert reply.metadata['reference_review']['retrieval_status'] == 'insufficient_evidence'
    assert not reply.content
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize(('failure', 'expected'), [(True, 'index_unavailable'), (False, 'not_found')])
def test_direct_index_distinguishes_outage_from_no_matching_results(monkeypatch, failure, expected):
    from allma_model.utils import searx_research

    transport = Mock(side_effect=searx_research.ProviderError(429)) if failure else Mock(return_value={'results': []})
    monkeypatch.setattr(searx_research, 'request_json', transport)
    research = searx_research.SearxResearch(use_companion=False)
    result = research.fetch('CERN new experiment', 'en', True, None, lambda: True)
    assert result == {'status': expected, 'results': []}
    assert transport.call_args.args[1] == searx_research.MWMBL_SEARCH
    if failure:
        research.fetch('CERN research update', 'en', True, None, lambda: True)
        transport.assert_called_once()


def test_research_uses_an_actual_abstract_when_searching_for_studies(core, monkeypatch):
    from allma_model.utils import searx_research

    expected = 'Graph neural networks can encode the relationship between pairs of connected objects.'
    transport = Mock(return_value={'resultList': {'result': [{
        'source': 'MED', 'id': '42', 'title': 'Graph learning', 'abstractText': f'<p>{expected}</p>',
    }]}})
    monkeypatch.setattr(searx_research, 'request_json', transport)
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search online graph neural networks scientific papers')
    assert reply.content == expected + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == 'https://europepmc.org/article/MED/42'
    assert transport.call_args.args[1] == searx_research.EUROPE_PMC


def test_origin_evidence_is_about_the_question_subject():
    from allma_model.utils.searx_research import _read_passages

    correct = 'The Bauhaus was founded by architect Walter Gropius in Weimar.'
    html = ('<p>The Vkhutemas was a school founded in Moscow and compared to Bauhaus.</p>'
            '<p>Founded a year after the Bauhaus school, Vkhutemas has close parallels with it.</p>'
            f'<p>{correct}</p>')
    result = _read_passages(html, 'text/html', 'What is the origin of the Bauhaus school',
                            'en', official_title='Bauhaus')
    assert result[1] == correct


def test_scholarly_search_uses_crossref_when_europe_pmc_times_out(core, monkeypatch):
    import requests
    from allma_model.utils import searx_research

    excerpt = 'Graph neural networks can represent relationships between connected objects through message passing.'
    attempts = []

    def transport(session, url, cancelled, allowed, **kwargs):
        attempts.append(url)
        if url == searx_research.EUROPE_PMC:
            raise requests.ReadTimeout()
        assert url == searx_research.CROSSREF_WORKS
        assert kwargs['params']['filter'] == 'has-abstract:true'
        return {'message': {'items': [
            {'DOI': '10.1234/graph/v1', 'title': ['Graph learning'], 'abstract': '<jats:p>Graph neural networks can model complex graphs.</jats:p>'},
            {'DOI': '10.1234/graph/v2', 'title': ['Graph learning'], 'abstract': f'<jats:p>{excerpt}</jats:p>'},
            {'DOI': '10.1234/other', 'title': ['Unrelated'], 'abstract': '<jats:p>This study examines soil bacteria.</jats:p>'},
        ]}}

    monkeypatch.setattr(searx_research, 'request_json', transport)
    core.public_references.configure(True)
    core.public_references.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search online graph neural networks scientific papers')
    assert reply.content == excerpt + ' [1]'
    assert [source['url'] for source in reply.metadata['reference_review']['sources']] == ['https://doi.org/10.1234/graph/v2']
    assert attempts == [searx_research.EUROPE_PMC, searx_research.CROSSREF_WORKS]


@pytest.mark.parametrize(('question', 'language'), [
    ('Cercami su internet, chi é stato il primo uomo a scoprire il continente americano', 'it'),
    ('Chi fu il primo a scoprire l’America?', 'it'),
    ('Search online who was the first person to discover the Americas?', 'en'),
    ('Busca en internet quién fue la primera persona en descubrir América', 'es'),
])
def test_ambiguous_discovery_verifies_each_historical_scope_before_answering(core, monkeypatch, question, language):
    from allma_model.utils import searx_research
    from allma_model.utils.research_scopes import _AMERICAS

    known = {
        _AMERICAS[0].sources[0].url: 'American Indians have lived in the Western Hemisphere for millennia.',
        _AMERICAS[1].sources[0].url: 'This 1,000-year-old Viking colony is the first known European settlement in North America.',
        _AMERICAS[2].sources[0].url: 'Columbus reached the Bahamian islands in the Caribbean in October 1492.',
    }
    mocked_page = Mock(side_effect=lambda url, *_: (url, 'text/html', '<html lang="en"><p>' + known[url] + '</p>'))
    monkeypatch.setattr(searx_research, 'read_public_page', mocked_page)
    index_search = Mock(side_effect=AssertionError('These facets have documented source pages'))
    monkeypatch.setattr(searx_research, 'request_json', index_search)
    service = core.public_references
    service.configure(True)
    service.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), question)
    audit = reply.metadata['reference_review']
    assert reply.is_valid and audit['coverage'] == 'full_scope'
    assert [source['facet'] for source in audit['sources']] == ['people', 'europe', 'voyage']
    assert [source['url'] for source in audit['sources']] == list(known)
    assert reply.content.startswith({'it': 'I primi abitanti', 'en': 'The earliest inhabitants',
                                     'es': 'Los primeros habitantes'}[language])
    assert '[1]' in reply.content and '[2]' in reply.content and '1492. [3]' in reply.content
    index_search.assert_not_called()
    service.reader.fetch.assert_not_called()
    core._llm.generate.assert_not_called()


def test_inaccessible_or_irrelevant_sources_leave_an_explicit_partial_result(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.research_scopes import _AMERICAS

    european = _AMERICAS[1].sources[0].url
    def read(url, *_):
        if url == european:
            body = 'The 1,000-year-old Viking colony marks the first known European settlement in North America.'
            return (url, 'text/html', '<p>' + body + '</p>')
        return (url, 'text/html', '<p>Welcome to the library. Browse our collections and events.</p>')
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    monkeypatch.setattr(searx_research, 'request_json', Mock(return_value={}))
    core.public_references.configure(True)
    core.public_references.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Cerca su internet chi ha scoperto l’America')
    assert reply.metadata['reference_review']['coverage'] == 'partial_scope'
    assert 'solo una parte' in reply.content and '1492' not in reply.content
    assert [source['facet'] for source in reply.metadata['reference_review']['sources']] == ['europe']


@pytest.mark.parametrize(('query', 'locale', 'accepted', 'rejected'), [
    ('Who was the first person to walk on the Moon', 'en',
     'Neil Armstrong was the first man to walk on the Moon in July 1969.',
     'Armstrong discussed his first chance to walk on the Moon in the interview.'),
    ('Who was the first woman to fly in space', 'en',
     'Valentina Tereshkova was the first woman in space, having flown aboard Vostok 6.',
     'Nguyen was the first woman of Vietnamese descent to fly to space on that mission.'),
    ('Chi fu il primo uomo a scalare l’Everest', 'it',
     'Hillary e Norgay furono i primi alpinisti a raggiungere la vetta dell’Everest.',
     'La prima ascensione filmata dell’Everest fu raccontata dalla spedizione svizzera.'),
])
def test_primacy_keeps_the_relation_and_rejects_a_different_record(query, locale, accepted, rejected):
    from allma_model.utils.research_intent import primacy_question

    plan = primacy_question(query, locale)
    assert plan is not None and plan.supports(accepted)
    assert not plan.supports(rejected)
    assert len(plan.discovery_queries()[0]) < len(query)


def test_a_fiction_article_does_not_verify_an_event_mentioned_in_its_plot():
    from allma_model.utils import searx_research
    from allma_model.utils.research_intent import primacy_question

    query = 'Who was the first person to walk on the Moon'
    paper = ('<p>A Walk on the Moon is a 1999 romantic drama film.</p>'
             '<p>Armstrong was the first man to walk on the moon, which the town celebrated.</p>')
    assert searx_research._read_passages(paper, 'text/html', query, 'en',
                                         primacy=primacy_question(query, 'en')) is None


def test_discovery_binds_the_ordinal_to_the_requested_object():
    from allma_model.utils.research_intent import primacy_question

    plan = primacy_question('Who first discovered penicillin', 'en')
    assert not plan.supports('It was the first discovered mechanism of penicillin resistance.')
    assert not plan.supports('Cecil George Paine was the first to use penicillin to treat eye infection.')
    assert not plan.supports('A researcher first discovered penicillin resistance in this organism.')
    assert plan.supports('Alexander Fleming first discovered penicillin in 1928.')
    account = 'Penicillin was discovered in 1928 by Alexander Fleming.'
    assert plan.supports(account, article_topic='Penicillin')
    assert not plan.supports(account, article_topic='Antibiotic resistance')


def test_first_solo_flight_requires_the_requested_route_and_flight_scope():
    from allma_model.utils.research_intent import primacy_question

    plan = primacy_question('Who was the first person to fly solo across the Atlantic', 'en')
    assert plan.discovery_queries()[0] == 'first solo transatlantic flight'
    assert plan.supports('Lindbergh completed the first solo crossing of the Atlantic, landing in Paris in 1927.')
    assert plan.supports('Lindbergh piloted the first solo, nonstop flight across the Atlantic.')
    assert not plan.supports('Amelia Earhart was the first woman to make a nonstop solo transatlantic flight.')
    assert not plan.supports('He completed the first solo flight across the Atlantic in a balloon.')
    assert not plan.supports('A sailor completed the first solo crossing of the Atlantic by rowing.')


def test_general_award_cannot_be_verified_by_a_winner_of_only_one_category():
    from allma_model.utils.research_intent import primacy_question

    plan = primacy_question('Who was the first woman to win a Nobel Prize', 'en')
    assert plan.supports('Marie Curie was the first woman to win a Nobel Prize.')
    assert not plan.supports('The first woman to win the Nobel Prize in Literature was Selma Lagerlöf.')


def test_public_inventions_are_separated_from_creative_and_private_requests(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.research_scopes import _PRINTING
    from allma_model.utils.web_search import search_query

    documents = {
        _PRINTING[0].sources[0].url: 'Bi Sheng developed a ceramic movable-type system in China around 1040.',
        _PRINTING[1].sources[0].url: 'The Jikji used movable metal type in Cheongju in 1377.',
        _PRINTING[2].sources[0].url: 'Gutenberg printed with movable type around 1450.',
    }
    wiki_page = Mock(return_value={'parse': {'title': 'Movable type', 'revid': 22, 'text': '<p>'
                                             + documents[_PRINTING[0].sources[0].url] + '</p>'}})
    monkeypatch.setattr(searx_research, 'request_json', wiki_page)
    monkeypatch.setattr(searx_research, 'read_public_page',
                        lambda url, *_: (url, 'text/html', f'<p>{documents[url]}</p>'))
    core.public_references.configure(True, expanded=True)
    cid = core.start_conversation('synthetic')
    reply = turn(core, cid, 'Busca en internet quién fue la primera persona en inventar la imprenta')
    assert reply.is_valid and reply.metadata['reference_review']['coverage'] == 'full_scope'
    assert all(value in reply.content for value in ('Bi Sheng', 'Jikji', 'Gutenberg'))
    assert len(reply.metadata['reference_review']['sources']) == 3
    assert search_query('Who invented the telephone') == 'Who invented the telephone'
    assert search_query('Search online invent a new machine', explicit=True) is None
    assert search_query('Who first invented my password') is None


def test_expanded_preference_migrates_existing_profile_and_persists(tmp_path):
    from allma_model.utils.public_references import PublicReferences

    preference = tmp_path / 'web_access.json'
    preference.write_text('{"version":1,"enabled":true}')
    service = PublicReferences(tmp_path / 'test.db', preference)
    assert service.status()['expanded'] is False
    assert service.configure_expanded(True)['enabled'] is True
    restored = PublicReferences(tmp_path / 'test.db', preference)
    assert restored.status()['expanded'] is True
    restored.configure(False)
    assert restored.status()['expanded'] is True
    assert restored.status()['enabled'] is False


def test_expanded_page_rejects_mixed_public_and_private_dns_before_connecting(monkeypatch):
    from allma_model.utils import searx_research
    import socket
    import time

    resolve = Mock(return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443)),
    ])
    network = Mock()
    monkeypatch.setattr(searx_research.socket, 'getaddrinfo', resolve)
    monkeypatch.setattr(searx_research.socket, 'socket', network)
    with pytest.raises(ValueError, match='not public'):
        searx_research._open_public_socket('example.org', time.monotonic() + 3, None, lambda: True)
    network.assert_not_called()


@pytest.mark.parametrize('question,command', [
    ('Perché ha lasciato il Milan?', 'Cerca su internet'),
    ('Perché ha lasciato il Milan?', 'Cerca su internet quando ha lasciato il milan'),
    ('Perché ha lasciato il Milan?', 'Cerca sul web quando ha lasciato il milan'),
    ('Why did he leave Milan?', 'Search online that question'),
    ('¿Por qué dejó el Milan?', 'Busca en internet cuándo dejó el Milan'),
])
def test_explicit_research_reads_the_question_and_cited_article_body(core, monkeypatch, question, command):
    import time
    from allma_model.utils import online_transport
    from allma_model.utils.public_references import Reference, WikipediaReader

    language = 'en' if question.startswith('Why') else 'es' if question.startswith('¿') else 'it'
    identity = {'it': 'Chi è Zlatan Ibrahimović?', 'en': 'Who is Zlatan Ibrahimović?',
                'es': '¿Quién es Zlatan Ibrahimović?'}[language]
    biographies = {'it': 'Zlatan Ibrahimović è un ex calciatore svedese, di ruolo attaccante.',
                   'en': 'Zlatan Ibrahimović is a Swedish former professional footballer.',
                   'es': 'Zlatan Ibrahimović es un exfutbolista sueco que jugaba de delantero.'}
    passages = {'it': 'Il 4 giugno 2023, dopo l’ultima partita del Milan, annuncia il ritiro dall’attività agonistica.',
                'en': 'On 4 June 2023, Ibrahimović announced his retirement from football after Milan’s final game.',
                'es': 'El 4 de junio de 2023, con el Milan, anunció su retiro oficial del fútbol profesional.'}
    cid = core.start_conversation('synthetic')
    service = core.public_references
    reader = WikipediaReader()
    url = f'https://{language}.wikipedia.org/wiki/Zlatan_Ibrahimovi%C4%87'
    reader._fetch = Mock(return_value=[Reference('Zlatan Ibrahimović', biographies[language], url, 123, time.time())])
    service.reader = reader
    service.configure(True)
    assert turn(core, cid, identity).content == biographies[language]
    memory = core.conversational_memory
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    memory.store_message(cid, question, {}, 'user', 'synthetic')
    memory.store_message(cid, 'A quale ruolo ti riferisci?', {'identity_policy': POLICY_VERSION, 'source': 'clarification'},
                         'assistant', 'synthetic')
    html = ('<table><tr><td><p>' + passages[language] + '</p></td></tr></table>'
            + '<p>Testo introduttivo senza alcun dettaglio richiesto.</p><p>'
            + passages[language] + '<sup>[1]</sup></p>')
    transport = Mock(return_value={'parse': {'title': 'Zlatan Ibrahimović', 'revid': 123, 'text': html}})
    monkeypatch.setattr(online_transport, 'request_json', transport)
    result = turn(core, cid, command)
    assert result.content == passages[language]
    assert result.metadata['reference_review']['citation']['url'] == url
    assert result.metadata['reference_review']['network_used']
    assert transport.call_args.args[1] == f'https://{language}.wikipedia.org/w/api.php'
    assert transport.call_args.kwargs['params']['oldid'] == 123
    assert 'search' not in str(transport.call_args.kwargs['params'])
    assert memory.messages[-2].content == command
    core._llm.generate.assert_not_called()


def test_search_previous_turn_does_not_send_a_private_or_unbound_question(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION

    cid = core.start_conversation('synthetic')
    memory = core.conversational_memory
    core.public_references.configure(True)
    for question in ('Ho un problema personale', 'Dove si trova la mia casa?', 'Quando ha lasciato il Milan?'):
        memory.store_message(cid, question, {}, 'user', 'synthetic')
        memory.store_message(cid, 'Quale riferimento intendi?', {'identity_policy': POLICY_VERSION},
                             'assistant', 'synthetic')
        reply = turn(core, cid, 'Cerca su internet')
        assert not reply.metadata['reference_review']['network_used']
    reply = turn(core, cid, 'Busca en internet cómo se llama mi vecino')
    assert not reply.metadata['reference_review']['network_used']
    core.public_references.reader.fetch.assert_not_called()
    core.public_references.search.fetch.assert_not_called()


def test_inline_research_can_discover_a_source_from_the_full_query(core):
    core.public_references.configure(True)
    core.public_references.search.fetch.return_value = {'status': 'obtained', 'results': [{
        'title': 'Ciclo dell’acqua', 'publisher': 'Wikipedia',
        'url': 'https://it.wikipedia.org/wiki/Ciclo_dell%27acqua?oldid=42',
        'snippet': 'Il ciclo dell’acqua descrive come l’acqua circola in natura attraverso evaporazione e precipitazioni.',
    }]}
    answer = turn(core, core.start_conversation('synthetic'), 'Cerca su internet ciclo dell’acqua in natura')
    assert answer.metadata['source'] == 'web_search'
    assert 'evaporazione e precipitazioni' in answer.content
    assert core.public_references.search.fetch.call_args.args[0] == 'ciclo dell’acqua in natura'
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('matches', [True, False])
def test_sourced_followup_keeps_the_named_club_and_requires_a_reason(core, matches):
    import time
    from allma_model.utils.public_references import Reference

    cid = core.start_conversation('synthetic')
    service = core.public_references
    service.configure(True)
    title = 'Zlatan Ibrahimović'
    origin = 'Zlatan Ibrahimović è un ex calciatore svedese, di ruolo attaccante.'
    cause = 'Zlatan Ibrahimović ha lasciato il Milan perché si è ritirato dal calcio giocato.'
    decoy = "Zlatan Ibrahimović ha lasciato l’Inter perché voleva giocare al Milan."
    url = 'https://it.wikipedia.org/wiki/Zlatan_Ibrahimovi%C4%87'
    service.reader.fetch.side_effect = [
        [Reference(title, origin, url, 123, time.time())],
        [Reference(title, cause if matches else decoy, url, 123, time.time())],
    ]
    assert turn(core, cid, 'Chi é zlatan ibrahimovic').content == origin
    result = turn(core, cid, 'Perché ha lasciato il Milan?')
    assert result.is_valid
    assert result.metadata['source'] == ('reference_excerpt' if matches else 'clarification')
    assert 'Milan' in result.content and 'Inter' not in result.content
    if matches:
        assert result.content == cause
    else:
        assert 'anno' in result.content and 'ruolo' in result.content and 'ritirat' not in result.content
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('language,question,topic,correction,source,private', [
    ('it', 'Chi é zlatan ibrahimovic', 'zlatan ibrahimovic',
     'Non è un calciatore svizzero ma svedese',
     'Zlatan Ibrahimović è un ex calciatore svedese, di ruolo attaccante.',
     'Chi è il mio vicino di casa?'),
    ('en', 'Who is Zlatan Ibrahimović?', 'Zlatan Ibrahimović',
     'He isn’t Swiss, he’s Swedish.',
     'Zlatan Ibrahimović is a Swedish former professional footballer.',
     'Who is my neighbour?'),
    ('es', '¿Quién es Zlatan Ibrahimović?', 'Zlatan Ibrahimović',
     'No es suizo, sino sueco.',
     'Zlatan Ibrahimović es un exfutbolista sueco que jugaba de delantero.',
     '¿Quién es mi médico?'),
    ('fr', 'Qui est Zlatan Ibrahimović ?', 'Zlatan Ibrahimović',
     'Il n’est pas suisse, mais suédois.',
     'Zlatan Ibrahimović est un footballeur international suédois.',
     'Qui est mon voisin ?'),
    ('de', 'Wer ist Zlatan Ibrahimović?', 'Zlatan Ibrahimović',
     'Er ist nicht Schweizer, sondern Schwede.',
     'Zlatan Ibrahimović ist ein ehemaliger schwedischer Fußballspieler.',
     'Wer ist mein Nachbar?'),
    ('pt', 'Quem é Zlatan Ibrahimović?', 'Zlatan Ibrahimović',
     'Ele não é suíço, mas sueco.',
     'Zlatan Ibrahimović é um ex-futebolista sueco que atuava como centroavante.',
     'Quem é meu médico?'),
    ('ru', 'Кто такой Златан Ибрагимович?', 'Златан Ибрагимович',
     'Он не швейцарец, а швед.',
     'Златан Ибрагимович — шведский футболист, выступавший на позиции нападающего.',
     'Кто мой сосед?'),
    ('ar', 'من هو زلاتان إبراهيموفيتش؟', 'زلاتان إبراهيموفيتش',
     'ليس سويسريًا بل سويديًا.',
     'زلاتان إبراهيموفيتش لاعب كرة قدم سويدي سابق كان يلعب مهاجمًا.',
     'من هو جاري؟'),
    ('zh', '兹拉坦·伊布拉希莫维奇是谁？', '兹拉坦·伊布拉希莫维奇',
     '他不是瑞士人，而是瑞典人。',
     '兹拉坦·伊布拉希莫维奇是瑞典前职业足球运动员。',
     '我的邻居是谁？'),
    ('ja', 'ズラタン・イブラヒモビッチとは誰ですか？', 'ズラタン・イブラヒモビッチ',
     'スイス人ではなく、スウェーデン人です。',
     'ズラタン・イブラヒモビッチはスウェーデンの元プロサッカー選手である。',
     '私の隣人は誰ですか？'),
])
def test_biography_and_typed_correction_after_downvote(core, language, question, topic, correction, source, private):
    import time
    from allma_model.core.autobiographical_identity import POLICY_VERSION, history_eligible
    from allma_model.utils.public_references import Reference, public_topic, reference_link_allowed

    user = 'synthetic'
    cid = core.start_conversation(user)
    memory = core.conversational_memory
    identifier = 'a' * 32
    memory.store_message(cid, question, {}, 'user', user)
    memory.store_message(cid, 'Zlatan is Swiss.', {'response_feedback_id': identifier,
        'is_valid': True, 'identity_policy': POLICY_VERSION, 'source': 'model_generated'}, 'assistant', user)
    service = core.public_references
    service.configure(True)
    url = f'https://{language}.wikipedia.org/wiki/Zlatan'
    service.reader.fetch.return_value = [Reference(topic, source, url, 123, time.time())]
    # Deliberately seed the previous language to test detection on a switch.
    core._language_lock[cid] = 'it' if language != 'it' else 'en'
    assert public_topic(question) == topic
    assert public_topic(private) is None
    review = core.give_response_feedback(user, cid, identifier, 'down')
    assert review['check']['text'] == source
    assert not history_eligible(memory.messages[-1])
    assert service.reader.fetch.call_args.args[:2] == (topic, language)
    answer = turn(core, cid, correction)
    assert answer.content == source
    assert answer.metadata['source'] == 'reference_excerpt'
    assert answer.metadata['reference_review']['network_used'] is False
    assert reference_link_allowed(url + '?oldid=123')
    assert turn(core, cid, question).content == source
    service.reader.fetch.assert_called_once()
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('allowed,original,correction', [
    (False, 'Chi é Zlatan Ibrahimovic?', 'Non è svizzero ma svedese'),
    (True, 'Chi é Zlatan Ibrahimovic? Non cercare online', 'Non è svizzero ma svedese'),
    (True, '¿Quién es Zlatan Ibrahimović?', 'No es suizo, sino sueco. No busques en internet.'),
    (True, 'Qui est Zlatan Ibrahimović ?', 'Il n’est pas suisse, mais suédois. Ne cherche pas sur Internet.'),
])
def test_typed_biography_correction_cannot_bypass_local_only(core, allowed, original, correction):
    from allma_model.core.autobiographical_identity import POLICY_VERSION

    cid = core.start_conversation('synthetic')
    memory = core.conversational_memory
    memory.store_message(cid, original, {}, 'user', 'synthetic')
    memory.store_message(cid, 'Un ancien attaquant de Milan.', {'is_valid': True,
        'identity_policy': POLICY_VERSION, 'source': 'model_generated'}, 'assistant', 'synthetic')
    core.public_references.configure(allowed)
    core._llm.generate.side_effect = None
    core._llm.generate.return_value = 'Il faudrait vérifier ce détail.'
    turn(core, cid, correction)
    core.public_references.reader.fetch.assert_not_called()
    core.public_references.search.fetch.assert_not_called()


def test_thumbs_suspend_wrong_answer_and_save_checked_source(core):
    import time
    from allma_model.core.autobiographical_identity import POLICY_VERSION, history_eligible
    from allma_model.utils.public_references import Reference

    user = 'synthetic'
    cid = core.start_conversation(user)
    memory = core.conversational_memory
    question = 'Quando fu firmato il Patto tripartito?'
    answer = 'Il Patto tripartito fu firmato nel 1941.'
    identifier, key = 'a' * 32, 'b' * 64
    memory.store_message(cid, question, {}, 'user', user)
    memory.store_message(cid, answer, {'response_feedback_id': identifier, 'recall_key': key,
        'is_valid': True, 'identity_policy': POLICY_VERSION, 'source': 'model_generated'}, 'assistant', user)
    core.answer_recall.observe(key, user, question, answer, 'original')
    # A thumbs-up records usefulness. It does not promote a generated fact.
    assert core.give_response_feedback(user, cid, identifier, 'up')['saved'] is False
    assert core.saved_references.entries(user) == []
    core.answer_recall.feedback(key, user, 'old-1', True)
    core.answer_recall.feedback(key, user, 'old-2', True)
    assert core.answer_recall.lookup(key, user)['answer'] == answer
    service = core.public_references
    service.configure(True)
    text = 'Il Patto tripartito fu firmato nel 1940 da Germania, Italia e Giappone.'
    service.reader.fetch.return_value = [Reference('Patto tripartito', text,
        'https://it.wikipedia.org/wiki/Patto_tripartito', 100, time.time())]
    review = core.give_response_feedback(user, cid, identifier, 'down')
    assert review['check']['status'] == 'corrected'
    assert review['check']['text'] == text
    assert review['check']['origin']['citation']['revision'] == 100
    assert '1941' not in service.reader.fetch.call_args.args[0]
    assert core.answer_recall.lookup(key, user) is None
    assert not history_eligible(memory.messages[-1])
    assert core.give_response_feedback(user, cid, identifier, 'down') == review
    service.reader.fetch.assert_called_once()
    assert core.give_response_feedback(user, cid, identifier, 'review_up')['saved'] is True
    assert [item['answer'] for item in core.saved_references.entries(user)] == [text]
    assert core.give_response_feedback(user, cid, identifier, 'review_down')['status'] == 'review_disputed'
    assert core.saved_references.entries(user) == []
    assert core.give_response_feedback(user, cid, identifier, 'correction', 'Controlla il giorno')['note'] == 'Controlla il giorno'
    assert len(memory.messages) == 2
    assert not history_eligible(memory.messages[-1])


def test_manual_correction_is_local_and_scoped_to_original_question(core):
    from allma_model.core.response_feedback import latest_correction

    user = 'synthetic'
    cid = core.start_conversation(user)
    question = 'Il mio personaggio ha un soprannome?'
    identifier = 'd' * 32
    memory = core.conversational_memory
    core.public_references.configure(True)
    memory.store_message(cid, question, {}, 'user', user)
    memory.store_message(cid, 'Sì, si chiama Verde.', {'response_feedback_id': identifier, 'is_valid': True},
                         'assistant', user)
    with pytest.raises(ValueError):
        core.give_response_feedback('another-user', cid, identifier, 'down')
    assert core.give_response_feedback(user, cid, identifier, 'down')['check']['status'] == 'unresolved'
    core.give_response_feedback(user, cid, identifier, 'correction', 'Il soprannome è Lince.')
    assert latest_correction(memory, user, question) == 'Il soprannome è Lince.'
    assert latest_correction(memory, 'another-user', question) is None
    assert latest_correction(memory, user, 'Hai un soprannome?') is None
    core.public_references.reader.fetch.assert_not_called()
    core.public_references.search.fetch.assert_not_called()


def test_thumbs_verify_calculations_with_globe_off(core):
    user = 'synthetic'
    cid = core.start_conversation(user)
    memory = core.conversational_memory
    identifier = 'e' * 32
    memory.store_message(cid, 'Quanto fa 18 + 24?', {}, 'user', user)
    memory.store_message(cid, '41', {'response_feedback_id': identifier, 'is_valid': True}, 'assistant', user)
    check = core.give_response_feedback(user, cid, identifier, 'down')['check']
    assert check['status'] == 'corrected'
    assert check['text'] == '42'
    assert check['origin']['kind'] == 'computation'
    assert turn(core, cid, 'Come ti chiami?').metadata['response_feedback_id']
    core.public_references.reader.fetch.assert_not_called()


@pytest.mark.parametrize('question', [
    'Sai fare ricerca su Internet?', 'ALLMA, puoi fare ricerche online?',
    'Hai accesso diretto a Internet in tempo reale?', 'Puoi navigare sul web ALLMA?',
    'Sai fare una ricerca su internet?', 'Quando puoi utilizzare la versione online?',
])
def test_capability_reads_actual_consent_without_transport(core, question):
    conversation = core.start_conversation('synthetic')
    for enabled in (False, True):
        core.public_references.configure(enabled)
        response = turn(core, conversation, question)
        assert response.metadata['source'] == 'runtime_web_access'
        assert ('abilitate' if enabled else 'disattivate') in response.content
    core._llm.generate.assert_not_called()
    core.public_references.search.fetch.assert_not_called()
    core.public_references.weather.fetch.assert_not_called()


def test_weather_city_followup_consent_and_privacy(core):
    conversation = core.start_conversation('synthetic')
    service = core.public_references
    offline = turn(core, conversation, 'Che tempo fa a Torino?')
    assert offline.metadata['reference_review']['retrieval_status'] == 'local_only'
    service.weather.fetch.assert_not_called()
    service.configure(True)
    service.weather.fetch.return_value = {'status':'obtained', 'answer':'9 °C', 'city':'Torino, Piemonte',
        'citation':{'title':'Torino', 'url':'https://open-meteo.com/', 'data_label':'Alle 21:15'}}
    response = turn(core, conversation, 'Meteo Torino')
    assert response_origin(response.metadata)['kind'] == 'weather'
    assert service.weather.fetch.call_args.args[0].day == 0
    turn(core, conversation, 'E domani?')
    request = service.weather.fetch.call_args.args[0]
    assert request.day == 1 and request.daily and request.city == 'Torino, Piemonte'
    private = turn(core, conversation, 'Che tempo fa a casa mia?')
    assert 'Quale località' in private.content
    assert service.weather.fetch.call_count == 2
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize(('question', 'language', 'day', 'daily', 'rain'), [
    ('Raccontami che meteo fa a torino', 'it', 0, False, False),
    ('Puoi dirmi che meteo farà a Torino?', 'it', 1, True, False),
    ('What’s the weather like in Turin right now?', 'en', 0, False, False),
    ('Will it rain in Turin tomorrow?', 'en', 1, True, True),
    ('¿Qué tiempo hace en Turín?', 'es', 0, False, False),
    ('¿Lloverá mañana en Turín?', 'es', 1, True, True),
])
def test_natural_weather_requests_route_to_the_provider(core, question, language, day, daily, rain):
    service = core.public_references
    service.configure(True)
    service.weather.fetch.return_value = {
        'status': 'obtained', 'answer': '6 °C', 'city': 'Torino, Piemonte',
        'citation': {'title': 'Torino', 'url': 'https://open-meteo.com/', 'provider': 'open_meteo'},
    }
    result = turn(core, core.start_conversation('synthetic'), question)
    assert result.metadata['source'] == 'weather_data'
    assert result.metadata['reference_review']['network_used']
    request = service.weather.fetch.call_args.args[0]
    assert (request.city.casefold(), request.language, request.day, request.daily, request.rain) == (
        'torino', language, day, daily, rain)
    service.search.fetch.assert_not_called()
    core._llm.generate.assert_not_called()


def test_explicit_search_recovers_weather_after_an_old_generic_reply(core):
    from allma_model.core.autobiographical_identity import POLICY_VERSION

    cid = core.start_conversation('synthetic')
    memory = core.conversational_memory
    memory.store_message(cid, 'Raccontami che meteo fa a torino', {}, 'user', 'synthetic')
    memory.store_message(cid, 'Non posso verificare il meteo attuale.', {
        'source': 'model_generated', 'identity_policy': POLICY_VERSION, 'is_valid': True,
    }, 'assistant', 'synthetic')
    service = core.public_references
    service.configure(True)
    service.weather.fetch.return_value = {
        'status': 'obtained', 'answer': '6 °C', 'city': 'Torino, Piemonte',
        'citation': {'title': 'Torino', 'url': 'https://open-meteo.com/', 'provider': 'open_meteo'},
    }
    result = turn(core, cid, 'Cerca su Internet')
    assert result.metadata['source'] == 'weather_data' and result.content == '6 °C'
    assert service.weather.fetch.call_args.args[0].city.casefold() == 'torino'
    assert memory.messages[-2].content == 'Cerca su Internet'
    service.configure(False)
    no_network = turn(core, cid, 'Cerca su Internet')
    assert no_network.metadata['reference_review']['retrieval_status'] == 'local_only'
    service.weather.fetch.assert_called_once()
    service.search.fetch.assert_not_called()
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('question', [
    'What is the weather at my home address?', '¿Qué tiempo hace cerca de mi casa?',
])
def test_weather_does_not_send_private_geocoding_queries(core, question):
    core.public_references.configure(True)
    reply = turn(core, core.start_conversation('synthetic'), question)
    assert reply.metadata['source'] == 'weather_status'
    assert not reply.metadata['reference_review']['network_used']
    core.public_references.weather.fetch.assert_not_called()


def test_general_search_differentiates_unresponsive_engines_from_no_results(core, monkeypatch):
    from allma_model.utils import searx_research

    monkeypatch.setattr(searx_research, 'request_json', Mock(return_value={
        'results': [], 'unresponsive_engines': [['mwmbl', 'timeout']],
    }))
    core.public_references.configure(True)
    core.public_references.configure_expanded(True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search online astronomy education activities')
    assert reply.metadata['reference_review']['retrieval_status'] == 'search_partial'
    assert 'Alcuni motori' in response_origin(reply.metadata)['detail']


@pytest.mark.parametrize(('question', 'language', 'correct', 'wrong'), [
    ('Quando è caduto il Muro di Berlino?', 'it',
     'Il Muro di Berlino cadde il 9 novembre 1989.',
     'Il custode del Muro di Berlino, caduto in depressione, morì nel 1998.'),
    ('Quando è caduto il Muro di Berlino?', 'it',
     'La caduta (o crollo) del Muro di Berlino è un evento geopolitico avvenuto il 9 novembre 1989.',
     'La caduta del Muro di Berlino aprì la strada alla riunificazione, che fu conclusa nel 1990.'),
    ('When did the Panama Canal open?', 'en',
     'The Panama Canal opened to traffic in 1914.',
     'A museum dedicated to the Panama Canal opened its doors in 2002.'),
    ('Chi ha scritto la Divina Commedia?', 'it',
     'La Divina Commedia è un poema allegorico di Dante Alighieri.',
     'Go Nagai ha scritto una trasposizione fumettistica della Divina Commedia.'),
    ('Who wrote the novel Frankenstein?', 'en',
     'Frankenstein is an 1818 Gothic novel written by Mary Shelley.',
     'The Man Who Wrote Frankenstein is an essay by John Doe about the novel.'),
    ('Dans quelle mer se jette le Danube?', 'fr',
     'Le Danube se jette dans la mer Noire par un vaste delta.',
     'Le Danube passe devant cette ville, où la Morava se jette dans le Danube.'),
    ('What is the capital of New Zealand?', 'en',
     'The capital of New Zealand has been Wellington since 1865.',
     'Capital punishment in New Zealand first appeared in codified form in 1840.'),
    ('What is the capital of New Zealand?', 'en',
     "New Zealand's capital city is Wellington.",
     'Auckland was the capital of New Zealand until 1865.'),
])
def test_fact_extraction_requires_the_named_subject_and_the_requested_relation(question, language, correct, wrong):
    from allma_model.utils.fact_search import fact_question

    request = fact_question(question, language)
    assert request is not None
    assert request.supports(correct)
    assert not request.supports(wrong, article_title=request.topic, opening=True)


def test_chat_uses_fact_search_instead_of_an_irrelevant_encyclopedia_excerpt(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://it.wikipedia.org/wiki/Muro_di_Berlino?oldid=11'
    correct = 'Il Muro di Berlino cadde il 9 novembre 1989.'
    wrong = 'Caduto successivamente in depressione, il custode morì nel 1998.'
    article = '<html lang="it"><p>' + wrong + '</p><p>' + correct + '</p></html>'
    search = Mock(return_value=iter([((url, 'text/html', article), 'Muro di Berlino')]))
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', search)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'Quando è caduto il Muro di Berlino?')
    assert reply.is_valid and reply.content == correct + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    assert search.call_args.args[1] == 'muro di berlino'
    core.public_references.reader.fetch.assert_not_called()
    core._llm.generate.assert_not_called()


def test_explicit_fact_search_preserves_the_relation_in_the_enquiry(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://en.wikipedia.org/wiki/Capital_of_New_Zealand?oldid=12'
    excerpt = 'The capital of New Zealand has been Wellington since 1865.'
    discovery = Mock(return_value=iter([((url, 'text/html', '<p>' + excerpt + '</p>'), 'Capital of New Zealand')]))
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', discovery)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'Search the web: What is the capital of New Zealand?')
    assert reply.is_valid and reply.content == excerpt + ' [1]'
    assert discovery.call_args.args[1:3] == ('capital of new zealand', 'en')
    assert discovery.call_args.kwargs['fact'].kind == 'capital'
    core._llm.generate.assert_not_called()


def test_fact_search_uses_the_current_question_language_after_a_language_switch(core, monkeypatch):
    from allma_model.utils import searx_research

    responses = {
        'en': ('Capital of New Zealand', 'The capital of New Zealand has been Wellington since 1865.'),
        'fr': ('Danube', 'Le Danube se jette dans la mer Noire par un vaste delta.'),
    }

    def pages(session, query, language, *args, **kwargs):
        title, excerpt = responses[language]
        url = f'https://{language}.wikipedia.org/wiki/{title.replace(" ", "_")}?oldid=19'
        return iter([((url, 'text/html', '<p>' + excerpt + '</p>'), title)])

    discovery = Mock(side_effect=pages)
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', discovery)
    core.public_references.configure(True, expanded=True)
    conversation = core.start_conversation('synthetic')
    first = turn(core, conversation, 'What is the capital of New Zealand?')
    assert first.is_valid and first.content == responses['en'][1] + ' [1]'
    second = turn(core, conversation, 'Dans quelle mer se jette le Danube?')
    assert second.is_valid and second.content == responses['fr'][1] + ' [1]'
    assert [call.args[2] for call in discovery.call_args_list] == ['en', 'fr']
    core._llm.generate.assert_not_called()


def test_science_search_requires_the_explanation_and_respects_internet_consent(core, monkeypatch):
    from allma_model.utils import searx_research

    question = 'Perché il ghiaccio galleggia sull’acqua?'
    url = 'https://it.wikipedia.org/wiki/Ghiaccio?oldid=20'
    effect = 'Il ghiaccio galleggia sull’acqua e per questo rallenta il raffreddamento del lago.'
    cause = 'Il ghiaccio galleggia perché è meno denso dell’acqua liquida.'
    body = '<html lang="it"><p>' + effect + '</p><p>' + cause + '</p></html>'
    discovery = Mock(return_value=iter([((url, 'text/html', body), 'Ghiaccio')]))
    monkeypatch.setattr(searx_research, '_encyclopedia_pages', discovery)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), question)
    assert reply.is_valid and reply.content == cause + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    assert discovery.call_args.args[1:3] == ('ghiaccio galleggia acqua', 'it')
    core.public_references.reader.fetch.assert_not_called()
    core.public_references.configure(False)
    offline = turn(core, core.start_conversation('synthetic'), 'Cerca su Internet ' + question)
    assert not offline.metadata['reference_review']['network_used']
    discovery.assert_called_once()
    core._llm.generate.assert_not_called()


def test_science_comparison_checks_the_relation_in_the_primary_source(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://pubs.usgs.gov/gip/volc/nature.html'
    body = ('<html lang="en"><p>Magma can cool and form minerals underground.</p>'
            '<p>Lava and magma often contain dissolved gases.</p>'
            '<p>Magma rises below the surface. When magma erupts onto the surface it is called lava.</p></html>')
    read = Mock(return_value=(url, 'text/html', body))
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'What is the difference between magma and lava?')
    assert reply.is_valid and reply.content == 'When magma erupts onto the surface it is called lava. [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    read.assert_called_once()
    core._llm.generate.assert_not_called()


def test_science_evidence_does_not_combine_unrelated_paragraphs():
    from allma_model.utils.science_search import science_question
    from allma_model.utils.searx_research import _read_passages

    query = 'How does pumped storage hydropower work'
    scope = science_question(query)
    discharge = 'Water flows between the reservoirs and passes through a turbine to generate power.'
    recharge = 'The system pumps water back into the upper reservoir.'
    split = f'<p>{discharge}</p><p>{recharge}</p>'
    together = f'<p>{discharge} {recharge}</p>'
    assert _read_passages(split, 'text/html', query, 'en', science=scope) is None
    assert _read_passages(together, 'text/html', query, 'en', science=scope)[1] == discharge + ' ' + recharge
    assert science_question("Come si forma un’eclissi lunare?") is None


def test_wind_search_requires_conversion_and_keeps_line_breaks(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.science_search import science_question

    query = 'Come genera elettricità una turbina eolica?'
    _, url = science_question(query).official[0]
    unrelated = 'Il vento fa girare le pale della turbina, mentre l’elettricità degli uffici arriva dalla rete.'
    explanation = 'Il vento fa girare le pale e il generatore trasforma quel movimento in energia elettrica.'
    body = f'<html lang="it"><p>{unrelated}</p><p>{explanation}<br/>La fonte descrive anche le dimensioni.</p></html>'
    monkeypatch.setattr(searx_research, 'read_public_page', Mock(return_value=(url, 'text/html', body)))
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), query)
    assert reply.is_valid and reply.content == explanation + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    core._llm.generate.assert_not_called()


def test_paris_agreement_keeps_the_two_temperature_goals_distinct():
    from allma_model.utils.science_search import science_question
    from allma_model.utils.searx_research import _read_passages

    query = 'What warming target does the Paris Agreement set?'
    scope = science_question(query)
    first = 'The aim is to hold warming well below 2°C above pre-industrial levels.'
    reversed_goals = 'The aim is to hold warming well below 1.5°C above pre-industrial levels and pursue efforts to limit it to 2°C.'
    both = 'The agreement aims to hold warming well below 2°C above pre-industrial levels and pursue efforts to limit warming to 1.5°C.'
    body = f'<p>{first}</p><p>{reversed_goals}</p><p>{both}<a href="/agreement">(Paris Agreement)</a></p>'
    assert not scope.supports(first)
    assert not scope.supports(reversed_goals)
    assert _read_passages(body, 'text/html', query, 'en', science=scope)[1] == both


def test_forest_carbon_sink_requires_uptake_and_storage():
    from allma_model.utils.science_search import science_question

    scope = science_question('Why are forests considered carbon sinks?')
    uptake = 'Trees absorb carbon dioxide from the air through photosynthesis.'
    storage = 'The trees store much of that carbon in their wood.'
    assert not scope.supports(uptake)
    assert not scope.supports(storage)
    assert scope.supports(uptake + ' ' + storage)


def test_geothermal_origin_uses_a_second_source_if_the_first_is_unavailable(core, monkeypatch):
    from allma_model.utils import searx_research
    from allma_model.utils.science_search import science_question

    query = 'Da dove viene l’energia geotermica?'
    scope = science_question(query)
    _, url = scope.official[1]
    extraction = 'Per sfruttare il calore terrestre occorre individuare un giacimento geotermico.'
    origin = 'La geotermia è l’energia termica (calore) immagazzinata sotto la superficie della Terra.'
    body = f'<html lang="it"><p>{extraction}</p><p>{origin}</p></html>'
    read = Mock(side_effect=[None, (url, 'text/html', body)])
    monkeypatch.setattr(searx_research, 'read_public_page', read)
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), query)
    assert reply.is_valid and reply.content == origin + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    assert read.call_count == 2
    core._llm.generate.assert_not_called()


def test_science_function_fallback_rejects_atp_mentions_outside_cellular_metabolism(core, monkeypatch):
    from allma_model.utils import searx_research

    url = 'https://pt.wikipedia.org/wiki/Mitoc%C3%B4ndria?oldid=21'
    anecdote = 'A origem das mitocôndrias envolve a perda de genes que participam da produção de ATP.'
    function = 'Nas mitocôndrias, a fosforilação oxidativa produz ATP para as necessidades energéticas da célula.'
    body = '<html lang="pt"><p>' + anecdote + '</p><p>' + function + '</p></html>'
    monkeypatch.setattr(searx_research, 'read_public_page', Mock(return_value=None))
    monkeypatch.setattr(searx_research, '_encyclopedia_pages',
                        Mock(return_value=iter([((url, 'text/html', body), 'Mitocôndria')])))
    core.public_references.configure(True, expanded=True)
    reply = turn(core, core.start_conversation('synthetic'), 'Para que servem as mitocôndrias?')
    assert reply.is_valid and reply.content == function + ' [1]'
    assert reply.metadata['reference_review']['sources'][0]['url'] == url
    core._llm.generate.assert_not_called()


def test_weather_changes_city_with_fresh_citations_and_preserves_forecast_day(core):
    service = core.public_references
    service.configure(True)
    cid = core.start_conversation('synthetic')
    readings = {'Torino': '8 °C', 'Milano': '11 °C', 'Tirana': '16 °C', 'Palermo': '19 °C'}

    def weather_result(request, *args):
        city = request.city.split(',')[0]
        return {'status':'obtained', 'city': city, 'answer': f'{city}, {readings[city]}',
                'citation': {'title': city, 'url': 'https://open-meteo.com/', 'provider': 'open_meteo'}}

    service.weather.fetch.side_effect = weather_result
    for question, city, day in (
        ('Bene, quanti gradi fanno a Torino?', 'Torino', 0), ('Invece a Milano?', 'Milano', 0),
        ('E a Tirana?', 'Tirana', 0), ('Invece a Palermo?', 'Palermo', 0),
        ('E domani?', 'Palermo', 1), ('Invece a Torino?', 'Torino', 1),
    ):
        response = turn(core, cid, question)
        assert response.is_valid and response.content == f'{city}, {readings[city]}'
        assert response_origin(response.metadata)['citation']['title'] == city
        assert service.weather.fetch.call_args.args[0].day == day
    offline = turn(core, cid, 'Invece a Milano? Senza internet.')
    assert offline.metadata['reference_review']['retrieval_status'] == 'local_only'
    assert service.weather.fetch.call_count == 6
    core._llm.generate.side_effect = None
    core._llm.generate.return_value = 'Posso aiutarti con diversi compiti e posso commettere errori.'
    response = turn(core, cid, 'Pensi di essere bravo?')
    assert response.is_valid and 'compiti' in response.content
    assert service.weather.fetch.call_count == 6
    assert '19 °C' not in core._llm.generate.call_args.kwargs['prompt']


def test_public_subject_transitions_restart_from_an_attributed_passage(core):
    import time
    from allma_model.utils.public_references import Reference

    excerpts = {
        'Achille': 'Achille (in greco antico: Ἀχιλλεύς?, Achilléus) è un eroe della mitologia greca. Dormiva sempre nella foresta di giorno.',
        'Ettore (mitologia)': 'Ettore (in greco antico: Ἕκτωρ?, Héktōr) è un eroe della mitologia greca e uno dei protagonisti dell’Iliade.',
        'Benito Mussolini': 'Benito Mussolini è stato un politico e dittatore italiano.',
        'Patto tripartito': 'Il Patto tripartito fu un accordo tra Germania, Italia e Giappone, firmato a Berlino nel 1940.',
        'Mao Zedong': 'Mao Zedong è stato un politico, rivoluzionario e dittatore cinese.',
        'Nativi americani': 'I nativi americani sono i popoli indigeni delle Americhe.',
        'ebrei': 'Gli ebrei sono un popolo e un gruppo etnoreligioso.',
        'Roger Federer': 'Roger Federer è un ex tennista svizzero, vincitore di numerosi tornei.',
        'Rafael Nadal': 'Rafael Nadal è un ex tennista spagnolo, noto per i suoi successi sulla terra battuta.',
    }
    def wiki(topic, *args):
        if topic not in excerpts:
            return []
        return [Reference(topic, excerpts[topic], 'https://it.wikipedia.org/wiki/'+topic.replace(' ', '_'), 41, time.time())]

    core.public_references.reader.fetch.side_effect = wiki
    core.public_references.configure(True)
    cid = core.start_conversation('synthetic')
    for question, topic in (
        ('Chi era Achille?', 'Achille'), ('Chi era Ettore?', 'Ettore (mitologia)'),
        ('Intendo ettore nell"iliade', 'Ettore (mitologia)'), ('Chi era Benito Mussolini?', 'Benito Mussolini'),
        ('Con chi si era alleato durante la seconda guerra mondiale?', 'Patto tripartito'),
        ('Chi era Mao Tse Tung?', 'Mao Zedong'), ('Chi erano i pelle rossa?', 'Nativi americani'),
        ('Chi sono gli ebrei?', 'ebrei'), ('Chi era Roger Federer?', 'Roger Federer'),
        ('Invece conosci Rafael Nadal?', 'Rafael Nadal'),
    ):
        response = turn(core, cid, question)
        assert response.is_valid, question
        assert response.metadata['reference_review']['citation']['title'] == topic
        assert response.content == excerpts[topic].split('. ')[0].rstrip('.') + '.'
    core._llm.generate.assert_not_called()


def test_continue_restarts_public_lookup_from_the_interrupted_user_request(core):
    import time
    from allma_model.core.autobiographical_identity import POLICY_VERSION
    from allma_model.utils.public_references import Reference

    service = core.public_references
    service.configure(True)
    cid = core.start_conversation('synthetic')
    meta = {'identity_policy': POLICY_VERSION, 'is_valid': True, 'source': 'model_generated'}
    core.conversational_memory.store_message(cid,'Che cos’è un arco?',{},'user','synthetic')
    core.conversational_memory.store_message(cid,'Un arco può essere un oggetto usato per lanciare frecce.',meta,'assistant','synthetic')
    core.conversational_memory.store_message(cid,'Chi era Achille?',{},'user','synthetic')
    core.conversational_memory.store_message(cid,'Diversi personaggi ebbero un ruolo nella guerra di Troia, tra cui',
        dict(meta,generation={'status':'truncated_answer'}),'assistant','synthetic')
    service.reader.fetch.return_value = [Reference('Achille','Achille è un eroe della mitologia greca.',
        'https://it.wikipedia.org/wiki/Achille',91,time.time())]
    response = turn(core, cid, 'Continua')
    assert response.metadata['source'] == 'reference_excerpt'
    assert service.reader.fetch.call_args.args[0] == 'Achille'
    assert response.content == 'Achille è un eroe della mitologia greca.'
    core._llm.generate.assert_not_called()


def test_continue_draft_rejects_reused_intro_and_projects_internal_header():
    from types import SimpleNamespace
    from allma_model.utils.dialogue_continuity import DialogueContinuity
    from allma_model.utils.dialogue_output import project_answer
    from allma_model.utils.dialogue_reasoning import TurnWorkspace

    request = SimpleNamespace(role='user', content='Scrivi una storia ambientata sulla Luna.', metadata={})
    draft = 'La protagonista lasciò il suo villaggio sotto il cielo stellato e salì sulla navetta.'
    reply = SimpleNamespace(role='assistant', content=draft, metadata={'generation':{'status':'truncated_answer'}})
    continuity = DialogueContinuity('Continua', [request], [request, reply])
    view = TurnWorkspace.build('Continua', continuity, [request])
    assert view.anchor == request.content and view.project_history([request, reply]) == []
    assert draft in view.instruction() and request.content in view.model_request()
    assert continuity.duplicate('Ecco la continuazione. ' + draft + ' Il portello si chiuse.')
    projection = project_answer('[Risposta precedente incompleta, non una conclusione verificata.]\n'
        '[Nuovo evento: Luna]\nIl portello si chiuse.', 'Continua', continuity)
    assert projection.text == 'Il portello si chiuse.'
    assert not continuity.duplicate(projection.text)


def test_reaction_and_its_acknowledgement_do_not_restart_research(core):
    import time
    from allma_model.utils.public_references import Reference

    service = core.public_references
    service.configure(True)
    biography = 'Roger Federer è un ex tennista svizzero, vincitore di numerosi tornei.'
    service.reader.fetch.return_value = [Reference('Roger Federer', biography,
        'https://it.wikipedia.org/wiki/Roger_Federer', 91, time.time())]
    cid = core.start_conversation('synthetic')
    assert turn(core, cid, 'Chi era Roger Federer?').content == biography
    core._llm.generate.side_effect = ['Si capisce, il suo stile aveva una grazia particolare.', 'Ti capisco.']
    for request in ('Mi piace molto', 'Sì.'):
        response = turn(core, cid, request)
        assert response.is_valid and response.content != biography
        assert response.metadata['turn_review']['purpose'] == 'reaction'
        assert biography not in core._llm.generate.call_args.kwargs['prompt']
    service.reader.fetch.assert_called_once()


def test_weather_declines_stale_data_and_clarifies_ambiguous_places():
    now = datetime(2026,11,14,12,tzinfo=timezone.utc).timestamp()
    place = {'name':'Torino','country':'Italia'}
    forecast = {'timezone':'Europe/Rome','current_units':{'time':'unixtime','temperature_2m':'°C',
        'apparent_temperature':'°C','wind_speed_10m':'km/h'},
        'current':{'time': now,'temperature_2m':10.5,'apparent_temperature':8,'wind_speed_10m':4,'weather_code':1}}
    request = weather_request('Che tempo fa a Torino?')
    assert '10,5 °C' in weather_answer(place, forecast, request, now=now)['answer']
    with pytest.raises(ValueError, match='stale'):
        weather_answer(place, forecast, request, now=now + 3601)
    rows = [{'name':'Springfield','country':'Stati Uniti','country_code':'US','latitude':lat,'longitude':-89,
             'admin1':region,'population':100000} for lat,region in ((39,'Illinois'), (44,'Massachusetts'))]
    assert _locations({'results':rows},'Springfield') == (None,['Springfield, Illinois','Springfield, Massachusetts'])
    assert _locations({'results':rows},'Springfield, Illinois')[0] == rows[0]


def test_weather_distinguishes_cities_from_homonymous_districts():
    city = {'name':'Palermo', 'country':'Italia', 'country_code':'IT', 'feature_code':'PPLA',
            'latitude':38, 'longitude':13, 'admin1':'Sicilia', 'population':648260}
    district = dict(city, country='Argentina', country_code='AR', feature_code='PPLX',
                    latitude=-34, longitude=-58, admin1='Buenos Aires', population=249016)
    other = dict(city, country='Colombia', country_code='CO', feature_code='PPLA2',
                 latitude=3, longitude=-75, admin1='Huila', population=9896)
    data = {'results': [city, district, other]}
    assert _locations(data, 'Palermo')[0] == city
    assert _locations(data, 'Palermo, Argentina')[0] == district


def test_native_search_bookmark_exact_citations_and_recent_followup(core):
    conversation = core.start_conversation('synthetic')
    service = core.public_references
    service.configure(True)
    published = datetime.now(timezone.utc).date().isoformat()
    service.search.fetch.return_value = fetch = {'status':'obtained','results':[
        {'title':'Android Studio', 'url':'https://developer.android.com/blog/nuova-versione',
         'snippet':'Android Studio ha ricevuto un aggiornamento con nuovi strumenti per il debug.',
         'date':published,'publisher':'Android Developers'}]}
    response = turn(core, conversation, 'Cerca sul web gli ultimi aggiornamenti su Android Studio')
    origin = response_origin(response.metadata)
    assert response.metadata['source'] == 'web_search' and '[1]' in response.content
    assert service.search.fetch.call_args.args[2] is True
    assert origin['sources'][0]['url'] == fetch['results'][0]['url']
    assert origin['save_id'] and service.web_link_allowed(origin['sources'][0]['url'])
    core.set_reference_saved('synthetic', conversation, origin['save_id'], True)
    assert core.saved_references.entries('synthetic')[0]['review']['sources'] == origin['sources']
    response = turn(core, conversation, 'Dimmi di più')
    assert response.metadata['reference_review']['retrieval_status'] == 'insufficient_evidence'
    fetched = service.search.fetch.call_count
    answer = turn(core, conversation, 'Cerca sul web il mio referto medico')
    assert answer.metadata['reference_review']['retrieval_status'] == 'not_applicable'
    assert service.search.fetch.call_count == fetched
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('turn_text', ['Cerca sul web Android Studio', 'Che tempo fa a Torino?'])
def test_late_online_results_are_discarded_when_consent_changes(core, turn_text):
    service = core.public_references
    service.configure(True)
    def revoke(*args):
        service.configure(False)
        service.configure(True)
        return {'status':'obtained','answer':'forged'}
    service.search.fetch.side_effect = service.weather.fetch.side_effect = revoke
    response = turn(core, core.start_conversation('synthetic'), turn_text)
    assert response.metadata['reference_review']['retrieval_status'] == 'consent_revoked'
    assert not response.content


def test_feed_parser_rejects_entities_and_external_destinations():
    feed = FEEDS[0]
    contents = b'''<rss><channel>
      <item><title>NASA mission</title><link>https://www.nasa.gov/mission/</link>
      <description><![CDATA[<!DOCTYPE html><p>NASA announced a new mission to explore the surface of Mars.</p>]]></description>
      <pubDate>Sat, 14 Nov 2026 09:00:00 GMT</pubDate></item>
      <item><title>Misleading</title><link>https://www.nasa.gov.internal/</link>
      <pubDate>Sat, 14 Nov 2026 09:00:00 GMT</pubDate></item>
      </channel></rss>'''
    entries = feed_results(contents, feed)
    assert len(entries) == 1 and entries[0]['date'] == '2026-11-14'
    assert compose_web_answer('NASA', entries, True, today=date(2026,11,14))
    assert not compose_web_answer('NASA oggi', entries, True, today=date(2026,11,15))
    assert not compose_web_answer('NASA clima', entries, True, today=date(2026,11,14))
    with pytest.raises(ValueError):
        feed_results(b'<!DOCTYPE x [<!ENTITY z SYSTEM "file:///etc/passwd">]><rss>&z;</rss>', feed)
    for address in ('file:///etc/passwd','http://127.0.0.1','https://user@example.com/','https://10.0.0.1/'):
        assert not public_url(address)


def test_native_feeds_receive_no_user_query(monkeypatch):
    feeds = Mock(return_value=b'<rss><channel></channel></rss>')
    encyclopedia = Mock(return_value={'query':{'pages':[]}})
    monkeypatch.setattr('allma_model.utils.web_search.request_bytes',feeds)
    monkeypatch.setattr('allma_model.utils.web_search.request_json',encyclopedia)
    reader = NativeWebSearch()
    result = reader.fetch('ultimi aggiornamenti su Android Studio','it',True,None,lambda:True)
    assert result['status'] == 'not_found'
    feeds.assert_called_once()
    assert 'params' not in feeds.call_args.kwargs
    assert 'Android' not in feeds.call_args.args[1]
    encyclopedia.assert_not_called()


def test_android_updates_use_bulletin_and_keep_its_dates(core, monkeypatch):
    published = datetime.now(timezone.utc).date() - timedelta(days=12)
    patch = published + timedelta(days=3)
    body = f'''<table><tr>
      <td><a href="/docs/security/bulletin/{published.year}/{published.isoformat()}">Bulletin</a></td>
      <td>English</td><td>{published:%B} {published.day}, {published.year}</td>
      <td>{published.isoformat()}<br>{patch.isoformat()}</td></tr></table>'''.encode()
    transport = Mock(return_value=body)
    monkeypatch.setattr('allma_model.utils.web_search.request_bytes', transport)
    core.public_references.search = NativeWebSearch()
    core.public_references.configure(True)
    response = turn(core, core.start_conversation('synthetic'), 'Quali sono gli ultimi aggiornamenti su Android?')
    assert response.is_valid and 'bollettino di sicurezza Android' in response.content
    assert patch.isoformat() in response.content
    assert response.metadata['reference_review']['sources'][0]['date'] == published.isoformat()
    assert transport.call_args.args[1].endswith('/asb-overview')
    assert transport.call_args.kwargs['params'] == {'hl':'en'}
    assert not compose_web_answer('Android oggi', [{'title':'Bollettino Android', 'publisher':'AOSP',
        'url':response.metadata['reference_review']['sources'][0]['url'], 'date':published.isoformat(),
        'snippet':'Il bollettino Android indica i livelli patch.'}], True)


def test_comparison_retrieves_both_subjects_before_explaining(core, monkeypatch):
    def page(title, revision, extract):
        return {'query':{'pages':[{'title':title,'ns':0,'revisions':[{'revid':revision}], 'extract':extract,
                                  'fullurl':f"https://it.wikipedia.org/wiki/{title.replace(' ', '_')}"}]}}
    ram = page('RAM', 111, 'In informatica la RAM è un tipo di memoria volatile con accesso diretto ai dati.')
    storage = page('Memoria di massa', 222, 'Una memoria di massa conserva grandi quantità di dati in maniera non volatile.')
    lookups = Mock(side_effect=[ram, storage, ram, {'query':{'pages':[]}}])
    monkeypatch.setattr('allma_model.utils.web_search.request_json', lookups)
    core.public_references.search = NativeWebSearch()
    core.public_references.configure(True)
    question = 'Cerca sul web la differenza tra RAM e memoria di archiviazione.'
    answer = turn(core, core.start_conversation('synthetic'), question)
    assert answer.is_valid and 'conserva i dati anche dopo lo spegnimento [2]' in answer.content
    assert [call.kwargs['params']['gsrsearch'] for call in lookups.call_args_list] == ['RAM','memoria di massa']
    sources = response_origin(answer.metadata)['sources']
    assert [source['subject'] for source in sources] == ['RAM', 'memoria di archiviazione']
    assert [source['url'].split('oldid=')[1] for source in sources] == ['111', '222']
    incomplete = turn(core, core.start_conversation('synthetic'), question)
    assert not incomplete.is_valid and not incomplete.content


def test_italian_politics_uses_scoped_public_feed(core, monkeypatch):
    from email.utils import format_datetime

    published = format_datetime(datetime.now(timezone.utc))
    transport = Mock(return_value=f'''<rss><channel><item>
      <title>Tavolo sulla legge di bilancio</title><link>https://www.governo.it/it/articolo/tavolo/1</link>
      <description>Si è svolto oggi un incontro presso la sede di Palazzo Chigi.</description>
      <pubDate>{published}</pubDate></item></channel></rss>'''.encode())
    monkeypatch.setattr('allma_model.utils.web_search.request_bytes', transport)
    core.public_references.search = NativeWebSearch()
    core.public_references.configure(True)
    politics = turn(core, core.start_conversation('synthetic'), 'Quali sono le ultime notizie sulla politica italiana?')
    assert politics.is_valid and 'Comunicati ufficiali del Governo italiano' in politics.content
    assert 'Tavolo sulla legge di bilancio' in politics.content
    assert transport.call_args.args[1] == 'https://www.governo.it/feed/rss'
    assert 'params' not in transport.call_args.kwargs
    guard = turn(core, core.start_conversation('synthetic'), 'Quali sono le ultime notizie sulla politica francese?')
    assert not guard.is_valid and not guard.metadata['reference_review']['network_used']
    transport.assert_called_once()


def test_inflation_picks_latest_consumer_prices_instead_of_other_prices():
    rows = [
        {'title':'Prezzi all’importazione','date':'2026-11-14','url':'https://www.istat.it/import/',
         'snippet':'I prezzi all’importazione crescono del tre per cento.'},
        {'title':'Prezzi al consumo – Settembre','date':'2026-10-16','url':'https://www.istat.it/settembre/',
         'snippet':'A settembre i prezzi al consumo sono cresciuti del quattro per cento.'},
        {'title':'Prezzi al consumo – Ottobre','date':'2026-10-30','url':'https://www.istat.it/ottobre/',
         'snippet':'Secondo le stime preliminari l’indice dei prezzi al consumo è aumentato del cinque per cento'},
    ]
    query = 'ultimi dati sull’inflazione italiana'
    rows = [dict(row, publisher='Istat') for row in rows]
    answer = compose_web_answer(query, rows, True, today=date(2026,11,14))
    assert len(answer) == 1 and answer[0]['url'] == 'https://www.istat.it/ottobre/'
    assert 'stime preliminari' in answer[0]['excerpt']
    assert not compose_web_answer(query + ' oggi', rows, True, today=date(2026,11,14))
