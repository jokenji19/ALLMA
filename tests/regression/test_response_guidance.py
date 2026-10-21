import pytest
from allma_model.utils.response_guidance import is_explicit_correction

@pytest.mark.parametrize('text', ["Se dice una bugia verrà impiccato", "Se potessi provare dolore per ogni errore di codice", "Spiega il significato di falso", "Un uomo dice: hai sbagliato"])
def test_hypothetical_errors_are_not_personal_corrections(text):
    assert not is_explicit_correction(text)

@pytest.mark.parametrize('text', ['Hai sbagliato il calcolo', 'No, ti sbagli.', 'La tua risposta è errata', 'Your answer is wrong'])
def test_explicit_corrections_are_recognized(text):
    assert is_explicit_correction(text)


@pytest.mark.parametrize('text', ['Sbagliato, 5 è la risposta', 'Sbagliata!', 'Non è così.',
    'La risposta corretta è 7', 'La risposta è 12', 'No, hai sbagliato il conteggio'])
def test_short_corrections_do_not_need_a_fixed_apology_phrase(text):
    assert is_explicit_correction(text)

@pytest.mark.parametrize('text', ['Sbagliato sarebbe sottrarre senza leggere',
    'Se hai sbagliato puoi riprovare', 'La risposta è interessante',
    'Scrivi la frase: non è così', 'Non è così facile capire il problema'])
def test_quoted_hypothetical_and_unrelated_statements_are_not_corrections(text):
    assert not is_explicit_correction(text)
