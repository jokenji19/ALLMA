import os
import sys
import logging
import traceback
import threading
from kivy.app import App
from kivy.uix.label import Label
from kivy.utils import platform
from kivy.clock import Clock

# Configura logging aggressivo SUBITO
if platform == 'android':
    from android.storage import app_storage_path
    log_dir = app_storage_path()
    log_file = os.path.join(log_dir, 'allma_crash.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# FIX CRITICO: Aggiungi la cartella corrente al path di Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
logging.info(f"Added to sys.path: {current_dir}")

# Variabili globali per i moduli ritardati
MDApp = None
MDScreen = None
MDBoxLayout = None
ScreenManager = None
Builder = None
StringProperty = None
BooleanProperty = None
ModelDownloader = None
ALLMACore = None

class ALLMAApp(App):
    def build(self):
        try:
            # Tenta di importare i moduli pesanti QUI, protetti da try-except
            global MDApp, MDScreen, MDBoxLayout, ScreenManager, Builder, StringProperty, BooleanProperty
            global ModelDownloader, ALLMACore
            
            logging.info("Starting lazy imports...")
            from kivy.lang import Builder
            from kivy.properties import StringProperty, BooleanProperty
            from kivy.uix.screenmanager import ScreenManager
            
            logging.info("Importing KivyMD...")
            from kivymd.app import MDApp
            from kivymd.uix.screen import MDScreen
            from kivymd.uix.boxlayout import MDBoxLayout
            
            logging.info("Importing ALLMA Model...")
            from Model.utils.model_downloader import ModelDownloader
            from Model.core.allma_core import ALLMACore
            
            logging.info("Imports successful!")
            
            # Se siamo qui, gli import sono andati a buon fine.
            # Ora possiamo definire le classi che dipendono da KivyMD
            # (Le definiamo dinamicamente o usiamo una factory, ma per semplicità
            #  possiamo usare una classe wrapper o inizializzare la vera app qui)
            
            # TRUCCO: Poiché MDApp deve essere la classe base, e noi siamo già in App,
            # non possiamo cambiare la classe base a runtime facilmente.
            # INVECE: Restituiamo un widget che gestisce tutto, oppure lanciamo la MDApp vera.
            # Ma siamo già dentro build()...
            
            # SOLUZIONE MIGLIORE:
            # Usiamo una "LoaderApp" (questa) che se tutto va bene,
            # istanzia e restituisce la Root Widget della vera app.
            # MA MDApp si aspetta di essere l'App corrente.
            
            # QUINDI: Facciamo un passo indietro.
            # Questo file deve definire le classi MA non eseguirle a livello globale.
            
            return self.real_build()
            
        except Exception as e:
            logging.critical(f"CRITICAL IMPORT ERROR: {e}", exc_info=True)
            return Label(
                text=f"ERRORE AVVIO:\n{str(e)}\n\nControlla allma_crash.log",
                halign="center",
                valign="middle",
                text_size=(None, None) # Adatta alla finestra
            )

    def real_build(self):
        # Qui mettiamo la logica originale di build()
        self.theme_cls = MDApp.get_running_app().theme_cls # Hack se usiamo MDApp
        # No, aspetta. Se siamo ALLMAApp(App), non abbiamo theme_cls.
        # Dobbiamo usare MDApp come base se possibile.
        pass

# Riscriviamo l'approccio:
# 1. Definiamo le classi DOPO gli import.
# 2. Se gli import falliscono, definiamo una FallbackApp.

try:
    logging.info("Attempting top-level imports...")
    from kivy.lang import Builder
    from kivy.properties import StringProperty, BooleanProperty
    from kivy.uix.screenmanager import ScreenManager
    from kivymd.app import MDApp
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.boxlayout import MDBoxLayout
    from Model.utils.model_downloader import ModelDownloader
    from Model.core.allma_core import ALLMACore
    logging.info("Top-level imports successful")
    
    # --- CODICE ORIGINALE (con le classi) ---
    class ChatMessage(MDBoxLayout):
        text = StringProperty()
        is_user = BooleanProperty(False)

    class ChatScreen(MDScreen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # self.app = MDApp.get_running_app() # Risolto a runtime

        def send_message(self):
            input_field = self.ids.message_input
            message = input_field.text.strip()
            if not message: return
            self.add_message(message, is_user=True)
            input_field.text = ""
            threading.Thread(target=self.process_response, args=(message,)).start()

        def add_message(self, text, is_user):
            self.ids.chat_list.data.append({
                'viewclass': 'ChatMessage',
                'text': text,
                'is_user': is_user
            })

        def process_response(self, message):
            try:
                app = MDApp.get_running_app()
                user_id = "local_user"
                conversation_id = "local_chat"
                if not app.allma.conversational_memory.get_conversation_history(conversation_id):
                    app.allma.start_conversation(user_id)
                response = app.allma.process_message(user_id=user_id, conversation_id=conversation_id, message=message)
                Clock.schedule_once(lambda dt: self.add_message(response.content, is_user=False))
            except Exception as e:
                error_msg = f"Errore: {str(e)}"
                Clock.schedule_once(lambda dt: self.add_message(error_msg, is_user=False))

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
                if total > 0:
                    percent = (current / total) * 100
                    Clock.schedule_once(lambda dt: self.update_progress(model_key, percent, current, total))

            def completion_callback(success):
                Clock.schedule_once(lambda dt: self.on_download_complete(success))

            downloader.start_background_download(missing, progress_callback, completion_callback)

        def update_progress(self, model_key, percent, current, total):
            if model_key == 'gemma':
                self.ids.progress_gemma.value = percent
                self.ids.label_gemma.text = f"{percent:.1f}%"
            elif model_key == 'moondream':
                self.ids.progress_moondream.value = percent
                self.ids.label_moondream.text = f"{percent:.1f}%"
            elif model_key == 'emotion':
                self.ids.progress_emotion.value = percent
                self.ids.label_emotion.text = f"{percent:.1f}%"

        def on_download_complete(self, success):
            if success:
                self.ids.btn_start.text = "COMPLETATO!"
                Clock.schedule_once(lambda dt: self.go_to_chat(), 1)
            else:
                self.ids.btn_start.disabled = False
                self.ids.btn_start.text = "ERRORE - RIPROVA"

        def go_to_chat(self):
            app = MDApp.get_running_app()
            app.initialize_allma()
            self.manager.current = 'chat'

    class ALLMAApp(MDApp):
        def build(self):
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.accent_palette = "Teal"
            self.theme_cls.theme_style = "Dark"
            
            base_path = os.path.dirname(os.path.abspath(__file__))
            Builder.load_file(os.path.join(base_path, "UI/chat_screen.kv"))
            Builder.load_file(os.path.join(base_path, "UI/download_screen.kv"))
            
            self.sm = ScreenManager()
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
                models_dir = self.downloader._get_models_dir()
                self.allma = ALLMACore(mobile_mode=True)

except Exception as e:
    # FALLBACK APP se gli import falliscono
    logging.critical(f"CRITICAL STARTUP ERROR: {e}", exc_info=True)
    
    class ALLMAApp(App):
        def build(self):
            return Label(text=f"CRASH AVVIO:\n{str(e)}\n\nVedi log.", halign="center")

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        logging.critical(f"RUNTIME CRASH: {e}", exc_info=True)
        if platform == 'android':
            from android.storage import app_storage_path
            with open(os.path.join(app_storage_path(), 'crash_dump.txt'), 'w') as f:
                f.write(traceback.format_exc())
