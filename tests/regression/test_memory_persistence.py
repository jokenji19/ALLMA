import json
from datetime import datetime

import pytest

from allma_model.core.vector_memory_engine import VectorMemoryEngine
from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.learning_system.incremental_learning import IncrementalLearner, LearningUnit, ConfidenceLevel
from allma_model.utils.persistence import atomic_write_json


def test_vector_reopen_with_growing_vocabulary(tmp_path):
    path = str(tmp_path / 'vectors.db')
    engine = VectorMemoryEngine(path)
    engine.add('u', 'gatto')
    engine.add('u', 'cane blu')
    reopened = VectorMemoryEngine(path)
    assert reopened.search('u', 'cane')[0]['content'] == 'cane blu'
    assert reopened.search('other', 'cane') == []


def test_single_document_is_searchable_and_other_instances_refresh(tmp_path):
    path = str(tmp_path / 'vectors.db')
    reader = VectorMemoryEngine(path)
    writer = VectorMemoryEngine(path)
    writer.add('u', 'tramonto')
    assert reader.search('u', 'tramonto')[0]['score'] == pytest.approx(1)
    writer.clear_user('u')
    assert reader.search('u', 'tramonto') == []


def test_message_indexing_and_restart_are_idempotent(tmp_path):
    memory = ConversationalMemory(load_persistent=False, storage_dir=str(tmp_path))
    conversation = memory.create_conversation('u')
    memory.store_message(conversation, 'mi piace il mare', role='user', user_id='u')
    memory.store_message(conversation, 'errore generazione', role='assistant', user_id='u', metadata={'is_valid': False})
    assert memory.vector_engine.count() == 1
    restored = ConversationalMemory(storage_dir=str(tmp_path))
    assert restored.vector_engine.count() == 1
    assert restored.vector_engine.search('u', 'mare')[0]['content'] == 'mi piace il mare'
    assert len(restored.messages) == 2


def test_atomic_write_failure_preserves_previous_state(tmp_path, monkeypatch):
    path = tmp_path / 'state.json'
    atomic_write_json(str(path), {'previous': True})
    def fail(*args):
        raise OSError('simulated replacement failure')
    monkeypatch.setattr('allma_model.utils.persistence.os.replace', fail)
    with pytest.raises(OSError):
        atomic_write_json(str(path), {'new': True})
    assert json.loads(path.read_text()) == {'previous': True}
    assert list(tmp_path.iterdir()) == [path]


def test_learning_is_persisted_without_manual_save(tmp_path):
    path = str(tmp_path / 'learning.json')
    learner = IncrementalLearner(path)
    learner.add_learning_unit(LearningUnit('mare', 'Il mare è blu', 'test', ConfidenceLevel.HIGH, datetime.now()))
    learner.add_response_variants('mare', ['Una variante'])
    restored = IncrementalLearner(path)
    assert restored.get_knowledge_by_topic('mare')[0]['content'] == 'Il mare è blu'
    assert restored.responses_pool['mare'] == ['Una variante']


def test_old_learning_snapshot_is_migrated(tmp_path):
    path = tmp_path / 'old.json'
    path.write_text(json.dumps({'knowledge_states': {'mare': {
        'topic': 'mare', 'content': 'blu', 'confidence': 2,
        'last_updated': datetime.now().isoformat(), 'sources': ['legacy']}}}))
    assert IncrementalLearner(str(path)).get_knowledge_by_topic('mare')[0]['content'] == 'blu'
