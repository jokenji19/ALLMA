"""Run the real WebView action callback without initializing Kivy or a model."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest


def callback(core):
    path = Path(__file__).resolve().parents[2] / 'allma_model/ui/chat_view.py'
    tree = ast.parse(path.read_text())
    node = next(item for item in ast.walk(tree) if isinstance(item, ast.FunctionDef)
                and item.name == 'on_js_message')
    bridge = Mock()
    view = SimpleNamespace(core=core, bridge=bridge)
    namespace = {'self': view}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['on_js_message'], bridge


def result(bridge):
    source = bridge.execute_js.call_args.args[0]
    return json.loads(source.removeprefix('window.dreamReviewResult(').removesuffix(')'))


def message(**extra):
    return json.dumps({'type': 'action', 'action': 'review_dream_hypothesis',
                       'id': 'sample', 'decision': 'correct', 'revision': 3,
                       'correction': 'Una correzione 🌊', 'note': 'Giudizio personale',
                       'user_id': 'other-user', **extra})


def test_bridge_pins_session_user_and_acknowledges_only_after_store_success():
    core = Mock()
    order = []
    core.review_dream_hypothesis.side_effect = lambda *args, **kwargs: order.append('save')
    core.get_dream_review_state.side_effect = lambda user: order.append('refresh') or {'items': [], 'version': 4}
    send, bridge = callback(core)
    send(message())
    core.review_dream_hypothesis.assert_called_once_with('user_default', 'sample', 'correct',
        correction='Una correzione 🌊', note='Giudizio personale', expected_revision=3)
    core.get_dream_review_state.assert_called_once_with('user_default')
    assert order == ['save', 'refresh']
    assert result(bridge) == {'ok': True, 'reviewed_id': 'sample', 'items': [], 'version': 4}


@pytest.mark.parametrize('error, expected', [(ValueError('Attendi la fine della risposta'), 'Attendi la fine della risposta'),
    (RuntimeError('private internal details'), 'Non è stato possibile salvare. Riprova.')])
def test_bridge_failure_is_not_success_and_refreshes_revision(error, expected):
    core = Mock()
    core.review_dream_hypothesis.side_effect = error
    core.get_dream_review_state.return_value = {'items': [{'id': 'sample', 'revision': 5}]}
    send, bridge = callback(core)
    send(message())
    payload = result(bridge)
    assert payload['ok'] is False and payload['error'] == expected
    assert payload['items'][0]['revision'] == 5
    assert 'private internal details' not in json.dumps(payload)


def test_archive_failure_returns_recoverable_error_without_fake_state():
    core = Mock()
    core.review_dream_hypothesis.side_effect = RuntimeError('disk unavailable')
    core.get_dream_review_state.side_effect = RuntimeError('disk unavailable')
    send, bridge = callback(core)
    send(message())
    assert result(bridge) == {'ok': False, 'error': 'Non è stato possibile salvare. Riprova.'}


def test_bridge_handles_commit_succeeded_but_refresh_failed_without_false_ack():
    core = Mock()
    core.get_dream_review_state.side_effect = [RuntimeError('read failed'), {'items': []}]
    send, bridge = callback(core)
    send(message())
    assert result(bridge)['ok'] is False
    assert result(bridge)['items'] == []
    core.review_dream_hypothesis.assert_called_once()


def test_review_payload_text_is_json_encoded_not_executable_javascript():
    text = '\"); window.attack = true; //\n<script>alert(1)</script>'
    core = Mock()
    core.get_dream_review_state.return_value = {'items': [{'text': text}]}
    send, bridge = callback(core)
    send(message())
    assert result(bridge)['items'][0]['text'] == text
    assert bridge.execute_js.call_count == 1
