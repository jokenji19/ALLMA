import pytest
from allma_model.learning_system.message_delivery import MessageDelivery, preference_request
from allma_model.utils.answer_stream import AnswerStream


@pytest.mark.parametrize('text,mode', [
    ('Preferisco le risposte progressive', 'progressive'),
    ('Da ora scrivimi tutto insieme!', 'complete'),
    ('Non scrivere in streaming.', 'complete'),
    ('Decidi tu come mandare le risposte', 'auto'),
    ('«Scrivimi tutto insieme» è una citazione', None),
    ('Non voglio le risposte progressive', None),
    ('Preferisco il colore blu', None),
    ('Voglio risposte complete', None),
    ('Scrivimi tutto insieme e spiegami Roma', None),
    ('Esatto', None),
])
def test_only_explicit_unambiguous_delivery_directives(text, mode):
    assert preference_request(text) == mode


def test_preference_persists_per_user_and_preserves_personal_validation(tmp_path):
    path = tmp_path / 'delivery.json'
    store = MessageDelivery(path)
    assert store.choose('u', 'Spiega le stelle')[0] == 'progressive'
    store.learn('u', 'complete')
    restored = MessageDelivery(path)
    assert restored.choose('u', 'Spiega le stelle')[0] == 'complete'
    assert restored.choose('other', 'Spiega le stelle')[0] == 'progressive'
    restored.learn('u', 'progressive')
    assert restored.choose('u', 'Qual è il tuo nome?') == ('complete', 'personal_validation')
    assert restored.choose('u', 'Spiega le stelle', voice=True)[0] == 'complete'


def test_corrupt_state_defaults_to_streaming_and_failed_save_does_not_learn(tmp_path, monkeypatch):
    path = tmp_path / 'delivery.json'
    path.write_text('null')
    store = MessageDelivery(path)
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr('allma_model.learning_system.message_delivery.atomic_write_json', fail)
    with pytest.raises(OSError):
        store.learn('u', 'complete')
    assert store.choose('u', 'Spiega le stelle')[0] == 'progressive'


def test_stream_releases_sentences_before_end_without_duplicate_answer():
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    stream.feed('Il mare è ')
    assert not events
    stream.feed('salato. ')
    assert events[0]['content'] == 'Il mare è salato.'
    stream.feed('Le onde si muovono')
    stream.feed('', final=True)
    assert ''.join(event['content'] for event in events) == 'Il mare è salato. Le onde si muovono'


def test_split_personal_claim_is_never_sent_even_in_a_general_answer():
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    for chunk in ['Ho visi', 'tato Roma.', ' Il mare è salato. ']:
        stream.feed(chunk)
    stream.feed('', final=True)
    assert stream.rejected
    assert not events


def test_identity_and_code_are_buffered_for_validation():
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    stream.feed('Mi chiamo Sophia. ')
    assert stream.rejected and not events
    stream = AnswerStream('Scrivi codice Python', events.append)
    stream.feed('```python\nprint("x")\n```')
    stream.feed('', final=True)
    assert not events
