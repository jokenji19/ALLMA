"""Bounded Android speech sessions with reuse, local languages and recovery."""
import logging
import time
from kivy.utils import platform
from kivy.clock import Clock
from .languages import language_tag

ERRORS = {1: 'La richiesta vocale è scaduta.', 2: 'Rete non disponibile per il riconoscimento.',
          3: 'Il microfono non è disponibile.', 4: 'Il servizio vocale non risponde.',
          5: 'La sessione vocale è stata interrotta.', 6: 'Non ho sentito una voce.',
          7: 'Non ho riconosciuto le parole. Riprova.', 8: 'Il servizio vocale è occupato.',
          9: 'Permesso microfono negato. Puoi abilitarlo nelle impostazioni di ALLMA.',
          10: 'Troppe richieste al servizio vocale. Attendi prima di riprovare.',
          11: 'Il servizio vocale si è disconnesso. Tocca il microfono per riprovare.',
          12: 'La lingua richiesta non è supportata dal servizio Android.',
          13: 'Scarica i dati vocali di questa lingua nelle impostazioni Android.'}


class STTEngine:
    def __init__(self, callback_text, callback_partial=None, on_state=None, on_level=None,
                 language='it-IT', on_language=None, allow_service_fallback=False):
        self.logger = logging.getLogger(__name__)
        self.callback_text, self.callback_partial = callback_text, callback_partial
        self.on_state, self.on_level, self.on_language = on_state, on_level, on_language
        self.language = language if language == 'auto' else language_tag(language)
        self.allow_service_fallback = allow_service_fallback
        self.speech_recognizer = self.listener = None
        self.is_listening = self.is_ready = self.permission_pending = self.on_device = False
        self.last_error = self.last_error_code = self.detected_language = None
        self.support = {'checked': False, 'installed': [], 'supported': [], 'pending': []}
        self._session = self._attempt = self._retries = 0
        self._closed = self._requested = self._stopping = False
        self._last_level_at = 0.0
        self._timer = self._retry_timer = self._support_timer = None
        self._support_listener = None
        if platform != 'android':
            self.last_error = 'Riconoscimento vocale disponibile su Android.'

    def _valid(self, session, attempt=None):
        return (not self._closed and self._requested and session == self._session
                and (attempt is None or attempt == self._attempt))

    def _state(self, state, message=''):
        if state != 'listening':
            self.logger.info('STT state=%s session=%s attempt=%s on_device=%s language=%s',
                             state, self._session, self._attempt, self.on_device, self.language)
        if self.on_state:
            session = self._session
            Clock.schedule_once(lambda dt: self.on_state(state, message)
                                if session == self._session and not self._closed else None, 0)

    def _cancel_timer(self, name):
        timer = getattr(self, name, None)
        if timer:
            timer.cancel()
        setattr(self, name, None)

    def _timeout(self, seconds, message, session, attempt):
        self._cancel_timer('_timer')
        self._timer = Clock.schedule_once(lambda dt: self._error(message, code=-1)
                                         if self._valid(session, attempt) else None, seconds)

    def _retire(self):
        """Called on Android's UI thread. Never destroy a subsequent session."""
        previous, self.speech_recognizer = self.speech_recognizer, None
        self.is_ready = False
        if previous:
            try:
                previous.cancel()
            except Exception:
                self.logger.warning('STT cancel unavailable')
            try:
                previous.destroy()
            except Exception:
                self.logger.warning('STT destroy unavailable')

    def _error(self, message, code=None):
        self._cancel_timer('_timer')
        self._cancel_timer('_support_timer')
        self.last_error, self.last_error_code = message, code
        self.is_listening = self.is_ready = False
        self.logger.warning('STT error_code=%s session=%s attempt=%s retry=%s on_device=%s language=%s',
                            code, self._session, self._attempt, self._retries, self.on_device, self.language)
        session = self._session
        # A lost/busy binding gets exactly one fresh connection, not a loop.
        retry = code in (8, 11) and self._retries == 0 and self._requested and not self._stopping and not self._closed
        self._attempt += 1  # invalidate callbacks from the failed listener immediately
        if platform == 'android':
            self._ui(self._retire)
        if retry:
            self._retries += 1
            self._state('starting', 'Ricollego il microfono…')
            self._retry_timer = Clock.schedule_once(lambda dt: self._start_android(session)
                                                   if self._valid(session) else None, .7)
        else:
            self._requested = False
            self._state('error', message)

    def _ui(self, function):
        from android.runnable import run_on_ui_thread
        run_on_ui_thread(function)()

    def configure(self, language, allow_service_fallback=False):
        language = language if language == 'auto' else language_tag(language)
        changed = (language, bool(allow_service_fallback)) != (self.language, self.allow_service_fallback)
        if changed:
            self.stop_listening(cancel=True)
            self.language, self.allow_service_fallback = language, bool(allow_service_fallback)
            self.detected_language = None
            self.support = {'checked': False, 'installed': [], 'supported': [], 'pending': []}
            if platform == 'android':
                self._ui(self._retire)

    def start_listening(self):
        if self._closed or self._requested:
            return False
        if platform != 'android':
            self._error(self.last_error)
            return False
        self._requested = True
        self._stopping = False
        self._session += 1
        self._retries = 0
        session = self._session
        self.last_error = self.last_error_code = None
        self.detected_language = None
        try:
            from android.permissions import request_permissions, Permission, check_permission
            if not check_permission(Permission.RECORD_AUDIO):
                self.permission_pending = True
                self._state('permission', 'Consenti l’uso del microfono per parlare.')
                def permission_result(permissions, grants):
                    if not self._valid(session): return
                    self.permission_pending = False
                    if grants and all(grants): self._start_android(session)
                    else: self._error(ERRORS[9], 9)
                def ask_permission():
                    if not self._valid(session): return
                    try:
                        request_permissions([Permission.RECORD_AUDIO], permission_result)
                    except Exception:
                        self.permission_pending = False
                        self._error('Impossibile richiedere il microfono.')
                self._ui(ask_permission)
            else:
                self._start_android(session)
            return True
        except Exception:
            self.logger.exception('STT start failed')
            self._error('Impossibile avviare il microfono.')
            return False

    def _start_android(self, session):
        def start():
            if not self._valid(session): return
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                recognizer = autoclass('android.speech.SpeechRecognizer')
                version = autoclass('android.os.Build$VERSION')
                engine = self
                self.on_device = version.SDK_INT >= 31 and recognizer.isOnDeviceRecognitionAvailable(activity)
                if not self.on_device and not self.allow_service_fallback:
                    self._error('Riconoscimento locale non disponibile. Puoi consentire il servizio Android nelle opzioni vocali.')
                    return
                if not self.on_device and not recognizer.isRecognitionAvailable(activity):
                    self._error('Nessun servizio di riconoscimento vocale disponibile su Android.')
                    return
                if self.speech_recognizer is None:
                    self.speech_recognizer = (recognizer.createOnDeviceSpeechRecognizer(activity) if self.on_device
                                              else recognizer.createSpeechRecognizer(activity))
                self._attempt += 1
                attempt = self._attempt
                class Listener(PythonJavaClass):
                    __javainterfaces__ = ['android/speech/RecognitionListener']
                    __javacontext__ = 'app'
                    def valid(self): return engine._valid(session, attempt)
                    @java_method('(I)V')
                    def onError(self, code):
                        if self.valid(): engine._error(ERRORS.get(code, f'Errore del riconoscimento vocale ({code}).'), int(code))
                    @java_method('(Landroid/os/Bundle;)V')
                    def onResults(self, result):
                        if not self.valid(): return
                        matches = result.getStringArrayList(recognizer.RESULTS_RECOGNITION)
                        if matches is None or matches.size() == 0:
                            engine._error(ERRORS[7], 7); return
                        text = str(matches.get(0)).strip()
                        if not text:
                            engine._error(ERRORS[7], 7); return
                        engine._cancel_timer('_timer')
                        engine.is_listening = engine._requested = False
                        engine.is_ready = True
                        engine.last_error = engine.last_error_code = None
                        engine._state('idle')
                        Clock.schedule_once(lambda dt: engine.callback_text(text)
                                            if session == engine._session and attempt == engine._attempt and not engine._closed else None, 0)
                    @java_method('(Landroid/os/Bundle;)V')
                    def onPartialResults(self, result):
                        if not self.valid(): return
                        matches = result.getStringArrayList(recognizer.RESULTS_RECOGNITION)
                        if matches is not None and matches.size() and engine.callback_partial:
                            text = str(matches.get(0))
                            Clock.schedule_once(lambda dt: engine.callback_partial(text) if self.valid() else None, 0)
                    @java_method('(Landroid/os/Bundle;)V')
                    def onLanguageDetection(self, result):
                        if not self.valid(): return
                        raw = result.getString('detected_language')
                        tag = language_tag(str(raw), fallback=None) if raw else None
                        if tag:
                            engine.detected_language = tag
                            if engine.on_language:
                                Clock.schedule_once(lambda dt: engine.on_language(tag)
                                                    if session == engine._session and not engine._closed else None, 0)
                    @java_method('(Landroid/os/Bundle;)V')
                    def onReadyForSpeech(self, params):
                        if self.valid():
                            engine.last_error = engine.last_error_code = None
                            engine.is_ready = True
                            engine._timeout(60, 'Il turno vocale è scaduto. Tocca il microfono per riprovare.', session, attempt)
                            engine._state('listening', 'Ti ascolto…')
                    @java_method('()V')
                    def onBeginningOfSpeech(self):
                        if self.valid(): engine._state('listening', 'Ti ascolto…')
                    @java_method('()V')
                    def onEndOfSpeech(self):
                        if self.valid():
                            engine._timeout(12, 'La trascrizione non è arrivata. Tocca il microfono per riprovare.', session, attempt)
                            engine._state('recognizing', 'Trascrivo…')
                    @java_method('([B)V')
                    def onBufferReceived(self, buffer): pass
                    @java_method('(F)V')
                    def onRmsChanged(self, value):
                        if self.valid() and engine.on_level:
                            now = time.monotonic()
                            if now - engine._last_level_at < .05: return
                            engine._last_level_at = now
                            level = max(0.0, min(1.0, (float(value) + 2.0) / 12.0))
                            Clock.schedule_once(lambda dt: engine.on_level(level) if self.valid() else None, 0)
                    @java_method('(ILandroid/os/Bundle;)V')
                    def onEvent(self, kind, params): pass
                self.listener = Listener()
                self.speech_recognizer.setRecognitionListener(self.listener)
                Intent = autoclass('android.content.Intent')
                RI = autoclass('android.speech.RecognizerIntent')
                intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
                tag = self.language if self.language != 'auto' else 'it-IT'
                intent.putExtra(RI.EXTRA_LANGUAGE, tag)
                intent.putExtra(RI.EXTRA_PARTIAL_RESULTS, True)
                intent.putExtra(RI.EXTRA_MAX_RESULTS, 1)
                intent.putExtra(RI.EXTRA_PREFER_OFFLINE, True)
                launched = [False]
                def listen():
                    if launched[0] or not self._valid(session, attempt): return
                    launched[0] = True
                    self._cancel_timer('_support_timer')
                    if self.language == 'auto' and version.SDK_INT >= 34:
                        installed = self.support['installed']
                        if installed:
                            intent.putExtra(RI.EXTRA_LANGUAGE, installed[0])
                            ArrayList = autoclass('java.util.ArrayList')
                            allowed = ArrayList()
                            for lang in installed: allowed.add(lang)
                            intent.putStringArrayListExtra('android.speech.extra.LANGUAGE_DETECTION_ALLOWED_LANGUAGES', allowed)
                            intent.putStringArrayListExtra('android.speech.extra.LANGUAGE_SWITCH_ALLOWED_LANGUAGES', allowed)
                        intent.putExtra('android.speech.extra.ENABLE_LANGUAGE_DETECTION', True)
                        intent.putExtra('android.speech.extra.ENABLE_LANGUAGE_SWITCH', 'balanced')
                    elif self.language == 'auto':
                        self._state('starting', 'Lingua automatica non disponibile: uso Italiano. Scegli una lingua per cambiarla.')
                    if self.on_device and self.support['checked'] and self.language != 'auto':
                        installed, supported = self.support['installed'], self.support['supported']
                        if supported and tag not in installed and not any(x.split('-')[0] == tag.split('-')[0] for x in installed):
                            self._error(ERRORS[13] if any(x.split('-')[0] == tag.split('-')[0] for x in supported) else ERRORS[12],
                                        13 if any(x.split('-')[0] == tag.split('-')[0] for x in supported) else 12)
                            return
                    self.is_listening = True
                    self._state('starting', 'Avvio il microfono…')
                    self._timeout(10, 'Il microfono non ha risposto. Tocca per riprovare.', session, attempt)
                    self.speech_recognizer.startListening(intent)
                if version.SDK_INT >= 33 and not self.support['checked']:
                    try:
                        class Support(PythonJavaClass):
                            __javainterfaces__ = ['org/allma/voice/SpeechSupport$Events']
                            __javacontext__ = 'app'
                            @java_method('(Ljava/lang/String;)V')
                            def onSupport(self, payload):
                                if not engine._valid(session, attempt): return
                                import json
                                data = json.loads(str(payload))
                                engine.support = {key: data.get(key, []) for key in ('installed', 'supported', 'pending')}
                                engine.support['checked'] = True
                                engine.logger.info('STT language_support installed=%s supported=%s', len(engine.support['installed']), len(engine.support['supported']))
                                listen()
                            @java_method('(I)V')
                            def onUnavailable(self, code):
                                if not engine._valid(session, attempt): return
                                engine.logger.info('STT language_support unavailable_code=%s', code)
                                listen()
                        self._support_listener = Support()
                        self._support_timer = Clock.schedule_once(lambda dt: self._ui(listen), 2.5)
                        autoclass('org.allma.voice.SpeechSupport').check(activity, self.speech_recognizer, intent, self._support_listener)
                    except Exception:
                        listen()
                else:
                    listen()
            except Exception:
                self.logger.exception('STT initialization failed')
                self._error('Il riconoscimento vocale non è disponibile.')
        self._ui(start)

    def stop_listening(self, cancel=False):
        active = self._requested
        self.is_listening = False
        if cancel:
            self._session += 1
            self._attempt += 1
            self._requested = self.permission_pending = False
            for name in ('_timer', '_retry_timer', '_support_timer'): self._cancel_timer(name)
        else:
            self._stopping = True
            if active: self._timeout(12, 'La trascrizione non è arrivata. Tocca per riprovare.', self._session, self._attempt)
        if platform == 'android':
            # Capture ownership now: a delayed UI stop must not stop the next mic.
            owned = self.speech_recognizer
            def stop():
                if owned is not self.speech_recognizer: return
                if cancel and active: self._retire()
                elif owned and not cancel: owned.stopListening()
            self._ui(stop)
        self._state('idle' if cancel else 'recognizing')

    def close(self):
        self._closed = True
        self.stop_listening(cancel=True)
        if platform == 'android': self._ui(self._retire)
        self.is_ready = False
