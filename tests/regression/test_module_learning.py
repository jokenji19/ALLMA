from unittest.mock import Mock
import pytest
from allma_model.learning_system.meta_learning_system import MetaLearningSystem
from allma_model.core.cognitive_tracker_lite import CognitiveTrackerLite


def test_mention_and_unattributed_feedback_do_not_learn_or_write(tmp_path):
    m = MetaLearningSystem(str(tmp_path / 'modules.db'))
    m.state_manager.save_state = Mock()
    m.process('Un’immagine può essere chiara: grazie per la domanda.', {'user_id': 'u'})
    assert set(m.style_scores.values()) == {.5}
    assert set(m.communication_scores.values()) == {.5}
    m.state_manager.save_state.assert_not_called()


def test_explicit_preferences_are_user_scoped_and_survive_restart(tmp_path):
    path = str(tmp_path / 'modules.db')
    m = MetaLearningSystem(path)
    m.process('Rispondi in breve', {'user_id': 'u'})
    assert m.communication_scores['direct'] == .6
    m.process('ciao', {'user_id': 'other'})
    assert m.communication_scores['direct'] == .5
    restored = MetaLearningSystem(path)
    restored.process('ciao', {'user_id': 'u'})
    assert restored.communication_scores['direct'] == .6


def test_strategy_reward_requires_actual_strategy_and_deduplicates_after_restart(tmp_path):
    path = str(tmp_path / 'modules.db')
    m = MetaLearningSystem(path)
    context = {'user_id': 'u', 'feedback_event': 'answer-1',
               'applied_style': {'suggested_style': 'textual', 'suggested_comm': 'detailed'}}
    m.process('Risposta corretta', context)
    assert m.style_scores['textual'] == .6
    assert m.style_scores['visual'] == .5
    restored = MetaLearningSystem(path)
    restored.process('Risposta corretta', context)
    assert restored.style_scores['textual'] == .6


def test_failed_preference_write_rolls_back_and_can_retry(tmp_path):
    m = MetaLearningSystem(str(tmp_path / 'modules.db'))
    save = m.state_manager.save_state
    m.state_manager.save_state = Mock(return_value=False)
    with pytest.raises(OSError):
        m.process('Rispondi in breve', {'user_id': 'u'})
    assert m.communication_scores['direct'] == .5
    m.state_manager.save_state = save
    m.process('Rispondi in breve', {'user_id': 'u'})
    assert m.communication_scores['direct'] == .6


def test_cognitive_feedback_is_idempotent_and_correction_replaces_approval(tmp_path):
    path = str(tmp_path / 'modules.db')
    m = CognitiveTrackerLite(path)
    m.process('Ricordi?', {})
    assert m.record_feedback('u', 'answer-1', 'memory', True)
    restored = CognitiveTrackerLite(path)
    assert not restored.record_feedback('u', 'answer-1', 'memory', True)
    assert restored.successful_interactions == 1
    assert restored.record_feedback('u', 'answer-1', 'memory', False)
    assert restored.successful_interactions == 0
    assert not restored.record_feedback('u', 'answer-1', 'memory', False)


def test_cognitive_feedback_disk_failure_can_retry(tmp_path):
    m = CognitiveTrackerLite(str(tmp_path / 'modules.db'))
    save = m.state_manager.save_state
    m.state_manager.save_state = Mock(return_value=False)
    with pytest.raises(OSError):
        m.record_feedback('u', 'answer-1', 'memory', True)
    assert not m.feedback_events
    assert m.abilities['memory'] == .5
    m.state_manager.save_state = save
    assert m.record_feedback('u', 'answer-1', 'memory', True)


def test_communication_preference_does_not_invent_a_visual_preference(tmp_path):
    m = MetaLearningSystem(str(tmp_path / 'modules.db'))
    output = m.process('Rispondi in breve', {'user_id': 'u'})
    assert output['confidence'] > .55
    assert output['suggested_comm'] == 'direct'
    assert output['suggested_style'] is None


def test_malformed_cognitive_state_restores_valid_fields_without_disabling_module(tmp_path):
    from allma_model.core.module_state_manager import ModuleStateManager
    path = str(tmp_path / 'modules.db')
    ModuleStateManager(path).save_state('cognitive_tracker_lite', {
        'abilities': {'memory': .7, 'creativity': 'bad', 'understanding': float('nan')},
        'interaction_count': -1, 'successful_interactions': 'bad', 'feedback_events': []})
    tracker = CognitiveTrackerLite(path)
    assert tracker.abilities == {'understanding': .5, 'creativity': .5, 'memory': .7}
    assert tracker.interaction_count == 0
    assert tracker.process('Una domanda', {})['abilities']['memory'] == .7


def test_failed_interaction_write_does_not_count_a_phantom_interaction(tmp_path):
    tracker = CognitiveTrackerLite(str(tmp_path / 'modules.db'))
    tracker.state_manager.save_state = Mock(return_value=False)
    with pytest.raises(OSError):
        tracker.process('Una domanda', {})
    assert tracker.interaction_count == 0
