import logging
from kivy.utils import platform
from kivy.clock import Clock

class TTSEngine:
    """
    Handles Text-to-Speech generation.
    Currently defaults to Native Android TTS for reliability, 
    with stubs for future Neural (VyvoTTS) integration.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.native_tts = None
        self.is_ready = False
        
        if platform == 'android':
            self._init_android_tts()
        else:
            self.logger.info("TTSEngine: Not on Android, TTS disabled (or use say/espeak).")

    def _init_android_tts(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            
            # Context needed for TTS constructor
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.context = PythonActivity.mActivity
            
            # Listener interface
            class TTSOnInitListener(PythonJavaClass):
                __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
                __javacontext__ = 'app'

                def __init__(self, engine_instance):
                    super().__init__()
                    self.engine = engine_instance

                @java_method('(I)V')
                def onInit(self, status):
                    if status == 0: # TextToSpeech.SUCCESS
                        print("TTSEngine: Native TTS Initialized Successfully!")
                        self.engine.is_ready = True
                        # Optional: Set Language
                        # Locale = autoclass('java.util.Locale')
                        # self.engine.native_tts.setLanguage(Locale.ITALIAN)
                    else:
                        print(f"TTSEngine: Native TTS Initialization Failed with status {status}")

            self.listener = TTSOnInitListener(self)
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            self.native_tts = TextToSpeech(self.context, self.listener)
            
        except Exception as e:
            self.logger.error(f"TTSEngine: Failed to init Android TTS: {e}")
            import traceback
            traceback.print_exc()

    def speak(self, text, flush=False):
        """
        Speaks the given text.
        flush=True interrupts current speech (QUEUE_FLUSH).
        flush=False appends to queue (QUEUE_ADD) - DEFAULT for streaming.
        """
        print(f"TTSEngine: Speak request -> '{text[:20]}...' (flush={flush})")
        
        if platform == 'android':
            if self.native_tts and self.is_ready:
                from jnius import cast
                # Queue mode: 0 = QUEUE_FLUSH, 1 = QUEUE_ADD
                mode = 0 if flush else 1
                self.native_tts.speak(text, mode, None)
            else:
                self.logger.warning("TTSEngine: Android TTS not ready.")
        else:
            # Desktop fallback (MacOS 'say' command)
            import os
            try:
                # Sanitize text
                clean_text = text.replace('"', '').replace("'", "")
                os.system(f'say "{clean_text}" &')
            except:
                pass

    def stop(self):
        if self.native_tts:
            self.native_tts.stop()
