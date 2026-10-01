"""Execute the production UI methods headlessly, without creating a Kivy window."""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from allma_model.ui.chat_session import ChatSession
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled


def test_reset_cannot_overtake_a_queued_message():
    pending = []
    class DelayedThread:
        def __init__(self, target, args, kwargs, daemon):
            self.target, self.args, self.kwargs = target, args, kwargs
        def start(self):
            pending.append(self)
        def run(self):
            self.target(*self.args, **self.kwargs)
    path = Path(__file__).resolve().parents[2] / 'allma_model/ui/chat_view.py'
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ChatView')
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
               and node.name in ('submit_message', 'process_message')]
    namespace = {'Thread': DelayedThread, 'GenerationCancelled': GenerationCancelled,
                 'check_cancelled': check_cancelled}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    create = Mock(side_effect=['old-chat', 'new-chat'])
    view = SimpleNamespace(core=Mock(), bridge=Mock(), chat_session=ChatSession(create),
                           tts=None, current_voice_params=None, voice_mode_enabled=False)
    for name in ('submit_message', 'process_message'):
        setattr(view, name, MethodType(namespace[name], view))
    assert view.submit_message('Primo messaggio')
    assert not view.submit_message('Invio simultaneo')
    assert view.chat_session.new_conversation() is None
    assert view.chat_session.conversation_id == 'old-chat'
    pending[0].run()
    view.core.process_message.assert_not_called()
    assert view.chat_session.conversation_id == 'new-chat'
    view.bridge.end_stream.assert_called_once_with('Risposta interrotta.', 1)
    view.bridge.call_js_function.assert_any_call('newChatReady', '"new-chat"')
    assert view.submit_message('Messaggio nella nuova chat')
