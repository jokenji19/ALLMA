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

# INLINED ANDROID BARS FIX TO ENSURE EXECUTION
class AndroidBars:
    @staticmethod
    def configure_bars():
        print(f"!!!! [AndroidBars-Inline] configure_bars called. Platform: {platform} !!!!")
        if platform != 'android':
            return
        
        # Try immediately and schedule retries
        AndroidBars._attempt_set_bars(0)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(1), 0.5)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(2), 1.5)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(3), 3.0)

    @staticmethod
    def _attempt_set_bars(attempt):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            Color = autoclass("android.graphics.Color")
            WindowManager = autoclass("android.view.WindowManager")
            View = autoclass("android.view.View")
            Build = autoclass("android.os.Build") 
            
            @run_on_ui_thread
            def _set_bars_ui():
                try:
                    print(f"!!!! [AndroidBars-Inline] UI Thread - Attempt {attempt} executing !!!!")
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    activity = PythonActivity.mActivity
                    window = activity.getWindow()
                    decor_view = window.getDecorView()

                    # 1. HANDLE CUTOUT (NOTCH) - API 28+
                    if Build.VERSION.SDK_INT >= 28:
                        params = window.getAttributes()
                        params.layoutInDisplayCutoutMode = 1 # SHORT_EDGES
                        window.setAttributes(params)
                        print(f"[AndroidBars-Inline] Cutout mode set to SHORT_EDGES")

                    # 2. VISIBILITY FLAGS
                    new_flags = decor_view.getSystemUiVisibility()
                    new_flags |= 0x00002000 # Light Status
                    if Build.VERSION.SDK_INT >= 26:
                        new_flags |= 0x00000010 # Light Nav
                    
                    decor_view.setSystemUiVisibility(new_flags)

                    # 3. WINDOW FLAGS
                    window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                    window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS)
                    window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_NAVIGATION)
                    
                    # 4. SET COLORS (WHITE)
                    white = Color.parseColor("#FFFFFF")
                    window.setStatusBarColor(white)
                    window.setNavigationBarColor(white)
                    
                    # 5. Nav Bar Divider (Transparent)
                    if Build.VERSION.SDK_INT >= 28:
                        window.setNavigationBarDividerColor(Color.parseColor("#00FFFFFF"))

                    print(f"!!!! [AndroidBars-Inline] Attempt {attempt}: SUCCESS !!!!")
                    
                except Exception as inner_e:
                    print(f"!!!! [AndroidBars-Inline] Attempt {attempt} INNER ERROR: {inner_e} !!!!")

            _set_bars_ui()

        except Exception as e:
            print(f"!!!! [AndroidBars-Inline] scheduling error: {e} !!!!")


class AllmaInternalApp(MDApp):
    def build(self):
        # Force window to resize when keyboard appears
        Window.softinput_mode = 'resize'
        
        # Configure Material Theme
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Teal"
        
        self.sm = ScreenManager(transition=FadeTransition())
        
        # Check initial state
        downloader = ModelDownloader()
        missing = downloader.check_models_missing()
        
        # Setup View is always needed first
        self.setup_screen = SetupView(name='setup')
        self.setup_screen.set_callback(self.on_setup_complete)
        self.sm.add_widget(self.setup_screen)
        
        if missing:
            print(f"[AllmaInternalApp] Missing models: {missing}. Enforcing SetupView.")
            # DO NOT ADD ChatView yet. This prevents any accidental switch.
            self.sm.current = 'setup'
        else:
            print("[AllmaInternalApp] Models present. Loading ChatView immediately.")
            # Setup done, load chat
            self.load_and_switch_chat()
            
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
            self.show_toast("VERSIONE DEBUG 999 - BIANCO TOTALE")

    def show_toast(self, text):
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                JString = autoclass('java.lang.String')
                Toast = autoclass('android.widget.Toast')
                context =  PythonActivity.mActivity
                Toast.makeText(context, cast('java.lang.CharSequence', JString(text)), Toast.LENGTH_LONG).show()
            except Exception as e:
                print(f"Toast Error: {e}")
        else:
            print(f"[TOAST] {text}")

if __name__ == '__main__':
    AllmaInternalApp().run()
