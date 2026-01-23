from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.clock import Clock
from kivy.lang import Builder
from threading import Thread

# Import Core (Adjust import as needed based on structure)
from allma_model.core.allma_core import ALLMACore

Builder.load_string('''
<MessageBubble>:
    size_hint_y: None
    height: self.texture_size[1] + 20
    text_size: self.width - 30, None
    padding: 15, 10
    font_name: 'Roboto'  # Force system font for better emoji support
    canvas.before:
        Color:
            rgba: (0.2, 0.6, 1, 1) if self.is_user else (0.3, 0.3, 0.3, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15, 15, 0, 15] if self.is_user else [15, 15, 15, 0]

<ChatView>:
    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        padding: 10
        canvas.before:
            Color:
                rgba: 0.1, 0.12, 0.15, 1
            Rectangle:
                pos: self.pos
                size: self.size

        RecycleView:
            id: rv
            scroll_type: ['bars', 'content']
            scroll_wheel_distance: dp(114)
            bar_width: dp(10)
            viewclass: 'MessageBubble'
            RecycleBoxLayout:
                default_size: None, dp(56)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(8)
                padding: dp(10)

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: 10
            
            TextInput:
                id: input_field
                multiline: False
                hint_text: "Scrivi un messaggio..."
                background_color: 0.2, 0.2, 0.2, 1
                foreground_color: 1, 1, 1, 1
                cursor_color: 1, 1, 1, 1
                padding_y: [15, 0]
                font_name: 'Roboto'  # Force system font
                on_text_validate: root.send_message()

            Button:
                text: "Send"
                size_hint_x: None
                width: dp(80)
                background_color: 0.2, 0.6, 1, 1
                on_release: root.send_message()
''')

class MessageBubble(RecycleDataViewBehavior, Label):
    is_user = BooleanProperty(False)
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.is_user = data.get('is_user', False)
        return super(MessageBubble, self).refresh_view_attrs(rv, index, data)

class ChatView(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core = None # Lazy init to avoid slow startup
        self.history = []

    def on_enter(self):
        if not self.core:
            # Initialize core in background or here if fast enough
            # For now synchronous as it's the first chat load
            try:
                # Recupera il percorso modelli corretto
                from allma_model.utils.model_downloader import ModelDownloader
                downloader = ModelDownloader()
                models_dir = downloader.models_dir
                
                self.core = ALLMACore(models_dir=models_dir)
                self.user_id = "user_mobile"
                self.conversation_id = self.core.start_conversation(self.user_id)
                
                # Init welcome message
                self.add_message("Sistema ALLMA online. Come posso aiutarti?", False)
            except Exception as e:
                self.add_message(f"Errore inizializzazione core: {e}", False)

    def send_message(self):
        text = self.ids.input_field.text.strip()
        if not text:
            return

        self.add_message(text, True)
        self.ids.input_field.text = ""
        
        # Show user we are thinking
        Clock.schedule_once(lambda dt: self.add_message("Thinking...", False, temp=True), 0.1)

        # Process in background
        Thread(target=self._process_message, args=(text,)).start()

    def _process_message(self, text):
        try:
            if self.core:
                result = self.core.process_message(
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    message=text
                )
                response = result.content if hasattr(result, 'content') else str(result)
            else:
                response = "Core non inizializzato."
        except Exception as e:
            response = f"Errore interno: {e}"

        Clock.schedule_once(lambda dt: self._update_response(response))

    def _update_response(self, response_text):
        # Remove "Thinking..." (last item) if present
        if self.history and self.history[-1].get('temp', False):
            self.history.pop()
        
        # Add real response
        self.history.append({'text': str(response_text), 'is_user': False})
        self.ids.rv.data = list(self.history)
        self.scroll_to_bottom()

    def add_message(self, text, is_user, temp=False):
        self.history.append({'text': text, 'is_user': is_user, 'temp': temp})
        self.ids.rv.data = list(self.history)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        # Schedule scroll to allow layout to update
        Clock.schedule_once(lambda dt: setattr(self.ids.rv, 'scroll_y', 0), 0.1)

