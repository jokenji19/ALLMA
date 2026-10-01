import pytest
from allma_model.utils.response_guidance import is_explicit_correction

@pytest.mark.parametrize('text', ["Se dice una bugia verrà impiccato", "Se potessi provare dolore per ogni errore di codice", "Spiega il significato di falso", "Un uomo dice: hai sbagliato"])
def test_hypothetical_errors_are_not_personal_corrections(text):
    assert not is_explicit_correction(text)

@pytest.mark.parametrize('text', ['Hai sbagliato il calcolo', 'No, ti sbagli.', 'La tua risposta è errata', 'Your answer is wrong'])
def test_explicit_corrections_are_recognized(text):
    assert is_explicit_correction(text)
