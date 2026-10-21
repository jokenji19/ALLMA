import pytest
from allma_model.learning_system.incremental_learning import IncrementalLearner


@pytest.mark.parametrize('flag', [None, False, 'true', 1])
def test_missing_or_invalid_verification_does_not_learn_model_invention(tmp_path, flag):
    path=str(tmp_path/'knowledge.json')
    learner=IncrementalLearner(path)
    interaction={'input':'Mi piace passeggiare', 'response':'L’utente si chiama Sophia e vive a Roma',
                 'topic':'passeggiare', 'feedback':'neutral'}
    if flag is not None:
        interaction['response_verified']=flag
    unit=learner.learn_from_interaction(interaction,'u')
    assert 'Sophia' not in unit.content
    assert unit.metadata['knowledge_verified'] is False
    restored=IncrementalLearner(path)
    state=restored.knowledge_states['passeggiare']
    assert state.content=='Mi piace passeggiare'
    assert state.metadata['source_kind']=='user_statement'
    assert state.metadata['knowledge_verified'] is False


def test_explicit_host_verified_answer_remains_separate_from_user_statement(tmp_path):
    learner=IncrementalLearner(str(tmp_path/'knowledge.json'))
    unit=learner.learn_from_interaction({'input':'Quanto fa 18+24?', 'response':'42',
        'response_verified':True, 'topic':'calcolo', 'feedback':'neutral'},'u')
    assert unit.metadata['knowledge_verified'] is True
    assert unit.metadata['source_kind']=='interaction'
    assert learner.knowledge_states['calcolo'].content=='42'
