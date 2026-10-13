from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

from allma_model.core.dream_system.dream_manager import DreamManager
from allma_model.core.dream_system.tree_of_thoughts import TreeOfThoughts


def manager(tmp_path):
    monitor = Mock()
    monitor.get_metabolic_state.return_value = SimpleNamespace(
        is_charging=True, energy_level=.9, battery_temp_celsius=30)
    memory = Mock()
    memory.get_interactions.return_value = [{'content': 'Oggi abbiamo parlato di Roma.'}]
    return DreamManager(memory, Mock(), system_monitor=monitor,
                        llm_wrapper=Mock(), journal_path=str(tmp_path / 'dreams.json'))


def test_failed_or_cancelled_generation_never_echoes_memory_as_insight():
    llm = Mock()
    llm.generate.return_value = ''
    tot = TreeOfThoughts(llm)
    assert tot.solve('Un ricordo personale') == []
    event = Event()
    tot.cancel_event = event
    def generate(*args, **kwargs):
        assert kwargs['cancel_event'] is event
        event.set()
        return 'Una generazione interrotta'
    llm.generate.side_effect = generate
    assert tot.solve('Un ricordo personale') == []


def test_only_one_dream_worker_and_user_activity_cancels_native_call(tmp_path):
    m = manager(tmp_path)
    active = Event()
    m.user_active_event = active
    entered, release = Event(), Event()
    def generate(*args, **kwargs):
        entered.set()
        release.wait(2)
        assert kwargs['cancel_event'].is_set()
        return 'Ipotesi non completata'
    m.llm_wrapper.generate.side_effect = generate
    try:
        assert m.check_and_start_dream('u') is True
        assert entered.wait(2)
        assert m.check_and_start_dream('another-user') is False
        assert m.current_user_id == 'u'
        active.set()
        release.set()
        m._worker.join(2)
        assert not m.is_dreaming
        assert not m.pending_verification
        m.system_monitor.release_wake_lock.assert_called_once()
    finally:
        release.set()
        m.close()


def test_monitor_failure_does_not_leave_dreaming_flag_stuck(tmp_path):
    m = manager(tmp_path)
    m.system_monitor.get_metabolic_state.side_effect = RuntimeError('sensor unavailable')
    assert m.check_and_start_dream('u')
    m._worker.join(2)
    assert not m.is_dreaming
    m.system_monitor.acquire_wake_lock.assert_not_called()


def test_hypotheses_are_persistent_but_never_confirmed_learning(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m._consolidate_insights(['Una relazione immaginata tra Roma e il mare.'])
    m.incremental_learner.add_learning_unit.assert_not_called()
    assert m.pending_verification[0]['status'] == 'unverified'
    restored = manager(tmp_path)
    assert restored.pending_verification == m.pending_verification
    restored.current_user_id = 'another-user'
    assert restored.get_and_clear_pending_verification() is None
    restored.current_user_id = 'u'
    assert restored.get_and_clear_pending_verification()['source'] == 'dream_hypothesis'
    assert manager(tmp_path).pending_verification == []


def test_cycle_requires_power_and_limits_model_calls(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.system_monitor.get_metabolic_state.return_value.battery_temp_celsius = 45
    m._dream_cycle()
    m.llm_wrapper.generate.assert_not_called()
    m.system_monitor.get_metabolic_state.return_value.battery_temp_celsius = 30
    m.memory_system.get_interactions.return_value = [{'content': f'esperienza {i}'} for i in range(20)]
    m.llm_wrapper.generate.return_value = 'Una possibile connessione, da verificare.'
    m._dream_cycle()
    assert m.llm_wrapper.generate.call_count == 3
    m.incremental_learner.add_learning_unit.assert_not_called()


def test_disabling_cancels_a_dream_even_without_active_chat(tmp_path):
    m = manager(tmp_path)
    entered, release = Event(), Event()
    def generate(*args, **kwargs):
        entered.set()
        release.wait(2)
        assert kwargs['cancel_event'].is_set()
        return 'Ipotesi interrotta'
    m.llm_wrapper.generate.side_effect = generate
    try:
        m.check_and_start_dream('u')
        assert entered.wait(2)
        m.cancel()
        release.set()
        m._worker.join(2)
        assert not m.pending_verification
    finally:
        release.set()
        m.close()


def test_dream_inputs_exclude_other_users_assistant_and_invalid_records(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.memory_system.get_interactions.return_value = [
        {'content': 'esperienza valida', 'user_id': 'u'},
        {'content': 'altro utente', 'user_id': 'v'},
        {'content': 'risposta generata', 'role': 'assistant'},
        {'content': 'risposta invalida', 'metadata': {'is_valid': False}},
    ]
    assert [item['text'] for item in m._fetch_unconsolidated_memories()] == ['esperienza valida']


def test_successful_dreams_do_not_repeat_same_evidence_after_restart(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = 'Una possibile connessione da verificare.'
    m._dream_cycle()
    assert m.llm_wrapper.generate.call_count == 1
    restored = manager(tmp_path)
    restored.current_user_id = 'u'
    restored._dream_cycle()
    restored.llm_wrapper.generate.assert_not_called()
    restored.current_user_id = 'other'
    restored.llm_wrapper.generate.return_value = 'Un’altra ipotesi.'
    restored._dream_cycle()
    restored.llm_wrapper.generate.assert_called_once()


def test_failed_dream_remains_available_for_future_attempt(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = ''
    m._dream_cycle()
    assert not m.processed_memories
    m.llm_wrapper.generate.return_value = 'Ipotesi successiva.'
    m._dream_cycle()
    assert len(m.processed_memories) == 1


def test_pending_write_failure_can_retry_without_losing_hypothesis(tmp_path, monkeypatch):
    import allma_model.utils.persistence as persistence
    original = persistence.atomic_write_json
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = 'Una nuova ipotesi da verificare.'
    failed = []
    def save(path, value, **kwargs):
        if str(path).endswith('.pending.json') and not failed:
            failed.append(True)
            raise OSError('Simulated disk write failure')
        return original(path, value, **kwargs)
    monkeypatch.setattr(persistence, 'atomic_write_json', save)
    m._dream_cycle()
    assert not m.processed_memories
    m._dream_cycle()
    restored = manager(tmp_path)
    assert len(restored.pending_verification) == 1
    assert restored.pending_verification[0]['text'] == 'Una nuova ipotesi da verificare.'
    assert len(restored.processed_memories) == 1


def test_temperature_rise_cancels_generation_without_consolidation(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    def generate(*args, **kwargs):
        m.system_monitor.get_metabolic_state.return_value.battery_temp_celsius = 45
        m._cancel_event.last_power_check = 0
        assert kwargs['cancel_event'].is_set()
        return 'Ipotesi interrotta da scartare.'
    m.llm_wrapper.generate.side_effect = generate
    m._dream_cycle()
    assert not m.pending_verification
    assert not m.processed_memories
    m.system_monitor.release_wake_lock.assert_called_once()


def test_processed_write_failure_remains_retryable_in_same_session(tmp_path, monkeypatch):
    import allma_model.utils.persistence as persistence
    original = persistence.atomic_write_json
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = 'Ipotesi con checkpoint.'
    failed = []
    def save(path, value, **kwargs):
        if str(path).endswith('.processed.json') and not failed:
            failed.append(True)
            raise OSError('Simulated checkpoint write failure')
        return original(path, value, **kwargs)
    monkeypatch.setattr(persistence, 'atomic_write_json', save)
    m._dream_cycle()
    assert not m.processed_memories
    m._dream_cycle()
    assert len(manager(tmp_path).processed_memories) == 1


def test_pending_consumer_write_failure_does_not_remove_item(tmp_path, monkeypatch):
    import pytest
    import allma_model.utils.persistence as persistence
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m._consolidate_insights(['Ipotesi da esaminare.'])
    def fail(*args, **kwargs):
        raise OSError('Simulated removal write failure')
    monkeypatch.setattr(persistence, 'atomic_write_json', fail)
    with pytest.raises(OSError):
        m.get_and_clear_pending_verification()
    assert len(m.pending_verification) == 1
    assert len(manager(tmp_path).pending_verification) == 1


def test_dream_history_is_scoped_to_the_requesting_user(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m._log_dream('Ipotesi privata u', 'hypothesis')
    m.current_user_id = 'other'
    m._log_dream('Ipotesi privata other', 'hypothesis')
    assert [item['text'] for item in m.get_history(user_id='u')] == ['Ipotesi privata u']
    assert m.get_history(user_id='unknown') == []


def test_review_queue_backpressure_skips_model_without_losing_existing_records(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m._consolidate_insights([f'Ipotesi da valutare {i}' for i in range(50)])
    m._dream_cycle()
    m.llm_wrapper.generate.assert_not_called()
    assert m.review_store.pending_count('u') == 50
    row = m.review_store.list('u')[0]
    m.review_store.review('u', row['id'], 'reject')
    m.llm_wrapper.generate.return_value = 'Una nuova ipotesi.'
    m._dream_cycle()
    m.llm_wrapper.generate.assert_called_once()
    assert m.review_store.pending_count('u') == 50
    assert len(m.review_store.list('u')) == 51


def test_review_store_write_failure_is_reconciled_without_duplicate_generation_checkpoint(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = 'Ipotesi riprovabile.'
    original = m.review_store.ingest
    def ingest(records):
        if records:
            raise OSError('Store temporarily unavailable')
        return original(records)
    m.review_store.ingest = ingest
    m._dream_cycle()
    assert len(m.pending_verification) == 1
    assert not m.processed_memories
    m.review_store.ingest = original
    m._dream_cycle()
    assert len(m.review_store.list('u')) == 1
    assert len(m.processed_memories) == 1


def test_hypothesis_preserves_actual_input_evidence(tmp_path):
    m = manager(tmp_path)
    m.current_user_id = 'u'
    m.llm_wrapper.generate.return_value = 'Ipotesi sul viaggio.'
    m._dream_cycle()
    assert m.review_store.list('u')[0]['evidence']['text'] == 'Oggi abbiamo parlato di Roma.'
    m.incremental_learner.add_learning_unit.assert_not_called()


def test_corrupt_review_archive_is_preserved_and_blocks_dreams_without_blocking_startup(tmp_path):
    path = tmp_path / 'dreams.json.reviews.db'
    path.write_bytes(b'corrupt sqlite archive')
    m = manager(tmp_path)
    assert m.review_store is None
    assert path.read_bytes() == b'corrupt sqlite archive'
    m.current_user_id = 'u'
    m._dream_cycle()
    m.llm_wrapper.generate.assert_not_called()
    assert not m.is_dreaming
