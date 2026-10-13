import pytest
from allma_model.emotional_system.emotion_analysis import analyze


@pytest.mark.parametrize('text,expected', [
    ('Non mi sento né nervosa né arrabbiata.', set()),
    ('Non c’è nessuno che mi faccia sentire felice.', set()),
    ('Non sono triste ma davvero felice.', {'joy'}),
    ('Mi sento serena e non sono impaurita.', {'trust'}),
    ('Mi sento amareggiata e impaurita.', {'sadness','fear'}),
    ('Non riesco a smettere di piangere.', {'sadness'}),
    ('Mi viene da piangere.', {'sadness'}),
    ('Ho il cuore in gola per la presentazione.', {'fear'}),
    ('Sono al settimo cielo per la notizia.', {'joy'}),
    ('Ho un vaso a pezzi.', set()),
    ('Il vaso è a pezzi.', set()),
    ('Devo scrivere la parola piangere.', set()),
    ('She feels happy but I feel worried.', {'fear'}),
    ('My colleague is anxious, but I am happy.', {'joy'}),
    ('Neither sad nor happy.', set()),
    ('I am not happy, but relieved.', {'joy'}),
])
def test_new_sentences_cover_scoping_and_generalization(text, expected):
    state = analyze(text)
    found = {state['primary_emotion'],*state['secondary_emotions']} - {'neutral'}
    assert found == expected
