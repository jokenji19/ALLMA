import os
import sys
import logging
import traceback
import threading
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.uix.screenmanager import ScreenManager
from kivy.utils import platform

# Mantiene logging di base su stdout per debug ADB
logging.basicConfig(level=logging.DEBUG)

# --- EMBEDDED KV STRINGS (Android 16 Fix) ---
KV_CHAT = '''
<ChatScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "ALLMA"
            elevation: 4
            pos_hint: {"top": 1}
            md_bg_color: app.theme_cls.primary_color
            specific_text_color: app.theme_cls.accent_color
            right_action_items: [["dots-vertical", lambda x: app.open_menu()]]

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(10)
            spacing: dp(10)

            RecycleView:
                id: chat_list
                viewclass: 'ChatMessage'
                RecycleBoxLayout:
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(8)

            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                padding: [dp(5), dp(5), dp(5), dp(5)]

                MDTextField:
                    id: message_input
                    hint_text: "Scrivi un messaggio..."
                    mode: "round"
                    fill_color_normal: app.theme_cls.bg_dark
                    text_color_normal: 1, 1, 1, 1
                    size_hint_x: 0.85
                    multiline: False
                    on_text_validate: root.send_message()

                MDIconButton:
                    icon: "send"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    user_font_size: "32sp"
                    size_hint_x: 0.15
                    on_release: root.send_message()

<ChatMessage>:
    size_hint_y: None
    height: self.minimum_height
    padding: dp(10)
    
    MDCard:
        size_hint: None, None
        size: self.minimum_size
        width: min(root.width * 0.8, self.minimum_width)
        pos_hint: {'right': 1} if root.is_user else {'left': 1}
        md_bg_color: app.theme_cls.primary_color if root.is_user else app.theme_cls.accent_color
        radius: [15, 15, 0, 15] if root.is_user else [15, 15, 15, 0]
        padding: dp(10)
        elevation: 2

        MDLabel:
            text: root.text
            color: 1, 1, 1, 1
            size_hint_y: None
            height: self.texture_size[1]
            size_hint_x: None
            width: self.texture_size[0]
            text_size: root.width * 0.7, None
'''

KV_DOWNLOAD = '''
<DownloadScreen>:
    name: 'download'
    
    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        
        MDLabel:
            text: "ALLMA Setup"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Primary"
            size_hint_y: None
            height: self.texture_size[1]
            
        MDLabel:
            text: "Per attivare la mia intelligenza, devo scaricare i miei modelli neurali (circa 1.6 GB). Consigliato Wi-Fi."
            halign: "center"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: self.texture_size[1]
            
        MDBoxLayout:
            orientation: 'vertical'
            spacing: dp(10)
            size_hint_y: None
            height: dp(150)
            
            MDLabel:
                text: "Gemma 2 (2B) - Latest"
                theme_text_color: "Primary"
                
            MDProgressBar:
                id: progress_gemma
                value: 0
                max: 100
                
            MDLabel:
                id: label_gemma
                text: "In attesa..."
                theme_text_color: "Secondary"
                font_style: "Caption"
                
            Widget:
                size_hint_y: None
                height: dp(10)
                
            MDLabel:
                text: "Moondream (Visione)"
                theme_text_color: "Primary"
                
            MDProgressBar:
                id: progress_moondream
                value: 0
                max: 100
                
            MDLabel:
                id: label_moondream
                text: "In attesa..."
                theme_text_color: "Secondary"
                font_style: "Caption"
                
            Widget:
                size_hint_y: None
                height: dp(10)

            Widget:
                size_hint_y: None
                height: dp(10)
                
        Widget:
            # Spacer

        MDFillRoundFlatButton:
            id: btn_start
            text: "AVVIA DOWNLOAD"
            pos_hint: {"center_x": .5}
            on_release: root.start_download()
'''

# --- END EMBEDDED KV ---

# Initialization Constants
ALLMACore = None
ModelDownloader = None
ALLMACore_imported = False
BUILD_VERSION = "Build 128-Diet"

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
            # Check if Core is active
            if not self.app.allma:
                 Clock.schedule_once(lambda dt: self.add_message("ALLMA Initializing... please wait.", is_user=False))
                 return

            # Simula un ID utente fisso per la versione locale
            user_id = "local_user"
            conversation_id = "local_chat"
            
            # Assicurati che la conversazione esista
            if not self.app.allma.conversational_memory.get_conversation_history(conversation_id):
                self.app.allma.start_conversation(user_id)

            response = self.app.allma.process_message(
                user_id,
                conversation_id,
                message
            )
            
            # Aggiorna la UI nel thread principale
            Clock.schedule_once(lambda dt: self.add_message(response.content, is_user=False))
            
        except Exception as e:
            error_msg = f"Errore: {str(e)}"
            logging.error(f"Chat Error: {e}", exc_info=True)
            Clock.schedule_once(lambda dt: self.add_message(error_msg, is_user=False))

class DownloadScreen(MDScreen):
    def start_download(self):
        self.ids.btn_start.disabled = True
        self.ids.btn_start.text = "DOWNLOAD IN CORSO..."
        
        # Lazy load if needed
        global ModelDownloader
        if not ModelDownloader:
             try:
                 from Model.utils.model_downloader import ModelDownloader as MD
                 ModelDownloader = MD
             except ImportError:
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

        def completion_callback(success, error_msg=None):
            Clock.schedule_once(lambda dt: self.on_download_complete(success, error_msg))

        downloader.start_background_download(missing, progress_callback, completion_callback)

    def update_progress(self, model_key, percent, current, total):
        # Update specific progress bars based on model key
        if model_key == 'gemma':
            self.ids.progress_gemma.value = percent
            self.ids.label_gemma.text = f"{percent:.1f}%"
        elif model_key == 'moondream':
            self.ids.progress_moondream.value = percent
            self.ids.label_moondream.text = f"{percent:.1f}%"

    def on_download_complete(self, success, error_msg=None):
        if success:
            self.ids.btn_start.text = "COMPLETATO!"
            Clock.schedule_once(lambda dt: self.go_to_chat(), 1)
        else:
            self.ids.btn_start.disabled = False
            # Show specific error if available
            self.ids.btn_start.text = f"ERRORE: {error_msg}" if error_msg else "ERRORE - RIPROVA"

    def go_to_chat(self):
        app = MDApp.get_running_app()
        # Inizializza ALLMA ora che i modelli ci sono
        app.initialize_allma()
        self.manager.current = 'chat'

class ALLMAApp(MDApp):
    def build(self):
        try:
            # Setup UI immediately
            
            # Placeholder for Injection
            global INCEPTION_BLOB
INCEPTION_BLOB = open(os.path.join(os.path.dirname(__file__), 'assets', 'inception.txt'), 'r').read()
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.accent_palette = "Teal"
            self.theme_cls.theme_style = "Dark"
            
            # Pre-load screens but don't init core yet
            self.sm = ScreenManager()
            
            # Load Embedded KV
            try:
                Builder.load_string(KV_CHAT)
                Builder.load_string(KV_DOWNLOAD)
            except Exception as kv_err:
                logging.error(f"KV Load Error: {kv_err}")
                from kivy.uix.label import Label
                return Label(text=f"KV ERROR: {kv_err}")

            # Add widgets normally
            self.sm.add_widget(ChatScreen(name='chat'))
            self.sm.add_widget(DownloadScreen(name='download'))
            self.sm.current = 'chat'
            
            return self.sm
        except Exception as e:
            logging.critical(f"BUILD CRASH: {e}", exc_info=True)
            return self.show_crash_ui(f"BUILD CRASH: {e}")

    def on_start(self):
        # Schedule startup sequence after UI is shown
        Clock.schedule_once(self.deferred_startup, 1)

    def deferred_startup(self, dt):
        try:
            global BUILD_VERSION
            # Helper to show status on chat screen
            def update_status(msg):
                try:
                    logging.info(f"STATUS UPDATE: {msg}")
                    chat_screen = self.sm.get_screen('chat')
                    if chat_screen:
                        chat_screen.add_message(f"[SYSTEM] {msg}", is_user=False)
                except: pass

            update_status(f"{BUILD_VERSION}: UI Loaded from Embedded KV")
            
            # 1. Request PERMISSIONS
            if platform == 'android':
                 update_status("Requesting Permissions...")
                 from android.permissions import request_permissions, Permission
                 request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE, 
                    Permission.READ_EXTERNAL_STORAGE, 
                    Permission.INTERNET
                 ])

            # 2. Imports and Core Init
            update_status("Loading Core...")
            global ALLMACore, ModelDownloader, ALLMACore_imported
            
            # FIX PATH: ensure libs/Model is findable
            try:
                base_path = os.path.dirname(os.path.abspath(__file__))
                
                # List candidates for where 'libs' might be
                possible_roots = [
                    base_path,
                    os.path.join(base_path, '_python_bundle'),
                    os.path.join(base_path, '_python_bundle', 'site-packages'),
                ]
                
                found_libs = False
                for root_search in possible_roots:
                    if not os.path.exists(root_search):
                         continue
                         
                    # Check for 'libs' folder
                    libs_path = os.path.join(root_search, 'libs')
                    if os.path.exists(libs_path) and os.path.isdir(libs_path):
                         if libs_path not in sys.path:
                             sys.path.append(libs_path)
                             update_status(f"FOUND libs at: {libs_path}")
                             found_libs = True
                             break
                    
                    # Also check if 'Model' is directly in root_search (flattened)
                    model_path = os.path.join(root_search, 'Model')
                    if os.path.exists(model_path) and os.path.isdir(model_path):
                         if root_search not in sys.path:
                             sys.path.append(root_search)
                             update_status(f"FOUND Model at: {model_path} (root added)")
                             found_libs = True # effectively found
                             break

                if not found_libs:
                    update_status(f"WARNING: Model/libs NOT FOUND in roots.")
                    # Debug _python_bundle specifically
                    bundle = os.path.join(base_path, '_python_bundle')
                    if os.path.exists(bundle):
                        update_status(f"Bundle contents: {str(os.listdir(bundle))}")
                        
                        # BUILD 83 ADDITION: Check site-packages
                        sp_path = os.path.join(bundle, 'site-packages')
                        if os.path.exists(sp_path):
                            update_status(f"Site-Packages: {str(os.listdir(sp_path))}")
                            # Check if libs is in site-packages (flattened?)
                            sp_libs = os.path.join(sp_path, 'libs')
                            if os.path.exists(sp_libs):
                                sys.path.append(sp_libs)
                                update_status(f"FOUND libs in site-packages")
                                found_libs = True
                            
                            # Check if Model is in site-packages
                            sp_model = os.path.join(sp_path, 'Model')
                            if os.path.exists(sp_model):
                                sys.path.append(sp_path)
                                update_status(f"FOUND Model in site-packages")
                                found_libs = True
                    else:
                        update_status("Bundle dir missing?")

                if not found_libs:
                    update_status("Strategy: MONOLITH (Build 90)...")
                    try:
                        # Use internal blob
                        # INCEPTION_BLOB is defined at module level (injected)
                        global INCEPTION_BLOB
                        if not INCEPTION_BLOB:
                             update_status("FATAL: INCEPTION_BLOB is empty!")
                             # Raise to trigger except block
                             raise ValueError("Empty Blob")
                             
                        import base64
                        import zipfile
                        import io
                        
                        update_status(f"Blob Found. Len: {len(INCEPTION_BLOB)}")
                        
                        # Decode
                        zip_data = base64.b64decode(INCEPTION_BLOB)
                        # Force fresh extraction by including version in path
                        extract_dir = os.path.join(base_path, f'monolith_brain_{BUILD_VERSION.replace(" ", "_")}')
                        
                        if os.path.exists(extract_dir):
                            try:
                                import shutil
                                shutil.rmtree(extract_dir)
                            except Exception as cleanup_err:
                                update_status(f"Cleanup non-fatal warning: {cleanup_err}")
                        os.makedirs(extract_dir)
                        
                        update_status("Extracting Monolith...")
                        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                            zf.extractall(extract_dir)
                        update_status("Monolith Expanded.")
                        
                        # Add path
                        sys.path.append(extract_dir)
                        if os.path.exists(os.path.join(extract_dir, 'libs')):
                             sys.path.append(os.path.join(extract_dir, 'libs'))
                        
                        found_libs = True
                        
                        # MOCK TORCH dependencies to prevent crash on import
                        # Real torch will be installed/checked later
                        # NOTE: Do NOT re-import sys here, it breaks scope!
                        from unittest.mock import MagicMock
                        
                        class MockTorch(MagicMock):
                            __version__ = '2.0.0'
                            pass
                            
                        if 'torch' not in sys.modules:
                            update_status("Mocking Torch for Startup...")
                            sys.modules['torch'] = MockTorch()
                            sys.modules['torch.nn'] = MagicMock()
                            
                        # Also mock transformers if needed
                        if 'transformers' not in sys.modules:
                             sys.modules['transformers'] = MagicMock()
                             
                    except Exception as ie:
                         update_status(f"Monolith Error: {ie}")

            except Exception as pe:
                update_status(f"Path Patch Error: {pe}")

            try:
                # Lazy Import inside try-block
                from Model.core.allma_core import ALLMACore as AC
                from Model.utils.model_downloader import ModelDownloader as MD
                ALLMACore = AC
                ModelDownloader = MD
                ALLMACore_imported = True
            except ImportError as ie:
                self.safe_trigger_crash(f"Module Import Error: {ie}")
                return

            # check logic
            try:
                self.downloader = ModelDownloader()
                missing_models = self.downloader.check_models_missing()
                
                if missing_models:
                    update_status("Models missing - Switching to Download")
                    self.sm.current = 'download'
                else:
                    update_status("Initializing AI...")
                    self.initialize_allma()
                    update_status("Ready!")
            except Exception as e:
                logging.error(f"Init Error: {e}")
                self.safe_trigger_crash(f"Init Failed: {e}")
            
        except Exception as e:
            logging.critical(f"DEFERRED CRASH: {e}", exc_info=True)
            self.safe_trigger_crash(f"Async Init Crash: {e}")

    @mainthread
    def safe_trigger_crash(self, error_msg):
        """Thread-safe method to switch to crash screen"""
        try:
            logging.critical(f"CRASH TRIGGERED: {error_msg}")
            if not hasattr(self, 'sm'):
                return

            # Check if crash screen already exists
            if not self.sm.has_screen('crash'):
                from kivymd.uix.screen import MDScreen
                from kivymd.uix.label import MDLabel
                from kivymd.uix.boxlayout import MDBoxLayout
                
                crash_screen = MDScreen(name='crash')
                
                # Layout for centering
                layout = MDBoxLayout(orientation='vertical', padding="20dp")
                
                # Title
                lbl_title = MDLabel(
                    text="CRASH REPORT", 
                    halign="center", 
                    theme_text_color="Error",
                    font_style="H4",
                    size_hint_y=None, 
                    height="100dp"
                )
                
                # Details (White text for visibility)
                lbl_msg = MDLabel(
                    text=f"Error Info:\n{str(error_msg)}", 
                    halign="center", 
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1), 
                    size_hint_y=0.8
                )
                
                layout.add_widget(lbl_title)
                layout.add_widget(lbl_msg)
                crash_screen.add_widget(layout)
                
                self.sm.add_widget(crash_screen)
            
            # Switch without creating a new transition loop if already there
            if self.sm.current != 'crash':
                self.sm.current = 'crash'
            
        except Exception as ui_e:
            print(f"CRITICAL: Failed to show crash UI: {ui_e}")

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
                        except: pass
                            
                    db_path = os.path.join(storage, 'allma.db')
                    
                    # Manual Touch of DB File
                    if not os.path.exists(db_path):
                         with open(db_path, 'w') as f: pass
                else:
                    db_path = 'allma.db'
                
                logging.info(f"Initializing ALLMA with models={models_dir}, db={db_path}")
                
                # RE-ENABLED CORE INIT
                global ALLMACore
                if ALLMACore:
                    self.allma = ALLMACore(
                        mobile_mode=True,
                        models_dir=models_dir,
                        db_path=db_path
                    )
                else:
                    logging.error("ALLMACore Class is None in initialize_allma")

        except Exception as e:
             logging.critical(f"ALLMA INIT CRASH: {e}", exc_info=True)
             self.safe_trigger_crash(f"Core Init Failed: {e}")
    
    def show_crash_ui(self, error_msg):
        from kivy.uix.label import Label
        return Label(text=f"RUNTIME CRASH:\n{error_msg}\n\nCheck logs.", halign="center")

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        print(f"BOOTSTRAP CRASH: {e}")
