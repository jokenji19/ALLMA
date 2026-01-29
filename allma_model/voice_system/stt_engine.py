import logging
from kivy.utils import platform
from kivy.clock import Clock

class STTEngine:
    """
    Handles Speech-to-Text using Android's native SpeechRecognizer.
    """
    def __init__(self, callback_text):
        self.logger = logging.getLogger(__name__)
        self.callback_text = callback_text # Function(text)
        self.speech_recognizer = None
        self.intent = None
        self.is_listening = False

        if platform == 'android':
            self._init_android_stt()

    def _init_android_stt(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android.permissions import request_permissions, Permission

            # Request Permissions first
            request_permissions([Permission.RECORD_AUDIO])

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            
            # Intent
            Intent = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')
            self.intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            # Optional: Set language to device default or specific
            # self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "it-IT")
            self.intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)

            # Listener
            class RecognitionListener(PythonJavaClass):
                __javainterfaces__ = ['android/speech/RecognitionListener']
                __javacontext__ = 'app'

                def __init__(self, engine):
                    super().__init__()
                    self.engine = engine

                @java_method('(I)V')
                def onError(self, error):
                    print(f"STT Error: {error}")
                    self.engine.is_listening = False
                    # error 7 = No match/Speech timeout, can ignore or retry

                @java_method('(Landroid/os/Bundle;)V')
                def onResults(self, results):
                    print("STT Results received")
                    matches = results.getStringArrayList(autoclass('android.speech.RecognizerIntent').EXTRA_RESULTS)
                    if matches and matches.size() > 0:
                        text = matches.get(0)
                        print(f"STT Final: {text}")
                        if self.engine.callback_text:
                            # Schedule on main thread to be safe with UI
                            Clock.schedule_once(lambda dt: self.engine.callback_text(text), 0)
                    self.engine.is_listening = False

                @java_method('(Landroid/os/Bundle;)V')
                def onPartialResults(self, results):
                    # We could stream partial results to UI if desired
                    pass

                @java_method('(Landroid/os/Bundle;)V')
                def onReadyForSpeech(self, params):
                    print("STT Ready")

                @java_method('(Landroid/os/Bundle;)V')
                def onBeginningOfSpeech(self, params):
                    print("STT Speaking started")

                @java_method('()V')
                def onEndOfSpeech(self):
                    print("STT Speaking ended")

                @java_method('(I)V')
                def onBufferReceived(self, buffer): pass
                @java_method('(F)V')
                def onRmsChanged(self, rmsdB): pass
                @java_method('(ILandroid/os/Bundle;)V')
                def onEvent(self, eventType, params): pass

            self.listener = RecognitionListener(self)
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            
            # Needs to run on UI Thread? SpeechRecognizer usually assumes main Looper.
            # We will ensure calls map to UI thread if needed, but usually Kivy main thread is sufficient.
            self.speech_recognizer = SpeechRecognizer.createSpeechRecognizer(context)
            self.speech_recognizer.setRecognitionListener(self.listener)

        except Exception as e:
            self.logger.error(f"STT Init Failed: {e}")
            import traceback
            traceback.print_exc()

    def start_listening(self):
        if platform == 'android' and self.speech_recognizer:
            try:
                # Ensure UI thread for Android UI calls
                from android.runnable import run_on_ui_thread
                
                @run_on_ui_thread
                def _start():
                    print("STT: Start Listening...")
                    self.speech_recognizer.startListening(self.intent)
                    self.is_listening = True
                
                _start()
            except Exception as e:
                print(f"STT Start Failed: {e}")

    def stop_listening(self):
        if platform == 'android' and self.speech_recognizer:
             try:
                from android.runnable import run_on_ui_thread
                @run_on_ui_thread
                def _stop():
                    print("STT: Stop Listening...")
                    self.speech_recognizer.stopListening()
                    self.is_listening = False
                _stop()
             except Exception as e:
                 print(f"STT Stop Failed: {e}")
