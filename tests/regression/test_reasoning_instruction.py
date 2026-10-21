import pytest
from allma_model.utils.sampling_policy import reasoning_instruction, REASONING_INSTRUCTION


@pytest.mark.parametrize('message,expected', [
    ('Rispondi in una frase.', 'esattamente 1 frase'),
    ('Spiega in due frasi.', 'esattamente 2 frasi'),
    ('Rispondi solo con JSON.', 'soltanto JSON valido'),
    ('Rispondi solo con un numero.', 'soltanto un numero'),
    ('Rispondi solo sì o no.', 'soltanto sì oppure no'),
])
def test_explicit_answer_shape_is_guided_without_exposing_reasoning(message,expected):
    instruction=reasoning_instruction(message)
    assert expected in instruction
    assert 'verifiche internamente' in instruction


def test_ordinary_reasoning_keeps_existing_instruction():
    assert reasoning_instruction('Come si forma un arcobaleno?')==REASONING_INSTRUCTION
