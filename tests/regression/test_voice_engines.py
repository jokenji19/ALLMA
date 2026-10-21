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
        pending = []
        @classmethod
        def schedule_once(cls, fn, delay=0):
            event = SimpleNamespace(fn=fn, delay=delay, cancelled=False)
            event.cancel = lambda: setattr(event, 'cancelled', True)
            if delay == 0: fn(0)
            else: cls.pending.append(event)
            return event
        @classmethod
        def advance(cls, seconds):
            pending, cls.pending = cls.pending, []
            for event in pending:
                if event.cancelled: continue
                event.delay -= seconds
                if event.delay <= 0: event.fn(0)
                else: cls.pending.append(event)
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
    return SimpleNamespace(stt=stt_engine, tts=tts_engine, recognizer=Recognizer, permission=permission, backend=tts, clock=Clock, classes=classes)


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


def result(text='Parole di prova'):
    matches = SimpleNamespace(size=lambda: 1, get=lambda _: text)
    return SimpleNamespace(getStringArrayList=lambda _: matches)


def test_thirty_successful_turns_reuse_one_connection_and_ignore_previous_listener(native):
    delivered=[]
    engine=native.stt.STTEngine(delivered.append)
    previous=None
    for i in range(30):
        assert engine.start_listening()
        if previous:
            previous.onError(11)
            previous.onResults(result('vecchio'))
        engine.listener.onReadyForSpeech(None)
        engine.listener.onResults(result(str(i)))
        previous=engine.listener
        engine.stop_listening(cancel=True)  # submit_message does this after final result
    assert delivered == [str(i) for i in range(30)]
    assert len(native.recognizer.instances)==1
    assert engine.is_ready
    native.clock.advance(100)
    assert len(native.recognizer.instances)==1
    engine.close()
    assert not engine.is_ready


def test_disconnect_reconnects_once_then_reports_actual_error(native):
    delivered=[]; states=[]
    engine=native.stt.STTEngine(delivered.append,on_state=lambda *x:states.append(x))
    engine.start_listening(); stale=engine.listener
    stale.onError(11)
    assert not engine.is_ready and not engine.is_listening
    assert states[-1][0]=='starting'
    native.clock.advance(.7)
    assert len(native.recognizer.instances)==2
    stale.onResults(result('stale'))
    engine.listener.onError(11)
    assert engine.last_error_code==11 and states[-1][0]=='error'
    assert not engine.is_ready
    native.clock.advance(100)
    assert len(native.recognizer.instances)==2 and not delivered
    engine.start_listening()
    engine.listener.onReadyForSpeech(None)
    engine.listener.onResults(result())
    assert engine.is_ready and engine.last_error is None


@pytest.mark.parametrize('operation',['cancel','close','configure'])
def test_pending_reconnect_cannot_reopen_microphone_after_exit(native,operation):
    engine=native.stt.STTEngine(Mock())
    engine.start_listening();engine.listener.onError(11)
    if operation=='cancel': engine.stop_listening(cancel=True)
    elif operation=='close': engine.close()
    else: engine.configure('en-US')
    native.clock.advance(100)
    assert len(native.recognizer.instances)==1
    assert not engine.is_listening


@pytest.mark.parametrize('code',[3,6,7,9,10,12,13])
def test_non_transient_errors_do_not_retry(native,code):
    engine=native.stt.STTEngine(Mock())
    engine.start_listening();engine.listener.onError(code)
    native.clock.advance(100)
    assert len(native.recognizer.instances)==1
    assert engine.last_error_code==code and not engine.is_ready


def test_watchdog_handles_service_that_never_responds(native):
    engine=native.stt.STTEngine(Mock())
    engine.start_listening();native.clock.advance(10)
    assert engine.last_error_code == -1
    assert not engine.is_listening and not engine._requested
    assert native.recognizer.instances[0].destroy.called


def test_end_of_speech_watchdog_and_late_result(native):
    final=Mock();engine=native.stt.STTEngine(final)
    engine.start_listening();listener=engine.listener
    listener.onReadyForSpeech(None);listener.onEndOfSpeech()
    native.clock.advance(12)
    listener.onResults(result())
    final.assert_not_called()
    assert not engine._requested


def test_manual_language_is_sent_to_recognizer(native):
    engine=native.stt.STTEngine(Mock(),language='de-DE')
    engine.start_listening()
    intent=native.recognizer.instances[0].startListening.call_args.args[0]
    assert any(c.args==('EXTRA_LANGUAGE','de-DE') for c in intent.putExtra.call_args_list)


def test_language_detection_accepts_actual_bcp47_and_discards_stale_callbacks(native):
    languages=[];engine=native.stt.STTEngine(Mock(),language='auto',on_language=languages.append)
    engine.start_listening();old=engine.listener
    old.onLanguageDetection(SimpleNamespace(getString=lambda _: 'pt-BR'))
    assert languages==['pt-BR'] and engine.detected_language=='pt-BR'
    engine.stop_listening(cancel=True)
    old.onLanguageDetection(SimpleNamespace(getString=lambda _: 'fr-FR'))
    assert languages==['pt-BR']


def test_local_unavailable_requires_explicit_service_opt_in(native):
    native.recognizer.available=False
    engine=native.stt.STTEngine(Mock())
    engine.start_listening()
    assert engine.last_error and not native.recognizer.instances


def test_tts_error_clears_after_successful_new_playback(native):
    engine=native.tts.TTSEngine();engine.listener.onInit(0)
    engine.speak('Primo');engine.events.onError(next(iter(engine._ids)),-1)
    assert engine.last_error
    assert engine.speak('Secondo')
    assert engine.last_error is None


def test_tts_keeps_portuguese_instead_of_falling_back_to_italian(native):
    engine=native.tts.TTSEngine();engine.listener.onInit(0)
    engine.speak('Olá',{'language':'pt-BR'})
    assert engine.language=='pt-BR'


def test_natural_voice_loads_java_on_ui_but_verifies_assets_off_ui(native,monkeypatch):
    import threading
    active={'ui':False}
    class Thread:
        def __init__(self,target,**kwargs):self.target=target
        def start(self):self.target()
    monkeypatch.setattr(threading,'Thread',Thread)
    backend=Mock()
    def create():
        assert active['ui'], 'Application JNI classes must load on Android UI thread'
        return backend
    native.classes['org.allma.voice.KokoroVoice']=create
    engine=native.tts.TTSEngine()
    def ui(fn):
        active['ui']=True
        try:fn()
        finally:active['ui']=False
    engine._ui=ui
    def verify():
        assert not active['ui'], 'Large model hashing must stay off UI thread'
        return '/verified/voice'
    engine.voice_pack=SimpleNamespace(verify=verify)
    engine.voice_choice='if_sara'
    assert engine.speak('Frase sintetica',{'language':'it-IT'})
    assert engine._natural is backend
    request=backend.speak.call_args.args[-2]
    assert backend.speak.call_args.args[2]==35
    engine._natural_events.onState(request,'speaking',1200,'Audio')
    assert engine.is_speaking
    engine.stop()
    engine._natural_events.onState(request,'speaking',1500,'Late')
    assert not engine.is_speaking
    engine.close()
    backend.close.assert_called_once()


def test_language_inventory_rejects_missing_local_model_without_recording(native):
    import json
    support=Mock()
    native.classes['org.allma.voice.SpeechSupport']=support
    engine=native.stt.STTEngine(Mock(),language='en-US')
    engine.start_listening()
    native.recognizer.instances[-1].startListening.assert_not_called()
    callback=support.check.call_args.args[-1]
    callback.onSupport(json.dumps({'installed':['it-IT'],'supported':['it-IT','en-US'],'pending':[]}))
    assert engine.last_error_code==13
    native.recognizer.instances[-1].startListening.assert_not_called()


def test_unsupported_inventory_still_allows_native_recognition(native):
    support=Mock();native.classes['org.allma.voice.SpeechSupport']=support
    engine=native.stt.STTEngine(Mock(),language='en-US')
    engine.start_listening()
    support.check.call_args.args[-1].onUnavailable(14)
    native.recognizer.instances[-1].startListening.assert_called_once()
    assert not engine.support['checked']


def test_language_inventory_timeout_does_not_start_twice(native):
    import json
    support=Mock();native.classes['org.allma.voice.SpeechSupport']=support
    engine=native.stt.STTEngine(Mock())
    engine.start_listening()
    callback=support.check.call_args.args[-1]
    native.clock.advance(2.5)
    callback.onSupport(json.dumps({'installed':['it-IT'],'supported':['it-IT'],'pending':[]}))
    native.recognizer.instances[-1].startListening.assert_called_once()


def test_repeated_tts_close_releases_native_helpers_once(native):
    engine=native.tts.TTSEngine()
    natural=Mock();engine._natural=natural
    engine.close();engine.close()
    natural.close.assert_called_once()
    native.backend.shutdown.assert_called_once()


def test_cancel_at_natural_handoff_cannot_enqueue_late_audio(native,monkeypatch):
    import threading
    class InlineThread:
        def __init__(self,target,**kwargs):self.target=target
        def start(self):self.target()
    monkeypatch.setattr(threading,'Thread',InlineThread)
    engine=native.tts.TTSEngine()
    backend=Mock();engine._natural=backend
    engine.voice_choice='if_sara'
    armed=[False]
    guard=threading.RLock()
    class CancelAtHandoff:
        def __enter__(self):
            guard.acquire()
            if armed[0]:
                armed[0]=False
                engine.stop()
            return self
        def __exit__(self,*args):guard.release()
    engine._delivery_lock=CancelAtHandoff()
    def verify():
        armed[0]=True
        return '/verified/voice'
    engine.voice_pack=SimpleNamespace(verify=verify)
    engine.speak('Frase sintetica',{'language':'it-IT'})
    backend.speak.assert_not_called()


def test_delayed_android_stop_cannot_stop_a_newer_utterance(native):
    engine=native.tts.TTSEngine();engine.listener.onInit(0)
    pending=[];engine._ui=pending.append
    engine.stop();older_stop=pending.pop()
    engine.speak('Un nuovo messaggio')
    for action in pending:action()
    before=native.backend.stop.call_count
    older_stop()
    assert native.backend.stop.call_count==before
    native.backend.speak.assert_called_once()


def test_numbered_headings_are_not_isolated_neural_speech_sentences():
    assert spoken_text('1. Prima idea.\n2) Seconda idea.')=='1: Prima idea. 2: Seconda idea.'
    assert spoken_text('Il valore è 3.14. La versione è 1.2.3.')=='Il valore è 3.14. La versione è 1.2.3.'
