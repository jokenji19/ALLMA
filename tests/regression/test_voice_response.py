from allma_model.utils.voice_response import voice_token_limit


def test_voice_limits_preserve_complex_answers_and_stricter_thermal_budget():
    assert voice_token_limit(256, 'SIMPLE') == 192
    assert voice_token_limit(512, 'COMPLEX') == 512
    assert voice_token_limit(64, 'SIMPLE') == 64
    assert voice_token_limit(64, 'COMPLEX') == 64


def test_voice_delivery_is_captured_before_worker_and_close_prevents_playback():
    import ast
    from pathlib import Path
    from types import MethodType, SimpleNamespace
    from unittest.mock import Mock
    from allma_model.ui.chat_session import ChatSession
    from allma_model.utils.generation_control import GenerationCancelled, check_cancelled

    pending = []
    class Thread:
        def __init__(self, target, args, kwargs, daemon):
            self.run = lambda: target(*args, **kwargs)
        def start(self): pending.append(self)
    path = Path(__file__).resolve().parents[2] / 'allma_model/ui/chat_view.py'
    cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ChatView')
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('submit_message', 'process_message')]
    namespace = {'Thread': Thread, 'GenerationCancelled': GenerationCancelled, 'check_cancelled': check_cancelled}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    core = Mock()
    core.process_message.return_value = SimpleNamespace(content='Risposta valida.', voice_params={'rate':1.0})
    view = SimpleNamespace(core=core, bridge=Mock(), stt=Mock(), tts=Mock(),
                           chat_session=ChatSession(lambda:'chat'), voice_mode_enabled=True,
                           current_voice_params=None, _voice_state=Mock())
    for name in ('submit_message', 'process_message'):
        setattr(view, name, MethodType(namespace[name], view))
    assert view.submit_message('Spiega una cosa')
    view.voice_mode_enabled = False
    pending[0].run()
    assert core.process_message.call_args.kwargs['context'] == {'delivery_mode':'voice'}
    view.tts.speak.assert_not_called()
