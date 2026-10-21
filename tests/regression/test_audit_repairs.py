import asyncio
import json
import threading
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity
from allma_model.utils.repetition_guard import requested_repetition
from allma_model.memory_system.conversational_memory import ConversationalMemory


def test_tfidf_preserves_rows_and_new_terms():
    vectorizer = SimpleTfidf()
    vectors = vectorizer.fit_transform(['gatto', None, 'cane'])
    assert vectors.shape == (3, 2)
    assert cosine_similarity(vectors[0], vectors[0])[0, 0] == pytest.approx(1)
    assert not vectors[1].any()
    assert vectorizer.transform([]).shape == (0, 2)


@pytest.mark.parametrize('instruction', ['Non ripetere 6 volte ghiandole',
    "Don't repeat 6 times", 'Evita di ripetere 6 volte',
    'La frase «ripeti 6 volte» è un esempio'])
def test_negated_or_quoted_repetition_does_not_disable_guard(instruction):
    assert not requested_repetition(instruction)


def test_affirmative_repetition_is_allowed():
    assert requested_repetition('Ripeti ciao 6 volte')


def test_corrupt_archive_keeps_live_state_and_original(tmp_path):
    memory = ConversationalMemory(load_persistent=False, storage_dir=str(tmp_path))
    conversation = memory.create_conversation('u')
    memory.store_message(conversation, 'conservami', role='user', user_id='u')
    previous = memory.messages
    data = json.loads((tmp_path/'allma_memory.json').read_text())
    data['messages'].append({'content': 'record incompleto'})
    original = json.dumps(data)
    (tmp_path/'allma_memory.json').write_text(original)
    assert memory.load_memory() is False
    assert memory.messages is previous
    with pytest.raises(RuntimeError, match='preserving original'):
        memory.save_memory()
    assert (tmp_path/'allma_memory.json').read_text() == original
    data['messages'].pop()
    (tmp_path/'allma_memory.json').write_text(json.dumps(data))
    assert memory.load_memory() is True
    memory.save_memory()
    assert memory.messages[0].content == 'conservami'


def test_incremental_retrieval_finds_new_topic_content(tmp_path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner, LearningUnit, ConfidenceLevel
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    for topic, content in [('animali', 'gatto domestico'), ('astronomia', 'telescopio galassia')]:
        learner.add_learning_unit(LearningUnit(topic, content, 'test', ConfidenceLevel.HIGH, datetime.now()))
    assert learner.find_related_knowledge('gatto')[0].topic == 'animali'
    assert learner.find_related_knowledge('telescopio')[0].topic == 'astronomia'


def test_cancelled_event_bus_can_restart():
    from allma_model.core.event_bus import EventBus
    async def run():
        bus = EventBus()
        for _ in range(2):
            task = asyncio.create_task(bus.consume_loop())
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert bus.get_stats()['running'] is False
    asyncio.run(run())


def test_foreground_turns_serialize_and_queued_cancellation_releases_lock():
    from allma_model.core.allma_core import ALLMACore
    from allma_model.utils.generation_control import GenerationCancelled
    core = ALLMACore.__new__(ALLMACore)
    from allma_model.utils.brain_activity import BrainActivity
    core.brain_activity = BrainActivity()
    core._lock = threading.RLock()
    core._turn_lock = threading.Lock()
    core._shutdown_event = threading.Event()
    core._user_active = threading.Event()
    entered = threading.Event()
    release = threading.Event()
    calls = []
    def execute(*args, **kwargs):
        calls.append(args[2])
        entered.set()
        assert release.wait(2)
        return SimpleNamespace(content=args[2], is_valid=True)
    core._process_message_turn = execute
    first = threading.Thread(target=core.process_message, args=('u', 'c', 'first'))
    first.start()
    assert entered.wait(2)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(GenerationCancelled):
        core.process_message('u', 'c', 'cancelled', cancel_event=cancel)
    assert calls == ['first'] and core._user_active.is_set()
    release.set()
    first.join(2)
    assert not first.is_alive() and not core._user_active.is_set()
    assert core.process_message('u', 'c', 'next').content == 'next'


def test_unavailable_temperature_is_not_fabricated(monkeypatch):
    from allma_model.ui.temperature_monitor import TemperatureMonitor
    monitor = TemperatureMonitor()
    monitor.is_android = False
    sample = monitor.get_temperatures()
    assert sample['cpu'] is None and sample['battery'] is None
    assert sample['cpu_source'] == 'unavailable'
    monkeypatch.setattr('allma_model.ui.temperature_monitor.glob.glob', lambda _: [])
    assert monitor._get_cpu_temperature(30) is None


def test_patterns_keep_keywords_and_validate_without_affecting_random_state():
    from allma_model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem, Pattern
    system = PatternRecognitionSystem()
    pattern = system.analyze_pattern('Programmare codice Python')
    assert pattern.category == 'programming' and 'python' in pattern.keywords
    assert system.validate_pattern(pattern)
    first = Pattern('programming', embedding=[1., 0.])
    assert system.calculate_pattern_similarity(first, first) == pytest.approx(1)
    np.random.seed(25)
    expected = np.random.random()
    np.random.seed(25)
    system._calculate_embedding('python codice')
    assert np.random.random() == expected


def test_topic_coordinates_are_consistent_and_known_topics_survive_extraction():
    from allma_model.learning_system.topic_extractor import TopicExtractor
    extractor = TopicExtractor()
    assert extractor.calculate_similarity('gatto', 'gatto') == pytest.approx(1)
    assert extractor.calculate_similarity('gatto', 'telescopio') == 0
    from allma_model.topic_extraction.topic_extractor import TopicExtractor as KnownTopics
    topics = KnownTopics()
    topics.add_known_topic('animali', ['gatto'])
    topics.add_known_topic('astronomia', ['telescopio'])
    assert topics.extract_topic('prova distinta') is not None
    assert topics.find_similar_topic('telescopio') == 'astronomia'


def test_dream_proactivity_reads_only_reviewed_current_user_records(tmp_path):
    from allma_model.core.dream_system.review_store import DreamReviewStore
    from allma_model.agency_system.proactive_core import ProactiveAgency
    store = DreamReviewStore(tmp_path/'dreams.db')
    store.ingest([{'user_id': 'u', 'text': 'ipotesi', 'timestamp': datetime.now().isoformat()}])
    agency = ProactiveAgency(review_store=store)
    assert agency._get_latest_dream_insight('u') is None
    record = store.list('u')[0]
    store.review('u', record['id'], 'correct', correction='testo corretto')
    assert agency._get_latest_dream_insight('u') == 'testo corretto'
    assert agency._get_latest_dream_insight('other') is None
    record = store.list('u')[0]
    store.review('u', record['id'], 'reject', expected_revision=record['revision'])
    assert agency._get_latest_dream_insight('u') is None


def test_preference_roundtrip_and_explicit_update(tmp_path):
    from allma_model.user_preferences.preference_analyzer import PreferenceAnalyzer
    analyzer = PreferenceAnalyzer(str(tmp_path/'preferences.db'))
    assert analyzer.update_user_preferences('u', {'learning_style': {'style': 'visual'}})
    assert analyzer.analyze_learning_style('u').style.value == 'visual'


def test_empty_emotions_do_not_break_personality_style():
    from allma_model.core.personality import Personality
    personality = Personality()
    personality.update_personality('ciao')
    assert isinstance(personality.get_interaction_style(), str)


def test_webview_polling_has_one_owner_and_can_close(monkeypatch):
    from allma_model.ui.webview_bridge import WebViewBridge
    from unittest.mock import Mock
    monkeypatch.setattr('allma_model.ui.webview_bridge.platform', 'linux')
    event = Mock()
    schedule = Mock(return_value=event)
    monkeypatch.setattr('allma_model.ui.webview_bridge.Clock.schedule_interval', schedule)
    bridge = WebViewBridge(lambda _: None)
    bridge._start_polling()
    bridge._start_polling()
    assert schedule.call_count == 1
    bridge.pause()
    event.cancel.assert_called_once()
    bridge.resume()
    bridge._start_polling()
    assert schedule.call_count == 2
    bridge.close()
    bridge._start_polling()
    assert schedule.call_count == 2 and bridge._closed


def test_memory_ui_never_falls_back_to_other_users():
    from allma_model.api.allma_api import AllmaAndroidBridge
    bridge = AllmaAndroidBridge.__new__(AllmaAndroidBridge)
    bridge.allma = SimpleNamespace(conversational_memory=SimpleNamespace(lock=__import__('threading').RLock(), user_data={}, messages=[
        SimpleNamespace(user_id='other', metadata={}, content='privato', timestamp=datetime.now(), role='user')]))
    assert bridge.get_memory_data('u')['logs'] == []


def test_personality_diary_reports_changes_not_absolute_values(tmp_path):
    from allma_model.core.personality_coalescence import CoalescenceProcessor
    processor = CoalescenceProcessor(db_path=str(tmp_path/'state.db'))
    assert processor._analyze_personality_changes() == {}
    processor.core.personality_traits['empathy'] += .01
    assert processor._analyze_personality_changes() == {'empathy': pytest.approx(.01)}
    assert processor._analyze_personality_changes() == {}


def test_entropy_of_previous_answers_reaches_next_turn(tmp_path):
    from allma_model.core.architecture.identity_state import IdentityStateEngine
    engine = IdentityStateEngine(str(tmp_path/'state.db'))
    engine.update_state('stessa risposta', [])
    engine.update_state('stessa risposta', [])
    assert engine.compute_state({}).entropy_index < 1



def test_positive_feedback_never_reduces_high_confidence():
    from allma_model.core.learning_feedback import LearningManager, Feedback, FeedbackType
    feedback = Feedback(FeedbackType.VALIDATION, 'corretto', 'user', 0, {}, 1.)
    delta = LearningManager()._calculate_confidence_impact(feedback, {'age': 0, 'confidence': .9})
    assert 0 <= delta <= .1 + 1e-12


def test_semantic_memory_nested_relation_query_finishes():
    from allma_model.incremental_learning.memory_system import SemanticMemory
    memory = SemanticMemory()
    memory.add_concept('gatto', {})
    memory.add_relationship('gatto', 'tipo', 'animale')
    results = []
    thread = threading.Thread(target=lambda: results.append(memory.query_knowledge('gatto')), daemon=True)
    thread.start()
    thread.join(2)
    assert not thread.is_alive() and results


def test_cache_release_keeps_all_memories_searchable(tmp_path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u', 'gatto domestico')
    engine.add('u', 'telescopio')
    assert engine.release_cache() == 2
    assert engine.count() == 2
    assert engine.search('u', 'gatto')[0]['content'] == 'gatto domestico'
    restored = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    assert restored.search('u', 'telescopio')[0]['content'] == 'telescopio'


def test_personal_concepts_have_explicit_owners(tmp_path):
    from allma_model.core.personality_coalescence import CoalescenceProcessor, EmotionalResponse, EmotionalState
    processor = CoalescenceProcessor(db_path=str(tmp_path/'state.db'))
    processor._extract_concepts_and_explanations = lambda _: {'preferenza': 'testo personale'}
    processor.integrate_knowledge('esperienza privata', 'user_interaction',
                                  EmotionalResponse(EmotionalState.NEUTRAL), user_id='u')
    assert processor.knowledge.get_concept('preferenza', user_id='u')['owner_user_id'] == 'u'
    assert processor.knowledge.get_concept('preferenza', user_id='other') is None
    assert processor.knowledge.get_concept('preferenza') is None
    assert processor.core.diary[-1]['context']['user_id'] == 'u'


def test_incremental_personal_retrieval_excludes_other_users(tmp_path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner, LearningUnit, ConfidenceLevel
    learner = IncrementalLearner(str(tmp_path/'learning.json'))
    for user, content in [('u', 'gatto domestico'), ('other', 'gatto nero')]:
        learner.add_learning_unit(LearningUnit('animali', content, 'user_'+user,
            ConfidenceLevel.HIGH, datetime.now(), metadata={'user_id': user}))
    assert [item.content for item in learner.find_related_knowledge('gatto', user_id='u')] == ['gatto domestico']
    assert learner.get_knowledge_by_topic('animali', user_id='u')[0]['content'] == 'gatto domestico'
    assert learner.find_related_knowledge('gatto', user_id='unknown') == []



def test_personality_changes_only_on_attributed_feedback_and_survives_restart(tmp_path):
    from allma_model.core.personality_coalescence import CoalescenceProcessor, EmotionalResponse, EmotionalState
    db = str(tmp_path/'state.db')
    processor = CoalescenceProcessor(db)
    initial = dict(processor.core.personality_traits)
    processor.integrate_knowledge('Sono triste', 'user_interaction', EmotionalResponse(EmotionalState.SADNESS), user_id='u')
    assert processor.core.personality_traits == initial
    assert processor.observe_feedback('u', 'original-answer', True, ['emotion'])
    evolved = dict(processor.core.personality_traits)
    assert initial['empathy'] < evolved['empathy'] < initial['empathy'] + .005
    assert evolved['curiosity'] == initial['curiosity']
    restored = CoalescenceProcessor(db)
    assert restored.core.personality_traits == evolved
    assert not restored.observe_feedback('u', 'original-answer', True, ['emotion'])
    assert restored.core.personality_traits == evolved
    assert restored.observe_feedback('u', 'corrected-answer', False, ['technical'])
    assert restored.core.personality_traits['openness'] > evolved['openness']


def test_failed_feedback_persistence_rolls_back_traits_and_can_retry(tmp_path, monkeypatch):
    from allma_model.core.personality_coalescence import CoalescenceProcessor
    processor = CoalescenceProcessor(str(tmp_path/'state.db'))
    before = dict(processor.core.personality_traits)
    save = processor._state_store.put
    def fail(*args):
        raise OSError('simulated save failure')
    monkeypatch.setattr(processor._state_store, 'put', fail)
    with pytest.raises(OSError):
        processor.observe_feedback('u', 'answer', True, ['emotion'])
    assert processor.core.personality_traits == before and processor._feedback_events == {}
    monkeypatch.setattr(processor._state_store, 'put', save)
    assert processor.observe_feedback('u', 'answer', True, ['emotion'])



def test_duplicate_indexing_does_not_dirty_or_inflate_document_frequency(tmp_path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    identifier = engine.add('u', 'gatto', source_key='stable-key')
    engine.search('u', 'gatto')
    before = engine._tfidf.to_dict()
    assert engine.add('u', 'gatto', source_key='stable-key') == identifier
    assert engine._tfidf.to_dict() == before and not engine._index_dirty



@pytest.mark.parametrize('enhanced', [False, True])
def test_alternative_memory_process_recall_and_consolidation_have_consistent_types(enhanced):
    from datetime import timedelta
    from allma_model.incremental_learning.memory_system import MemorySystem, EnhancedMemorySystem
    memory = EnhancedMemorySystem() if enhanced else MemorySystem()
    result = memory.process_experience('Studio Python con interesse', .7, {'source': 'test'})
    assert result['memory_stored']
    assert memory.recall_memory('Python')
    old = datetime.now() - timedelta(seconds=memory.consolidation_interval + 1)
    if enhanced:
        memory.working_memory.items[0].timestamp = old
    else:
        memory.working_memory[0]['timestamp'] = old.isoformat()
    memory._consolidate_memories()
    assert memory.recall_memory('Python')
    assert memory.get_memory_stats()['total_memories'] > 0
