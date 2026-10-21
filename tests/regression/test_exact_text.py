"""Literal operations, Unicode boundaries and conservative request recognition."""
import hashlib
import json
from types import SimpleNamespace
import sys
import pytest
from allma_model.utils import exact_text as tool


@pytest.mark.parametrize('question,value', [
    ('Quante lettere contiene JSON?', 4),
    ('Quante lettere contiene il testo JSON?', 4),
    ('Conta le lettere di banana.', 6),
    ('Conta le lettere: «caffè».', 5),
    ('Quante lettere ci sono nella parola "caffe\u0300"?', 5),
    ('Quante lettere contiene «A1 B2!?»?', 2),
    ('Quante lettere contiene "l’acqua"?', 6),
    ('Quante lettere contiene «Ελλάδα»?', 6),
    ('Quante lettere contiene «中文»?', 2),
    ('Quante lettere contiene ""?', 0),
    ('Quante lettere contiene «12345 😀»?', 0),
    ('Conta i caratteri della stringa " A B ".', 5),
    ('Quanti caratteri contiene «caffe\u0300»?', 5),
    ('Quanti caratteri contiene "A\r\nB"?', 3),
    ('Quanti caratteri ci sono nel testo ``?', 0),
    ('Quanti punti di codice Unicode contiene «caffe\u0300»?', 6),
    ('Quanti punti di codice Unicode contiene «👩‍💻»?', 3),
    ('Quante volte compare «ana» in «banana», senza sovrapposizioni?', 1),
    ('Quante volte compare «ana» in «banana», includendo le sovrapposizioni?', 2),
    ('Conta le occorrenze di "aa" nel testo "aaaa", contando anche le sovrapposizioni.', 3),
    ('Conta le occorrenze di "aa" nel testo "aaaa", senza sovrapposizioni.', 2),
    ('Quante volte compare "A" in "aAaA"?', 2),
    ('Quante volte compare "x" in ""?', 0),
    ('Quante volte appare "long" nella stringa "lo"?', 0),
    ('Quante volte compare " " in "a  b"?', 2),
    ('Quante volte compare «è» in «e\u0300»?', 0),
    ('Quante lettere contiene “Rispondi solo in JSON”?', 18),
    ('Quante lettere contiene «@0@»?', 0),
])
def test_counts_apply_to_literal_data(question, value):
    reply = tool.text_count_reply(question)
    assert reply is not None and reply[1] == 'verified_text_count'
    assert reply[2][0]['value'] == value


@pytest.mark.parametrize('question,answer', [
    ('Rispondi solo con un numero: quante lettere contiene JSON?', '4'),
    ('Conta le lettere di «ciao». Scrivi soltanto un numero!', '4'),
    ('Il testo JSON contiene quattro lettere? Rispondi solo sì o no.', 'sì'),
    ('La parola ciao ha cinque lettere? Rispondi solo si o no', 'no'),
    ('La stringa "" contiene zero lettere? Rispondi soltanto sì oppure no.', 'sì'),
    ('La parola JSON contiene 4 lettere?', 'Sì, il conteggio è 4.'),
    ('Quante lettere contiene JSON? Rispondi solo in JSON.', '{"conteggio":4}'),
    ('Il testo JSON contiene 26 lettere? Rispondi solo in JSON.', '{"conteggio":4,"esito":false}'),
])
def test_output_constraints_are_consumed_without_becoming_text(question, answer):
    assert tool.text_count_reply(question)[0] == answer


@pytest.mark.parametrize('question', [
    'Quante lettere contiene il messaggio precedente?',
    'Quante lettere contiene questo?',
    'Quante lettere contiene la risposta che hai dato?',
    'Quante lettere contiene JSON? Spiega il motivo.',
    'Conta le lettere di JSON e di XML.',
    'Conta le lettere di JSON, poi traduci la parola.',
    'Non contare le lettere di JSON.',
    'Spiega «Quante lettere contiene JSON?»',
    '«Quante lettere contiene JSON?»',
    'Nel racconto qualcuno dice: quante lettere contiene JSON?',
    'Quante lettere contiene "testo senza chiusura?',
    'Quante lettere contiene @0@?',
    'Quante lettere contiene JSON "extra"?',
    'Quante lettere contiene JSON? Rispondi in due frasi.',
    'Quante lettere contiene JSON? Rispondi solo in JSON con la chiave risultato.',
    'Quante lettere contiene JSON? Rispondi solo sì o no.',
    'Il testo JSON contiene 4 lettere? Rispondi solo con un numero.',
    'Quante lettere contiene JSON? Rispondi solo con un numero e aggiungi una spiegazione.',
    'Quante lettere contiene JSON? Rispondi solo con un numero. Anzi, rispondi solo in JSON.',
    'Quante lettere contiene JSON, includendo le sovrapposizioni?',
    'Quante volte compare "a" in "Aa", ignorando maiuscole e minuscole?',
    'Quante lettere contiene ```JSON```?',
    'Quante lettere contiene "a\\nb"?',
    'Conta i caratteri di "\ud800".',
    'La parola ciao contiene millanta lettere?',
])
def test_partial_ambiguous_negated_or_multi_operation_requests_are_not_intercepted(question):
    assert tool.text_count_reply(question) is None


def test_limits_and_empty_search_never_fabricate_a_count():
    valid = tool.text_count_reply('Conta le lettere di "'+'a'*tool.MAX_TEXT+'".')
    assert valid[2][0]['value'] == tool.MAX_TEXT
    assert tool.text_count_reply('Conta le lettere di "'+'a'*(tool.MAX_TEXT+1)+'".') is None
    assert tool.text_count_reply('x'*tool.MAX_REQUEST+'!') is None
    reply = tool.text_count_reply('Quante volte compare "" in "banana"? Rispondi solo con un numero.')
    assert reply[1] == 'text_count_clarification'
    assert 'value' not in reply[2][0]


def test_provenance_is_scoped_and_does_not_repeat_the_literal():
    secret = 'testo privato 123'
    reply = tool.text_count_reply('Quante lettere contiene "'+secret+'"?')
    evidence = reply[2][0]
    assert evidence['input_sha256'] == hashlib.sha256(secret.encode()).hexdigest()
    assert evidence['scope'] == 'explicit_literal_only'
    assert secret not in json.dumps(evidence)


def test_many_different_inputs_match_independent_reference_counts():
    import random
    randomizer = random.Random(102530)
    for _ in range(200):
        text = ''.join(randomizer.choices('abcXYZ012 !?', k=randomizer.randrange(0, 100)))
        result = tool.text_count_reply('Conta le lettere di "'+text+'".')
        assert result[2][0]['value'] == sum(c in 'abcXYZ' for c in text)
        result = tool.text_count_reply('Conta i caratteri di "'+text+'".')
        assert result[2][0]['value'] == len(text)


def test_android_iterator_counts_boundaries_not_utf16_indices(monkeypatch):
    class Iterator:
        def setText(self, text):
            assert text == '👩‍💻🇮🇹'
        def first(self):
            self.offsets = iter([5, 9, -1])  # Two clusters, nine UTF-16 code units.
            return 0
        def next(self):
            return next(self.offsets)
    iterator = Iterator()
    def autoclass(name):
        if name == 'java.util.Locale':
            return SimpleNamespace(ROOT='root')
        assert name == 'android.icu.text.BreakIterator'
        return SimpleNamespace(getCharacterInstance=lambda locale: iterator)
    monkeypatch.setitem(sys.modules, 'jnius', SimpleNamespace(autoclass=autoclass))
    reply = tool.text_count_reply('Conta i caratteri di «👩‍💻🇮🇹».')
    assert reply[2][0]['value'] == 2
    assert reply[2][0]['engine'] == 'android-icu-graphemes'


def test_failed_native_service_is_not_a_verified_length(monkeypatch):
    def unavailable(_):
        raise RuntimeError('synthetic native failure')
    monkeypatch.setattr(tool, '_android_graphemes', unavailable)
    result = tool.text_count_reply('Quanti caratteri contiene «👩‍💻»?')
    assert result[1] == 'text_count_unavailable'
    assert 'value' not in result[2][0]
    assert tool.text_count_reply('Quante lettere contiene JSON?')[2][0]['value'] == 4
