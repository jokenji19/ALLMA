"""Integration of current core/memory/learner APIs; no removed legacy systems."""
from datetime import datetime
from unittest.mock import Mock
import pytest
from allma_model.core.allma_core import ALLMACore
from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.learning_system.incremental_learning import IncrementalLearner


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    instance = ALLMACore(db_path=str(tmp_path / 'core.db'), mobile_mode=True)
    instance._ensure_mobile_llm = lambda: None
    instance._llm = None
    yield instance
    instance.close()


def test_failed_generation_keeps_user_history_without_learning(core, tmp_path):
    from copy import deepcopy
    initial_knowledge = deepcopy(core.incremental_learner.knowledge_base)
    conversation = core.start_conversation('u')
    result = core.process_message('u', conversation, 'Parliamo del mare')
    assert not result.is_valid
    restored = ConversationalMemory(storage_dir=str(tmp_path))
    assert [m.role for m in restored.get_conversation_history(conversation)] == ['user', 'assistant']
    assert restored.vector_engine.count() == 1
    assert core.incremental_learner.knowledge_base == initial_knowledge


def test_profiles_do_not_expose_other_users_history(core):
    conversation = core.start_conversation('a')
    core.conversational_memory.store_message(conversation, 'privato', role='user', user_id='a')
    profile = core.get_user_profile('b')
    assert profile['interaction_count'] == 0
    assert profile['interactions'] == []


def test_explicit_learning_survives_restart(core, tmp_path):
    core.incremental_learner.learn_from_interaction({'input': 'mare', 'response': 'blu', 'topic': 'mare', 'feedback': 'neutral'}, 'u')
    restored = IncrementalLearner(core.incremental_learner.storage_path)
    assert restored.get_knowledge_by_topic('mare')[0]['content'].endswith('blu')


@pytest.mark.parametrize('args', [('', 'c', 'test'), ('u', '', 'test'), ('u', 'c', '')])
def test_invalid_requests_do_not_write(core, args):
    with pytest.raises(ValueError):
        core.process_message(*args)
    assert core.conversational_memory.messages == []


def test_identity_and_dream_preference_survive_restart(core, tmp_path):
    core.update_user_identity('Ada', 31)
    core.set_dream_mode(True)
    core.set_dream_mode(False, persist=False)  # A pause does not change the preference.
    restored = ALLMACore(db_path=str(tmp_path / 'core.db'), mobile_mode=True)
    try:
        assert restored.user_profile.name == 'Ada'
        assert restored.user_profile.age == 31
        assert restored.dream_enabled is True
    finally:
        restored.close()
