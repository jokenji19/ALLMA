"""Failure injection for the persistence defects found in the October audit."""
from copy import deepcopy
from datetime import datetime
import json
from unittest.mock import patch
import pytest
from allma_model.learning_system.answer_recall import AnswerRecall
from allma_model.learning_system.incremental_learning import IncrementalLearner, LearningUnit, ConfidenceLevel, FeedbackType
from allma_model.utils.cognitive_state import CognitiveStateStore
from allma_model.utils.persistence import StateRecoveryRequired


def unit(topic='navigazione'):
    return LearningUnit(topic, 'La bussola indica il nord', 'user_u', ConfidenceLevel.LOW,
                        datetime.now(), {'user_id':'u'})


def test_failed_confirmation_is_not_used_or_committed_by_next_feedback(tmp_path):
    recall = AnswerRecall(tmp_path/'recall.json')
    recall.observe('k', 'u', 'Qual è la capitale della Francia?', 'Parigi.', 'e')
    recall.feedback('k', 'u', 'one', True)
    before = recall.path.read_bytes()
    with patch.object(recall, '_save', side_effect=OSError('full')):
        with pytest.raises(OSError):
            recall.feedback('k', 'u', 'failed', True)
    assert recall.lookup('k', 'u') is None
    assert recall.path.read_bytes() == before
    recall.feedback('k', 'u', 'retry', True)
    assert recall.lookup('k', 'u')['confirmations'] == ['one','retry']
    assert AnswerRecall(recall.path).lookup('k', 'u')['confirmations'] == ['one','retry']


def test_failed_observation_does_not_replace_a_confirmed_answer(tmp_path):
    recall = AnswerRecall(tmp_path/'recall.json', confirmations=1)
    recall.observe('k','u','Spiega la luce bianca','Una miscela di colori.','e')
    recall.feedback('k','u','one',True)
    before = deepcopy(recall.records)
    with patch.object(recall,'_save',side_effect=OSError('full')):
        with pytest.raises(OSError):
            recall.observe('k','u','Spiega la luce bianca','Nuova risposta.','two')
    assert recall.records == before
    answer = recall.lookup('k','u')
    answer['confirmations'].clear()
    assert recall.lookup('k','u') is not None


@pytest.mark.parametrize('operation', ['add', 'learn', 'feedback', 'success', 'variants'])
def test_learning_write_failure_rolls_back_every_mutator(tmp_path, operation):
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    learner.add_learning_unit(unit())
    fields = ('knowledge_base','knowledge_states','user_progress','success_counters','responses_pool')
    before = deepcopy({k:getattr(learner,k) for k in fields})
    disk = (tmp_path/'learning.json').read_bytes()
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=OSError('full')):
        with pytest.raises(OSError):
            if operation == 'add': learner.add_learning_unit(unit('astronomia'))
            elif operation == 'learn': learner.learn_from_interaction({'input':'nuovo contenuto','topic':'navigazione'},'u')
            elif operation == 'feedback': learner.integrate_feedback('navigazione', FeedbackType.POSITIVE, 'utile')
            elif operation == 'success': learner.record_success('navigazione', threshold=1)
            else: learner.add_response_variants('navigazione',['altra risposta'])
    assert {k:getattr(learner,k) for k in fields} == before
    assert (tmp_path/'learning.json').read_bytes() == disk
    learner.add_learning_unit(unit('retry'))
    assert set(IncrementalLearner(learner.storage_path).knowledge_base) == {'navigazione','retry'}


def test_failed_learning_reload_preserves_all_live_state_and_blocks_overwrite(tmp_path):
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    learner.add_learning_unit(unit())
    original = deepcopy(learner.knowledge_base)
    data = json.loads((tmp_path/'learning.json').read_text())
    data['knowledge_states']['broken'] = {'topic':'broken'}
    broken = json.dumps(data)
    (tmp_path/'learning.json').write_text(broken)
    assert learner.load_state() is False
    assert learner.knowledge_base == original
    with pytest.raises(StateRecoveryRequired): learner.add_learning_unit(unit('ghost'))
    assert (tmp_path/'learning.json').read_text() == broken
    assert (tmp_path/'learning.json.invalid.bak').read_text() == broken
    del data['knowledge_states']['broken']
    (tmp_path/'learning.json').write_text(json.dumps(data))
    assert learner.load_state() is True
    learner.add_learning_unit(unit('repaired'))


def test_interaction_updates_related_search_immediately_and_after_restart(tmp_path):
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    learner.learn_from_interaction({'input':'La bussola indica il nord','topic':'navigazione'}, 'u')
    assert learner.find_related_knowledge('bussola nord', user_id='u')
    assert not learner.find_related_knowledge('bussola nord', user_id='other')
    learner.learn_from_interaction({'input':'Un telescopio osserva galassie','topic':'astronomia'}, 'u')
    assert learner.find_related_knowledge('telescopio galassie', user_id='u')[0].topic == 'astronomia'
    assert IncrementalLearner(learner.storage_path).find_related_knowledge('telescopio galassie', user_id='u')


def test_invalid_learning_version_preserves_live_state_and_archive(tmp_path):
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    learner.add_learning_unit(unit())
    original = deepcopy(learner.knowledge_base)
    data = json.loads((tmp_path/'learning.json').read_text())
    data['schema_version'] = True
    broken = json.dumps(data)
    (tmp_path/'learning.json').write_text(broken)
    assert learner.load_state() is False
    assert learner.knowledge_base == original
    with pytest.raises(StateRecoveryRequired):
        learner.add_learning_unit(unit('ghost'))
    assert (tmp_path/'learning.json').read_text() == broken


@pytest.mark.parametrize('broken', ['{truncated', '[]', '{"version":1,"sections":{"identity":[]}}'])
def test_corrupt_cognitive_archive_cannot_be_replaced_by_another_section(tmp_path, broken):
    store = CognitiveStateStore(tmp_path/'core.db')
    store.path.write_text(broken)
    assert store.get('identity') == {}
    with pytest.raises(StateRecoveryRequired): store.put('different', {'a':1})
    assert store.path.read_text() == broken
    store.path.write_text('{"version":1,"sections":{"identity":{"name":"ALLMA"}}}')
    store.put('different', {'a':1})
    assert store.get('identity') == {'name':'ALLMA'}
