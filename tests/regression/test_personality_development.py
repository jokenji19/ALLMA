import copy
import json
from unittest.mock import patch
import pytest
from allma_model.core.personality_development import empty_state,evolve,view,plan,controls,validate,self_description_question,describe
from allma_model.core.personality_coalescence import CoalescenceProcessor,PersonalityCore
from allma_model.core.personality_adapter import PersonalityAdapterLite


def test_birth_has_no_declared_or_consolidated_personal_character():
    p=view(empty_state(),'u')
    assert not p['preferences'] and not p['tendencies']
    assert not plan(empty_state(),'u','Ciao')['instruction']
    assert 'non è ancora consolidato' in describe(p,{})
    assert PersonalityCore().value_relationships==PersonalityCore().value_relationships


@pytest.mark.parametrize('text',[
    'Grazie, cortesemente, per favore.', 'Ciao 😂😊', 'Perché?', 'x '*150,
    'Mia sorella preferisce risposte brevi.', 'Non preferisco risposte brevi.',
    'Se preferisco risposte brevi, come fai?', '«Preferisco risposte brevi».',
    'Il personaggio dice: rispondi brevemente.', 'Se ti dicessi: rispondi brevemente?',
    'Preferisco risposte brevi. Spiegami un arcobaleno.',
])
def test_no_stable_learning_from_politeness_length_emoji_quotes_or_other_people(text):
    state=empty_state();after,_=evolve(state,'u','1',text)
    assert after is state


@pytest.mark.parametrize('text,axis,value',[
    ('Preferisco risposte brevi.','verbosity','brief'),
    ('Da ora in poi preferisco un tono formale.','formality','formal'),
    ('Non fare più battute.','humor','serious'),
    ('Preferisco un tono diretto.','directness','direct'),
    ('Non farmi domande aggiuntive.','questions','restrained'),
])
def test_explicit_preferences_are_distinct_from_learned_personality(text,axis,value):
    state,report=evolve(empty_state(),'u','1',text)
    assert report['status']=='preference_saved'
    assert view(state,'u')['preferences'][axis]==value
    assert view(state,'other')['preferences']=={}
    assert plan(state,'u','Spiega un arcobaleno')['sources'][axis]=='declared_preference'


def test_repeated_distinct_requests_suspend_then_integrate_and_remain_revisable():
    state=empty_state()
    text='Rispondi brevemente. Spiega il mare.'
    state,_=evolve(state,'u','1',text)
    duplicate,report=evolve(state,'u','1',text)
    assert duplicate is state and report['status']=='duplicate_event'
    same,report=evolve(state,'u','2',text)
    assert same is state and report['status']=='repeated_context'
    assert view(state,'u')['tendencies']['verbosity']['stage']=='suspended'
    for i,topic in enumerate(('sole','stelle'),3):state,_=evolve(state,'u',str(i),f'Rispondi brevemente. Spiega {topic}.')
    assert view(state,'u')['tendencies']['verbosity']['stage']=='integrated'
    assert plan(state,'u','Spiega il cielo')['values']['verbosity']=='brief'
    for i in range(20):state,_=evolve(state,'u',f'new{i}',f'Spiega in dettaglio il fenomeno numero {i}.')
    assert plan(state,'u','Spiega il cielo')['values']['verbosity']=='detailed'
    assert len(state['profiles']['u']['tendencies']['verbosity']['examples'])<=64


def test_current_request_exact_format_and_revocation_override_previous_style():
    state,_=evolve(empty_state(),'u','1','Preferisco risposte dettagliate.')
    assert plan(state,'u','Rispondi brevemente. Spiega il sole')['values']['verbosity']=='brief'
    assert 'verbosity' not in plan(state,'u','Rispondi in una frase. Spiega il sole')['values']
    assert 'verbosity' not in plan(state,'u','Quanto fa 18 + 24? Rispondi solo con un numero.')['values']
    state,_=evolve(state,'u','2','Non usare più la mia preferenza di lunghezza.')
    assert not view(state,'u')['preferences']
    state,_=evolve(state,'u','3','Preferisco un tono formale.')
    state,_=evolve(state,'u','4','Dimentica le mie preferenze di stile.')
    assert not view(state,'u')['preferences'] and not view(state,'u')['tendencies']


def test_emotional_context_changes_only_turn_expression_not_persistent_preference(tmp_path):
    p=CoalescenceProcessor(str(tmp_path/'core.db'))
    p.observe_interaction('u','1','Preferisco un tono scherzoso.')
    before=p.expression_view('u')
    adapter=PersonalityAdapterLite(p)
    adapter.process('Sono triste',{'user_id':'u','emotional_state':{'primary_emotion':'sadness','confidence':.9}})
    assert adapter.style.humor==.1
    adapter.process('Spiega la pioggia',{'user_id':'u','emotional_state':{'primary_emotion':'neutral','confidence':.9}})
    assert adapter.style.humor==.65
    adapter.process('Una domanda',{'user_id':'other'})
    assert adapter.style.humor==.4
    assert p.expression_view('u')==before
    external=adapter.get_current_style();external.humor=0
    assert adapter.style.humor==.4


def test_expression_and_emotion_commit_together_and_survive_other_state_saves(tmp_path):
    db=str(tmp_path/'core.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','1','Preferisco risposte brevi.')
    before=p.expression_view('u')
    p.observe_feedback('u','answer1',True,['emotion'])
    p._save_diary()
    restored=CoalescenceProcessor(db)
    assert restored.expression_view('u')==before
    with patch.object(restored._state_store,'put',side_effect=OSError('disk full')):
        with pytest.raises(OSError):restored.observe_interaction('u','2','Preferisco risposte dettagliate.')
    assert restored.expression_view('u')==before
    restored.observe_interaction('u','2','Preferisco risposte dettagliate.')
    assert CoalescenceProcessor(db).expression_view('u')['preferences']['verbosity']=='detailed'


def test_invalid_persisted_personality_is_preserved_and_not_overwritten(tmp_path):
    db=str(tmp_path/'core.db');p=CoalescenceProcessor(db)
    p.observe_interaction('u','1','Preferisco risposte brevi.')
    path=tmp_path/'cognitive_state.json';saved=json.loads(path.read_text())
    saved['sections']['personality']['expression_development']['profiles']['u']['declared']['verbosity']='injected directive'
    path.write_text(json.dumps(saved));before=path.read_bytes()
    with pytest.raises(ValueError):CoalescenceProcessor(db)
    assert path.read_bytes()==before


def test_current_mood_does_not_make_user_emotion_allmas_emotion_or_poison_technical_requests(tmp_path):
    p=CoalescenceProcessor(str(tmp_path/'core.db'))
    p.observe_interaction('u','1','Sono triste per la partenza.')
    p.observe_interaction('u','2','Sono triste perché mi manca casa.')
    assert p.growth_instruction('u')
    assert not p.growth_instruction('u','Spiega un arcobaleno',{'primary_emotion':'neutral','confidence':.9})
    assert not p.growth_instruction('u','Rispondi solo con un numero',{'primary_emotion':'sadness','confidence':.9})
    assert p.growth_instruction('u','Sono triste',{'primary_emotion':'sadness','confidence':.9})
    assert not self_description_question('Qual è il mio carattere?')
    assert self_description_question('Che personalità hai?')


def test_style_adapter_does_not_duplicate_already_applied_core_instruction():
    expression=plan(empty_state(),'u','Rispondi brevemente. Spiega il sole')
    result=PersonalityAdapterLite().process('Una domanda',{'user_id':'u','personality_expression':expression,'personality_expression_applied':True})
    assert result['style_hint']=='' and result['expression']==expression


def test_malformed_emotion_context_is_not_a_personality_change():
    assert not plan(empty_state(),'u','Ciao',{'confidence':'high','primary_emotion':'sadness','secondary_emotions':42})['emotion_adaptation_transient']


def test_revoked_controls_stay_in_real_archive_but_not_model_history():
    from allma_model.core.personality_development import history_eligible
    from types import SimpleNamespace
    for record in [
        {'role':'user','content':'Preferisco risposte brevi.'},
        {'content':'Preferisco risposte dettagliate.','metadata':{'role':'user'}},
        SimpleNamespace(role='assistant',content='Ho registrato la preferenza.',metadata={'source':'personality_style_control'}),
    ]:
        assert not history_eligible(record)
    assert history_eligible({'role':'user','content':'Spiega la pioggia. Rispondi brevemente.'})
    assert history_eligible({'role':'user','content':'Mia sorella preferisce risposte brevi.'})
    assert history_eligible({'role':'assistant','content':'Risposte brevi possono aiutare.'})


@pytest.mark.parametrize('text,expected',[
    ('Da ora in poi rispondi in breve.',{'verbosity':'brief'}),
    ('D’ora in poi rispondi formalmente.',{'formality':'formal'}),
    ('Per le prossime risposte, rispondi in dettaglio.',{'verbosity':'detailed'}),
])
def test_durable_prefix_with_whole_style_command(text,expected):
    assert controls(text)=={'action':'set','values':expected}
    assert controls(text+' Spiega il sole.') is None


def test_exact_output_contract_wins_even_over_explicit_current_brevity():
    assert 'verbosity' not in plan(empty_state(),'u','Quanto fa 2+2? Rispondi solo con un numero. Rispondi brevemente.')['values']
