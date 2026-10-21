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


@pytest.mark.parametrize('answer', [
    'Sono orgoglioso di aver condiviso questa fase con te.',
    'Ho vissuto questa esperienza insieme a te.',
    'Abbiamo affrontato il trasloco insieme.',
    'Sono felice per te: ho condiviso questa esperienza con te.',
    'Non ho vissuto quel viaggio. Ho affrontato il trasloco con te.',
])
def test_indirect_coparticipation_is_rejected(answer):
    assert borrowed_user_experience(answer, 'Sono sollevata dopo il trasloco.')


@pytest.mark.parametrize('answer,user_message', [
    ('Sono felice per te.', 'Sono felice per il nuovo lavoro.'),
    ('Ho condiviso alcune idee con te.', 'Abbiamo discusso alcune idee.'),
    ('Abbiamo affrontato questo argomento nella chat.', 'Riprendiamo questo argomento.'),
    ('Abbiamo condiviso una conversazione sul trasloco.', 'Parliamo del trasloco.'),
    ('Non ho vissuto questa esperienza con te.', 'Hai vissuto questa esperienza con me?'),
    ('Potremmo affrontare questo percorso insieme nella conversazione.', 'Aiutami a prepararmi.'),
    ('Il protagonista dice: «Ho condiviso questa fase con te».', 'Analizza una frase.'),
    ('Ho vissuto questa esperienza con te.', 'Scrivi un racconto in prima persona.'),
])
def test_support_and_conversational_reference_are_allowed(answer, user_message):
    assert not borrowed_user_experience(answer, user_message)


def test_stream_checks_shared_claim_split_across_tokens():
    from allma_model.utils.answer_stream import AnswerStream
    emit=Mock(); stream=AnswerStream('Ho finito il trasloco.',emit)
    for token in ['Sono orgoglioso di aver condi', 'viso questa fase', ' con te. ']:
        stream.feed(token)
    assert stream.rejected and not emit.called


@pytest.mark.parametrize('answer', [
    'Sono soddisfatto di aver completato il trasloco e posso sentire la tua tranquillità.',
    'Sono soddisfatto di aver completato il trasloco e posso sentire quella tranquillità.',
    'Ho finito il trasloco, sono felice per te.',
    'Ho capito il tuo sollievo e ho completato il trasloco.',
])
def test_user_reference_cannot_exempt_personal_action(answer):
    message='Mia sorella è triste, io non sono triste: sono sollevata di aver finito il trasloco.'
    assert borrowed_user_experience(answer, message)
    assert borrowed_user_experience(answer, 'Scrivi una risposta: '+message)


@pytest.mark.parametrize('answer', [
    'Sono soddisfatto che tu abbia completato il trasloco.',
    'Ho capito il tuo sollievo dopo il trasloco.',
    'Sono felice per il tuo trasloco.',
    'Non ho completato il trasloco: è una tua esperienza.',
])
def test_support_does_not_claim_the_users_action(answer):
    assert not borrowed_user_experience(answer, 'Sono sollevata di aver finito il trasloco.')


def test_stream_rejects_action_despite_later_user_reference():
    from allma_model.utils.answer_stream import AnswerStream
    emit=Mock(); stream=AnswerStream('Sono sollevata di aver finito il trasloco.',emit)
    stream.feed('Sono soddisfatto di aver completato il trasloco e posso sentire la tua tranquillità. ')
    assert stream.rejected and not emit.called


@pytest.mark.parametrize('user_message,answer', [
    ('In una scatola ci sono 7 palline. Ne tolgo 2. Quante rimangono?',
     'Rimangono 5 palline. All’inizio ci sono 7 palline e ne vengono tolte 2.'),
    ('Vi sono 9 oggetti, 3 si rompono. Quanti restano dentro?',
     'Vi sono ancora 9 oggetti: quelli rotti non sono stati rimossi.'),
    ('Nel recinto ci sono 4 animali. Quanti animali ci sono?',
     'Ci sono 4 animali nel recinto.'),
    ('Nella scatola ci sono cinque oggetti.', 'Ci sono cinque oggetti.'),
])
def test_existential_plural_is_not_borrowed_personal_experience(user_message, answer):
    assert not borrowed_user_experience(answer, user_message)


def test_existential_clause_cannot_hide_a_later_personal_claim():
    request = 'Ci sono sette palline. Sono felice e preoccupata per il nuovo lavoro.'
    answer = 'Ci sono sette palline. Sono felice e preoccupata per il nuovo lavoro.'
    assert borrowed_user_experience(answer, request)
    assert borrowed_user_experience('Ci sono sette palline. Ho due figli.', 'Ho due figli.')
    assert borrowed_user_experience('Ci sono sette palline. Ho vissuto il trasloco con te.', 'Sono sollevata dopo il trasloco.')


@pytest.mark.parametrize('answer', ['Ci sono stata al mare ieri.', 'Vi sono già stata al mare ieri.'])
def test_locative_first_person_is_not_exempted_as_existential(answer):
    assert borrowed_user_experience(answer, 'Sono stata al mare ieri.')
