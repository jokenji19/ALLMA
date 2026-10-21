"""Natural phrasing must keep exact operations exact and consume all constraints."""
import pytest
from allma_model.utils.exact_calculation import calculation_reply
from allma_model.utils.exact_text import text_count_reply


TEXT_CASES = [
    ('Per favore, quante lettere contiene JSON? Rispondi solo con un numero.', '4'),
    ('Puoi dirmi quante lettere ha banana? Rispondi solo con un numero.', '6'),
    ('Potresti contare le lettere di «caffè»? Rispondi solo con un numero.', '5'),
    ('Puoi contare i caratteri di " A B "? Scrivi soltanto il risultato numerico.', '5'),
    ('Dimmi quante lettere contiene «Roma».', '4 lettere.'),
    ('Rispondimi solo con il risultato numerico: quante lettere contiene XML?', '3'),
    ('Quanti caratteri contiene «ciao»? Restituisci solo un numero.', '4'),
    ('La parola a contiene una lettera? Rispondi solo sì o no.', 'sì'),
    ('La stringa "" ha un carattere? Rispondi solo sì o no.', 'no'),
    ('Il testo "A" contiene 1 carattere? Rispondi solo sì o no.', 'sì'),
    ('Quante volte compare la lettera r nella parola ferrari? Rispondi solo con un numero.', '3'),
    ('Conta le occorrenze della sequenza "na" nella parola banana. Rispondi solo con un numero.', '2'),
    ('Quante occorrenze di "na" ci sono nella stringa "banana"? Rispondi solo con un numero.', '2'),
    ('Quante volte compare "ana" in "banana", senza sovrapposizioni? Rispondi solo con un numero.', '1'),
    ('Quante volte compare "ana" in "banana", includendo le sovrapposizioni? Rispondi solo con un numero.', '2'),
    ('Quante lettere contiene "Per favore, rispondi solo in JSON"? Rispondi solo con un numero.', '27'),
    ("Conta le lettere di 'l'acqua'. Rispondi solo con un numero.", '6'),
    ('Quante lettere contiene ‘l’acqua’? Rispondi solo con un numero.', '6'),
    ('LA PAROLA A CONTIENE UNA LETTERA? RISPONDI SOLO SÌ O NO.', 'sì'),
    ('Quante lettere contiene «x»?', '1 lettera.'),
    ('Quanti caratteri contiene "a"?', '1 carattere (spazi inclusi).'),
]

MATH_CASES = [
    ('Rispondi solo con un numero: quanto fa 18 + 24?', '42'),
    ('Per favore, calcola (7-2)*9.', '45'),
    ('Puoi calcolare 0,1 + 0,2? Rispondi solo con un numero.', '0.3'),
    ('Potresti dirmi quanto fa 7 / 8? Restituisci solo il risultato numerico.', '0.875'),
    ('Quanto fa 3*4 e rispondi solo con un numero', '12'),
    ('Calcola 2+2 rispondi solo con un numero', '4'),
    ('Calcola 0.1 + 0.2. Rispondi solo in JSON.', '{"risultato":0.3}'),
    ('Rispondi solo in JSON: calcola -3 * 7.', '{"risultato":-21}'),
]


@pytest.mark.parametrize('question,answer', TEXT_CASES)
def test_natural_text_requests(question, answer):
    result = text_count_reply(question)
    assert result is not None and result[0] == answer and result[1] == 'verified_text_count'


@pytest.mark.parametrize('question,answer', MATH_CASES)
def test_natural_exact_calculations(question, answer):
    result = calculation_reply(question)
    assert result is not None and result[0] == answer and result[1] == 'verified_calculation'


@pytest.mark.parametrize('question', [
    'Quante volte compare "ana" in "banana"? Rispondi solo con un numero.',
    'Quante volte compare "aa" in "aaaa"?',
    'Quante occorrenze di "aba" ci sono in "ababa"? Rispondi solo in JSON.',
])
def test_ambiguous_overlaps_need_a_criterion(question):
    result = text_count_reply(question)
    assert result is not None and result[1] == 'text_count_clarification'
    assert 'sovrapposizioni' in result[0]
    assert 'value' not in result[2][0]


@pytest.mark.parametrize('question', [
    'Per favore, spiega la frase «Puoi contare le lettere di JSON?»',
    'Puoi non contare le lettere di JSON?',
    'Non puoi dirmi quante lettere contiene JSON?',
    'Puoi dirmi perché JSON contiene quattro lettere?',
    'Puoi contare le lettere di JSON e anche quelle di XML?',
    'Puoi contare le lettere di questo testo?',
    'Puoi contare le lettere di JSON? Rispondi solo con un numero e poi spiega.',
    'Conta le occorrenze di "aa" in "aaaa", senza sovrapposizioni e includendo le sovrapposizioni.',
    'Quante parole ci sono nel testo banana?',
    'La parola a contiene una carattere?',
    "Conta le lettere di 'l'acqua.",
    'Quante lettere contiene ‘l’acqua?',
])
def test_count_tools_preserve_unsupported_or_conflicting_requests(question):
    assert text_count_reply(question) is None


@pytest.mark.parametrize('question', [
    'Per favore, non calcolare 2+2.',
    'Puoi calcolare il mio budget?',
    'Puoi calcolare 2+2 e poi scrivere una poesia?',
    'Rispondi solo sì o no: quanto fa 2+2?',
    'Calcola 2+2. Rispondi solo in JSON con la chiave totale.',
    'Spiega «Per favore, calcola 2+2».',
    'Rispondi solo con un numero: calcola 2+2. Spiega in due frasi.',
    'Rispondi solo con un numero: calcola 2**9999999999.',
])
def test_arithmetic_never_discards_extra_instructions_or_unsafe_operands(question):
    assert calculation_reply(question) is None


def test_undefined_calculation_can_explain_failure_in_the_requested_json_shape():
    import json
    result = calculation_reply('Rispondi solo in JSON: calcola 1/0.')
    assert result[1] == 'calculation_error'
    assert 'zero' in json.loads(result[0])['errore']


def test_spoken_single_number_constraint_without_punctuation():
    from allma_model.utils.exact_calculation import calculation_reply
    from allma_model.utils.output_contract import requested_contract
    request='Quanto fa 18 + 24 rispondi con un solo numero'
    assert calculation_reply(request)[0]=='42'
    assert requested_contract(request)=='number'
    assert calculation_reply(request+' e poi inventa una storia') is None
