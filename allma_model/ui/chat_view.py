from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget, MDList
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawer
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.recycleview import MDRecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.clock import Clock
from kivy.lang import Builder
from threading import Thread
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp

# Import Theme
from allma_model.ui.theme import Theme
from allma_model.core.allma_core import ALLMACore

# Register Theme for KV
from kivy.factory import Factory
Factory.register('Theme', cls=Theme)

Builder.load_string('''
<ChatView>:
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: 0, 0, 0, 0
        
        MDLabel:
            text: "Initializing Web Interface..."
            halign: "center"
            theme_text_color: "Hint"
''')

class ChatView(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core = None
        self.bridge = None
        self.conversation_id = None
        self.is_initialized = False

        if self.is_initialized:
            return
            
        print("ChatView: Initializing...")
        
        # Initialize Core
        try:
            from allma_model.ui.webview_bridge import WebViewBridge
            from allma_model.core.allma_core import ALLMACore
            
            # Determine Models Directory
            from kivy.utils import platform
            import os
            
            models_dir = None
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    models_dir = os.path.join(app_storage_path(), 'models')
                except ImportError:
                    # Fallback if android module not found (should not happen on device)
                    models_dir = "/data/user/0/org.allma.allma_prime/files/models"
            else:
                models_dir = os.path.join(os.getcwd(), 'models')
            
            print(f"ChatView: Initializing Core with models_dir={models_dir}")
            
            # Initialize with Model Path
            self.core = ALLMACore(models_dir=models_dir)
            
            # Start a conversation session
            self.conversation_id = self.core.start_conversation("user_default")
            print(f"ChatView: Started conversation {self.conversation_id}")
            
            # Define callback for JS messages (Input from User)
            def on_js_message(message):
                print(f"Message from WebView: {message}")
                
                try:
                    # Try to parse as JSON for system messages
                    import json
                    data = json.loads(message)
                    
                    if isinstance(data, dict):
                        msg_type = data.get('type')
                        action = data.get('action')
                        
                        # System Actions (Profile)
                        if msg_type == 'system':
                            if action == 'update_profile':
                                name = data.get('name')
                                age = data.get('age')
                                print(f"ChatView: Updating Profile -> {name}, {age}")
                                if self.core:
                                    self.core.update_user_identity(name, int(age) if age else 0)
                            return
                        
                        # UI Actions (Mic / Voice Mode)
                        if msg_type == 'action':
                            if action == 'toggle_mic':
                                print("ChatView: Toggle Mic Requested")
                                if self.stt:
                                    if self.stt.is_listening:
                                        self.stt.stop_listening()
                                    else:
                                        self.stt.start_listening()
                                return
                            
                            if action == 'set_voice_mode':
                                enabled = data.get('enabled', False)
                                self.voice_mode_enabled = enabled
                                print(f"ChatView: Voice Mode Set -> {enabled}")
                                # Auto-start listening if opening voice mode
                                if enabled and self.stt and not self.stt.is_listening:
                                    self.stt.start_listening()
                                # Auto-stop listening if closing voice mode
                                if not enabled and self.stt and self.stt.is_listening:
                                    self.stt.stop_listening()
                                return
                        
                except Exception as e:
                    # Not JSON or simple string, standard chat message
                    pass

                # Send to Core (Standard Chat)
                Thread(target=self.process_message, args=(message,)).start()
                
            # Initialize TTS Engine
            try:
                from allma_model.voice_system.tts_engine import TTSEngine
                self.tts = TTSEngine()
                print("ChatView: TTS Engine Linked.")
            except Exception as e:
                print(f"ChatView: TTS Init Failed: {e}")
                self.tts = None

            # Initialize Bridge
            self.bridge = WebViewBridge(on_js_message)
            self.is_initialized = True
            self.voice_mode_enabled = False # Track Voice Mode State
            
            # Initialize STT Engine
            try:
                from allma_model.voice_system.stt_engine import STTEngine
                # Callback: When text is recognized
                def on_stt_text(text):
                    print(f"ChatView: STT Recognized -> {text}")
                    
                    if self.voice_mode_enabled:
                        # Route to Voice Overlay
                        if self.bridge:
                            self.bridge.update_voice_text(text)
                            # Optional: Auto-Send after silence?
                            # For now, let's keep it simple: Just visualize.
                            # The user might need a "Send" trigger or silence detection.
                            # But per user request: "voglio vedere su quella modalità vocale anche le parole che pronuncio"
                    else:
                        # Standard Chat Input
                        if self.bridge:
                            self.bridge.set_input_text(text)
                
                self.stt = STTEngine(on_stt_text)
                print("ChatView: STT Engine Linked.")
            except Exception as e:
                print(f"ChatView: STT Init Failed: {e}")
                self.stt = None

            # Start Learning Status Loop (Every 5 seconds)
            Clock.schedule_interval(self.update_learning_status, 5.0)
            
        except Exception as e:
            print(f"Error initializing ChatView: {e}")
            import traceback
            traceback.print_exc()

    
    def process_message(self, user_text):
        if not self.core:
            return

        # BUG FIX: Ignore JSON control messages leaking into chat
        if user_text.strip().startswith('{') and '"type":' in user_text:
             print(f"ChatView: Ignoring Control Message in Chat -> {user_text}")
             return

        try:
            # Call the ACTUAL Core API
            print(f"Processing message: {user_text}")
            
            # Start Stream UI
            self.bridge.start_stream()
            
            # Stop any previous speech & Clear Queue
            if self.tts:
                self.tts.stop()
            
            # TTS Buffer
            tts_buffer = ""
            
            def on_stream_data(data):
                nonlocal tts_buffer
                msg_type = data.get('type')
                content = data.get('content')
                
                if not content: return
                
                is_thought = (msg_type == 'thought')
                self.bridge.stream_chunk(content, is_thought)
                
                # TTS Logic: Accumulate and speak on punctuation/phrases
                if not is_thought and self.tts and self.voice_mode_enabled:
                    tts_buffer += content
                    
                    # Delimiters for natural pauses
                    delimiters = ['.', '!', '?', '\n', ',', ';', ':']
                    
                    while True:
                        # Find the earliest delimiter
                        earliest_idx = -1
                        for d in delimiters:
                            try:
                                idx = tts_buffer.index(d)
                                if earliest_idx == -1 or idx < earliest_idx:
                                    earliest_idx = idx
                            except ValueError:
                                continue
                        
                        if earliest_idx != -1:
                            # Extract phrase INCLUDING the delimiter (pause)
                            phrase = tts_buffer[:earliest_idx+1]
                            tts_buffer = tts_buffer[earliest_idx+1:]
                            
                            if phrase.strip():
                                self.tts.speak(phrase.strip())
                        else:
                            # No more delimiters, wait for more data
                            break
            
            # Call Core with Callback
            processed_response = self.core.process_message(
                user_id="user_default",
                conversation_id=self.conversation_id,
                message=user_text,
                stream_callback=on_stream_data
            )
            
            # End Stream
            self.bridge.end_stream()
            
            # Flush remaining TTS
            if self.tts and tts_buffer.strip() and self.voice_mode_enabled:
                self.tts.speak(tts_buffer.strip())
            
            # Fallback checks?
            if not processed_response.is_valid:
                 self.bridge.stream_chunk("\n[Errore Generazione]", False)

        except Exception as e:
            print(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            self.bridge.end_stream()

    def update_learning_status(self, dt):
        if not self.core or not self.bridge:
            return
            
        try:
             # --- CALCOLO REALISTICO LIFELONG LEARNING ---
             # Recupera metriche dal profilo utente (o calcola da memoria)
             msg_count = 0
             days_active = 0.0
             
             # Tentativo 1: UserProfile
             if hasattr(self.core, 'user_profile') and self.core.user_profile:
                 metrics = self.core.user_profile.interaction_metrics
                 msg_count = metrics.total_interactions
                 # Calcola giorni attivi
                 import time
                 first_ts = metrics.first_interaction_timestamp
                 days_active = (time.time() - first_ts) / 86400.0
             
             # Tentativo 2: Fallback su ConversationalMemory se msg_count è 0 (profilo non persistito)
             if msg_count == 0 and hasattr(self.core, 'conversational_memory'):
                  if hasattr(self.core.conversational_memory, 'messages'):
                       msg_count = len(self.core.conversational_memory.messages)
                       # Stima giorni (grezza) se non abbiamo timestamp preciso
                       if msg_count > 0:
                           days_active = 0.1 # Almeno iniziata
             
             # --- FORMULA DI EVOLUZIONE ---
             import math
             
             if msg_count < 20:
                 # FASE 0-10% (Onboarding - Primi passi)
                 # Lineare veloce: 20 msg = 10%
                 synergy_percent = (msg_count / 20.0) * 10.0
             else:
                 # FASE 10-100% (Logaritmica - La vera scalata)
                 # log10(20) ~= 1.3  -> 10%
                 # log10(100) = 2    -> 30%
                 # log10(1000) = 3   -> 60%
                 # log10(10000) = 4  -> 90%
                 
                 log_val = math.log10(msg_count)
                 # Mappiamo range [1.3, 4.0] su [10, 90]
                 # Slope ~ 30
                 synergy_percent = 10.0 + 30.0 * (log_val - 1.301)
                 
                 # Bonus Tempo: +1% per ogni giorno di attività (Max 10%)
                 time_bonus = min(10.0, days_active * 1.0)
                 synergy_percent += time_bonus

             # Cap a 100%
             synergy_percent = min(100.0, max(0.0, synergy_percent))
             
             # Determina Stato
             status_text = "Simbiosi Attiva"
             if synergy_percent < 10: status_text = "Analisi Iniziale"
             elif synergy_percent < 30: status_text = "Costruzione Pattern"
             elif synergy_percent < 60: status_text = "Simbiosi Neurale" 
             elif synergy_percent < 90: status_text = "Coscienza Condivisa"
             else: status_text = "Unità Completa"
             
             # Formatta per UI (Intero)
             final_score = int(synergy_percent)
             
             self.bridge.update_synergy(final_score, status_text)
             
        except Exception as e:
            # print(f"Error updating learning status: {e}") # Silenzia log per pulizia
            pass
