import pytest

from allma_model.utils.reference_comparison import (
    comparison_subject,
    source_comparison_followup,
    source_comparison_request,
)


@pytest.mark.parametrize('message', [
    'Mi spieghi come verificare le fonti?',
    'Le fonti concordano con la mia storia?',
    'Vorrei studiare come divergono le fonti.',
    'Confronta le fonti che ti ho mandato.',
    'Le fonti che hai citato sono davvero indipendenti?',
    'Compare sources sulfur.',
    'Confronta le fonti sul\ntelefono',
])
def test_discussing_sources_does_not_start_a_comparison(message):
    assert not source_comparison_request(message)
    assert not source_comparison_followup(message)
    assert comparison_subject(message) == message


@pytest.mark.parametrize('message, subject', [
    ('Confronta due fonti sull’entropia', 'entropia'),
    ('Potresti confrontare le due fonti sulla fotosintesi?', 'fotosintesi?'),
    ('Verifica due fonti indipendenti sulle maree', 'maree'),
    ('Confronta ESA e NASA: c’è un oceano su Europa?', 'c’è un oceano su Europa?'),
    ('Le fonti concordano sul Medioevo?', 'Medioevo?'),
    ('Can you cross-check two sources about photosynthesis?', 'photosynthesis?'),
    ('Do the two sources disagree on photosynthesis?', 'photosynthesis?'),
    ('Puoi fare un confronto tra due fonti sui vulcani?', 'vulcani?'),
    ('Metti a confronto le fonti tra loro sulla tettonica.', 'tettonica.'),
])
def test_explicit_comparison_keeps_its_own_subject(message, subject):
    assert source_comparison_request(message)
    assert not source_comparison_followup(message)
    assert comparison_subject(message) == 'Cerca ' + subject


@pytest.mark.parametrize('message', [
    'Puoi confrontare le fonti?',
    'Le due fonti concordano tra loro?',
    'Confronta NASA e NOAA',
    'Can you compare the two sources?',
])
def test_only_a_closed_subjectless_comparison_can_inherit_context(message):
    assert source_comparison_request(message)
    assert source_comparison_followup(message)
