"""Boundary, corruption and concurrency tests for message delivery."""
import json
import random
from concurrent.futures import ThreadPoolExecutor

import pytest

from allma_model.learning_system.message_delivery import MessageDelivery, preference_request
from allma_model.utils.answer_stream import AnswerStream
from allma_model.utils.thinking_stream import ThinkingStream


def chunks(text, seed):
    rng = random.Random(seed)
    i = 0
    while i < len(text):
        width = rng.randint(1, 11)
        yield text[i:i + width]
        i += width


@pytest.mark.parametrize('seed', range(40))
def test_random_token_boundaries_preserve_unicode_and_keep_reasoning_private(seed):
    answer = 'Il mare è salato. Le onde si muovono! ✨\nLa luce cambia colore.'
    raw = 'Un ragionamento riservato.</think>' + answer
    parser = ThinkingStream(in_thought=True)
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    for token in chunks(raw, seed):
        for event in parser.feed(token):
            if event['type'] == 'answer':
                stream.feed(event['content'])
    for event in parser.feed('', final=True):
        if event['type'] == 'answer':
            stream.feed(event['content'])
    stream.feed('', final=True)
    assert ''.join(e['content'] for e in events) == answer
    assert not stream.rejected


@pytest.mark.parametrize('seed', range(20))
@pytest.mark.parametrize('claim', [
    ' Mi chiamo Sophia. ',
    '\nMi chiamo Sophia. ',
    ' Mi\nchiamo Sophia. ',
    ' Ho\nvisitato Roma. ',
])
def test_unsafe_second_sentence_never_reaches_preview_at_any_boundary(seed, claim):
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    for token in chunks('Il mare è salato.' + claim, seed):
        stream.feed(token)
    stream.feed('', final=True)
    emitted = ''.join(e['content'] for e in events)
    assert 'Sophia' not in emitted and 'Roma' not in emitted
    assert stream.rejected


@pytest.mark.parametrize('value', [[], {}, None, 1, True])
def test_malformed_saved_modes_do_not_crash_startup(tmp_path, value):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'version': 1, 'users': {'u': {'mode': value}}}))
    store = MessageDelivery(path)
    assert store.choose('u', 'Spiega il mare')[0] == 'progressive'


@pytest.mark.parametrize('payload', ['{broken', 'null', '[]', '42', '"text"', '{"version":1,"users":[]}'])
def test_unreadable_or_wrong_schema_is_safe(tmp_path, payload):
    path = tmp_path / 'state.json'
    path.write_text(payload)
    assert MessageDelivery(path).choose('u', 'Spiega il mare')[0] == 'progressive'


def test_concurrent_preference_writes_do_not_lose_users(tmp_path):
    path = tmp_path / 'state.json'
    store = MessageDelivery(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: store.learn(f'user-{i}', 'complete' if i % 2 else 'progressive'), range(80)))
    restored = MessageDelivery(path)
    assert len(restored.users) == 80
    for i in range(80):
        assert restored.choose(f'user-{i}', 'Spiega il mare')[0] == ('complete' if i % 2 else 'progressive')
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize('text', [
    'Allma, da ora in poi scrivimi tutto insieme',
    'Per favore, ALLMA, rispondi progressivamente',
])
def test_combined_polite_prefixes_are_understood(text):
    assert preference_request(text) in {'complete', 'progressive'}
