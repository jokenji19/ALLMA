from unittest.mock import Mock
import pytest
from allma_model.utils.output_contract import requested_contract, valid_contract, borrowed_user_experience


@pytest.mark.parametrize('message,kind', [
    ('Rispondi soltanto sì o no.', 'yes_no_it'),
    ('Answer only yes or no.', 'yes_no_en'),
    ('Scrivi soltanto il risultato numerico.', 'number'),
    ('Rispondi solo con JSON valido.', 'json'),
    ('Spiega che significa "rispondi solo con un numero".', None),
    ('Spiega il calcolo.', None),
    ('Rispondi non solo con JSON, ma anche con una spiegazione.', None),
])
def test_explicit_contracts(message,kind):
    assert requested_contract(message)==kind


@pytest.mark.parametrize('text,kind,valid', [
    ('no','yes_no_it',True),('No. Una spiegazione.','yes_no_it',False),
    ('42','number',True),('-3.5','number',True),('42 perché...','number',False),
    ('{"x":true}','json',True),('```json\n{}\n```','json',False),('NaN','json',False),
])
def test_output_validation_never_rewrites(text,kind,valid):
    assert valid_contract(text,kind) is valid


def test_user_experience_is_not_an_assistant_biography():
    request='Sono felice per il nuovo lavoro e preoccupata per il primo giorno.'
    assert borrowed_user_experience('Sono felice per il nuovo lavoro e preoccupata.',request)
    assert not borrowed_user_experience('Sono felice per il tuo nuovo lavoro.',request)
    assert not borrowed_user_experience('Ho capito la preoccupazione per il nuovo lavoro.',request)
    assert not borrowed_user_experience('Puoi sentirti felice e preoccupata insieme.',request)
    assert not borrowed_user_experience('Sono felice per il nuovo lavoro.', 'Riscrivi in prima persona: '+request)


def test_grammar_only_applies_to_answer_and_thought_still_runs():
    from allma_model.utils.generation_budget import bounded_completion
    calls=[]
    def generate(prompt,**kwargs):
        calls.append(kwargs)
        yield {'choices':[{'text':'Ragiono.' if len(calls)==1 else 'no','finish_reason':'stop'}]}
    llm=Mock(side_effect=generate);llm.tokenize.side_effect=lambda data:data.split()
    grammar=object()
    result=bounded_completion(llm,'<think>',{'max_tokens':96},32,answer_grammar=grammar)
    assert 'grammar' not in calls[0]
    assert calls[1]['grammar'] is grammar
    assert result['budget_meta']['reasoning_tokens'] > 0


def test_brief_contract_budget_preserves_complex_reasoning():
    from allma_model.utils.prompt_budget import reasoning_budget
    assert reasoning_budget('Quanto fa 5+4? Rispondi solo con un numero.','SIMPLE',256)==32
    assert reasoning_budget('Dimostra il teorema. Rispondi solo con un numero.','COMPLEX',512)==192


def test_stream_does_not_emit_borrowed_personal_experience():
    from allma_model.utils.answer_stream import AnswerStream
    emit=Mock();s=AnswerStream('Sono triste per il nuovo lavoro.',emit)
    s.feed('Sono triste per il nuovo lavoro. ')
    assert s.rejected and not emit.called
