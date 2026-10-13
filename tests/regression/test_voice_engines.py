import sys
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock
import pytest
from allma_model.voice_system.speech_text import spoken_text, speech_chunks


def test_speech_text_removes_internal_blocks_code_links_and_markup():
    source = '<think>Do not say this</think>\n## Saluto\n**Ciao** [Erika](https://example.org)!\n```python\nsecret()\n```\n[[TH: private]]'
    result = spoken_text(source)
    assert 'Ciao Erika!' in result
    assert not any(s in result for s in ('secret', 'private', 'Do not', 'http', '**'))
    assert spoken_text('<think>unfinished private text') == ''
    assert spoken_text('Ciao <think>unfinished private text') == 'Ciao'


def test_long_text_chunks_respect_native_limit_without_losing_words():
    text = 'Prima frase. Seconda frase molto lunga. ' * 50
    chunks = speech_chunks(text.strip(), 65)
    assert all(0 < len(c) <= 65 for c in chunks)
    assert ' '.join(chunks) == text.strip()
    assert ''.join(speech_chunks('a'*100, 20)) == 'a'*100


@pytest.fixture
def native(monkeypatch):
    def java_method(signature):
        def decorate(fn):
            fn.signature = signature
            return fn
        return decorate
    class Clock:
        @staticmethod
        def schedule_once(fn, delay=0): fn(0)
    class Recognizer:
        RESULTS_RECOGNITION = 'matches'
        available = True
        instances = []
        @classmethod
        def isOnDeviceRecognitionAvailable(cls, activity): return cls.available
        @classmethod
        def isRecognitionAvailable(cls, activity): return cls.available
        @classmethod
        def createOnDeviceSpeechRecognizer(cls, activity):
            result = Mock()
            cls.instances.append(result)
            return result
        createSpeechRecognizer = createOnDeviceSpeechRecognizer
    RI = SimpleNamespace(**{name:name for name in ('ACTION_RECOGNIZE_SPEECH','EXTRA_LANGUAGE_MODEL','LANGUAGE_MODEL_FREE_FORM','EXTRA_LANGUAGE','EXTRA_PARTIAL_RESULTS','EXTRA_MAX_RESULTS','EXTRA_PREFER_OFFLINE')})
    permission = SimpleNamespace(granted=True, callbacks=[])
    def request(permissions, callback): permission.callbacks.append(callback)
    permissions = ModuleType('android.permissions')
    permissions.Permission = SimpleNamespace(RECORD_AUDIO='mic')
    permissions.check_permission = lambda _: permission.granted
    permissions.request_permissions = request
    runnable = ModuleType('android.runnable')
    runnable.run_on_ui_thread = lambda fn: fn
    class Locale:
        @staticmethod
        def forLanguageTag(tag): return SimpleNamespace(getLanguage=lambda:tag.split('-')[0])
    tts = Mock()
    tts.setLanguage.return_value = 0
    tts.getVoices.return_value = None
    tts.getVoice.return_value = None
    tts.getMaxSpeechInputLength.return_value = 100
    tts.speak.return_value = 0
    classes = {'org.kivy.android.PythonActivity':SimpleNamespace(mActivity=Mock()),
               'android.speech.SpeechRecognizer':Recognizer, 'android.os.Build$VERSION':SimpleNamespace(SDK_INT=34),
               'android.content.Intent':lambda _:Mock(), 'android.speech.RecognizerIntent':RI,
               'org.allma.voice.TtsProgressListener':lambda events:events,
               'android.speech.tts.TextToSpeech':lambda *args:tts,
               'java.util.Locale':Locale,'android.os.Bundle':dict,
               'java.lang.String':lambda text:SimpleNamespace(text=text)}
    jnius = ModuleType('jnius')
    jnius.PythonJavaClass = object
    jnius.java_method = java_method
    jnius.autoclass = lambda name:classes[name]
    jnius.cast = lambda name,value:value
    for name,module in [('android',ModuleType('android')),('android.permissions',permissions),('android.runnable',runnable),('jnius',jnius)]:
        monkeypatch.setitem(sys.modules,name,module)
    from allma_model.voice_system import stt_engine, tts_engine
    for module in (stt_engine,tts_engine):
        monkeypatch.setattr(module,'platform','android')
        monkeypatch.setattr(module,'Clock',Clock)
    return SimpleNamespace(stt=stt_engine, tts=tts_engine, recognizer=Recognizer, permission=permission, backend=tts)


def test_permission_is_requested_once_and_denial_does_not_retry(native):
    native.permission.granted=False
    states=[]
    engine=native.stt.STTEngine(Mock(),on_state=lambda *args:states.append(args))
    engine.start_listening()
    engine.start_listening()
    assert len(native.permission.callbacks)==1
    native.permission.callbacks[0](['mic'],[False])
    assert not engine.is_listening and engine.last_error
    assert not native.recognizer.instances
    assert states[-1][0]=='error'


def test_granted_permission_starts_once_and_late_result_after_cancel_is_ignored(native):
    native.permission.granted=False
    final=Mock()
    engine=native.stt.STTEngine(final)
    engine.start_listening()
    native.permission.callbacks[0](['mic'],[True])
    assert engine.is_listening and engine.on_device
    listener=engine.listener
    assert listener.onBufferReceived.signature=='([B)V'
    engine.stop_listening(cancel=True)
    matches=SimpleNamespace(size=lambda:1,get=lambda _: 'late words')
    listener.onResults(SimpleNamespace(getStringArrayList=lambda _:matches))
    final.assert_not_called()
    engine.close()
    native.recognizer.instances[-1].destroy.assert_called()


def test_tts_pending_language_chunking_completion_and_late_callback(native):
    states=[]
    engine=native.tts.TTSEngine(on_state=lambda *args:states.append(args))
    assert engine.speak('**Ciao** '+('frase. '*40))
    native.backend.speak.assert_not_called()
    engine.listener.onInit(0)
    assert engine.is_ready
    native.backend.setLanguage.assert_called()
    assert native.backend.speak.call_count>1
    assert native.backend.speak.call_args.args[0].text
    identifiers=list(engine._ids)
    engine.events.onStart(identifiers[0])
    assert engine.is_speaking
    for identifier in identifiers: engine.events.onDone(identifier)
    assert not engine.is_speaking and states[-1][0]=='idle'
    engine.speak('Nuovo testo')
    old=list(engine._ids)[0]
    engine.stop()
    engine.events.onStart(old)
    assert not engine.is_speaking
    engine.close()
    native.backend.shutdown.assert_called_once()


def test_missing_language_is_reported(native):
    engine=native.tts.TTSEngine()
    native.backend.setLanguage.return_value=-1
    engine.listener.onInit(0)
    assert not engine.is_ready and engine.last_error
    assert not engine.speak('Ciao')


def test_playback_error_cancels_remaining_chunks(native):
    engine = native.tts.TTSEngine()
    engine.listener.onInit(0)
    engine.speak('frase. ' * 40)
    identifier = next(iter(engine._ids))
    engine.events.onError(identifier, -1)
    assert engine.last_error and not engine._ids and not engine.is_speaking
    native.backend.stop.assert_called()
    engine.events.onStart(identifier)
    assert not engine.is_speaking
