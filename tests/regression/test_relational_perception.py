"""Context is revisable evidence; user needs are not personality diagnoses."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from allma_model.emotional_system.emotion_analysis import analyze
from allma_model.emotional_system.relational_perception import plan, boundary_reply, support_request
from allma_model.core import personality_development as personality
from allma_model.core.personality_outcomes import delivery_receipt, evolve as assess, feedback_signal
from allma_model.core.personality_coalescence import CoalescenceProcessor

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)


def turn(text, **extra):
    return SimpleNamespace(content=text, role='user', user_id='u', conversation_id='c',
                           timestamp=extra.pop('timestamp', NOW-timedelta(minutes=1)), metadata={}, **extra)


def perceive(message, history=(), **extra):
    return plan(message, analyze(message), history, 'u', 'c', now=NOW, **extra)


def test_current_and_past_moods_are_separate():
    result=perceive('Oggi sono felice.', [turn('Sono triste per la partenza.')])
    assert result['current_labels']==['joy'] and result['prior_labels']==['sadness']
    assert result['relation']=='recent_context'
    assert 'contesto passato' in result['instruction']
    assert not result['persistent_emotion_inferred']


@pytest.mark.parametrize('text', ['Non sono triste, sono stanco.', 'Non mi sento triste: sono sollevato.'])
def test_self_correction_removes_rejected_label(text):
    result=perceive(text, [turn('Sono triste.')])
    assert result['relation']=='self_correction' and 'sadness' in result['denied_labels']
    assert 'sadness' not in result['prior_labels']
    assert 'prevale' in result['instruction']


@pytest.mark.parametrize('text', ['Lascia perdere', 'Non importa', 'Vabbè', 'Niente'])
def test_ambiguous_short_turn_does_not_diagnose_emotion(text):
    result=perceive(text)
    assert not result['current_labels'] and result['interpretation_uncertain']
    assert 'non scegliere un’emozione' in result['instruction']
    assert boundary_reply(text) is None


@pytest.mark.parametrize('text', ['Non voglio parlarne', 'Preferisco non parlarne', 'Cambiamo argomento'])
def test_explicit_boundary_is_a_closed_host_response(text):
    assert boundary_reply(text)[1]=='conversation_boundary'


@pytest.mark.parametrize('text', ['Non voglio parlarne. Spiega il sole.',
    'Il personaggio dice «Non voglio parlarne»', 'Se non voglio parlarne?', 'Lascia perdere'])
def test_mixed_reported_and_hypothetical_requests_are_not_consumed(text):
    assert boundary_reply(text) is None


def test_reference_needs_recent_same_owner_same_chat_self_attribution():
    good=perceive('Sto come prima', [turn('Sono triste.')])
    assert good['relation']=='recent_reference' and good['prior_labels']==['sadness']
    for changes in ({'user_id':'other'}, {'conversation_id':'other'}, {'role':'assistant'},
                    {'timestamp':NOW-timedelta(hours=1)}, {'timestamp':NOW+timedelta(minutes=1)},
                    {'timestamp':None}, {'metadata':{'is_valid':False}}):
        record=turn('Sono triste.')
        for key,value in changes.items():setattr(record,key,value)
        assert not perceive('Sto come prima',[record])['prior_labels']
    for text in ('Mia sorella è triste.', 'Ieri ero triste.', 'Forse sono triste.', '«Sono triste».'):
        assert not perceive('Sto come prima',[turn(text)])['prior_labels']


def test_unrelated_topic_and_explicit_boundary_stop_emotional_carryover():
    assert not perceive('Spiega il sole', [turn('Sono triste.')])['instruction']
    assert not perceive('Non importa', [turn('Sono triste.'), turn('Quanto fa 2+2?')])['prior_labels']
    assert not perceive('Sto come prima', [turn('Sono triste.'), turn('Non voglio parlarne')])['prior_labels']


def test_repeated_failure_is_uncertain_and_not_an_invented_memory():
    result=perceive('Ho fallito ancora.')
    assert result['interpretation_uncertain'] and not result['current_labels']
    assert 'senza inventare' in result['instruction']
    assert not perceive('Scrivi una storia: ho fallito ancora.')['instruction']
    assert not perceive('Traduci «Ho fallito ancora».')['instruction']


def test_strict_format_keeps_optional_guidance_out():
    assert not perceive('Sono triste e felice. Rispondi solo con JSON.')['instruction']
    assert not perceive('Sono triste e felice. Rispondi in una frase.')['instruction']


def test_metadata_contains_no_prior_raw_text_or_unbounded_history():
    records=[turn('Sono triste per la vicenda riservata XYZ.')]*2000
    result=perceive('Sto come prima', records)
    assert 'XYZ' not in str(result) and len(result['instruction'])<1200


def test_truncated_text_is_not_a_confident_context_source():
    assert not perceive('Sono triste. '+('x '*7000))['instruction']
    assert not perceive('Sto come prima', [turn('Sono triste. '+('x '*7000))])['prior_labels']


@pytest.mark.parametrize('text,mode', [
    ('Voglio solo sfogarmi.', 'listening'),
    ('Sono triste, non voglio consigli.', 'listening'),
    ('Ascoltami senza darmi consigli.', 'listening'),
    ('Aiutami a capire cosa fare adesso.', 'practical'),
    ('Vorrei suggerimenti pratici.', 'practical'),
])
def test_current_support_need_is_not_a_durable_preference(text,mode):
    state,report=personality.evolve(personality.empty_state(),'u','e',text)
    learned=personality.view(state,'u')
    assert support_request(text)==mode and not learned['preferences']
    assert 'support_mode' not in learned['tendencies']
    assert personality.plan(state,'u',text)['values']['support_mode']==mode
    assert 'support_mode' not in personality.plan(state,'u','Spiega il sole')['values']


@pytest.mark.parametrize('text', ['Mia sorella dice che non voglio consigli.',
    'Traduci «Voglio solo sfogarmi».', 'Se fossi triste, non voglio consigli.',
    'Non voglio consigli, ma dammi suggerimenti pratici.'])
def test_no_support_preference_from_reports_hypotheses_or_conflict(text):
    assert support_request(text) is None


@pytest.mark.parametrize('text,mode', [
    ('Non voglio solo sfogarmi, dammi consigli pratici.', 'practical'),
    ('Non voglio consigli pratici.', 'listening'),
    ('Non ho bisogno di sfogarmi.', None),
    ('Spiega cosa significa non voglio consigli.', None),
    ("'Voglio solo sfogarmi'", None),
    ('Quando sono triste non voglio consigli.', None),
])
def test_negated_quoted_or_conditional_needs_do_not_turn_into_current_requests(text,mode):
    assert support_request(text)==mode


def test_technical_utility_cannot_teach_a_default_for_emotional_support():
    from allma_model.core.personality_outcomes import context_for
    text='Dammi consigli pratici per usare Git.'
    assert context_for(text)=='general'
    metadata={'source':'model_generated','generation':{'status':'completed','finish_reason':'stop'},
              'personality_expression':{'values':{'support_mode':'practical'},'instruction_received':True}}
    receipt=delivery_receipt('u','e',text,'Usa un ramo per ogni modifica.',metadata,True)
    assert 'support_mode' not in receipt['offered']


def test_declared_support_preference_is_scoped_overridden_revoked_and_restarted(tmp_path):
    db=str(tmp_path/'state.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','pref','Quando sto male preferisco essere ascoltato senza consigli.')
    state={'primary_emotion':'sadness','confidence':.9}
    assert p.expression_plan('u','Sono triste.',state)['values']['support_mode']=='listening'
    assert 'support_mode' not in p.expression_plan('u','Spiega una stella')['values']
    restored=CoalescenceProcessor(db)
    assert restored.expression_plan('u','Sono triste.',state)['values']['support_mode']=='listening'
    assert restored.expression_plan('u','Sono triste, dammi consigli pratici.',state)['values']['support_mode']=='practical'
    assert 'support_mode' not in restored.expression_plan('other','Sono triste.',state)['values']
    assert 'support_mode' not in restored.expression_plan('u','Sono triste. Rispondi solo con JSON.',state)['values']
    restored.observe_interaction('u','revoke','Dimentica la mia preferenza di supporto.')
    assert 'support_mode' not in restored.expression_plan('u','Sono triste.',state)['values']


def test_three_assessed_support_experiences_integrate_without_copying_emotion():
    state=personality.empty_state();receipt=None
    emotion={'primary_emotion':'sadness','confidence':.9}
    for i in range(3):
        metadata={'source':'model_generated','generation':{'status':'completed','finish_reason':'stop'},
                  'personality_expression':{'values':{'support_mode':'listening'},
                     'instruction_received':True,'response_context':'support'}}
        receipt=delivery_receipt('u',str(i),f'Sono triste per il motivo {i}. Voglio solo sfogarmi.',
            'Ti ascolto. Puoi raccontare quello che desideri.', metadata, True, emotion)
        state,report=assess(state,'u','f'+str(i),'Il tuo ascolto senza consigli mi è stato utile.',receipt)
        if i<2:assert 'support_mode' not in personality.plan(state,'u','Sono triste.',emotion)['values']
    result=personality.plan(state,'u','Sono triste.',emotion)
    assert result['values']['support_mode']=='listening' and result['sources']['support_mode']=='interaction_outcomes'
    assert 'support_mode' not in personality.plan(state,'u','Spiega una stella')['values']
    state,_=assess(state,'u','correct','Il tuo ascolto senza consigli non mi è stato utile.',receipt)
    assert 'support_mode' not in personality.plan(state,'u','Sono triste.',emotion)['values']
    assert feedback_signal('I suggerimenti pratici mi sono stati utili.')['value']=='practical'
    personality.validate(state)
