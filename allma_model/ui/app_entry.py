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

if __name__ == '__main__':
    AllmaInternalApp().run()
