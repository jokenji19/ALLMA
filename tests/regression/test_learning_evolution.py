from allma_model.learning_system.evolution_diagnostics import CASES
import pytest

@pytest.mark.parametrize('challenge',CASES,ids=[c[1] for c in CASES])
def test_learning_evolution_challenge(tmp_path,challenge):
    challenge[3](tmp_path)


@pytest.mark.parametrize('manual_kind',['in_place','replace_list'])
def test_unsaved_history_cannot_be_silently_discarded_by_a_delta(tmp_path,manual_kind):
    from allma_model.learning_system.learning_diagnostics import create,unit
    from allma_model.utils.persistence import StateRecoveryRequired
    learner=create(tmp_path/'learning.db');learner.add_learning_unit(unit('topic','original'))
    if manual_kind=='in_place':learner.knowledge_base['topic'][0].content='corrected'
    else:learner.knowledge_base['topic']=[unit('topic','corrected'),unit('topic','additional')]
    before=(tmp_path/'learning.db').read_bytes()
    with pytest.raises(StateRecoveryRequired):learner.add_learning_unit(unit('topic','next'))
    assert (tmp_path/'learning.db').read_bytes()==before
    learner.save_state();learner.add_learning_unit(unit('topic','next'))
    restored=create(tmp_path/'learning.db')
    assert restored.knowledge_base['topic'][0].content=='corrected'
    assert restored.knowledge_base['topic'][-1].content=='next'


def test_combined_runner_executes_every_case_with_a_unique_directory(tmp_path):
    from allma_model.learning_system.evolution_diagnostics import run_battery
    result=run_battery(tmp_path/'reports')
    assert result['complete'] and result['passed']==result['total']==50
    assert not result['failures']
