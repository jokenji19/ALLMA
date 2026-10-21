import pytest
from allma_model.utils.source_claims import unbacked_source_claim
from allma_model.utils.answer_stream import AnswerStream


@pytest.mark.parametrize('text',[
    'Le informazioni sopra sono confermate da fonti storiche.',
    'Ho consultato le fonti storiche.',
    'Ho verificato fonti online.',
    'Questi dati sono verificati dalle fonti.',
])
def test_unperformed_external_verification_rejected(text):
    assert unbacked_source_claim(text)
    events=[];stream=AnswerStream('Spiega',events.append)
    stream.feed(text+' ');stream.feed('',final=True)
    assert stream.rejected and not events


@pytest.mark.parametrize('text',[
    'Non ho consultato le fonti storiche.',
    'Le informazioni non sono confermate da fonti.',
    'Garibaldi partecipò al Risorgimento.',
    'Il testo dice «Ho consultato le fonti storiche».',
    'Non posso verificare questa informazione offline.',
    'Le fonti storiche possono contenere errori.',
    'Non è vero che ho consultato fonti.',
    'Il testo dice «Ho consultato le fonti storiche',
])
def test_facts_uncertainty_and_quotes_are_not_fabricated_verification(text):
    assert not unbacked_source_claim(text)


def test_generated_source_claim_not_observed_as_learnable_answer(tmp_path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    cache=AnswerRecall(tmp_path/'recall.json')
    cache.observe('k','u','Spiega una nozione storica.','Ho consultato le fonti storiche.','event')
    assert cache.records=={}


def test_old_confirmed_cache_does_not_bypass_source_claim_gate(tmp_path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    cache=AnswerRecall(tmp_path/'recall.json')
    cache.records['k']={'user':'u','question':'Spiega una nozione storica.',
        'answer':'Le informazioni sono confermate da fonti storiche.',
        'observations':2,'confirmations':['a','b'],'rejected':False}
    cache._save()
    restored=AnswerRecall(cache.path)
    assert restored.lookup('k','u') is None
    assert restored.records['k']['confirmations']==['a','b']  # preserved, never silently deleted
