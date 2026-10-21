"""Integration: real ALLMA core/archive/UI methods, simulated Android I/O/model.

The tests do not claim physical microphone, natural inference or audible quality.
They join the production STT callback, turn ownership, cognitive core, persistence,
streaming and native TTS dispatch instead of testing these modules in isolation.
"""
import ast
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import pytest
from tests.regression.test_exact_text_core import core
from tests.regression.test_voice_engines import native, result
from allma_model.ui.chat_session import ChatSession
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def flow(core,native):
    pending=[]
    class Thread:
        def __init__(self,target,args=(),kwargs=None,**options):
            self.run=lambda:target(*args,**(kwargs or {}))
        def start(self):pending.append(self)
    tree=ast.parse((ROOT/'allma_model/ui/chat_view.py').read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ChatView')
    names={'submit_message','process_message','set_voice_mode','toggle_voice_listening',
           'suspend_voice','_on_voice_language','_on_stt_state','_on_tts_state','_voice_state'}
    methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace={'Thread':Thread,'GenerationCancelled':GenerationCancelled,'check_cancelled':check_cancelled}
    exec(compile(ast.Module(body=methods,type_ignores=[]),str(ROOT/'allma_model/ui/chat_view.py'),'exec'),namespace)
    view=SimpleNamespace(core=core,bridge=Mock(),chat_session=ChatSession(lambda:core.start_conversation('user_default')),
                         voice_mode_enabled=True,current_voice_params=None,_report_voice_stack_status=Mock(),
                         voice_preferences=SimpleNamespace(options={'language':'it-IT','voice':'android','allow_service_fallback':False}))
    for name in names:setattr(view,name,MethodType(namespace[name],view))
    # Compile the exact nested production callback with its existing self closure.
    callback=next(n for n in ast.walk(cls) if isinstance(n,ast.FunctionDef) and n.name=='on_stt_text')
    callback_env={'self':view}
    exec(compile(ast.Module(body=[callback],type_ignores=[]),str(ROOT/'allma_model/ui/chat_view.py'),'exec'),callback_env)
    view.stt=native.stt.STTEngine(callback_env['on_stt_text'],on_state=view._on_stt_state,on_language=view._on_voice_language)
    view.tts=native.tts.TTSEngine(on_state=view._on_tts_state)
    view.tts.listener.onInit(0)
    def recognized(text,run=True):
        assert view.stt.start_listening()
        view.stt.listener.onReadyForSpeech(None)
        view.stt.listener.onResults(result(text))
        assert len(pending)==1
        if run:pending.pop().run()
    def finish_audio():
        identifiers=list(view.tts._ids)
        assert identifiers
        view.tts.events.onStart(identifiers[0])
        assert view.tts.is_speaking
        for identifier in identifiers:view.tts.events.onDone(identifier)
        assert not view.tts.is_speaking
    def spoken():
        return ' '.join(call.args[0].text for call in native.backend.speak.call_args_list)
    fixture=SimpleNamespace(view=view,native=native,pending=pending,recognized=recognized,finish_audio=finish_audio,spoken=spoken,core=core)
    yield fixture
    view.suspend_voice(close=True)


def test_microphone_exact_tool_archive_and_native_speech_are_one_turn(flow):
    text='Quanto fa 18 + 24? Rispondi solo con un numero.'
    flow.recognized(text)
    assert flow.spoken()=='42'
    flow.core._llm.generate.assert_not_called()
    history=flow.core.conversational_memory.get_conversation_history(flow.view.chat_session.conversation_id)
    assert [(m.role,m.content) for m in history]==[('user',text),('assistant','42')]
    flow.finish_audio()
    assert not flow.view.chat_session.is_busy


def test_microphone_model_streaming_history_and_speech(flow):
    flow.core._llm.generate.return_value='La luce del Sole attraversa le gocce e si separa nei suoi colori.'
    flow.recognized('Spiegami perché si forma un arcobaleno.')
    flow.core._llm.generate.assert_called_once()
    assert 'gocce' in flow.spoken()
    assert flow.view.bridge.start_stream.called and flow.view.bridge.end_stream.called
    history=flow.core.conversational_memory.get_conversation_history(flow.view.chat_session.conversation_id)
    assert len(history)==2 and history[-1].content==flow.spoken()
    flow.finish_audio()


def test_second_voice_turn_recalls_first_from_real_memory_without_model(flow):
    flow.recognized('Il codice di prova è FARO-VOCE-37.')
    flow.finish_audio();flow.native.backend.speak.reset_mock()
    flow.recognized('Quale codice di prova ti avevo indicato?')
    assert 'FARO-VOCE-37' in flow.spoken()
    flow.core._llm.generate.assert_not_called()
    assert len(flow.native.recognizer.instances)==1
    flow.finish_audio()


def test_cancel_before_processing_never_calls_model_or_reads_an_answer(flow):
    flow.recognized('Raccontami una lunga storia inventata.',run=False)
    assert flow.view.chat_session.is_busy
    flow.view.toggle_voice_listening()
    flow.pending.pop().run()
    flow.core._llm.generate.assert_not_called()
    flow.native.backend.speak.assert_not_called()
    assert not flow.view.chat_session.is_busy


def test_background_cancels_pending_turn_and_resume_does_not_open_microphone(flow):
    tree=ast.parse((ROOT/'allma_model/ui/app_entry.py').read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AllmaInternalApp')
    methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('on_pause','on_resume')]
    env={};exec(compile(ast.Module(body=methods,type_ignores=[]),str(ROOT/'allma_model/ui/app_entry.py'),'exec'),env)
    app=SimpleNamespace(chat_screen=flow.view,_paused=False)
    flow.recognized('Raccontami una lunga storia inventata.',run=False)
    assert env['on_pause'](app)
    flow.pending.pop().run()
    env['on_resume'](app)
    assert not flow.view.voice_mode_enabled and not flow.view.stt.is_listening
    assert not flow.view.chat_session.is_busy
    flow.native.backend.speak.assert_not_called()


def test_language_of_recognition_reaches_conversation_and_native_speech(flow):
    flow.view.voice_preferences.options['language']='en-US'
    flow.view.stt.configure('en-US')
    flow.view.set_voice_mode(True)
    flow.view.stt.listener.onReadyForSpeech(None)
    flow.core._llm.generate.return_value='Sunlight separates into colours as it passes through water droplets.'
    flow.view.stt.listener.onResults(result('Explain how a rainbow forms.'))
    flow.pending.pop().run()
    assert flow.core._language_lock[flow.view.chat_session.conversation_id]=='en'
    assert flow.view.tts.language=='en-US'
    assert 'water droplets' in flow.spoken()
    flow.finish_audio()


def test_thirty_complete_voice_turns_do_not_duplicate_history_or_connections(flow):
    for index in range(30):
        flow.native.backend.speak.reset_mock()
        text=f'Quanto fa {index+20} + 2? Rispondi solo con un numero.'
        flow.recognized(text)
        assert flow.spoken()==str(index+22)
        flow.finish_audio()
        assert not flow.view.chat_session.is_busy
    history=flow.core.conversational_memory.get_conversation_history(flow.view.chat_session.conversation_id)
    assert len(history)==60
    assert len(flow.native.recognizer.instances)==1
    flow.core._llm.generate.assert_not_called()


def test_actual_speech_variant_uses_exact_tool_instead_of_conflicting_model(flow):
    flow.core._llm.generate.return_value='32.\n18 + 24 = 42.'
    flow.recognized('Quanto fa 18 + 24 rispondi con un solo numero')
    assert flow.spoken()=='42'
    flow.core._llm.generate.assert_not_called()
    flow.finish_audio()


def test_changed_subject_cannot_read_previous_arithmetic_as_explanation(flow):
    flow.recognized('Quanto fa 18 + 24 rispondi con un solo numero')
    flow.finish_audio();flow.native.backend.speak.reset_mock()
    flow.core._llm.generate.return_value='18 + 24 = 42'
    flow.recognized('spiegami perché si forma un arcobaleno in due fasi')
    assert '18 + 24 = 42' not in flow.spoken()
    history=flow.core.conversational_memory.get_conversation_history(flow.view.chat_session.conversation_id)
    assert history[-1].metadata.get('is_valid') is False


def test_changed_subject_can_still_deliver_a_valid_model_explanation(flow):
    flow.recognized('Quanto fa 18 + 24 rispondi con un solo numero')
    flow.finish_audio();flow.native.backend.speak.reset_mock()
    flow.core._llm.generate.return_value='La luce del Sole attraversa le gocce e si separa nei suoi colori.'
    flow.recognized('spiegami perché si forma un arcobaleno in due fasi')
    assert 'gocce' in flow.spoken()
    flow.finish_audio()


def test_cancel_while_model_is_running_never_queues_late_speech(flow):
    def interrupted_model(*args,**kwargs):
        flow.view.toggle_voice_listening()
        return 'Questa risposta tardiva non deve essere pronunciata.'
    flow.core._llm.generate.side_effect=interrupted_model
    flow.recognized('Descrivi una città immaginaria.')
    flow.core._llm.generate.assert_called_once()
    flow.native.backend.speak.assert_not_called()
    assert not flow.view.chat_session.is_busy
    history=flow.core.conversational_memory.get_conversation_history(flow.view.chat_session.conversation_id)
    assert not any(m.role=='assistant' and m.metadata.get('is_valid') for m in history)
