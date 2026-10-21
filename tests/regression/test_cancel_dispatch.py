"""Exercise the actual WebView action branch without loading Kivy."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from allma_model.ui.chat_session import ChatSession


def handler():
    path=Path(__file__).resolve().parents[2]/'allma_model/ui/chat_view.py'
    tree=ast.parse(path.read_text())
    branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If)
                and "action in ('new_chat', 'cancel_generation')" in ast.unparse(n.test))
    wrapper=ast.parse('def dispatch(self, data, action, msg_type="action"):\n pass').body[0]
    wrapper.body=[branch]
    namespace={'json':json}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[])),str(path),'exec'),namespace)
    return namespace['dispatch']


def test_stale_or_missing_cancel_cannot_stop_current_turn_or_audio():
    dispatch=handler();chat=ChatSession(lambda:'c')
    old=chat.begin();chat.finish(old);current=chat.begin()
    view=SimpleNamespace(chat_session=chat,stt=Mock(),tts=Mock())
    for data in ({},{'request_id':True},{'request_id':old.request_id}):
        dispatch(view,data,'cancel_generation')
        assert not current.cancelled.is_set()
    view.stt.stop_listening.assert_not_called();view.tts.stop.assert_not_called()
    dispatch(view,{'request_id':current.request_id},'cancel_generation')
    assert current.cancelled.is_set()
    view.tts.stop.assert_called_once();view.stt.stop_listening.assert_called_once_with(cancel=True)
    dispatch(view,{'request_id':current.request_id},'cancel_generation')
    view.tts.stop.assert_called_once()


def test_new_chat_still_cancels_and_waits_for_current_worker():
    dispatch=handler();chat=ChatSession(lambda:'c');turn=chat.begin()
    view=SimpleNamespace(chat_session=chat,stt=Mock(),tts=Mock(),bridge=Mock())
    dispatch(view,{},'new_chat')
    assert turn.cancelled.is_set()
    assert chat.is_busy
    view.bridge.call_js_function.assert_not_called()
