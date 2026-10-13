"""Native TTS with real playback events, language checks and owned utterances."""
import logging
import subprocess
import uuid
from kivy.utils import platform
from kivy.clock import Clock
from .speech_text import spoken_text, speech_chunks


class TTSEngine:
    def __init__(self, on_state=None, language='it-IT'):
        self.logger = logging.getLogger(__name__)
        self.native_tts = None
        self.is_ready = False
        self.is_speaking = False
        self.last_error = None
        self.on_state = on_state
        self.language = language
        self.voice_name = None
        self._ids = set()
        self._pending = None
        self._closed = False
        self._process = None
        self._epoch = 0
        if platform == 'android':
            self._init_android_tts()
        elif platform == 'macosx':
            self.is_ready = True
        else:
            self.last_error = 'Sintesi vocale non disponibile su questa piattaforma.'

    def _state(self, state, message=''):
        self.logger.info('TTS state=%s', state)
        if self.on_state:
            epoch = self._epoch
            Clock.schedule_once(lambda dt: self.on_state(state, message) if epoch == self._epoch and not self._closed else None, 0)

    def _error(self, message):
        self.stop()
        self.last_error = message
        self.is_speaking = False
        self._ids.clear()
        self._state('error', message)

    def _ui(self, function):
        from android.runnable import run_on_ui_thread
        run_on_ui_thread(function)()

    def _init_android_tts(self):
        def initialize():
            if self._closed: return
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                engine = self
                class InitListener(PythonJavaClass):
                    __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
                    __javacontext__ = 'app'
                    @java_method('(I)V')
                    def onInit(self, status):
                        Clock.schedule_once(lambda dt: engine._on_initialized(status), 0)
                class Events(PythonJavaClass):
                    __javainterfaces__ = ['org/allma/voice/TtsProgressListener$Events']
                    __javacontext__ = 'app'
                    @java_method('(Ljava/lang/String;)V')
                    def onStart(self, identifier):
                        Clock.schedule_once(lambda dt: engine._progress('speaking', str(identifier)), 0)
                    @java_method('(Ljava/lang/String;)V')
                    def onDone(self, identifier):
                        Clock.schedule_once(lambda dt: engine._progress('done', str(identifier)), 0)
                    @java_method('(Ljava/lang/String;I)V')
                    def onError(self, identifier, code):
                        Clock.schedule_once(lambda dt: engine._progress('error', str(identifier), code), 0)
                self.listener = InitListener()
                self.events = Events()
                self.progress = autoclass('org.allma.voice.TtsProgressListener')(self.events)
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                self.native_tts = autoclass('android.speech.tts.TextToSpeech')(activity, self.listener)
            except Exception as error:
                self.logger.exception('TTS initialization failed')
                self._error(f'Impossibile inizializzare la voce: {error}')
        self._ui(initialize)

    def _on_initialized(self, status):
        if self._closed: return
        if status != 0:
            self._pending = None
            self._error('Il motore vocale Android non si è inizializzato.')
            return
        def configure():
            if self._closed: return
            try:
                self.native_tts.setOnUtteranceProgressListener(self.progress)
                if not self._set_language(self.language): return
                self.is_ready = True
                self._state('ready')
                pending, self._pending = self._pending, None
                if pending:
                    self.speak(*pending, flush=True)
            except Exception as error:
                self._error(f'Impossibile configurare la voce: {error}')
        self._ui(configure)

    def _set_language(self, tag):
        from jnius import autoclass
        locale = autoclass('java.util.Locale').forLanguageTag(tag)
        result = self.native_tts.setLanguage(locale)
        if result < 0:
            self._error('Voce non disponibile per questa lingua. Installa i dati vocali nelle impostazioni Android.')
            return False
        self.language = tag
        voices = self.native_tts.getVoices()
        candidates = []
        if voices is not None:
            for voice in voices.toArray():
                if str(voice.getLocale().getLanguage()) == str(locale.getLanguage()) and not voice.isNetworkConnectionRequired():
                    candidates.append(voice)
        if candidates:
            candidates.sort(key=lambda v: (-v.getQuality(), v.getLatency(), str(v.getName())))
            self.native_tts.setVoice(candidates[0])
        selected = self.native_tts.getVoice()
        self.voice_name = str(selected.getName()) if selected else None
        self.logger.info('TTS language=%s voice=%s', tag, self.voice_name)
        return True

    def _progress(self, state, identifier, code=None):
        if self._closed or identifier not in self._ids: return
        if state == 'error':
            self._error(f'La riproduzione vocale è fallita ({code}).')
        elif state == 'speaking':
            self.is_speaking = True
            self._state('speaking', 'Sto parlando…')
        else:
            self._ids.discard(identifier)
            if not self._ids:
                self.is_speaking = False
                self._state('idle', 'Tocca il microfono per parlare.')

    def speak(self, text, voice_params=None, flush=True):
        text = spoken_text(text)
        if self._closed or not text: return False
        params = dict(voice_params or {})
        if not self.is_ready:
            if self.last_error:
                self._state('error', self.last_error)
                return False
            self._pending = (text, params)
            self._state('starting', 'Preparo la voce…')
            return True
        if flush: self.stop()
        epoch = self._epoch
        if platform == 'android':
            def speak_native():
                if self._closed or epoch != self._epoch: return
                try:
                    from jnius import autoclass
                    language = params.get('language', self.language)
                    if language != self.language and not self._set_language(language): return
                    pitch = max(.9, min(1.1, float(params.get('pitch', 1.0))))
                    rate = max(.85, min(1.15, float(params.get('rate', 1.0))))
                    self.native_tts.setPitch(pitch)
                    self.native_tts.setSpeechRate(rate)
                    limit = min(3500, self.native_tts.getMaxSpeechInputLength() - 1)
                    chunks = speech_chunks(text, limit)
                    identifiers = [uuid.uuid4().hex for _ in chunks]
                    self._ids.update(identifiers)
                    Bundle = autoclass('android.os.Bundle')
                    JavaString = autoclass('java.lang.String')
                    for i, (chunk, identifier) in enumerate(zip(chunks, identifiers)):
                        # PyJNIus cannot resolve Python str as the CharSequence overload.
                        from jnius import cast
                        speech = cast('java.lang.CharSequence', JavaString(chunk))
                        result = self.native_tts.speak(speech, 0 if flush and i == 0 else 1, Bundle(), identifier)
                        if result != 0:
                            self.native_tts.stop()
                            self._error('Il motore vocale ha rifiutato la risposta.')
                            break
                except Exception as error:
                    self.logger.exception('TTS playback failed')
                    self._error(f'Impossibile leggere la risposta: {error}')
            self._ui(speak_native)
        elif platform == 'macosx':
            self._process = subprocess.Popen(['say', '--', text])
            self.is_speaking = True
            self._state('speaking')
            process = self._process
            def poll(dt):
                if self._closed or process is not self._process: return False
                if process.poll() is not None:
                    self.is_speaking = False
                    self._state('idle')
                    return False
            Clock.schedule_interval(poll, .2)
        else:
            return False
        return True

    def stop(self):
        self._epoch += 1
        self._pending = None
        self._ids.clear()
        self.is_speaking = False
        if self.native_tts:
            self._ui(lambda: self.native_tts.stop())
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self._process = None

    def close(self):
        self._closed = True
        self.stop()
        self.is_ready = False
        if self.native_tts:
            self._ui(lambda: self.native_tts.shutdown())
