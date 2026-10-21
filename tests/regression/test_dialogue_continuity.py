from types import SimpleNamespace
import pytest
from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.answer_stream import AnswerStream


ANSWER = 'Ciao! Sto bene, grazie. Il tempo è 20:13, in carica. Come ti senti?'


def history(question='Bene, tu?', answer=ANSWER):
    return [SimpleNamespace(role='user', content=question),
            SimpleNamespace(role='assistant', content=answer)]


@pytest.mark.parametrize('message', ['Ti ho già risposto che sto bene',
    'Mr lhai già chiesto, ti ho risposto prima che sto bene',
    'Ora parliamo di musica', 'Non ripetere la risposta precedente'])
def test_duplicate_across_different_turns(message):
    guard = DialogueContinuity(message, history())
    assert guard.duplicate(ANSWER)
    assert not guard.duplicate('Possiamo parlare di musica.')


@pytest.mark.parametrize('message', ['Ripeti la risposta precedente',
    'Traduci la risposta precedente', 'Riscrivi questo testo', 'Bene, tu?'])
def test_legitimate_repetition(message):
    answer = 'La risposta resta uguale perché la domanda è esattamente la stessa.' if message == 'Bene, tu?' else ANSWER
    assert not DialogueContinuity(message, history(answer=answer)).duplicate(answer)


def test_short_identical_answers_to_different_questions_are_valid():
    assert not DialogueContinuity('Quanto fa 6 per 7?', history('Quanto fa 23 più 19?', '42')).duplicate('42')
    assert not DialogueContinuity('Anche le balene?', history('I gatti sono mammiferi?', 'Sì.')).duplicate('Sì.')


def test_duplicate_is_not_streamed_and_divergence_releases_buffer():
    guard = DialogueContinuity('Te l’ho già detto', history())
    events=[];stream=AnswerStream(guard.message,events.append,guard)
    for token in ['Ciao! ', 'Sto bene, grazie. ', 'Il tempo è 20:13, in carica. ', 'Come ti senti?']:
        stream.feed(token)
    stream.feed('',final=True)
    assert stream.rejected and not events
    events=[];stream=AnswerStream(guard.message,events.append,guard)
    stream.feed('Ciao! ')
    assert not events
    stream.feed('Hai ragione, avevi già risposto. ')
    assert events and not stream.rejected


def test_only_latest_assistant_and_no_history_are_safe():
    assert not DialogueContinuity('Nuova domanda', []).duplicate(ANSWER)
    old='Questa risposta precedente contiene abbastanza parole ma non fa domande.'
    turns=history(answer=old)+history('Altra domanda','Una risposta diversa con almeno otto parole nel testo completo.')
    assert not DialogueContinuity('Nuovo tema',turns).duplicate(old)


def test_continuation_repeated_opening_is_held_and_rejected():
    old='Garibaldi fu importante perché unì il movimento per l’unità nazionale italiana. Un altro punto.'
    guard=DialogueContinuity('Completa la risposta precedente dal punto in cui si è interrotta, senza ripetere la parte già scritta.',history(answer=old))
    repeated='Garibaldi fu importante perché unì il movimento per l’unità nazionale italiana, con altri dettagli.'
    assert guard.continuation and guard.duplicate(repeated)
    assert not guard.duplicate('Il punto successivo riguarda invece le conseguenze politiche della sua attività.')
    events=[];stream=AnswerStream(guard.message,events.append,guard)
    stream.feed(repeated+' ')
    assert stream.rejected and not events
    assert not DialogueContinuity('Riassumi la risposta precedente',history(answer=old)).repeated_continuation_prefix(repeated)


def test_answered_checkin_cannot_be_reasked_with_another_wording():
    turns=history('Ciao','Ciao! Come stai?')
    guard=DialogueContinuity('Bene, tu?',turns)
    assert guard.answered_checkin
    assert guard.duplicate('Sto bene, grazie. Come ti va?')
    assert not guard.duplicate('Grazie per avermelo detto.')
    assert not guard.duplicate('Hai detto «Come stai?» e hai già risposto.')


def test_checkin_is_allowed_without_answer_and_in_explicit_examples():
    assert not DialogueContinuity('Ciao',[]).duplicate('Come ti senti?')
    turns=history('Ciao','Come stai?')
    assert not DialogueContinuity('Scrivi un dialogo di saluti',turns).duplicate('Come ti va?')


def test_project_or_technical_questions_are_not_wellbeing():
    from allma_model.utils.dialogue_continuity import wellbeing_question
    assert not wellbeing_question('Come va risolto questo problema?')
    assert not wellbeing_question('Come va il progetto?')


def test_explicit_request_to_ask_again_is_allowed():
    turns=history('Ciao','Come stai?')+history('Bene','Grazie per avermelo detto.')
    assert not DialogueContinuity('Ora chiedimi di nuovo come sto',turns).duplicate('Come ti senti?')


def test_expansion_guidance_without_rejecting_legitimate_overlap():
    guard = DialogueContinuity('Puoi spiegare meglio?', history())
    assert 'ampliamento' in guard.guidance()
    assert not guard.duplicate('Ciao! Sto bene, grazie. Ecco un elemento diverso e pertinente.')


def test_smalltalk_budget_retains_reasoning_without_cutting_complex_tasks():
    from allma_model.utils.prompt_budget import reasoning_budget
    assert reasoning_budget('Come stai?', 'SIMPLE', 224) == 32
    assert reasoning_budget('Come stai?', 'COMPLEX', 512) == 128
    assert reasoning_budget('Come va risolto questo problema?', 'SIMPLE', 256) == 64


@pytest.mark.parametrize('question,answer,correction', [
    ('Ci sono 7 palline; 2 diventano rosse. Quante rimangono nella scatola?', '5', 'Sbagliato, sono 7.'),
    ('Ci sono 7 palline; 2 vengono tolte. Quante rimangono?', '5', 'La risposta corretta è 7'),
    ('Una scatola contiene 9 oggetti; 3 si rompono. Quanti ne restano dentro?', '6', 'Non è così.'),
])
def test_content_challenges_recheck_without_accepting_proposed_facts(question, answer, correction):
    guard = DialogueContinuity(correction, history(question, answer))
    instruction = guard.guidance()
    assert guard.factual_correction and not guard.correction
    assert 'non accettarla automaticamente' in instruction
    assert 'domanda originale' in instruction and 'effettivamente rimosso' in instruction
    assert '5' not in instruction and '7' not in instruction
    assert not guard.duplicate(answer)  # A false correction may leave the result unchanged.


def test_quantity_guidance_applies_to_first_turn_but_no_spurious_correction():
    guard = DialogueContinuity('Quanti oggetti rimangono nel contenitore?', [])
    assert not guard.factual_correction
    assert 'totale presente' in guard.guidance()
    assert not DialogueContinuity('Sbagliato, sono 8.', []).factual_correction



def test_stream_allows_exercise_premises_without_personal_claim_warning():
    emitted = []
    stream = AnswerStream('In una scatola ci sono 7 palline. Ne tolgo 2. Quante rimangono?', emitted.append)
    stream.feed('Rimangono 5 palline. ')
    stream.feed('All’inizio ci sono 7 palline e ne vengono tolte 2. ')
    stream.feed('', final=True)
    assert not stream.rejected
    assert ''.join(item['content'] for item in emitted).startswith('Rimangono 5 palline.')
    assert len([item for item in emitted if item['content'].strip()]) == 2


def test_short_arithmetic_cannot_answer_a_new_explicit_explanation():
    guard=DialogueContinuity('Spiegami perché si forma un arcobaleno in due fasi',history('Quanto fa 18 + 24?', '42'))
    assert guard.duplicate('18 + 24 = 42')
    assert guard.hold_prefix('18 + 24')
    assert not guard.duplicate('La luce si separa nei colori attraversando le gocce.')
    assert not DialogueContinuity('Spiegami il calcolo precedente',history('Quanto fa 18 + 24?','42')).duplicate('18 + 24 = 42')
    assert not DialogueContinuity('Quanto fa 6 * 7?',history('Quanto fa 18 + 24?','42')).duplicate('42')
