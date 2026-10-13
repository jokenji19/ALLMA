from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
import os

from allma_model.ui.setup_view import SetupView
from allma_model.ui.chat_view import ChatView
from allma_model.utils.model_downloader import ModelDownloader

from allma_model.ui.android_bars import AndroidBars


class AllmaInternalApp(MDApp):
    def build(self):
        # Force window to resize when keyboard appears
        Window.softinput_mode = 'resize'
        
        # Configure Material Theme
        self.theme_cls.theme_style = "Dark" # PREMIUM DARK OVERHAUL
        self.theme_cls.primary_palette = "LightBlue"
        self.theme_cls.accent_palette = "Cyan" # Modern Neon Accent
        
        self.sm = ScreenManager(transition=FadeTransition())
        
        # Setup View is always needed first
        self.setup_screen = SetupView(name='setup')
        self.setup_screen.set_callback(self.on_setup_complete)
        self.sm.add_widget(self.setup_screen)
        
        # SetupView verifies the model checksum on a worker before entering chat.
        self.sm.current = 'setup'

        return self.sm

    def load_and_switch_chat(self):
        if not self.sm.has_screen('chat'):
            # Lazy load ChatView
            from allma_model.ui.chat_view import ChatView
            self.chat_screen = ChatView(name='chat')
            self.sm.add_widget(self.chat_screen)
        
        self.sm.current = 'chat'

    def on_setup_complete(self):
        # Switch to chat when setup is done
        print("[AllmaInternalApp] Setup Complete. Switching to Chat.")
        self.load_and_switch_chat()

    def on_start(self):
        # Configure Android System Bars (White/Light Theme)
        # Use a delay to ensure Kivy Window is fully initialized before we override flags
        Clock.schedule_once(lambda dt: AndroidBars.configure_bars(), 0.5)

        # REDUNDANT CHECK: If we are in Setup, trigger check again just in case
        if self.sm.current == 'setup':
             Clock.schedule_once(lambda dt: self.setup_screen.check_requirements(0), 1.0)

        # Check if the native library was just downloaded
        if os.environ.get("ALLMA_LIB_DOWNLOADED") == "1":
            self.show_toast("Componenti aggiornati. ALLMA è pronta.")

    def show_toast(self, text):
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                from android.runnable import run_on_ui_thread
                
                @run_on_ui_thread
                def _toast_ui(t_text):
                    try:
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        JString = autoclass('java.lang.String')
                        Toast = autoclass('android.widget.Toast')
                        context =  PythonActivity.mActivity
                        Toast.makeText(context, cast('java.lang.CharSequence', JString(t_text)), Toast.LENGTH_LONG).show()
                    except Exception as inner:
                        print(f"Toast Inner Error: {inner}")

                _toast_ui(text)
                
            except Exception as e:
                print(f"Toast Error: {e}")
        else:
            print(f"[TOAST] {text}")
            print(f"[TOAST] {text}")

    def on_pause(self):
        """Called when the app is about to be paused (backgrounded)."""
        print("[AllmaInternalApp] Pausing... Saving state.")
        try:
            if hasattr(self, 'chat_screen') and hasattr(self.chat_screen, 'core'):
                core = self.chat_screen.core
                if core is None:
                    self.chat_screen.intro.stop()
                    return True
                stt = getattr(self.chat_screen, 'stt', None)
                if not (stt and stt.permission_pending) and hasattr(self.chat_screen, 'suspend_voice'):
                    try:
                        self.chat_screen.suspend_voice()
                    except Exception as error:
                        print(f"[AllmaInternalApp] Voice cleanup failed: {error}")
                if hasattr(self.chat_screen, 'chat_session'):
                    self.chat_screen.chat_session.cancel()
                if not getattr(self, "_paused", False):
                    self._dream_before_pause = core.dream_enabled
                self._paused = True
                core.set_dream_mode(False, persist=False)
                core.incremental_learner.save_state()
                # 1. Force Save Memory
                core = self.chat_screen.core
                if core.conversational_memory:
                    core.conversational_memory.save_memory()
                    print("[AllmaInternalApp] Memory saved on pause.")
                
                # 2. Suspend Dreaming/Heavy processes
                if hasattr(core, 'dream_manager'):
                    # core.dream_manager.suspend() # If implemented
                    pass
                
                # 3. Suspend LLM is hard, but we can stop generation flag if we wanted
        except Exception as e:
            print(f"[AllmaInternalApp] Error in on_pause: {e}")
            
        return True # Allow backgrounding

    def on_resume(self):
        """Called when the app resumes."""
        print("[AllmaInternalApp] Resumed.")
        try:
            if hasattr(self, 'chat_screen') and hasattr(self.chat_screen, 'core'):
                if self.chat_screen.core is None:
                    self.chat_screen.intro.progress_bar.indeterminate = self.chat_screen.intro.busy
                    return
                self.chat_screen.core.set_dream_mode(getattr(self, "_dream_before_pause", False), persist=False)
                self._paused = False
        except Exception as e:
                print(f"[AllmaInternalApp] Error in on_resume: {e}")
    def on_stop(self):
        self.on_pause()
        chat = getattr(self, 'chat_screen', None)
        if chat and hasattr(chat, 'cancel_startup'):
            chat.cancel_startup()
        if chat and chat.core:
            try:
                chat.suspend_voice(close=True)
            except Exception as error:
                print(f"[AllmaInternalApp] Voice shutdown failed: {error}")
            event = getattr(chat, "_learning_status_event", None)
            if event:
                event.cancel()
            # Closing can wait for a native inference call; keep the UI responsive.
            from threading import Thread
            Thread(target=chat.core.close, name="allma-shutdown", daemon=True).start()

if __name__ == '__main__':
    AllmaInternalApp().run()
