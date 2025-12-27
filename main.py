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

# Configura logging con protezione per la directory mancante
try:
    if platform == 'android':
        from android.storage import app_storage_path
        # Usa un path temporaneo finché l'App non parte
        log_dir = app_storage_path()
        if not os.path.exists(log_dir):
             try:
                 os.makedirs(log_dir)
             except:
                 pass
        log_file = os.path.join(log_dir, 'allma_crash.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
except Exception as e:
    # Fallback to stdout if file logging fails
    logging.basicConfig(level=logging.DEBUG)
    print(f"File logging setup failed, using stdout: {e}")

# ... (rest of imports)

# ...

    def initialize_allma(self):
        try:
            if not hasattr(self, 'allma'):
                # Passiamo il path dei modelli ad ALLMACore
                models_dir = self.downloader._get_models_dir()
                
                # Definisci path assoluto per il DB usando user_data_dir (più sicuro)
                # self.user_data_dir è gestito da Kivy e garantito
                storage = self.user_data_dir
                
                # Logga il path usato
                logging.info(f"USING USER_DATA_DIR: {storage}")
                
                # Assicurati che storage esista (dovrebbe già esistere)
                if not os.path.exists(storage):
                    try:
                        os.makedirs(storage)
                    except Exception as create_err:
                        logging.error(f"Failed to create user_data_dir: {create_err}")
                            
                db_path = os.path.join(storage, 'allma.db')
                
                # Manual Touch of DB File
                if not os.path.exists(db_path):
                    logging.info("DB file doesn't exist, creating empty file...")
                    try:
                        with open(db_path, 'w') as f:
                            f.write("")
                    except Exception as touch_err:
                        # Se fallisce qui, proviamo un path alternativo nella cache
                        logging.error(f"Failed to touch DB in user_data_dir: {touch_err}")
                        if platform == 'android':
                             from jnius import autoclass
                             Context = autoclass('android.content.Context')
                             PythonActivity = autoclass('org.kivy.android.PythonActivity')
                             context = PythonActivity.mActivity
                             cache_dir = context.getCacheDir().getAbsolutePath()
                             db_path = os.path.join(cache_dir, 'allma.db')
                             logging.info(f"Retrying with Cache Dir: {db_path}")

                self.allma = ALLMACore(
                    mobile_mode=True,
                    models_dir=models_dir,
                    db_path=db_path
                )
        except Exception as e:
             logging.critical(f"ALLMA INIT CRASH: {e}", exc_info=True)
             if hasattr(self, 'sm'):
                 from kivy.uix.label import Label
                 # Gather debugging info
                 try:
                     storage_files = str(os.listdir(os.path.dirname(db_path)))
                 except:
                     storage_files = "Cannot list dir"
                     
                 self.sm.clear_widgets()
                 self.sm.add_widget(MDScreen(name='crash'))
                 # Mostra più contesto nell'errore
                 error_details = f"CRASH (Build 65):\n{str(e)}\n\nDB Path: {db_path}\nFiles: {storage_files}"
                 self.sm.get_screen('crash').add_widget(Label(text=error_details, halign='center'))
                 self.sm.current = 'crash'

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

# NUCLEAR OPTION: Scarica lo zip direttamente da GitHub se non c'è
def download_model_code_from_github(target_path):
    import requests
    url = "https://raw.githubusercontent.com/jokenji19/ALLMA/main/assets/model_code.zip"
    logging.info(f"Attempting NUCLEAR DOWNLOAD from {url}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info("NUCLEAR DOWNLOAD SUCCESSFUL")
        return True
    except Exception as e:
        logging.error(f"NUCLEAR DOWNLOAD FAILED: {e}")
        return False

# ZIP STRATEGY: Se non troviamo il modello, proviamo a scompattare lo zip
def extract_model_zip(start_dir):
    import zipfile
    # Cerca in assets (posizione standard)
    zip_path = os.path.join(start_dir, 'assets', 'model_code.zip')
    
    # Cerca anche in _python_bundle/assets
    if not os.path.exists(zip_path):
        bundle_zip = os.path.join(start_dir, '_python_bundle', 'assets', 'model_code.zip')
        if os.path.exists(bundle_zip):
            zip_path = bundle_zip
            
    # Fallback: cerca nella root (vecchia posizione)
    if not os.path.exists(zip_path):
        root_zip = os.path.join(start_dir, 'model_code.zip')
        if os.path.exists(root_zip):
            zip_path = root_zip

    # NUCLEAR FALLBACK: Se non c'è, scaricalo!
    if not os.path.exists(zip_path):
        logging.warning("ZIP NOT FOUND LOCALLY. INITIATING NUCLEAR OPTION.")
        # Salva nella cartella privata dell'app
        nuclear_path = os.path.join(app_storage_path(), 'model_code.zip')
        if download_model_code_from_github(nuclear_path):
            zip_path = nuclear_path
        else:
            logging.critical("NUCLEAR OPTION FAILED.")

    if os.path.exists(zip_path):
        logging.info(f"FOUND ZIP AT: {zip_path}")
        try:
            extract_dir = os.path.join(app_storage_path(), 'extracted_model')
            # Rimuovi vecchia estrazione se esiste per forzare aggiornamento
            # if os.path.exists(extract_dir):
            #     import shutil
            #     shutil.rmtree(extract_dir)
            
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
                
            logging.info(f"Extracting to {extract_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # Aggiungi il percorso estratto a sys.path
            sys.path.append(extract_dir)
            
            # Se lo zip conteneva "libs/Model", dobbiamo aggiungere "extract_dir/libs"
            if os.path.exists(os.path.join(extract_dir, 'libs')):
                sys.path.append(os.path.join(extract_dir, 'libs'))
                
            logging.info("Extraction successful and path added.")
            return True
        except Exception as e:
            logging.error(f"Failed to extract zip: {e}")
            return False
    return False

# Prova a trovare Model
if not find_model_package(current_dir):
    # Prova dentro _python_bundle se esiste
    bundle_dir = os.path.join(current_dir, '_python_bundle')
    found = False
    if os.path.exists(bundle_dir):
        if find_model_package(bundle_dir):
            found = True
            
    if not found:
        # ULTIMA SPIAGGIA: Estrai lo ZIP (o scaricalo)
        extract_model_zip(current_dir)

# Importa Model DOPO aver sistemato il path
try:
    # Tenta importazione critica
    from Model.core.allma_core import ALLMACore
    from Model.utils.model_downloader import ModelDownloader
    # Se arriviamo qui, il modello è stato trovato!
except ImportError as e:
    # Se fallisce ancora, mostra UI di errore con debug avanzato
    error_trace = traceback.format_exc()
    
    # Raccogli info sui file per debug
    files_root = str(os.listdir(current_dir)) if os.path.exists(current_dir) else "DIR_NOT_FOUND"
    
    # Debug Assets
    assets_dir = os.path.join(current_dir, 'assets')
    files_assets = str(os.listdir(assets_dir)) if os.path.exists(assets_dir) else "ASSETS_NOT_FOUND"
    
    # Debug Bundle
    bundle_path = os.path.join(current_dir, '_python_bundle')
    files_bundle = str(os.listdir(bundle_path)) if os.path.exists(bundle_path) else "BUNDLE_NOT_FOUND"
    
    # Debug Bundle Assets
    bundle_assets = os.path.join(bundle_path, 'assets')
    files_bundle_assets = str(os.listdir(bundle_assets)) if os.path.exists(bundle_assets) else "BUNDLE_ASSETS_NOT_FOUND"

    class ErrorApp(MDApp):
        def build(self):
            return Builder.load_string(f'''
MDScreen:
    md_bg_color: 0, 0, 0, 1
    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        MDLabel:
            text: "ERRORE CRITICO: {str(e)}"
            color: 1, 0, 0, 1
            halign: "center"
            font_style: "H5"
        MDLabel:
            text: "ROOT: {files_root}"
            color: 1, 1, 1, 1
            font_style: "Caption"
            size_hint_y: None
            height: self.texture_size[1]
        MDLabel:
            text: "ASSETS: {files_assets}"
            color: 0, 1, 0, 1
            font_style: "Caption"
            size_hint_y: None
            height: self.texture_size[1]
        MDLabel:
            text: "BUNDLE: {files_bundle}"
            color: 0.5, 0.5, 1, 1
            font_style: "Caption"
            size_hint_y: None
            height: self.texture_size[1]
        MDLabel:
            text: "B_ASSETS: {files_bundle_assets}"
            color: 1, 0.5, 0, 1
            font_style: "Caption"
            size_hint_y: None
            height: self.texture_size[1]
            ''')

    ErrorApp().run()
    sys.exit(1)

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
        try:
            if platform == 'android':
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE, 
                    Permission.READ_EXTERNAL_STORAGE, 
                    Permission.INTERNET
                ])
                
            BUILD_VERSION = "Build 65" # Kivy user_data_dir strategy
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.accent_palette = "Teal"
            self.theme_cls.theme_style = "Dark"
            
            if not ALLMACore:
                from kivy.uix.label import Label
                msg = globals().get('IMPORT_ERROR_MSG', 'Unknown Import Error')
                return Label(text=f"ERRORE CRITICO ({BUILD_VERSION}):\n{msg}", halign="center", text_size=(None, None))

            # Carica i file KV con percorso assoluto sicuro
            base_path = os.path.dirname(os.path.abspath(__file__))
            try:
                Builder.load_file(os.path.join(base_path, "UI/chat_screen.kv"))
                Builder.load_file(os.path.join(base_path, "UI/download_screen.kv"))
            except Exception as kv_err:
                logging.error(f"KV Load Error: {kv_err}")
                from kivy.uix.label import Label
                return Label(text=f"KV ERROR: {kv_err}")
            
            self.sm = ScreenManager()
            
            # Controlla se i modelli esistono
            try:
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
            except Exception as downloader_err:
                 logging.critical(f"Downloader Crash: {downloader_err}", exc_info=True)
                 return self.show_crash_ui(f"DOWNLOADER ERROR: {downloader_err}")
                
            return self.sm
        except Exception as e:
            logging.critical(f"BUILD CRASH: {e}", exc_info=True)
            return self.show_crash_ui(f"BUILD CRASH: {e}")

    def initialize_allma(self):
        try:
            if not hasattr(self, 'allma'):
                # Passiamo il path dei modelli ad ALLMACore
                models_dir = self.downloader._get_models_dir()
                
                # Definisci path assoluto per il DB per evitare errori "No such file"
                if platform == 'android':
                    from android.storage import app_storage_path
                    storage = app_storage_path()
                    # Assicurati che storage esista
                    if not os.path.exists(storage):
                        try:
                            os.makedirs(storage)
                            logging.info(f"Created storage dir: {storage}")
                        except Exception as create_err:
                            logging.error(f"Failed to create storage dir: {create_err}")
                            
                    db_path = os.path.join(storage, 'allma.db')
                    # Test write permissions
                    try:
                        with open(os.path.join(storage, 'test_write.txt'), 'w') as f:
                            f.write("test")
                        logging.info("Write permission OK")
                    except Exception as write_err:
                        logging.critical(f"Write permission FAILED: {write_err}")
                else:
                    db_path = 'allma.db'
                
                logging.info(f"Initializing ALLMA with models={models_dir}, db={db_path}")
                
                # Check if DB file location is valid
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                     os.makedirs(db_dir)
                
                # Manual Touch of DB File
                if not os.path.exists(db_path):
                    logging.info("DB file doesn't exist, creating empty file...")
                    with open(db_path, 'w') as f:
                        pass
                
                self.allma = ALLMACore(
                    mobile_mode=True,
                    models_dir=models_dir,
                    db_path=db_path
                )
        except Exception as e:
             logging.critical(f"ALLMA INIT CRASH: {e}", exc_info=True)
             if hasattr(self, 'sm'):
                 from kivy.uix.label import Label
                 # Gather debugging info
                 try:
                     storage_files = str(os.listdir(os.path.dirname(db_path)))
                 except:
                     storage_files = "Cannot list dir"
                     
                 self.sm.clear_widgets()
                 self.sm.add_widget(MDScreen(name='crash'))
                 # Mostra più contesto nell'errore
                 error_details = f"CRASH (Build 62):\n{str(e)}\n\nDB Path: {db_path}\nFiles: {storage_files}"
                 self.sm.get_screen('crash').add_widget(Label(text=error_details, halign='center'))
                 self.sm.current = 'crash'
    
    def show_crash_ui(self, error_msg):
        from kivy.uix.label import Label
        return Label(text=f"RUNTIME CRASH:\n{error_msg}\n\nCheck logs.", halign="center")

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        logging.critical(f"CRITICAL CRASH: {e}", exc_info=True)
        # Se siamo su Android, proviamo a salvare l'errore in un file visibile se possibile
        if platform == 'android':
            from android.storage import app_storage_path
            try:
                 # Usa app_storage_path() ma catcha errori se non esiste
                path = app_storage_path()
                if not os.path.exists(path):
                    os.makedirs(path)
                with open(os.path.join(path, 'crash_dump.txt'), 'w') as f:
                    f.write(traceback.format_exc())
            except:
                pass
