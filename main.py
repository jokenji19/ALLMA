import os
import sys
import logging
import traceback
import threading
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.utils import platform

# Configura logging
if platform == 'android':
    from android.storage import app_storage_path
    log_dir = app_storage_path()
    log_file = os.path.join(log_dir, 'allma_crash.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# FIX CRITICO: Aggiungi la cartella corrente e libs al path di Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Aggiungi la cartella libs (dove abbiamo spostato Model)
libs_dir = os.path.join(current_dir, 'libs')
if os.path.exists(libs_dir):
    sys.path.append(libs_dir)
    logging.info(f"Added to sys.path: {libs_dir}")

# SELF-HEALING: Cerca la cartella 'Model' ovunque (backup)
def find_model_package(start_dir):
def find_model_package(start_dir):
    logging.info(f"Searching for Model in {start_dir}...")
    for root, dirs, files in os.walk(start_dir):
        if 'Model' in dirs:
            model_path = os.path.join(root, 'Model')
            parent_dir = os.path.dirname(model_path)
            logging.info(f"FOUND MODEL AT: {model_path}")
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
                logging.info(f"Added {parent_dir} to sys.path")
            return True
        # Non scendere troppo in profondità per evitare loop o lentezza
        if root.count(os.sep) - start_dir.count(os.sep) > 2:
            del dirs[:]
    return False

# Prova a trovare Model
if not find_model_package(current_dir):
    # Prova dentro _python_bundle se esiste
    bundle_dir = os.path.join(current_dir, '_python_bundle')
    if os.path.exists(bundle_dir):
        find_model_package(bundle_dir)

# Importa Model DOPO aver sistemato il path
try:
    from Model.utils.model_downloader import ModelDownloader
    from Model.core.allma_core import ALLMACore
except ImportError as e:
    logging.critical(f"IMPORT ERROR: {e}")
    # DEBUG: List directory contents to see if Model exists
    try:
        files = os.listdir(current_dir)
        bundle_files = []
        site_packages_files = []
        modules_files = []
        
        bundle_path = os.path.join(current_dir, '_python_bundle')
        if os.path.exists(bundle_path):
            bundle_files = os.listdir(bundle_path)
            
            # Check site-packages
            sp_path = os.path.join(bundle_path, 'site-packages')
            if os.path.exists(sp_path):
                site_packages_files = os.listdir(sp_path)
                # Try to add site-packages to path just in case
                if sp_path not in sys.path:
                    sys.path.append(sp_path)
            
            # Check modules
            mod_path = os.path.join(bundle_path, 'modules')
            if os.path.exists(mod_path):
                modules_files = os.listdir(mod_path)

        logging.critical(f"DIR CONTENTS: {files}")
        logging.critical(f"BUNDLE CONTENTS: {bundle_files}")
        logging.critical(f"SITE-PACKAGES: {site_packages_files}")
        
        error_details = f"{e}\n\nROOT: {files}\n\nBUNDLE: {bundle_files}\n\nSITE-PACKAGES: {site_packages_files}"
    except Exception as list_err:
        error_details = f"{e}\n\nList Error: {list_err}"
        
    # Non crashare subito, lascia che l'app mostri l'errore nella UI
    ModelDownloader = None
    ALLMACore = None
    
    # Salva l'errore in una variabile globale per mostrarlo nella UI
    IMPORT_ERROR_MSG = error_details

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

class DownloadScreen(MDScreen):
    def start_download(self):
        self.ids.btn_start.disabled = True
        self.ids.btn_start.text = "DOWNLOAD IN CORSO..."
        
        if not ModelDownloader:
             self.ids.btn_start.text = "ERRORE: Modulo Model non trovato"
             return

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
        elif model_key == 'emotion':
            self.ids.progress_emotion.value = percent
            self.ids.label_emotion.text = f"{percent:.1f}% ({current//1024//1024}MB / {total//1024//1024}MB)"

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
        
        if not ALLMACore:
            from kivy.uix.label import Label
            msg = globals().get('IMPORT_ERROR_MSG', 'Unknown Error')
            return Label(text=f"ERRORE CRITICO:\n{msg}", halign="center", text_size=(None, None))

        # Carica i file KV con percorso assoluto sicuro
        base_path = os.path.dirname(os.path.abspath(__file__))
        Builder.load_file(os.path.join(base_path, "UI/chat_screen.kv"))
        Builder.load_file(os.path.join(base_path, "UI/download_screen.kv"))
        
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

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        logging.critical(f"CRITICAL CRASH: {e}", exc_info=True)
        # Se siamo su Android, proviamo a salvare l'errore in un file visibile se possibile
        if platform == 'android':
            from android.storage import app_storage_path
            with open(os.path.join(app_storage_path(), 'crash_dump.txt'), 'w') as f:
                f.write(traceback.format_exc())

if __name__ == "__main__":
    try:
        DepTestApp().run()
    except Exception as e:
        logging.critical(f"CRASH: {e}")
        if platform == 'android':
            from android.storage import app_storage_path
            with open(os.path.join(app_storage_path(), 'crash_fatal.txt'), 'w') as f:
                f.write(traceback.format_exc())
