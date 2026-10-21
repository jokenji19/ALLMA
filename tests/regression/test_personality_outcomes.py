import copy
import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from allma_model.core.personality_development import empty_state,plan,view,evolve as request_evolve,revision
from allma_model.core.personality_outcomes import (delivery_receipt,feedback_signal,feedback_target,
    evolve,validate,LIMIT,WEAK_LIMIT,context_for)
from allma_model.core.personality_coalescence import CoalescenceProcessor


def receipt(user='u',event='answer1',question='Spiega il sole.',values=None,answer='Il sole è una stella.',**extra):
    metadata={'source':'model_generated','generation':{'status':'completed','finish_reason':'stop'},
              'personality_expression':{'values':values or {},'instruction_received':bool(values)}}
    metadata.update(extra)
    return delivery_receipt(user,event,question,answer,metadata,True)


def integrate(state=None,n=3,question_prefix='Spiega il fenomeno'):
    state=state or empty_state()
    for i in range(n):
        state,_=evolve(state,'u',f'f{i}','La risposta breve mi è stata utile.',
                       receipt(event=f'a{i}',question=f'{question_prefix} {i}.'))
    return state


@pytest.mark.parametrize('message',[
    'La risposta breve mi è stata utile.','La spiegazione dettagliata mi ha aiutato.',
    'Il tono delicato mi è stato utile.','La domanda di approfondimento mi ha aiutato a riflettere.',
    'La risposta breve non mi è stata utile.','Mi correggo: il tono diretto non mi è stato utile.',
])
def test_closed_style_assessments(message):
    assert feedback_signal(message)['kind']=='explicit_style'


@pytest.mark.parametrize('message',[
    'La risposta è corretta.','Mia sorella dice che il tono delicato mi è stato utile.',
    '«La risposta breve mi è stata utile».','Se la risposta breve mi è stata utile?',
    'La risposta breve mi è stata utile. Spiega il sole.',
])
def test_correctness_quotes_and_other_people_do_not_reward_style(message):
    assert feedback_signal(message) is None


def test_spontaneous_brevity_is_observable_and_forced_formats_are_excluded():
    assert receipt()['offered']=={'verbosity':'brief'}
    assert receipt(question='Rispondi in una frase: spiega il sole.') is None
    assert receipt(question='Quanto fa 2+2? Rispondi solo con un numero.') is None
    assert receipt(values={'verbosity':'detailed'})['offered']['verbosity']=='brief'
    assert receipt(answer='parola '*120) is None
    assert receipt(answer='parola '*180)['offered']['verbosity']=='detailed'
    assert 'questions' not in receipt(values={'questions':'exploratory'})['offered']


@pytest.mark.parametrize('extra',[
    {'generation':{'status':'truncated_answer','finish_reason':'length'}},
    {'generation':{'status':'completed','finish_reason':None}},
    {'source':'confirmed_answer_recall'}, {'source':'grounded_emotional_recovery'},
    {'source':'identity_guard_notice'}, {'recovery':{'reason':'invalid_model'}},
])
def test_only_complete_valid_original_model_answers_can_teach_utility(extra):
    assert receipt(**extra) is None


def test_repeated_courtesy_does_not_consolidate_or_invalidate_answer_cache():
    state=empty_state();before=revision(state,'u')
    for i in range(150):state,_=evolve(state,'u',f'f{i}','Grazie.',receipt(event=f'a{i}'))
    learned=view(state,'u')['outcome_learning']
    assert learned['strong_feedback']==0 and learned['weak_feedback']==WEAK_LIMIT
    assert not learned['contexts'] and not plan(state,'u','Spiega il mare')['values']
    assert revision(state,'u')==before


def test_same_answer_and_same_question_do_not_manufacture_independent_support():
    state=empty_state();r=receipt()
    state,_=evolve(state,'u','f1','La risposta breve mi è stata utile.',r)
    after,status=evolve(state,'u','f2','La risposta breve mi è stata utile.',r)
    assert after is state and status['status']=='duplicate_feedback'
    for i in range(12):
        state,_=evolve(state,'u',f'new{i}','La risposta breve mi è stata utile.',receipt(event=f'answer{i}'))
    learned=view(state,'u')['outcome_learning']
    assert learned['strong_feedback']==1
    assert learned['contexts']['explanation']['verbosity']['stage']=='suspended'


def test_distinct_positive_experiences_integrate_only_the_assessed_axis_and_context():
    state=integrate()
    learned=view(state,'u')
    assert not learned['preferences'] and not learned['tendencies']
    assert learned['outcome_learning']['contexts']['explanation']['verbosity']['stage']=='integrated'
    response=plan(state,'u','Spiega un arcobaleno.')
    assert response['values']=={'verbosity':'brief'}
    assert response['sources']['verbosity']=='interaction_outcomes'
    assert not plan(state,'other','Spiega il cielo')['values']
    assert not plan(state,'u','Mi sento triste',{'primary_emotion':'sadness','confidence':.9})['sources'].get('verbosity')
    assert not plan(state,'u','Ciao')['values']
    assert not plan(state,'u','Spiega in dettaglio un arcobaleno')['values']['verbosity']=='brief'
    assert not plan(state,'u','Spiega il mare in una frase')['values'].get('verbosity')


def test_explicit_preference_beats_outcome_and_revocation_removes_latent_outcomes():
    state=integrate()
    state,_=request_evolve(state,'u','pref','Preferisco risposte dettagliate.')
    assert plan(state,'u','Spiega il mare')['values']['verbosity']=='detailed'
    state,_=request_evolve(state,'u','revoke','Non usare più la mia preferenza di lunghezza.')
    assert not plan(state,'u','Spiega il mare')['values']
    state=integrate(state)
    state,_=request_evolve(state,'u','reset','Dimentica le mie preferenze di stile.')
    assert not view(state,'u')['outcome_learning']['contexts']


def test_negative_corrections_replace_the_original_vote_and_can_suspend_consolidation():
    state=integrate()
    for i in (0,1):
        state,status=evolve(state,'u',f'correction{i}','Mi correggo: la risposta breve non mi è stata utile.',
                            receipt(event=f'a{i}',question=f'Spiega il fenomeno {i}.'))
        assert status['status']=='feedback_corrected'
    outcome=view(state,'u')['outcome_learning']
    assert outcome['strong_feedback']==3
    assert outcome['contexts']['explanation']['verbosity']['stage']=='suspended'
    assert not plan(state,'u','Spiega il cielo')['values']


def test_feedback_targets_only_original_owned_unmodified_answer_or_its_acknowledgement():
    r=receipt();answer='Il sole è una stella.'
    msg=SimpleNamespace(role='assistant',user_id='u',content=answer,
        metadata={'is_valid':True,'source':'model_generated','personality_delivery':r,
                  'generation':{'status':'completed','finish_reason':'stop'}})
    signal=feedback_signal('La risposta breve mi è stata utile.')
    assert feedback_target(msg,'u',signal)==r
    assert feedback_target(msg,'other',signal) is None
    msg.content='Testo sostituito';assert feedback_target(msg,'u',signal) is None
    msg.metadata.update(source='personality_response_feedback',personality_feedback_target=r)
    assert feedback_target(msg,'u',signal)==r
    msg.metadata['is_valid']=False;assert feedback_target(msg,'u',signal) is None
    assert evolve(empty_state(),'other','f','La risposta breve mi è stata utile.',r)[1]['status']=='unattributed_feedback'


def test_outcomes_are_atomic_persistent_and_compatible_with_old_profiles(tmp_path):
    db=str(tmp_path/'core.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','request','Preferisco un tono formale.')
    for i in range(3):p.observe_interaction('u',f'f{i}','La risposta breve mi è stata utile.',
        response_context=receipt(event=f'a{i}',question=f'Spiega il fenomeno {i}.'))
    before=p.expression_view('u');p._save_diary();p.observe_feedback('u','correct1',True,[])
    restored=CoalescenceProcessor(db);assert restored.expression_view('u')==before
    with patch.object(restored._state_store,'put',side_effect=OSError('disk full')):
        with pytest.raises(OSError):restored.observe_interaction('u','correction','La risposta breve non mi è stata utile.',
            response_context=receipt(event='a0',question='Spiega il fenomeno 0.'))
    assert restored.expression_view('u')==before
    assert CoalescenceProcessor(db).expression_view('u')==before
    # A historical profile without the additive field still loads unchanged.
    path=tmp_path/'cognitive_state.json';saved=json.loads(path.read_text())
    del saved['sections']['personality']['expression_development']['profiles']['u']['outcomes']
    path.write_text(json.dumps(saved));assert not CoalescenceProcessor(db).expression_view('u')['outcome_learning']['contexts']


def test_invalid_outcomes_fail_closed_without_replacing_the_original_file(tmp_path):
    db=str(tmp_path/'core.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','request','Preferisco un tono formale.')
    path=tmp_path/'cognitive_state.json';saved=json.loads(path.read_text())
    saved['sections']['personality']['expression_development']['profiles']['u']['outcomes']=[{'axis':'malicious'}]
    path.write_text(json.dumps(saved));before=path.read_bytes()
    with pytest.raises(ValueError):CoalescenceProcessor(db)
    assert path.read_bytes()==before


def test_negative_usefulness_can_suspend_inferred_request_defaults_but_not_explicit_preference():
    state=empty_state()
    for i in range(3):state,_=request_evolve(state,'u',f'request{i}',f'Rispondi brevemente. Spiega il fenomeno {i}.')
    assert plan(state,'u','Spiega il mare')['sources']['verbosity']=='integrated_requests'
    for i in range(2):state,_=evolve(state,'u',f'negative{i}','La risposta breve non mi è stata utile.',
        receipt(event=f'answer{i}',question=f'Spiega il fenomeno {i}.'))
    assert 'verbosity' not in plan(state,'u','Spiega il mare')['values']
    assert plan(state,'u','Rispondi brevemente. Spiega il mare')['values']['verbosity']=='brief'
    state,_=request_evolve(state,'u','explicit','Preferisco risposte brevi.')
    assert plan(state,'u','Spiega il mare')['values']['verbosity']=='brief'


def test_contextual_directness_confirmed_by_user_survives_generic_mood_default():
    state=empty_state()
    for i in range(3):
        r=receipt(event=f'a{i}',question=f'Un momento difficile {i}',values={'directness':'direct'})
        r['context']='support'
        state,_=evolve(state,'u',f'f{i}','Il tono diretto mi è stato utile.',r)
    expression=plan(state,'u','Mi sento triste',{'primary_emotion':'sadness','confidence':.9})
    assert expression['values']['directness']=='direct'
    assert expression['sources']['directness']=='interaction_outcomes'
    assert expression['values']['humor']=='serious'


def test_courtesy_cannot_evict_significant_experiences_and_candidates_are_independent():
    state=integrate()
    for i in range(150):state,_=evolve(state,'u',f'weak{i}','Grazie.',receipt(event=f'new{i}'))
    assert view(state,'u')['outcome_learning']['strong_feedback']==3
    assert plan(state,'u','Spiega il mare')['sources']['verbosity']=='interaction_outcomes'
    candidate,_=evolve(state,'u','another','Grazie.',receipt(event='last'))
    candidate['profiles']['u']['outcomes'][0]['positive']=False
    assert state['profiles']['u']['outcomes'][0]['positive'] is True
