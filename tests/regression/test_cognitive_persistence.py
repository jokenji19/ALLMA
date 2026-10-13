import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from allma_model.learning_system.answer_recall import AnswerRecall
from allma_model.utils.cognitive_state import CognitiveStateStore
from allma_model.core.architecture.identity_state import IdentityStateEngine
from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem
from allma_model.core.identity_system import IdentityManager
from allma_model.core.personality_coalescence import CoalescenceProcessor, EmotionalResponse, EmotionalState
from allma_model.utils.background_work import BackgroundCancellation, power_allows_background
from allma_model.utils.generation_control import GenerationCancelled


@pytest.fixture(autouse=True)
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize('data', [[], None, {'version': 1, 'records': []},
                                   {'version': 1, 'records': {'k': {'answer': 'x'}}}])
def test_bad_recall_preserves_original_and_accepts_new_learning(tmp_path, data):
    path = tmp_path / 'answers.json'
    original = json.dumps(data)
    path.write_text(original)
    recall = AnswerRecall(path)
    assert recall.lookup('k', 'u') is None
    recall.observe('new', 'u', 'Una domanda completa', 'Risposta', 'event')
    assert path.with_name(path.name + '.invalid.bak').read_text() == original
    assert AnswerRecall(path).records['new']['answer'] == 'Risposta'


def test_mixed_recall_keeps_only_valid_confirmed_answer(tmp_path):
    path = tmp_path / 'answers.json'
    recall = AnswerRecall(path)
    recall.observe('good', 'u', 'Una domanda completa', 'Risposta corretta', 'e')
    recall.feedback('good', 'u', 'one', True)
    recall.feedback('good', 'u', 'two', True)
    data = json.loads(path.read_text())
    data['records']['bad'] = {'confirmations': ['one', 'one'], 'user': 'u'}
    path.write_text(json.dumps(data))
    restored = AnswerRecall(path)
    assert restored.lookup('good', 'u')['answer'] == 'Risposta corretta'
    assert restored.lookup('good', 'other') is None
    assert restored.lookup('bad', 'u') is None


def test_identity_integrity_and_rules_survive_restart_without_cross_db_leak(tmp_path):
    db = tmp_path / 'one' / 'allma.db'
    identity = IdentityStateEngine(str(db))
    identity.update_state('Prima esperienza', ['violation'])
    rules = NeuroplasticitySystem(str(db))
    rules.add_rule(r'frase vietata', 'frase corretta')
    rules.analyze(['FORBIDDEN:frase vietata'])
    integrity = IdentityManager(str(db))
    integrity.record_conflict('conflict', .2, 'test')
    restored = IdentityStateEngine(str(db))
    assert restored._maturity == identity._maturity
    assert restored._base_stability == identity._base_stability
    assert not restored.entropy_tracker.word_sets
    restored_rules = NeuroplasticitySystem(str(db))
    assert restored_rules.rules[r'frase vietata'].activation_count == 2
    assert IdentityManager(str(db)).stability == pytest.approx(.8)
    assert IdentityStateEngine(str(tmp_path / 'two' / 'allma.db'))._maturity == .5
    assert set(CognitiveStateStore(str(db))._read()['sections']) == {'identity_state', 'neuroplasticity', 'identity_integrity'}


def test_bad_numeric_state_and_regex_are_ignored(tmp_path):
    db = str(tmp_path / 'allma.db')
    store = CognitiveStateStore(db)
    store.put('identity_state', {'maturity': 'old', 'stability': float('nan')})
    store.put('neuroplasticity', {'rules': [{'pattern': '[', 'replacement': '', 'activation_count': 2}]})
    restored = IdentityStateEngine(db)
    assert restored._maturity == .5 and restored._base_stability == .9
    assert NeuroplasticitySystem(db).rules == {}


def test_atomic_save_failure_preserves_last_cognitive_state(tmp_path, monkeypatch):
    import allma_model.utils.persistence as persistence
    store = CognitiveStateStore(str(tmp_path / 'allma.db'))
    store.put('identity', {'maturity': .6})
    original = store.path.read_bytes()
    monkeypatch.setattr(persistence.os, 'replace', Mock(side_effect=OSError('disk unavailable')))
    with pytest.raises(OSError):
        store.put('identity', {'maturity': .7})
    assert store.path.read_bytes() == original


def test_coalescence_real_concept_integration_and_diary_no_duplicate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = str(tmp_path / 'private' / 'allma.db')
    processor = CoalescenceProcessor(db)
    processor._extract_concepts_and_explanations = lambda content: {'bicicletta': 'Un mezzo a pedali'}
    processor.integrate_knowledge('Una bicicletta ha due ruote', 'user_interaction',
                                  EmotionalResponse(EmotionalState.NEUTRAL))
    assert processor.knowledge.db_path == db
    assert processor.knowledge.get_concept('bicicletta')['knowledge_verified'] is False
    assert len(processor.core.diary) == 1
    processor.core.personality_traits['curiosity'] = .73
    processor.core.values['empatia'].strength = .67
    processor._save_diary()
    restored = CoalescenceProcessor(db)
    assert restored.core.personality_traits['curiosity'] == .73
    assert restored.core.values['empatia'].strength == .67
    assert len(restored.core.diary) == 1
    assert not (tmp_path / 'Model').exists()
    assert not (tmp_path / 'allma_diary.json').exists()


def test_legacy_knowledge_and_diary_migration_is_idempotent_and_non_destructive(tmp_path):
    from allma_model.memory_system.knowledge_memory import KnowledgeMemory
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    legacy = tmp_path / 'legacy'
    old = KnowledgeMemory(str(legacy / 'Model/data/allma.db'))
    old.store_knowledge('Dato storico', {'source': 'user_statement'})
    diary = {'entries': [{'content': 'Esperienza precedente'}]}
    (legacy / 'allma_diary.json').write_text(json.dumps(diary))
    state_dir = prepare_runtime_storage(tmp_path / 'private', legacy)
    processor = CoalescenceProcessor(str(Path(state_dir) / 'allma.db'))
    assert processor.core.diary == diary['entries']
    assert processor.knowledge.get_all_knowledge()[0]['content'] == 'Dato storico'
    processor.knowledge.import_legacy(Path(state_dir) / 'legacy_coalescence.db')
    assert len(processor.knowledge.get_all_knowledge()) == 1
    assert (legacy / 'Model/data/allma.db').exists()


@pytest.mark.parametrize('charging,energy,temp,expected', [
    (True,.9,30,True), (False,.9,30,False), (True,.5,30,False),
    (True,.9,42,False), (True,.9,0,False), (True,.9,float('nan'),False)])
def test_background_admission(charging, energy, temp, expected):
    monitor = Mock()
    monitor.get_metabolic_state.return_value = SimpleNamespace(is_charging=charging, energy_level=energy, battery_temp_celsius=temp)
    assert power_allows_background(monitor) is expected


def test_maintenance_cancelled_or_bad_extraction_never_erases_history(tmp_path):
    from allma_model.memory_system.conversational_memory import ConversationalMemory
    memory = ConversationalMemory(storage_dir=str(tmp_path))
    conv = memory.create_conversation('u')
    memory.store_message(conv, 'Il mio hobby è fotografia', {}, 'user', 'u')
    memory.messages[-1].timestamp = datetime.now() - timedelta(days=40)
    before = list(memory.messages)
    memory.condense_and_clear_old('u', datetime.now() - timedelta(days=30), lambda _: '{"hobby":"fotografia"}')
    assert memory.user_data['u']['hobby'] == 'fotografia'
    assert memory.messages == before
    active, shutdown = Event(), Event()
    monitor = Mock()
    monitor.get_metabolic_state.return_value = SimpleNamespace(is_charging=True, energy_level=.9, battery_temp_celsius=30)
    cancel = BackgroundCancellation(shutdown, active, monitor)
    def extract(_):
        active.set()
        return '{"hobby":"nuoto"}'
    with pytest.raises(GenerationCancelled):
        memory.condense_and_clear_old('u', datetime.now(), extract, cancel)
    assert memory.messages == before
    assert memory.user_data['u']['hobby'] == 'fotografia'


def test_vision_does_not_invent_objects_from_filename():
    from allma_model.vision_system.vision_core import VisionSystem
    result = VisionSystem().analyze_image('frigo_tramonto.jpg')
    assert 'non è ancora disponibile' in result
    assert 'uova' not in result and 'mare' not in result


def test_context_fitting_retains_system_and_current_question():
    from allma_model.utils.prompt_budget import fit_prompt, reasoning_budget
    system = '<|im_start|>system\nMi chiamo ALLMA.<|im_end|>\n'
    old = '<|im_start|>user\n' + 'vecchio ' * 80 + '<|im_end|>\n<|im_start|>assistant\nRisposta vecchia.<|im_end|>\n'
    current = '<|im_start|>user\nDomanda attuale.<|im_end|>\n<|im_start|>assistant\n<think>'
    tokenizer = lambda value: list(value)
    fitted, count = fit_prompt(system + old + current, tokenizer, 256, 64)
    assert fitted == system + current
    assert count == 1
    with pytest.raises(ValueError):
        fit_prompt(system + current, tokenizer, 128, 64)
    assert reasoning_budget('Dimostra passo per passo', 'COMPLEX', 512) == 192
    assert reasoning_budget('Ciao', 'SIMPLE', 256) == 64
    assert reasoning_budget('Dimostra', 'COMPLEX', 96) == 32


def test_only_consumed_legacy_output_is_computed():
    from allma_model.core.legacy_brain_adapter import LegacyBrainAdapter
    adapter = LegacyBrainAdapter.__new__(LegacyBrainAdapter)
    for name in ('curiosity', 'ethics', 'metacognition', 'social', 'creativity', 'meta_learning'):
        setattr(adapter, name, Mock())
    adapter.social.analyze_social_context.return_value = SimpleNamespace(formality=.7)
    result = adapter.pulse('Una nuova idea abbastanza lunga', enabled_systems={'social'})
    assert result.active_systems == ['Social']
    assert result.social_context == 'Formalità: 0.70'
    for name in ('curiosity', 'ethics', 'metacognition', 'creativity', 'meta_learning'):
        assert not getattr(adapter, name).mock_calls


def test_unavailable_vision_does_not_invoke_text_model():
    from allma_model.core.allma_core import ALLMACore
    from allma_model.vision_system.vision_core import VisionSystem
    core = ALLMACore.__new__(ALLMACore)
    core.vision_system = VisionSystem()
    core.process_message = Mock()
    result = core.process_visual_input('u', 'frigo.jpg', 'Cosa vedi?')
    assert not result.is_valid
    assert result.metadata['source'] == 'vision_unavailable'
    core.process_message.assert_not_called()


def test_concurrent_concept_updates_preserve_independent_fields(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from allma_model.memory_system.knowledge_memory import KnowledgeMemory
    memory = KnowledgeMemory(str(tmp_path / 'concepts.db'))
    memory.add_concept('prova', {'explanation': 'Un concetto di prova'})
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda index: memory.update_concept('prova', {f'field_{index}': index}), range(40)))
    record = memory.get_concept('prova')
    assert all(record.get(f'field_{index}') == index for index in range(40))
    assert record['knowledge_verified'] is False


def test_coalescence_accepts_emotion_enum_from_another_module(tmp_path):
    from enum import Enum
    class OtherEmotion(Enum):
        NEUTRAL = 'neutral'
    processor = CoalescenceProcessor(str(tmp_path / 'enum.db'))
    processor._extract_concepts_and_explanations = lambda content: {'prova': 'Un concetto'}
    processor.integrate_knowledge('Concetto di prova', 'user_interaction',
                                  SimpleNamespace(primary_emotion=OtherEmotion.NEUTRAL, intensity=.4))
    assert len(processor.core.diary) == 1
    assert processor.knowledge.has_concept('prova')


@pytest.mark.parametrize('text,expected', [
    ('Rispondi solo con il numero.', 'neutral'),
    ('Voglio soltanto una risposta breve.', 'neutral'),
    ('Mi sento solo e triste.', 'sadness'),
    ('Mi sento sola.', 'sadness'),
])
def test_output_constraints_are_not_emotional_loneliness(text, expected):
    from allma_model.emotional_system.emotional_core import EmotionalCore
    core = EmotionalCore.__new__(EmotionalCore)
    assert core._heuristic_detect_emotion(text).primary_emotion == expected
