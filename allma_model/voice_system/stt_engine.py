"""Android recognition with explicit permission, ownership and lifecycle handling."""
import logging
import time
from kivy.utils import platform
from kivy.clock import Clock

ERRORS = {1: 'La richiesta vocale è scaduta.', 2: 'Rete non disponibile per il riconoscimento.',
          3: 'Il microfono non è disponibile.', 4: 'Il servizio vocale non risponde.',
          5: 'La sessione vocale è stata interrotta.', 6: 'Non ho sentito una voce.',
          7: 'Non ho riconosciuto le parole. Riprova.', 8: 'Il servizio vocale è occupato.',
          9: 'Permesso microfono negato. Puoi abilitarlo nelle impostazioni di ALLMA.',
          10: 'Troppe richieste al servizio vocale.', 11: 'Il servizio vocale si è disconnesso.',
          12: 'La lingua richiesta non è supportata.', 13: 'Scarica i dati vocali della lingua nelle impostazioni Android.'}


class STTEngine:
    def __init__(self, callback_text, callback_partial=None, on_state=None, on_level=None, language='it-IT'):
        self.logger = logging.getLogger(__name__)
        self.callback_text, self.callback_partial = callback_text, callback_partial
        self.on_state, self.on_level = on_state, on_level
        self.language = language
        self.speech_recognizer = None
        self.listener = None
        self.is_listening = False
        self.is_ready = False
        self.permission_pending = False
        self.on_device = False
        self.last_error = None
        self._session = 0
        self._closed = False
        self._requested = False
        self._last_level_at = 0.0
        if platform != 'android':
            self.last_error = 'Riconoscimento vocale disponibile su Android.'

    def _state(self, state, message=''):
        if state != 'listening':
            self.logger.info('STT state=%s on_device=%s', state, self.on_device)
        if self.on_state:
            session = self._session
            Clock.schedule_once(lambda dt: self.on_state(state, message) if session == self._session and not self._closed else None, 0)

    def _error(self, message):
        self.last_error = message
        self.is_listening = False
        self._requested = False
        self._state('error', message)

    def start_listening(self):
        if self._closed or self._requested:
            return False
        if platform != 'android':
            self._error(self.last_error)
            return False
        self._requested = True
        self._session += 1
        session = self._session
        self.last_error = None
        try:
            from android.permissions import request_permissions, Permission, check_permission
            if not check_permission(Permission.RECORD_AUDIO):
                self.permission_pending = True
                self._state('permission', 'Consenti l’uso del microfono per parlare.')
                def permission_result(permissions, grants):
                    self.permission_pending = False
                    if session != self._session or self._closed:
                        return
                    if grants and all(grants):
                        self._start_android(session)
                    else:
                        self._error(ERRORS[9])
                from android.runnable import run_on_ui_thread
                @run_on_ui_thread
                def ask_permission():
                    if session != self._session or self._closed:
                        return
                    try:
                        request_permissions([Permission.RECORD_AUDIO], permission_result)
                    except Exception as error:
                        self.permission_pending = False
                        self._error(f'Impossibile richiedere il microfono: {error}')
                ask_permission()
            else:
                self._start_android(session)
            return True
        except Exception as error:
            self.logger.exception('STT start failed')
            self._error(f'Impossibile avviare il microfono: {error}')
            return False

    def _start_android(self, session):
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def start():
            if session != self._session or self._closed or not self._requested:
                return
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                recognizer = autoclass('android.speech.SpeechRecognizer')
                version = autoclass('android.os.Build$VERSION')
                engine = self
                if self.speech_recognizer:
                    self.speech_recognizer.destroy()
                    self.speech_recognizer = None
                self.on_device = version.SDK_INT >= 31 and recognizer.isOnDeviceRecognitionAvailable(activity)
                if not self.on_device and not recognizer.isRecognitionAvailable(activity):
                    self.is_ready = False
                    self._error('Nessun servizio di riconoscimento vocale disponibile su Android.')
                    return

                class Listener(PythonJavaClass):
                    __javainterfaces__ = ['android/speech/RecognitionListener']
                    __javacontext__ = 'app'
                    def valid(self):
                        return session == engine._session and engine._requested and not engine._closed
                    @java_method('(I)V')
                    def onError(self, code):
                        if self.valid():
                            engine._error(ERRORS.get(code, f'Errore del riconoscimento vocale ({code}).'))
                    @java_method('(Landroid/os/Bundle;)V')
                    def onResults(self, result):
                        if not self.valid(): return
                        matches = result.getStringArrayList(recognizer.RESULTS_RECOGNITION)
                        engine.is_listening = False
                        engine._requested = False
                        if matches is None or matches.size() == 0:
                            engine._error(ERRORS[7])
                            return
                        text = str(matches.get(0)).strip()
                        if not text:
                            engine._error(ERRORS[7])
                            return
                        engine._state('idle')
                        def deliver(dt):
                            if session == engine._session and not engine._closed:
                                engine.callback_text(text)
                        Clock.schedule_once(deliver, 0)
                    @java_method('(Landroid/os/Bundle;)V')
                    def onPartialResults(self, result):
                        if not self.valid(): return
                        matches = result.getStringArrayList(recognizer.RESULTS_RECOGNITION)
                        if matches is not None and matches.size() and engine.callback_partial:
                            text = str(matches.get(0))
                            Clock.schedule_once(lambda dt: engine.callback_partial(text) if session == engine._session else None, 0)
                    @java_method('(Landroid/os/Bundle;)V')
                    def onReadyForSpeech(self, params):
                        if self.valid(): engine._state('listening', 'Ti ascolto…')
                    @java_method('()V')
                    def onBeginningOfSpeech(self):
                        if self.valid(): engine._state('listening', 'Ti ascolto…')
                    @java_method('()V')
                    def onEndOfSpeech(self):
                        if self.valid(): engine._state('recognizing', 'Trascrivo…')
                    @java_method('([B)V')
                    def onBufferReceived(self, buffer): pass
                    @java_method('(F)V')
                    def onRmsChanged(self, value):
                        if self.valid() and engine.on_level:
                            now = time.monotonic()
                            if now - engine._last_level_at < .05:
                                return
                            engine._last_level_at = now
                            level = max(0.0, min(1.0, (float(value) + 2.0) / 12.0))
                            Clock.schedule_once(lambda dt: engine.on_level(level) if session == engine._session else None, 0)
                    @java_method('(ILandroid/os/Bundle;)V')
                    def onEvent(self, kind, params): pass
                self.listener = Listener()
                self.speech_recognizer = (recognizer.createOnDeviceSpeechRecognizer(activity) if self.on_device
                                          else recognizer.createSpeechRecognizer(activity))
                self.speech_recognizer.setRecognitionListener(self.listener)
                Intent = autoclass('android.content.Intent')
                RI = autoclass('android.speech.RecognizerIntent')
                intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
                intent.putExtra(RI.EXTRA_LANGUAGE, self.language)
                intent.putExtra(RI.EXTRA_PARTIAL_RESULTS, True)
                intent.putExtra(RI.EXTRA_MAX_RESULTS, 1)
                intent.putExtra(RI.EXTRA_PREFER_OFFLINE, True)
                self.is_ready = True
                self.is_listening = True
                self._state('starting', 'Avvio il microfono…')
                self.speech_recognizer.startListening(intent)
            except Exception as error:
                self.is_ready = False
                self.logger.exception('STT initialization failed')
                self._error(f'Il riconoscimento vocale non è disponibile: {error}')
        start()

    def stop_listening(self, cancel=False):
        if cancel:
            self._session += 1
            self._requested = False
            self.permission_pending = False
        self.is_listening = False
        if platform == 'android':
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def stop():
                if self.speech_recognizer:
                    if cancel: self.speech_recognizer.cancel()
                    else: self.speech_recognizer.stopListening()
            stop()
        self._state('idle' if cancel else 'recognizing')

    def close(self):
        self._closed = True
        self.stop_listening(cancel=True)
        if platform == 'android':
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def destroy():
                if self.speech_recognizer:
                    self.speech_recognizer.destroy()
                    self.speech_recognizer = None
                self.is_ready = False
            destroy()
