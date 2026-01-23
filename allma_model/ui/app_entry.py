from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder

from allma_model.ui.setup_view import SetupView
from allma_model.ui.chat_view import ChatView
from allma_model.utils.model_downloader import ModelDownloader

class AllmaInternalApp(App):
    def build(self):
        self.sm = ScreenManager(transition=FadeTransition())
        
        # Check initial state
        downloader = ModelDownloader()
        missing = downloader.check_models_missing()
        
        # Always add both screens, but decide which to show first
        self.setup_screen = SetupView(name='setup')
        self.setup_screen.set_callback(self.on_setup_complete)
        self.chat_screen = ChatView(name='chat')
        
        self.sm.add_widget(self.setup_screen)
        self.sm.add_widget(self.chat_screen)
        
        if missing:
            self.sm.current = 'setup'
        else:
            self.sm.current = 'chat'
            
        return self.sm

    def on_setup_complete(self):
        # Switch to chat when setup is done
        self.sm.current = 'chat'

    def on_start(self):
        # Check if the native library was just downloaded
        if os.environ.get("ALLMA_LIB_DOWNLOADED") == "1":
            self.show_toast("Motore AI (Lib) installato correttamente!")

    def show_toast(self, text):
        from kivy.utils import platform
        if platform == 'android':
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            JString = autoclass('java.lang.String')
            Toast = autoclass('android.widget.Toast')
            context =  PythonActivity.mActivity
            Toast.makeText(context, cast('java.lang.CharSequence', JString(text)), Toast.LENGTH_LONG).show()
        else:
            print(f"[TOAST] {text}")

if __name__ == '__main__':
    AllmaInternalApp().run()
