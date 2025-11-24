import os
import sys
import threading
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout

# Aggiungi la directory corrente al path per importare i moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

class ChatMessage(MDBoxLayout):
    text = StringProperty()
    is_user = BooleanProperty(False)

class ChatScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()

    def send_message(self):
        input_field = self.ids.message_input
        message = input_field.text.strip()
        
        if not message:
            return

        # Aggiungi messaggio utente alla lista
        self.add_message(message, is_user=True)
        input_field.text = ""

        # Processa la risposta in un thread separato per non bloccare la UI
        threading.Thread(target=self.process_response, args=(message,)).start()

    def add_message(self, text, is_user):
        self.ids.chat_list.data.append({
            'viewclass': 'ChatMessage',
            'text': text,
            'is_user': is_user
        })

    def process_response(self, message):
        try:
            # Simula un ID utente fisso per la versione locale
            user_id = "local_user"
            conversation_id = "local_chat"
            
            # Assicurati che la conversazione esista
            if not self.app.allma.conversational_memory.get_conversation_history(conversation_id):
                self.app.allma.start_conversation(user_id)

            response = self.app.allma.process_message(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message
            )
            
            # Aggiorna la UI nel thread principale
            Clock.schedule_once(lambda dt: self.add_message(response.content, is_user=False))
            
        except Exception as e:
            error_msg = f"Errore: {str(e)}"
            Clock.schedule_once(lambda dt: self.add_message(error_msg, is_user=False))

from kivy.uix.screenmanager import ScreenManager
from Model.utils.model_downloader import ModelDownloader

class DownloadScreen(MDScreen):
    def start_download(self):
        self.ids.btn_start.disabled = True
        self.ids.btn_start.text = "DOWNLOAD IN CORSO..."
        
        downloader = ModelDownloader()
        missing = downloader.check_models_missing()
        
        if not missing:
            self.go_to_chat()
            return

        def progress_callback(model_key, current, total):
            # Calcola percentuale
            if total > 0:
                percent = (current / total) * 100
                
                # Aggiorna UI nel thread principale
                Clock.schedule_once(lambda dt: self.update_progress(model_key, percent, current, total))

        def completion_callback(success):
            Clock.schedule_once(lambda dt: self.on_download_complete(success))

        downloader.start_background_download(missing, progress_callback, completion_callback)

    def update_progress(self, model_key, percent, current, total):
        if model_key == 'gemma':
            self.ids.progress_gemma.value = percent
            self.ids.label_gemma.text = f"{percent:.1f}% ({current//1024//1024}MB / {total//1024//1024}MB)"
        elif model_key == 'moondream':
            self.ids.progress_moondream.value = percent
            self.ids.label_moondream.text = f"{percent:.1f}% ({current//1024//1024}MB / {total//1024//1024}MB)"

    def on_download_complete(self, success):
        if success:
            self.ids.btn_start.text = "COMPLETATO!"
            Clock.schedule_once(lambda dt: self.go_to_chat(), 1)
        else:
            self.ids.btn_start.disabled = False
            self.ids.btn_start.text = "ERRORE - RIPROVA"

    def go_to_chat(self):
        app = MDApp.get_running_app()
        # Inizializza ALLMA ora che i modelli ci sono
        app.initialize_allma()
        self.manager.current = 'chat'

class ALLMAApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Dark"
        
        # Carica i file KV
        Builder.load_file("UI/chat_screen.kv")
        Builder.load_file("UI/download_screen.kv")
        
        self.sm = ScreenManager()
        
        # Controlla se i modelli esistono
        self.downloader = ModelDownloader()
        missing_models = self.downloader.check_models_missing()
        
        if missing_models:
            self.sm.add_widget(DownloadScreen(name='download'))
            self.sm.add_widget(ChatScreen(name='chat'))
            self.sm.current = 'download'
        else:
            self.sm.add_widget(ChatScreen(name='chat'))
            self.sm.add_widget(DownloadScreen(name='download'))
            self.initialize_allma()
            self.sm.current = 'chat'
            
        return self.sm

    def initialize_allma(self):
        if not hasattr(self, 'allma'):
            # Passiamo il path dei modelli ad ALLMACore
            models_dir = self.downloader._get_models_dir()
            # Nota: ALLMACore dovrà essere aggiornato per accettare models_dir
            self.allma = ALLMACore(mobile_mode=True) # TODO: Passare models_dir
