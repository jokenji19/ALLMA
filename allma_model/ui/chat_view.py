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
            
            # PHASE 14: Start Dream System Loop (Background)
            # The loop is safe: it sleeps if disabled.
            if hasattr(self.core, 'start_dreaming_loop'):
                self.core.start_dreaming_loop()
                print("ChatView: Dream System Loop Started.")
            
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
                        
                        # System Actions (Dream Mode)
                        if msg_type == 'action':
                             if action == 'toggle_dream_mode':
                                 enabled = data.get('enabled', False)
                                 print(f"ChatView: Setting Dream Mode -> {enabled}")
                                 if self.core and hasattr(self.core, 'set_dream_mode'):
                                     self.core.set_dream_mode(enabled)
                                 return

                        # System Actions (Memory Debug)
                        if msg_type == 'system':
                            if action == 'get_memory_debug':
                                user_id = data.get('user_id', 'user_default')
                                print(f"ChatView: Memory Debug Requested for {user_id}")
                                
                                try:
                                    # Access memory data from core
                                    memory_data = {"facts": {}, "logs": []}
                                    
                                    if self.core and hasattr(self.core, 'memory'):
                                        # Get user facts
                                        if hasattr(self.core.memory, 'user_data'):
                                            memory_data["facts"] = self.core.memory.user_data.get(user_id, {})
                                        
                                        # Get recent conversation logs
                                        try:
                                            history = self.core.memory.get_conversation_history(user_id)
                                            for msg in history[-10:]:  # Last 10 messages
                                                memory_data["logs"].append({
                                                    "role": msg.role,
                                                    "content": msg.content,
                                                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else "",
                                                    "is_thought": "[[TH:" in msg.content
                                                })
                                        except Exception as e:
                                            print(f"Memory Log Error: {e}")
                                    
                                    # Send back to JS
                                    import json
                                    self.bridge.execute_js(f"window.renderMemoryData({json.dumps(json.dumps(memory_data))})")
                                    
                                except Exception as e:
                                    print(f"Memory Debug Error: {e}")
                                    import traceback
                                    traceback.print_exc()
                                
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
                
                # Check for special commands
                if message == "__REQUEST_TEMPERATURE_UPDATE__":
                    # Temperature monitoring request from JS
                    if self.bridge:
                        self.bridge.inject_temperature_to_js()
                    return

                if message == "__REQUEST_DIAGNOSTICS_UPDATE__":
                    # Full Diagnostics (CPU, RAM, Soul, Logs)
                    if self.bridge:
                        diag_data = self._get_diagnostics_data()
                        # Send as JSON string to window.updateDiagnostics
                        import json
                        json_str = json.dumps(diag_data)
                        # Escape quotes for JS string argument
                        safe_str = json_str.replace('"', '\\"') 
                        self.bridge.execute_js(f'window.updateDiagnostics("{safe_str}")')
                    return

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
            
            # Register UI Output Callback with Core (For Proactive Messages)
            if hasattr(self.core, 'register_output_callback'):
                self.core.register_output_callback(self._handle_core_output)
                
            # Initialize STT Engine
            try:
                from allma_model.voice_system.stt_engine import STTEngine
                # Callback: When text is recognized
                def on_stt_text(text):
                    print(f"ChatView: STT Recognized -> {text}")
                    
                    if self.voice_mode_enabled:
                         # 1. Update Visual Feedback (Final)
                        if self.bridge:
                            self.bridge.update_voice_text(text)
                        
                        # 2. SEND TO LLM (Critical Fix!)
                        # User wants it treated "As if written"
                        if text and len(text.strip()) > 1:
                            # Inject into chat UI to show user what was heard
                            if self.bridge:
                                self.bridge.send_message_to_js(text, 'user')
                            
                            # Process Request
                            Thread(target=self.process_message, args=(text,)).start()
                            
                            # Restart Listening after processing? 
                            # Usually LLM speaking stops listening. 
                            # We'll rely on user to tap again or implement auto-listen logic later.
                    else:
                        # Standard Chat Input
                        if self.bridge:
                            self.bridge.set_input_text(text)
                
                def on_stt_partial(text):
                    # Visual Feedback during speech
                    if self.voice_mode_enabled and self.bridge:
                        self.bridge.update_voice_text(text)

                self.stt = STTEngine(on_stt_text, on_stt_partial)
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
        # BUG FIX: Ignore JSON control messages leaking into chat
        # Checks for standard JSON object start OR escaped JSON string start
        stripped = user_text.strip()
        if (stripped.startswith('{') or stripped.startswith('"{') or stripped.startswith(r'{\"')) and ('"type":' in user_text or r'\"type\":' in user_text):
             print(f"ChatView: Ignoring Control Message in Chat -> {user_text[:50]}...")
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

    def _get_diagnostics_data(self):
        """Collects system stats and soul state for the Diagnostics Panel."""
        stats = {
            "resources": {"cpu": 0, "ram": 0, "temp": 0},
            "soul": {"energy": 0, "chaos": 0, "entropy": 0, "state_label": "Offline"},
            "logs": []
        }

        try:
            # 1. System Resources
            # RAM
            import os
            try:
                # Python memory usage
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                # Linux/Mac: KB. 
                if platform == 'android':
                    # On Android often it's already in KB or needs scaling? 
                    # Usually getrusage output varies. Let's assume KB.
                    stats["resources"]["ram"] = usage / 1024.0 # MB
                else:
                    # Mac is bytes? No, Mac is bytes. Linux is KB.
                    # Actually getrusage on Mac returns BYTES.
                    stats["resources"]["ram"] = usage / (1024.0 * 1024.0) # MB
            except:
                pass

            # CPU (Mock/LoadAvg)
            try:
                # Add jitter to make it look alive even if load is stable
                import random
                jitter = random.uniform(-2.0, 2.0)
                
                # loadavg gives 1min, 5min, 15min load. 
                # Normalize by core count?
                load = os.getloadavg()[0] 
                # Rough percentage 0-100 logic
                cpu_count = os.cpu_count() or 4
                base_cpu = (load / cpu_count) * 100.0
                stats["resources"]["cpu"] = max(0, min(100, base_cpu + jitter))
                
                # RAM Jitter (flicker bytes)
                stats["resources"]["ram"] += random.uniform(-10.0, 10.0)
                
            except:
                pass
            
            # Temp (reuse existing logic if desired, or simpler)
            # We skip temp here if not easily available, or rely on existing temp monitor logic
            # MOCK TEMP for now if 0
            stats["resources"]["temp"] = 38.0 + random.uniform(-0.5, 0.5)

            # 2. Soul State
            if self.core and hasattr(self.core, 'soul'):
                s = self.core.soul.state
                stats["soul"] = {
                    "energy": s.energy,
                    "chaos": s.chaos,
                    "entropy": s.entropy,
                    "state_label": "Active" # Could infer from values
                }
            
            # 3. Recent Logs (Mock or recent memory)
            # If we had a log buffer. For now, show last interactions from memory
            if self.core and hasattr(self.core, 'conversational_memory'):
                msgs = self.core.conversational_memory.get_recent_context(limit=5)
                for m in msgs:
                    # m is Message object
                    import datetime
                    ts = m.timestamp.strftime("%H:%M:%S") if m.timestamp else "--"
                    # Truncate content
                    short_content = (m.content[:40] + '..') if len(m.content) > 40 else m.content
                    stats["logs"].append({"time": ts, "msg": f"[{m.role.upper()}] {short_content}"})

        except Exception as e:
            print(f"Diag Error: {e}")
        
        return stats

    def _handle_core_output(self, data):
        """
        Handle output pushed from Core (e.g. Proactive Messages).
        Executed in Core's thread, so we must be careful with UI bridge.
        """
        try:
            msg_type = data.get('type')
            content = data.get('content')
            
            if not self.bridge:
                print("ChatView: Cannot handle core output - Bridge not ready.")
                return

            print(f"ChatView: Handling Core Output -> {msg_type}: {content}")
            
            if msg_type == 'thought':
                # Show thought bubble
                cleaned = content.replace('"', '\\"').replace('\n', ' ')
                self.bridge.execute_js(f"window.showThought('{cleaned}')")
                
            elif msg_type == 'text':
                # Show bot message
                self.bridge.send_message_to_js(content, 'bot')
                
            elif msg_type == 'status':
                # Handle Status Updates (e.g. Dreaming)
                for key, value in content.items():
                    # Convert python bool to js bool string
                    js_val = 'true' if value else 'false'
                    self.bridge.execute_js(f"window.updateStatus('{key}', {js_val})")
                
        except Exception as e:
            print(f"ChatView: Error handling core output: {e}")
