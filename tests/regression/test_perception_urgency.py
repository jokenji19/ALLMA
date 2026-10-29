"""Urgency is an attributed request, not a substring or an object's property."""
import pytest

from allma_model.core.perception_lite import PerceptionSystemLite


@pytest.mark.parametrize('text', [
    'Vorrei un disegno colorato', 'Come posso migliorare la memoria?',
    'Ora parliamo di astronomia', 'La luce è veloce',
    'Spiegami perché un treno è veloce', 'Descrivi un algoritmo rapido',
    'Non è urgente e non devi rispondere subito', 'Non rispondere ora',
    'Non ho bisogno di una risposta veloce', 'It is not urgent',
    'Do not reply now', 'A quick train is not an urgent request',
    'Traduci urgente in inglese', 'Che significa la parola urgente?',
    'Scrivi una storia urgente', 'Translate: reply now',
    'Dice che è urgente', 'Mario ha detto di rispondere subito',
    'Se fosse urgente, cosa faresti?', 'If I need an answer now, what happens?',
    '«Rispondi subito» è una citazione', 'Scrive "urgente!" nel libro',
    'Il codice è `urgent`', '```\nreply now\n```',
    'Ho un orologio', '', None,
])
def test_non_requests_do_not_create_urgency(text):
    assert PerceptionSystemLite()._detect_urgency(text) is None


@pytest.mark.parametrize('text,level', [
    ('È urgente, ho bisogno di aiuto', 'high'),
    ('Ho un problema urgente', 'high'), ('Please reply urgently', 'high'),
    ('I need help ASAP', 'high'), ('Rispondimi subito', 'medium'),
    ('Mi serve una risposta veloce', 'medium'), ('Dammi una risposta rapida', 'medium'),
    ('Ora rispondimi', 'medium'), ('Rispondimi adesso', 'medium'),
    ('Please answer quickly', 'medium'), ('I need help now', 'medium'),
    ('Non è urgente, ma rispondimi subito', 'medium'),
    ('Non voglio aspettare: rispondimi ora', 'medium'),
])
def test_explicit_requests_preserve_local_negation_and_evidence(text, level):
    result = PerceptionSystemLite()._detect_urgency(text)
    assert result and result['level'] == level
    assert result['source'] == 'local_urgency_evidence_v2'
    for evidence in result['evidence']:
        assert text[evidence['start']:evidence['end']].strip()


def test_urgency_does_not_leak_to_next_turn_or_another_user():
    perception = PerceptionSystemLite()
    assert 'urgency' in perception.process('È urgente', {'user_id': 'a', 'conversation_id': '1'})
    assert 'urgency' not in perception.process('Parliamo di colori', {'user_id': 'a', 'conversation_id': '1'})
    assert 'urgency' not in perception.process('Parliamo di colori', {'user_id': 'b', 'conversation_id': '2'})


def test_urgency_analysis_is_bounded():
    result = PerceptionSystemLite()._detect_urgency('È urgente. ' * 2000)
    assert len(result['evidence']) == 16
    assert all(row['end'] <= 12000 for row in result['evidence'])
