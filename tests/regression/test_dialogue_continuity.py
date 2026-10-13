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
