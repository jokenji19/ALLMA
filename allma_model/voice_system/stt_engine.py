import logging
from kivy.utils import platform
from kivy.clock import Clock

class STTEngine:
    """
    Handles Speech-to-Text using Android's native SpeechRecognizer.
    """
    def __init__(self, callback_text, callback_partial=None):
        self.logger = logging.getLogger(__name__)
        self.callback_text = callback_text # Function(text) - FINAL
        self.callback_partial = callback_partial # Function(text) - PARTIAL
        self.speech_recognizer = None
        self.intent = None
        self.is_listening = False

        if platform == 'android':
            self._init_android_stt()

    def _init_android_stt(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android.permissions import request_permissions, Permission
            from android.runnable import run_on_ui_thread

            # Request Permissions first
            request_permissions([Permission.RECORD_AUDIO])

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            
            # Intent
            Intent = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')
            
            # BARE MINIMUM DEFAULT (System Default)
            # We are removing ALL custom language/model flags to let the OS decide.
            self.intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            
            # Safer Package Name Retrieval
            try:
                pkg_name = context.getPackageName()
                if hasattr(pkg_name, 'toString'):
                    pkg_name = pkg_name.toString()
                else:
                    pkg_name = str(pkg_name)
            except:
                pkg_name = "org.allma.allma_prime" # Fallback
                
            if self.intent:
                self.intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, pkg_name)
            
            # Visual Feedback - Keep this so we know it's working
            self.intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True) 
            self.intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)

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
                    msg = f"Errore {error}"
                    if error == 7: msg = "Non ho sentito nulla..."
                    if error == 9: msg = "Permessi negati (Mic)"
                    if error == 3: msg = "Errore Audio"
                    if error == 5: msg = "Errore Client"
                    if error == 2: msg = "Errore Rete"
                    
                    self.engine.is_listening = False
                    # FORCE UI UPDATE ON ERROR
                    if self.engine.callback_partial:
                         Clock.schedule_once(lambda dt: self.engine.callback_partial(msg), 0)

                @java_method('(Landroid/os/Bundle;)V')
                def onResults(self, results):
                    print("STT Results received")
                    try:
                        matches = results.getStringArrayList(autoclass('android.speech.RecognizerIntent').EXTRA_RESULTS)
                        if matches and matches.size() > 0:
                            text = matches.get(0)
                            print(f"STT Final: {text}")
                            if self.engine.callback_text:
                                # Schedule on main thread to be safe with UI
                                Clock.schedule_once(lambda dt: self.engine.callback_text(text), 0)
                        else:
                            print("STT Results: No matches found.")
                            # VISUAL FEEDBACK FOR NO MATCH
                            if self.engine.callback_partial:
                                Clock.schedule_once(lambda dt: self.engine.callback_partial("Non ho capito..."), 0)
                    except Exception as e:
                        print(f"STT Results Error: {e}")
                        if self.engine.callback_partial:
                            Clock.schedule_once(lambda dt: self.engine.callback_partial(f"Errore risultati: {e}"), 0)
                        import traceback
                        traceback.print_exc()

                    self.engine.is_listening = False

                @java_method('(Landroid/os/Bundle;)V')
                def onPartialResults(self, results):
                    # PARTIAL RESULTS HANDLING
                    try:
                        matches = results.getStringArrayList(autoclass('android.speech.RecognizerIntent').EXTRA_RESULTS)
                        if matches and matches.size() > 0:
                            text = matches.get(0)
                            if self.engine.callback_partial:
                                Clock.schedule_once(lambda dt: self.engine.callback_partial(text), 0)
                    except Exception as e:
                        pass

                @java_method('(Landroid/os/Bundle;)V')
                def onReadyForSpeech(self, params):
                    print("STT Ready")
                    if self.engine.callback_partial:
                        Clock.schedule_once(lambda dt: self.engine.callback_partial("Ti ascolto..."), 0)

                @java_method('()V')
                def onBeginningOfSpeech(self):
                    # FIXED SIGNATURE: No params for onBeginningOfSpeech
                    print("STT Speaking started")
                    # Optional: specific feedback
                    if self.engine.callback_partial:
                        Clock.schedule_once(lambda dt: self.engine.callback_partial("Sto ascoltando..."), 0)

                @java_method('()V')
                def onEndOfSpeech(self):
                    print("STT Speaking ended")
                    if self.engine.callback_partial:
                        Clock.schedule_once(lambda dt: self.engine.callback_partial("Elaboro..."), 0)

                @java_method('(I)V')
                def onBufferReceived(self, buffer): pass
                @java_method('(F)V')
                def onRmsChanged(self, rmsdB): pass
                @java_method('(ILandroid/os/Bundle;)V')
                def onEvent(self, eventType, params): pass

            self.listener = RecognitionListener(self)
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            
            # Check availability
            if not SpeechRecognizer.isRecognitionAvailable(context):
                print("STT: Recognition NOT Available on this device!")
                return

            # Ensure creation on UI Thread
            @run_on_ui_thread
            def create_recognizer():
                self.speech_recognizer = SpeechRecognizer.createSpeechRecognizer(context)
                self.speech_recognizer.setRecognitionListener(self.listener)
                print("STT: Recognizer Created on UI Thread")
            
            create_recognizer()

        except Exception as e:
            # FORCE PRINT for Logcat visibility (Logger can be silenced)
            print(f"STT CRITICAL ERROR: Init Failed: {e}")
            import traceback
            traceback.print_exc()

    def start_listening(self):
        if platform == 'android':
            try:
                # Ensure UI thread for Android UI calls
                from android.runnable import run_on_ui_thread
                
                @run_on_ui_thread
                def _start():
                    if not self.speech_recognizer:
                        print("STT: Recognizer not ready yet...")
                        return
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
