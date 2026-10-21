from allma_model.utils.support_roles import role_map, role_instruction
from benchmark_iq import CognitiveBenchmark


def test_role_map_preserves_negation_and_other_people():
    data=role_map('Mia sorella è triste, io non sono triste: sono sollevata dopo il trasloco.')
    assert data['emozioni_utente']==['sollievo']
    assert data['emozioni_altre_persone']==['tristezza']
    assert data['emozioni_negate']==['tristezza']
    assert data['azione_ALLMA']=='rispondere nella conversazione'
    assert 'trasloco' not in str(data) # No fabricated episode or answer text.


def test_no_emotion_is_invented_by_role_map():
    assert role_map('Quanto fa 12 + 8?')['emozioni_utente']==[]
    assert role_map('Forse sono triste')['interpretazione_incerta']
    assert 'tu/ti' in role_instruction('Sono felice e in ansia.')


def test_paired_roles_experiment_matches_input_seed_and_budget():
    cases=CognitiveBenchmark(profile='support_roles').load_questions()
    assert len(cases)==4
    assert [r['execution_mode'] for r in cases]==['model','role_map','role_map','model']
    for a,b in zip(cases[::2],cases[1::2]):
        assert a['question']==b['question'] and a['pair_seed']==b['pair_seed']
        assert a['total_budget']==b['total_budget']==192
        assert a['thought_budget']==b['thought_budget']==48


def test_emotional_reasoning_experiment_changes_only_budget():
    a,b=CognitiveBenchmark(profile='support_reasoning').load_questions()
    assert a['question']==b['question'] and a['pair_seed']==b['pair_seed']==20261312
    assert a['execution_mode']==b['execution_mode']=='model'
    assert [a['thought_budget'],b['thought_budget']]==[48,128]
    assert a['total_budget']-a['thought_budget']==b['total_budget']-b['thought_budget']==144
    assert [a['total_budget'],b['total_budget']]==[192,272]


def test_natural_closure_experiment_keeps_total_budget_and_input():
    a,b=CognitiveBenchmark(profile='support_natural').load_questions()
    assert a['question']==b['question'] and a['pair_seed']==b['pair_seed']==20261312
    assert a['total_budget']==b['total_budget']==384
    assert [a['reasoning_mode'],b['reasoning_mode']]==['bounded','natural']
