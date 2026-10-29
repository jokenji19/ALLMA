"""Durable initiative delivery under disk, callback and lifecycle failures."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
import time

import pytest

from allma_model.memory_system.conversational_memory import ConversationalMemory


@pytest.fixture
def initiative(tmp_path):
    from allma_model.core.allma_core import ALLMACore
    core = ALLMACore(mobile_mode=True, db_path=str(tmp_path/'core.db'))
    conversation = core.start_conversation('synthetic')
    core.conversational_memory.store_message(conversation, 'Parliamo di lettura.', {}, 'user', 'synthetic')
    core.conversational_memory.messages[-1].timestamp = datetime.now()-timedelta(hours=12)
    core.conversational_memory.save_memory()
    core._current_user_id = 'synthetic'
    core.dream_enabled = True
    core.output_callback = Mock()
    core.system_monitor = SimpleNamespace(get_metabolic_state=lambda: SimpleNamespace(
        is_tired=False, energy_level=.9, battery_temp_celsius=35., is_charging=True,
        is_power_save=False, is_valid=True, source='synthetic', observed_at=time.monotonic()))
    core.proactive_agency.check_initiative = Mock(return_value=SimpleNamespace(should_contact=True, context={}))
    class Engine:
        binding = SimpleNamespace(sampling=lambda: {})
        calls = 0
        def prepare_chat(self, *args, **kwargs):
            return SimpleNamespace(prompt='synthetic', reasoning=False, stops=[])
        def generate(self, **kwargs):
            self.calls += 1
            return 'Possiamo riprendere la conversazione quando vuoi.'
        def get_generation_meta(self, *args):
            return {'finish_reason': 'stop'}
    core._llm = Engine()
    yield core, tmp_path, conversation
    core.close()


def initiatives(memory):
    return [m for m in memory.messages if m.metadata.get('source') == 'proactive']


def test_failed_save_never_sends_a_proactive_message(initiative):
    core, root, _ = initiative
    with patch.object(core.conversational_memory._history_store, 'commit',
               side_effect=OSError('Synthetic disk full')):
        result = core.check_proactive_trigger()
    assert result['status'] == 'error'
    core.output_callback.assert_not_called()
    assert not initiatives(core.conversational_memory)
    assert not initiatives(ConversationalMemory(storage_dir=str(root)))


def test_callback_sees_an_already_durable_message(initiative):
    core, root, conversation = initiative
    def receive(event):
        restored = ConversationalMemory(storage_dir=str(root))
        rows = initiatives(restored)
        assert len(rows) == 1
        assert rows[0].content == event['content']
        assert rows[0].metadata['request_id'] == event['request_id']
        assert rows[0].conversation_id == conversation
        return True
    core.output_callback = Mock(side_effect=receive)
    assert core.check_proactive_trigger()['status'] == 'delivered'
    core.output_callback.assert_called_once()


def test_failed_callback_retries_saved_message_without_another_generation(initiative):
    core, root, _ = initiative
    core.output_callback.side_effect = RuntimeError('UI unavailable')
    first = core.check_proactive_trigger()
    assert first['status'] == 'delivery_pending'
    assert len(initiatives(core.conversational_memory)) == 1
    core.conversational_memory = ConversationalMemory(storage_dir=str(root))
    core._proactive_attempt_at.clear()
    core._llm = None  # Recovery needs the saved message, not the model.
    core.output_callback = Mock(return_value=True)
    second = core.check_proactive_trigger()
    assert second['status'] == 'delivered'
    assert second['request_id'] == first['request_id']
    assert len(initiatives(core.conversational_memory)) == 1
    assert core.check_proactive_trigger()['status'] == 'cooldown'
    core.output_callback.assert_called_once()


def test_explicit_ui_rejection_keeps_delivery_pending(initiative):
    core, _, _ = initiative
    core.output_callback.return_value = False
    first = core.check_proactive_trigger()
    assert first['status'] == 'delivery_pending'
    core.output_callback.return_value = True
    second = core.check_proactive_trigger()
    assert second['status'] == 'delivered'
    assert second['request_id'] == first['request_id']
    assert core._llm.calls == 1
    assert len(initiatives(core.conversational_memory)) == 1


def test_ack_failure_retries_the_same_delivery_id(initiative):
    core, _, _ = initiative
    save = core.conversational_memory.save_memory
    calls = 0
    def flaky_save():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('Acknowledgement disk failure')
        return save()
    with patch.object(core.conversational_memory, 'save_memory', side_effect=flaky_save):
        first = core.check_proactive_trigger()
    assert first['status'] == 'delivery_pending'
    assert initiatives(core.conversational_memory)[0].metadata['proactive_delivery']['state'] == 'pending'
    second = core.check_proactive_trigger()
    assert second['request_id'] == first['request_id']
    assert second['status'] == 'delivered'
    assert core._llm.calls == 1
    assert len(initiatives(core.conversational_memory)) == 1


def test_pause_between_save_and_callback_keeps_recoverable_message(initiative):
    core, _, _ = initiative
    store = core.conversational_memory.store_message
    def pause_after_store(*args, **kwargs):
        store(*args, **kwargs)
        core.set_foreground(False)
    with patch.object(core.conversational_memory, 'store_message', side_effect=pause_after_store):
        assert core.check_proactive_trigger()['status'] == 'cancelled'
    core.output_callback.assert_not_called()
    assert len(initiatives(core.conversational_memory)) == 1
    core.set_foreground(True)
    assert core.check_proactive_trigger()['status'] == 'delivered'
    assert core._llm.calls == 1


def test_initiative_is_saved_in_the_active_users_new_chat(initiative):
    core, _, old_conversation = initiative
    current = core.start_conversation('synthetic')
    assert current != old_conversation
    assert core.check_proactive_trigger()['status'] == 'delivered'
    assert initiatives(core.conversational_memory)[0].conversation_id == current
    assert core.output_callback.call_args.args[0]['conversation_id'] == current


def test_event_bus_cannot_deliver_unvalidated_module_text(initiative):
    import asyncio
    core, _, _ = initiative
    core.dream_enabled = False
    event = SimpleNamespace(event_type='proactive_message', source='synthetic',
                            payload={'text': 'Unvalidated module text'})
    asyncio.run(core._handle_bus_event(event))
    core.output_callback.assert_not_called()
    assert not initiatives(core.conversational_memory)


def test_pending_delivery_still_respects_revoked_consent(initiative):
    core, _, _ = initiative
    core.output_callback.return_value = False
    assert core.check_proactive_trigger()['status'] == 'delivery_pending'
    core.output_callback.reset_mock()
    core.dream_enabled = False
    assert core.check_proactive_trigger()['status'] == 'inactive'
    core.output_callback.assert_not_called()
    assert core._llm.calls == 1


def test_process_interruption_leaves_one_recoverable_record(initiative):
    core, root, _ = initiative
    core.output_callback.side_effect = KeyboardInterrupt('Synthetic process interruption')
    with pytest.raises(KeyboardInterrupt):
        core.check_proactive_trigger()
    assert not core._user_active.is_set()
    core.conversational_memory = ConversationalMemory(storage_dir=str(root))
    assert len(initiatives(core.conversational_memory)) == 1
    core.output_callback = Mock(return_value=True)
    assert core.check_proactive_trigger()['status'] == 'delivered'
    assert core._llm.calls == 1


def test_pending_message_is_not_an_already_delivered_conversation(initiative):
    from allma_model.core.autobiographical_identity import history_eligible
    core, _, conversation = initiative
    core.output_callback.return_value = False
    assert core.check_proactive_trigger()['status'] == 'delivery_pending'
    memory = core.conversational_memory
    record = initiatives(memory)[0]
    assert not history_eligible(record)
    assert [m.role for m in memory.get_conversation_history(conversation)] == ['user']
    assert [m['role'] for m in memory.get_recent_history(user_id='synthetic')] == ['user']
    assert memory.vector_engine.count() == 1
    core.output_callback.return_value = True
    assert core.check_proactive_trigger()['status'] == 'delivered'
    assert history_eligible(record)
    assert [m.role for m in memory.get_conversation_history(conversation)] == ['user', 'assistant']
    assert memory.vector_engine.count() == 2


def test_pending_delivery_yields_to_a_user_turn(initiative):
    core, _, _ = initiative
    core.output_callback.return_value = False
    assert core.check_proactive_trigger()['status'] == 'delivery_pending'
    core.output_callback.reset_mock()
    core._proactive_cancel.set()
    with core._turn_lock:
        assert core.check_proactive_trigger()['status'] == 'busy'
    assert core._proactive_cancel.is_set()
    core.output_callback.assert_not_called()


@pytest.fixture
def ui_handler():
    import ast
    from pathlib import Path
    path = Path(__file__).resolve().parents[2]/'allma_model/ui/chat_view.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_handle_core_output')
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(path), 'exec'), namespace)
    return namespace['_handle_core_output']


def test_ui_repeated_ack_does_not_duplicate_message_or_notification(ui_handler):
    view = SimpleNamespace(bridge=Mock(webview=object()), conversation_id='c')
    event = {'type': 'proactive', 'content': 'Messaggio salvato.', 'user_id': 'user_default',
             'conversation_id': 'c', 'request_id': 'PROACTIVE:'+'a'*32}
    assert ui_handler(view, event) is True
    assert ui_handler(view, event) is True
    view.bridge.send_message_to_js.assert_called_once()
    view.bridge.notify_event.assert_called_once()


def test_ui_never_inserts_into_another_conversation(ui_handler):
    view = SimpleNamespace(bridge=Mock(webview=object()), conversation_id='new-chat')
    event = {'type': 'proactive', 'content': 'Messaggio salvato.', 'user_id': 'user_default',
             'conversation_id': 'old-chat', 'request_id': 'PROACTIVE:'+'a'*32}
    assert ui_handler(view, event) is False
    view.bridge.send_message_to_js.assert_not_called()
    view.bridge.notify_event.assert_not_called()
