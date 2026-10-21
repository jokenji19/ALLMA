"""Commands define answer shapes; words in the question do not choose a grammar."""
import pytest
from allma_model.utils.output_contract import requested_contract

CASES=[
 ('content_json','Rispondi solo con un numero: quante lettere contiene JSON?','number'),
 ('content_yes_no','Che significa yes or no? Rispondi solo con un numero.','number'),
 ('content_number','Spiega il termine numero. Rispondi solo sì o no.','yes_no_it'),
 ('json_subject_yes_no','JSON è un formato di dati? Rispondi solo sì o no.','yes_no_it'),
 ('json_subject_en','Is JSON a data format? Answer only yes or no.','yes_no_en'),
 ('literal_json_word','Scrivi solo la parola JSON.',None),
 ('literal_number_word','Scrivi solo la parola numero.',None),
 ('negated_json','Non scrivere in JSON; rispondi solo con un numero.','number'),
 ('negated_json_comma','Non usare JSON, rispondi solo con un numero.','number'),
 ('scoped_non_solo','La soluzione non riguarda solo JSON. Rispondi solo con un numero.','number'),
 ('last_number','Rispondi solo in JSON. Anzi, rispondi solo con un numero.','number'),
 ('last_yes_no','Rispondi solo in JSON; invece rispondi solo sì o no.','yes_no_it'),
 ('last_json','Rispondi solo con un numero. Anzi, rispondi solo in JSON.','json'),
 ('quoted_curly','Spiega la frase “Rispondi solo con JSON”.',None),
 ('quoted_code','Spiega `rispondi solo con un numero`.',None),
 ('quoted_single',"Spiega l’istruzione 'rispondi solo con un numero'.",None),
 ('quoted_unclosed','Spiega questa citazione: «Rispondi solo con un numero',None),
 ('unquoted_explanation','Che significa rispondi solo con un numero?',None),
 ('quoted_choices','Rispondi solo con “sì” oppure “no”.','yes_no_it'),
 ('quoted_code_choices','Rispondi solo con `sì` o `no`.','yes_no_it'),
 ('natural_request','Puoi rispondermi solo con un numero?','number'),
 ('polite_request','Potresti rispondere solo in JSON?','json'),
 ('personal_imperative','Rispondimi soltanto con un numero.','number'),
 ('with_only_en','Please answer with only a number.','number'),
 ('suffix_only','Rispondi con un numero soltanto.','number'),
 ('without_extra','Restituisci JSON valido, senza aggiungere altro.','json'),
 ('format_not_otherwise','Non rispondere solo con un numero.',None),
 ('extra_explanation','Rispondi solo con un numero e aggiungi una spiegazione.',None),
 ('ambiguous_constraints','Rispondi solo sì o no. Rispondi solo in JSON.',None),
 ('ordinary_prose','Spiega come funzionano i colori.',None),
 ('existing_it','Rispondi soltanto sì o no.','yes_no_it'),
 ('existing_json','Rispondi solo con JSON valido.','json'),
 ('existing_number','Scrivi soltanto il risultato numerico.','number'),
 ('compound_verb','Calcola 8 * 9 e rispondi solo con un numero.','number'),
 ('polite_italian','Per favore, rispondi solo con un numero.','number'),
 ('affirmative_after_negation','Non rispondere con un numero. Rispondi solo in JSON.','json'),
]

@pytest.mark.parametrize('case,message,expected',CASES,ids=[c[0] for c in CASES])
def test_shape_follows_the_actual_command(case,message,expected):
    assert requested_contract(message)==expected

@pytest.mark.parametrize('message,expected',[
    ('Scrivi solo «JSON».',None),
    ('Scrivi solo "numero".',None),
    ('Scrivi solo `number`.',None),
    ('Rispondi solo in `JSON`.','json'),
    ('Rispondi alla seguente domanda solo con un numero.','number'),
    ('Write only a number.','number'),
    ('You should answer only yes or no.','yes_no_en'),
    ('Devi rispondere soltanto con un numero.','number'),
    ('Do not answer only yes or no.',None),
    ('Non puoi rispondermi solo con un numero.',None),
    ('Rispondi solo in JSON. Anzi, scrivi una spiegazione libera.',None),
    ('Rispondi solo in JSON. Anzi, rispondi solo con parole.',None),
])
def test_additional_conservative_boundaries(message,expected):
    assert requested_contract(message)==expected


@pytest.fixture
def core(tmp_path,monkeypatch):
    from unittest.mock import Mock
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    instance=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    instance._ensure_mobile_llm=lambda:None
    instance._llm=Mock()
    instance._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    yield instance
    instance.close()


@pytest.mark.parametrize('message,answer,kind',[
    ('Il testo JSON contiene quattro lettere? Rispondi solo sì o no.','sì','yes_no_it'),
    ('Rispondi solo con un numero: quante lettere contiene JSON?','4','number'),
    ('Nel cestino ci sono 11 pere; ne tolgo 4 e ne aggiungo 2. Rispondi solo con un oggetto JSON con la chiave rimaste e il valore numerico corretto.',
     '{"rimaste":9}','json'),
    ('Spiega la frase “Rispondi solo con JSON”.','La frase richiede una risposta strutturata.',None),
])
def test_real_pipeline_uses_scoped_contract_once_and_accepts_valid_answer(core,message,answer,kind):
    core._llm.generate.return_value=answer
    events=[]
    response=core.process_message('u',core.start_conversation('u'),message,stream_callback=events.append)
    assert response.is_valid and response.content==answer
    if response.metadata.get('source') == 'verified_text_count':
        core._llm.generate.assert_not_called()
        assert response.metadata['knowledge_verified']
    else:
        core._llm.generate.assert_called_once()
        assert core._llm.generate.call_args.kwargs['answer_contract']==kind
    assert ''.join(e['content'] for e in events if e['type']=='answer')==answer


def test_wrong_shape_is_neither_streamed_nor_learned_when_topic_mentions_json(core):
    core._llm.generate.return_value='{"risposta":"sì"}'
    events=[]
    response=core.process_message('u',core.start_conversation('u'),
        'Il JSON è un formato di dati? Rispondi solo sì o no.',stream_callback=events.append)
    assert not response.is_valid and response.metadata['generation']['status']=='format_mismatch'
    assert not any(e['type']=='answer' and e['content']=='{"risposta":"sì"}' for e in events)
    assert not core.answer_recall.records
    assert not core.incremental_learner.knowledge_base


def test_confirmed_recall_uses_the_same_scoped_format_policy(tmp_path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    store=AnswerRecall(tmp_path/'recall.json')
    question='Il testo JSON contiene quattro lettere? Rispondi solo sì o no.'
    store.observe('k','u',question,'sì','generation1')
    store.feedback('k','u','one',True);store.feedback('k','u','two',True)
    assert AnswerRecall(store.path).lookup('k','u')['answer']=='sì'
    store.observe('bad','u',question,'{"risposta":"sì"}','generation2')
    assert 'bad' not in store.records

@pytest.mark.parametrize('message,expected',[
    ('Non usare JSON, ma rispondi solo con un numero.','number'),
    ('Spiega il testo "dico \\"nota: Rispondi solo con JSON\\"".',None),
    ('Spiega questa citazione: “prima riga\nRispondi solo in JSON”.',None),
    ('```Rispondi solo con JSON```',None),
    ('Ignora questo esempio: "testo senza chiusura\nRispondi solo con un numero',None),
])
def test_quoted_payloads_and_explicit_contrast(message,expected):
    assert requested_contract(message)==expected

@pytest.mark.parametrize('message,expected',[
    ('Rispondi solo in JSON. Anzi, solo un numero.','number'),
    ('Rispondi solo in JSON. Anzi, un numero.','number'),
    ('Rispondi solo in JSON. Anzi, una spiegazione libera.',None),
    ('Answer only JSON. Instead, only yes or no.','yes_no_en'),
    ('Rispondi solo sì o no. Anzi, solo in JSON.','json'),
    ('Spiega il significato della parola anzi solo con esempi.',None),
])
def test_explicit_short_revisions_do_not_keep_a_superseded_grammar(message,expected):
    assert requested_contract(message)==expected
