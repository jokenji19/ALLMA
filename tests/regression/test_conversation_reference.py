from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from allma_model.utils.conversation_reference import question_reply


def turn(text, index, *, role='user', user='u', conversation='c', metadata=None):
    return SimpleNamespace(content=text, role=role, user_id=user, conversation_id=conversation,
                           timestamp=datetime(2026,1,1)+timedelta(seconds=index), metadata=metadata or {})


@pytest.mark.parametrize('query', [
    'Che cosa ti ho domandato nella precedente domanda?',
    'Cosa ti ho chiesto prima?', 'Qual era la mia domanda precedente?',
    'Che domanda ti ho fatto poco fa?',
])
def test_previous_means_last_user_turn_not_first_or_assistant(query):
    history=[turn('Prima domanda?',0),turn('Seconda domanda?',1),
             turn('Risposta non verificata.',2,role='assistant'),
             turn('Domanda di un altro utente?',3,user='other'),
             turn('Domanda di un’altra chat?',4,conversation='other')]
    reply=question_reply(query,history,'u','c')
    assert reply.grounded[2]==['Seconda domanda?']
    assert reply.target['timestamp']==history[1].timestamp.isoformat()


@pytest.mark.parametrize('query', [
    'Che domanda ti ho fatto dopo la domanda: Prima domanda?',
    'Quale domanda ti ho fatto dopo «Prima domanda?»?',
    'Che domanda ti ho fatto dopo la domanda “Prima domanda?”?',
])
def test_explicit_anchor_selects_adjacent_user_turn(query):
    history=[turn('Prima domanda?',0),turn('Risposta.',1,role='assistant'),turn('Seconda domanda?',2)]
    reply=question_reply(query,history,'u','c')
    assert reply.grounded[2]==['Seconda domanda?']


def test_followup_uses_saved_reference_after_reload_not_generated_claims():
    history=[turn('Prima domanda?',0),turn('Seconda domanda?',1),turn('Terza domanda?',2)]
    first=question_reply('Che domanda ti ho fatto dopo la domanda: Prima domanda?',history,'u','c')
    history.append(turn(first.grounded[0],3,role='assistant',
        metadata={'source':first.grounded[1],'conversation_reference':dict(first.target)}))
    reply=question_reply('E quella dopo?',history,'u','c')
    assert reply.grounded[2]==['Terza domanda?']
    previous=question_reply('E quella prima?',history,'u','c')
    assert previous.grounded[2]==['Prima domanda?']


def test_duplicates_and_missing_scope_never_guess():
    history=[turn('Stessa domanda?',0),turn('Stessa domanda?',1)]
    reply=question_reply('Che domanda ti ho fatto dopo la domanda: Stessa domanda?',history,'u','c')
    assert reply.grounded[1]=='conversation_question_clarification'
    assert question_reply('Cosa ti ho chiesto prima?',history,'other','c').grounded[1]=='conversation_question_absent'
    assert question_reply('Che domanda ti ho fatto dopo la domanda: Mai presente?',history,'u','c').grounded[1]=='conversation_question_absent'


@pytest.mark.parametrize('query', [
    'E dopo?', 'Perché dopo la pioggia cambia il cielo?',
    'Spiega cosa significa la domanda precedente.',
    'Nel racconto scrivi: Cosa ti ho chiesto prima?',
])
def test_other_tasks_remain_in_normal_pipeline(query):
    assert question_reply(query,[turn('Una domanda?',0)],'u','c') is None
