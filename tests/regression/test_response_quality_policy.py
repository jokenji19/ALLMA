from threading import Lock
from unittest.mock import Mock
import pytest
from allma_model.utils.output_contract import requested_sentence_count, valid_sentence_count
from allma_model.utils.sampling_policy import sampling_options


@pytest.mark.parametrize('message,count', [
    ('Rispondimi in due frasi.',2),('Spiegalo in tre frasi semplici.',3),
    ('Answer in exactly two sentences.',2),
    ('Rispondi in 4 frasi.',4),('Rispondi in almeno due frasi.',None),
    ('Non rispondere in due frasi.',None),
    ('Che significa «Rispondimi in due frasi»?',None),
])
def test_explicit_sentence_request(message,count):
    assert requested_sentence_count(message)==count


def test_sentence_validation_is_conservative_and_does_not_truncate():
    assert valid_sentence_count('La misura è 2.5. Il totale è 3.',2)
    assert not valid_sentence_count('Una sola frase.',2)
    assert valid_sentence_count('Davvero?! Certamente...',2)
    # Uncertainty must not silently satisfy an exact output contract.
    assert not valid_sentence_count('Dott. Rossi è arrivato.',2)
    assert not valid_sentence_count('Dice «Una frase. Due frasi.»',1)
    assert valid_sentence_count('Dice «Una frase. Due frasi.»',2)
    assert not valid_sentence_count('```python\nprint("x")\n```',2)
    assert valid_sentence_count('```python\nprint("x")\n```',None)


def test_sampling_is_specific_to_qwen3_and_does_not_disable_reasoning():
    assert sampling_options('/models/qwen3-1.7b-q8_0.gguf')==dict(temperature=.6,top_p=.95,top_k=20,min_p=0.)
    assert sampling_options('/models/other.gguf')==dict(temperature=.4,top_p=.9)
    assert sampling_options(Mock())==dict(temperature=.4,top_p=.9)


def test_native_wrapper_receives_and_reports_sampling_values():
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    wrapper=MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.inference_lock=Lock();wrapper.n_ctx=2048
    wrapper.llm=Mock(return_value={'choices':[{'text':'Risposta.','finish_reason':'stop'}]})
    wrapper.llm.tokenize.return_value=[1]
    assert wrapper.generate('Domanda',max_tokens=20,**sampling_options('qwen3.gguf'))=='Risposta.'
    call=wrapper.llm.call_args.kwargs
    assert call['top_k']==20 and call['min_p']==0.
    assert wrapper.last_generation['top_k']==20 and wrapper.last_generation['min_p']==0.


def test_old_confirmed_answer_with_wrong_sentence_count_is_not_recalled(tmp_path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    store=AnswerRecall(tmp_path/'recall.json')
    question='Spiega una scelta in due frasi.'
    store.records['legacy']={'user':'u','question':question,'answer':'Una sola frase.',
                             'rejected':False,'confirmations':['one','two']}
    assert store.lookup('legacy','u') is None
    store.observe('new','u',question,'Una sola frase.','event')
    assert 'new' not in store.records
    store.records['legacy']['answer']='Una frase. Una seconda frase.'
    assert store.lookup('legacy','u') is not None
