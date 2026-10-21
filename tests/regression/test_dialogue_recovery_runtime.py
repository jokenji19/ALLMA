from types import SimpleNamespace as T
from unittest.mock import Mock
import pytest

from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.answer_stream import AnswerStream
from allma_model.utils.runtime_capabilities import self_description_reply


def turn(role, content, valid=True):
    return T(role=role, content=content, metadata={'is_valid': valid})


def test_failed_retry_compares_latest_attempt_and_never_uses_invalid_answer():
    valid = [turn('user', 'Spiegami il tema'),
             turn('assistant', 'Una spiegazione pertinente che contiene almeno otto parole per il confronto.')]
    raw = valid + [turn('user', 'Mi confermi?'), turn('assistant', 'Notizia inventata', False)]
    guard = DialogueContinuity('Mi confermi?', valid + [raw[-2]], attempt_history=raw)
    assert guard.same_request and guard.retry_after_failure
    assert guard.previous_answer == valid[-1].content
    assert not guard.duplicate(valid[-1].content)
    assert guard.duplicate('Come stai?') is False
    assert DialogueContinuity('Un tema diverso', valid, raw).check_duplicate


def test_correction_is_not_permission_to_repeat_after_failure():
    valid = [turn('user', 'Prima richiesta'),
             turn('assistant', 'La stessa risposta abbastanza lunga da essere confrontata e bloccata.')]
    raw = valid + [turn('user', 'Non ripetere la risposta'), turn('assistant', 'Avviso', False)]
    guard = DialogueContinuity('Non ripetere la risposta', valid, raw)
    assert guard.duplicate(valid[-1].content)


def test_checkin_limits_only_current_checkin_response():
    greetings = [turn('user', 'Ciao'), turn('assistant', 'Come stai?')]
    assert DialogueContinuity('Sto bene', greetings).responding_to_checkin
    later = greetings + [turn('user', 'Bene'), turn('assistant', 'Grazie per avermelo detto.')]
    guard = DialogueContinuity('Parliamo di musica', later)
    assert guard.answered_checkin and not guard.responding_to_checkin
    events = []
    stream = AnswerStream(guard.message, events.append, guard)
    stream.feed('La musica può avere ritmi diversi. ')
    assert events and not stream.rejected
    stream.feed('Come ti va? ')
    assert stream.rejected
    assert 'Come ti va?' not in ''.join(e['content'] for e in events)


@pytest.mark.parametrize('query', ['Bene, come stai tu?', 'Hai emozioni?',
    'Non hai emozioni?', 'Non sei una macchina, hai delle emozioni', 'Sei un modello di linguaggio?'])
def test_runtime_descriptions_are_not_model_biographies(query):
    core = T(emotional_core=object(), identity_engine_v5=object(),
             conversational_memory=object(), _llm=object())
    answer, source, evidence = self_description_reply(query, core, [])
    assert source == 'runtime_self_description' and not evidence
    assert 'Sono un modello' not in answer
    assert 'provo emozioni' not in answer


def test_unrelated_or_complex_requests_are_not_intercepted():
    core = T()
    for query in ['Tu', 'Mia sorella ha emozioni', 'Spiega come funziona il cervello',
                  'Hai emozioni? Rispondi solo con JSON.', 'Sono triste, come stai tu?']:
        assert self_description_reply(query, core, []) is None


def test_error_clarification_explains_control_without_repeating_invalid_text():
    previous = turn('assistant', 'Contenuto inventato', False)
    previous.metadata['generation'] = {'status': 'dialogue_repetition'}
    answer, source, _ = self_description_reply('Cosa intendi?', T(), [previous])
    assert source == 'runtime_recovery_explanation'
    assert 'Contenuto inventato' not in answer
    assert self_description_reply('Cosa intendi?', T(), [turn('assistant', 'Una spiegazione')]) is None
