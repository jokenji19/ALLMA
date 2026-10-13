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
from allma_model.ui.chat_session import ChatSession
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled
from allma_model.ui.theme import Theme
from allma_model.core.allma_core import ALLMACore

# Register Theme for KV
from kivy.factory import Factory
Factory.register('Theme', cls=Theme)


class ChatView(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from threading import Event
        from allma_model.ui.cosmic_widgets import StartupPanel
        self._startup_cancelled = Event()
        self.intro = StartupPanel()
        self.add_widget(self.intro)
        self.intro.set_stage('Carico il modello…','Preparo il modello locale e recupero la memoria.',1)
        self.core = None
        self.bridge = None
        self.conversation_id = None
        self.is_initialized = False
        self.current_voice_params = None
        self.voice_stack_status = {}
        self.voice_mode_enabled = False
        self.tts = None
        self.stt = None

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
            db_path = "allma.db"
            if platform == "android":
                from allma_model.utils.runtime_storage import prepare_runtime_storage
                storage_dir = prepare_runtime_storage(os.path.dirname(models_dir), os.getcwd())
                db_path = os.path.join(storage_dir, "allma.db")
            Thread(target=self._load_core,args=(db_path,models_dir,platform == 'android'),
                   daemon=True,name='ALLMA-ModelStartup').start()
        except Exception as error:
            self._accept_core(None,str(error))

    def _load_core(self, db_path, models_dir, mobile):
        core = None
        try:
            core = ALLMACore(db_path=db_path, models_dir=models_dir, mobile_mode=mobile)
            if mobile and not self._startup_cancelled.is_set():
                core._ensure_mobile_llm()
                if getattr(core, '_llm_ready', False) is not True:
                    raise RuntimeError('Non riesco a caricare il modello. Riapri ALLMA per riprovare.')
            if self._startup_cancelled.is_set():
                core.close()
                return
            Clock.schedule_once(lambda dt: self._accept_core(core,None))
        except Exception as error:
            if core is not None:
                try:
                    core.close()
                except Exception:
                    pass
            message = str(error)
            Clock.schedule_once(lambda dt: self._accept_core(None,message))

    def cancel_startup(self):
        self._startup_cancelled.set()
        self.intro.stop()

    def _accept_core(self, core, error):
        if self._startup_cancelled.is_set():
            if core:
                Thread(target=core.close,daemon=True,name='ALLMA-StartupCleanup').start()
            return
        if error:
            self.intro.set_stage('Avvio non riuscito',error,1,busy=False)
            return
        self.core = core
        self.intro.set_stage('Apro la chat…','Modello e memoria sono pronti.',2)
        try:
            from allma_model.ui.webview_bridge import WebViewBridge
            # Start a conversation session
            self.chat_session = ChatSession(lambda: self.core.start_conversation("user_default"))
            self.conversation_id = self.chat_session.conversation_id
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
                        if msg_type == 'action' and action == 'review_dream_hypothesis':
                            try:
                                self.core.review_dream_hypothesis('user_default', data.get('id'),
                                    data.get('decision'), correction=data.get('correction', ''),
                                    note=data.get('note', ''), expected_revision=data.get('revision', 0))
                                result = {'ok': True, 'reviewed_id': data.get('id'), **self.core.get_dream_review_state('user_default')}
                            except Exception as error:
                                safe_error = str(error) if isinstance(error, ValueError) else 'Non è stato possibile salvare. Riprova.'
                                result = {'ok': False, 'error': safe_error}
                                try:
                                    result.update(self.core.get_dream_review_state('user_default'))
                                except Exception:
                                    pass
                            self.bridge.execute_js(f"window.dreamReviewResult({json.dumps(result)})")
                            return
                        if msg_type == 'action' and action == 'set_theme':
                            from allma_model.ui.android_bars import AndroidBars
                            AndroidBars.set_dark(data.get('dark') is True)
                            return
                        
                        if msg_type == 'action' and action in ('new_chat', 'cancel_generation'):
                            if self.stt:
                                self.stt.stop_listening(cancel=True)
                            if self.tts:
                                self.tts.stop()
                            if action == 'cancel_generation':
                                self.chat_session.cancel()
                            else:
                                try:
                                    conversation = self.chat_session.new_conversation()
                                    if conversation is not None:
                                        self.conversation_id = conversation
                                        self.bridge.call_js_function('newChatReady', json.dumps(conversation))
                                except Exception:
                                    self.bridge.call_js_function('newChatFailed')
                            return

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
                                            from allma_model.utils.repetition_guard import memory_display
                                            history = self.core.memory.get_conversation_history(user_id)
                                            for msg in history[-10:]:  # Last 10 messages
                                                memory_data["logs"].append({
                                                    "role": msg.role,
                                                    "content": memory_display(msg.content,msg.role),
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
                                self.toggle_voice_listening()
                                return
                            if action == 'set_voice_mode':
                                self.set_voice_mode(data.get('enabled') is True)
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
                        # Pass object directly to JS
                        import json
                        self.bridge.execute_js(f"window.updateDiagnostics({json.dumps(diag_data)})")
                    return

                if message == "__REQUEST_DREAM_HISTORY__":
                    if self.bridge and hasattr(self.core, 'dream_manager'):
                        try:
                            import json
                            history = self.core.dream_manager.get_history(user_id='user_default')
                            safe_data = json.dumps(history)
                            self.bridge.execute_js(f"window.restoreDreamHistory({safe_data})")
                            reviews = self.core.get_dream_review_state('user_default')
                            self.bridge.execute_js(f"window.restoreDreamReviews({json.dumps(reviews)})")
                        except Exception as e:
                            print(f"[ChatView] Error fetching dream history: {e}")
                            self.bridge.execute_js('window.dreamReviewResult({ok:false,error:"Archivio delle revisioni non disponibile. Nessuna ipotesi è stata modificata."})')
                    return

                if message == "__REQUEST_MEMORY_UPDATE__":
                    if self.bridge:
                        try:
                            memory_data = {"facts": {}, "logs": []}
                            if self.core:
                                # Popula i "facts" dal profilo utente (se esiste)
                                if hasattr(self.core, 'user_profile') and self.core.user_profile:
                                    prefs = self.core.user_profile.get_preferences()
                                    memory_data["facts"] = {
                                        "Stile Comunicazione": prefs.get('communication_style', 'neutral'),
                                        "Sensibilità Emotiva (0-1)": f"{prefs.get('emotional_sensitivity', 0.5):.2f}",
                                        "Coinvolgimento Sociale (0-1)": f"{prefs.get('social_engagement', 0.5):.2f}",
                                    }
                                    topics = prefs.get('favorite_topics', [])
                                    if topics:
                                        memory_data["facts"]["Argomenti Preferiti"] = ", ".join(topics)

                                # Aggiungi la cronologia vettoriale se disponibile
                                if hasattr(self.core, 'conversational_memory') and self.core.conversational_memory:
                                    mem = self.core.conversational_memory
                                    if hasattr(mem, 'vector_engine') and mem.vector_engine:
                                        memory_data["facts"]["Vettori Memorizzati"] = str(mem.vector_engine.count())

                                    # Popola i Logs (ultimi 10 messaggi)
                                    history = []
                                    if hasattr(mem, 'messages') and mem.messages:
                                        history = mem.messages[-10:]

                                    from allma_model.utils.repetition_guard import memory_display
                                    for msg in history:
                                        ts = msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and hasattr(msg.timestamp, 'isoformat') else ""
                                        role = getattr(msg, 'role', 'system')
                                        content = memory_display(getattr(msg, 'content', ''),role)
                                        memory_data["logs"].append({
                                            "role": role,
                                            "content": content,
                                            "timestamp": ts,
                                            "is_thought": '[[TH:' in content
                                        })

                            import json
                            safe_data = json.dumps(memory_data)
                            self.bridge.execute_js(f"window.updateMemory({safe_data})")
                        except Exception as e:
                            print(f"[ChatView] Error fetching memory: {e}")
                            import traceback
                            traceback.print_exc()
                    return

                # Send to Core (Standard Chat)
                self.submit_message(message)
                
            # Initialize TTS Engine
            try:
                from allma_model.voice_system.tts_engine import TTSEngine
                self.tts = TTSEngine(on_state=self._on_tts_state)
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
                    print("ChatView: STT final result received.")
                    
                    if self.voice_mode_enabled:
                         # 1. Update Visual Feedback (Final)
                        if self.bridge:
                            self.bridge.update_voice_text(text)
                        
                        # 2. SEND TO LLM (Critical Fix!)
                        # User wants it treated "As if written"
                        if text and text.strip():
                            if not self.submit_message(str(text), echo_user=True):
                                self._voice_state('idle', 'Attendi la risposta oppure interrompila.')

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

                self.stt = STTEngine(on_stt_text, on_stt_partial, on_state=self._on_stt_state, on_level=self._on_voice_level)
                print("ChatView: STT Engine Linked.")
            except Exception as e:
                print(f"ChatView: STT Init Failed: {e}")
                self.stt = None

            self._report_voice_stack_status()

            # Start Learning Status Loop (Every 5 seconds)
            self._learning_status_event = Clock.schedule_interval(self.update_learning_status, 5.0)
            self.is_initialized = True
            self.intro.stop()
            
        except Exception as e:
            self.intro.set_stage('Interfaccia non disponibile',str(e),2,busy=False)
            print(f"Error initializing ChatView: {e}")
            import traceback
            traceback.print_exc()

    
    def submit_message(self, user_text, echo_user=False):
        """Reserve the turn before starting a worker, so reset/cancel cannot overtake it."""
        if not self.core or not isinstance(user_text, str) or not user_text.strip():
            return False
        import json
        try:
            control = json.loads(user_text)
            if isinstance(control, dict) and control.get('type') in ('system', 'action'):
                return False
        except (ValueError, TypeError):
            pass
        turn = self.chat_session.begin()
        if turn is None:
            self.bridge.call_js_function('chatNotice', '"Attendi la risposta o premi Interrompi."')
            return False
        turn.voice_delivery = bool(self.voice_mode_enabled)
        try:
            if getattr(self, 'stt', None):
                self.stt.stop_listening(cancel=True)
            Thread(target=self.process_message, args=(user_text,),
                   kwargs={'echo_user': echo_user, 'turn': turn}, daemon=True).start()
        except Exception:
            self.chat_session.finish(turn)
            self.bridge.call_js_function('newChatFailed')
            raise
        return True

    def process_message(self, user_text, echo_user=False, turn=None):
        if turn is None:
            turn = self.chat_session.begin()
        if turn is None:
            self.bridge.call_js_function('chatNotice', '"Attendi la risposta o premi Interrompi."')
            return

        try:
            # Call the ACTUAL Core API
            print(f"Processing message: {user_text}")
            
            # Start Stream UI
            if echo_user:
                self.bridge.send_message_to_js(user_text, "user")
            self.bridge.start_stream(turn.request_id)
            
            # Stop any previous speech & Clear Queue
            if self.tts:
                self.tts.stop()
            
            voice_params = None
            
            def on_stream_data(data):
                check_cancelled(turn.cancelled)
                msg_type = data.get('type')
                content = data.get('content')
                
                if not content: return
                
                is_thought = (msg_type == 'thought')
                self.bridge.stream_chunk(content, is_thought, turn.request_id)
                
            # Call Core with Callback
            check_cancelled(turn.cancelled)
            processed_response = self.core.process_message(
                user_id="user_default",
                conversation_id=turn.conversation_id,
                message=user_text,
                context={'delivery_mode': 'voice'} if getattr(turn, 'voice_delivery', self.voice_mode_enabled) else None,
                cancel_event=turn.cancelled,
                stream_callback=on_stream_data
            )
            
            # End Stream
            check_cancelled(turn.cancelled)
            self.bridge.end_stream(processed_response.content, turn.request_id)

            if self.bridge and self.voice_mode_enabled:
                try:
                    metadata = processed_response.metadata if hasattr(processed_response, 'metadata') else {}
                    emotion = processed_response.emotion
                    if hasattr(emotion, "value"):
                        emotion = emotion.value
                    payload = {
                        "emotion": str(emotion),
                        "intensity": metadata.get("emotion_intensity"),
                        "valence": metadata.get("emotion_valence"),
                        "arousal": metadata.get("emotion_arousal"),
                        "dominance": metadata.get("emotion_dominance"),
                        "topic": processed_response.topic if hasattr(processed_response, 'topic') else None,
                        "intent": metadata.get("intent"),
                        "memory_gate_status": metadata.get("memory_gate_status"),
                        "memory_score": metadata.get("memory_score"),
                        "confidence": getattr(processed_response, 'confidence', None),
                        "knowledge_integrated": getattr(processed_response, 'knowledge_integrated', False),
                    }
                    self.bridge.update_voice_internal_state(payload)
                except Exception:
                    pass
            
            # Flush remaining TTS
            if hasattr(processed_response, 'voice_params'):
                self.current_voice_params = processed_response.voice_params
                voice_params = processed_response.voice_params
            
            if self.tts and processed_response.content.strip() and self.voice_mode_enabled:
                voice_params = dict(voice_params or {})
                language = getattr(self.core, '_language_lock', {}).get(turn.conversation_id, 'it')
                voice_params['language'] = {'it': 'it-IT', 'en': 'en-US', 'fr': 'fr-FR', 'de': 'de-DE', 'es': 'es-ES'}.get(language, 'it-IT')
                self.tts.speak(processed_response.content.strip(), voice_params=voice_params, flush=True)
            

        except GenerationCancelled:
            if hasattr(self, '_voice_state'):
                self._voice_state('idle', 'Risposta interrotta. Tocca il microfono per parlare.')
            self.bridge.end_stream('Risposta interrotta.', turn.request_id)
        except Exception:
            import logging
            logging.exception('Errore durante la risposta')
            self._voice_state('error', 'Non sono riuscita a completare la risposta.')
            self.bridge.end_stream('Non sono riuscita a completare la risposta. Riprova.', turn.request_id)
        finally:
            try:
                import json
                conversation = self.chat_session.finish(turn)
                self.bridge.call_js_function("turnFinished", json.dumps(turn.request_id))
                if conversation is not None:
                    self.conversation_id = conversation
                    self.bridge.call_js_function('newChatReady', json.dumps(conversation))
            except Exception:
                import logging
                logging.exception('Impossibile creare la nuova conversazione')
                self.bridge.call_js_function('newChatFailed')

    def _voice_state(self, state, message=''):
        if self.bridge and self.voice_mode_enabled:
            import json
            self.bridge.call_js_function('updateVoiceState', json.dumps({'state': state, 'message': message}))

    def _on_stt_state(self, state, message):
        # A cancelled microphone must not overwrite an active response/playback.
        if state == 'idle' and (self.chat_session.is_busy or (self.tts and self.tts.is_speaking)):
            return
        self._voice_state(state, message)
        self._report_voice_stack_status()

    def _on_tts_state(self, state, message):
        if state == 'ready':
            self._report_voice_stack_status()
            return
        self._voice_state(state, message)
        self._report_voice_stack_status()

    def _on_voice_level(self, level):
        if self.bridge and self.voice_mode_enabled:
            self.bridge.call_js_function('updateVoiceLevel', str(float(level)))

    def set_voice_mode(self, enabled):
        self.voice_mode_enabled = enabled
        if not enabled:
            if self.stt: self.stt.stop_listening(cancel=True)
            if self.tts: self.tts.stop()
            return
        if self.chat_session.is_busy:
            self._voice_state('thinking', 'Sto preparando la risposta…')
        elif self.stt:
            self.stt.start_listening()
        else:
            self._voice_state('error', 'Il riconoscimento vocale non è disponibile.')

    def toggle_voice_listening(self):
        if self.chat_session.is_busy:
            self.chat_session.cancel()
            if self.tts: self.tts.stop()
            self._voice_state('idle', 'Risposta interrotta. Tocca il microfono per parlare.')
            return
        if self.tts: self.tts.stop()
        if not self.stt:
            self._voice_state('error', 'Il riconoscimento vocale non è disponibile.')
        elif self.stt.is_listening:
            self.stt.stop_listening()
        else:
            self.stt.start_listening()

    def suspend_voice(self, close=False):
        self.voice_mode_enabled = False
        if self.stt:
            self.stt.close() if close else self.stt.stop_listening(cancel=True)
        if self.tts:
            self.tts.close() if close else self.tts.stop()
        if self.bridge:
            self.bridge.call_js_function('hideVoiceMode')

    def _report_voice_stack_status(self):
        stt_ok = (True if self.stt.is_ready else False if self.stt.last_error else None) if self.stt else False
        tts_ok = (True if self.tts.is_ready else False if self.tts.last_error else None) if self.tts else False
        llm_ready = bool(getattr(self.core, '_llm_ready', False))
        llm_error = getattr(self.core, '_mobile_llm_error', None)
        models_dir = getattr(self.core, 'models_dir', None)
        llm_ok = True if llm_ready else (False if llm_error else None)
        self.voice_stack_status = {
            'stt': stt_ok,
            'tts': tts_ok,
            'stt_error': getattr(self.stt, 'last_error', None),
            'tts_error': getattr(self.tts, 'last_error', None),
            'stt_on_device': getattr(self.stt, 'on_device', False),
            'voice_name': getattr(self.tts, 'voice_name', None),
            'llm': llm_ok,
            'models_dir': models_dir,
            'llm_error': llm_error
        }

        if self.bridge:
            llm_label = "OK" if llm_ok is True else ("KO" if llm_ok is False else "LOADING")
            status_line = f"Diagnostica Voce → STT: {'OK' if stt_ok else 'KO'} | TTS: {'OK' if tts_ok else 'KO'} | LLM: {llm_label}"
            if llm_ok is False and llm_error:
                status_line += f" | LLM Err: {llm_error}"
            try:
                import json
                status_payload = json.dumps(self.voice_stack_status)
                self.bridge.call_js_function("updateVoiceStackStatus", status_payload)
            except Exception:
                pass
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
            "resources": {"cpu": None, "ram": None, "temp": None},
            "soul": {"energy": 0, "chaos": 0, "entropy": 0, "state_label": "Offline"},
            "logs": []
        }

        try:
            from allma_model.utils.resource_diagnostics import ResourceDiagnostics
            if not hasattr(self, '_resource_diagnostics'):
                self._resource_diagnostics = ResourceDiagnostics()
            stats['resources'] = self._resource_diagnostics.read(
                getattr(self.core, 'system_monitor', None))
            orchestrator = getattr(self.core, 'module_orchestrator', None)
            if orchestrator:
                stats['modules'] = orchestrator.get_stats()
                for name, module in stats['modules']['modules'].items():
                    stats['logs'].append({'time': '', 'msg': f"[MODULO] {name}: {module['last_status']}"})

            # 2. V5 Identity State (Metabolic)
            if self.core and hasattr(self.core, 'identity_engine_v5') and self.core.identity_engine_v5:
                eng = self.core.identity_engine_v5
                # Access internal state directly for diagnostics (lightweight)
                stats["soul"] = {
                    "energy": getattr(eng, '_maturity', 0.0), # Reusing energy bar for Maturity
                    "chaos": getattr(eng, '_base_stability', 0.5), # Reusing chaos bar for Stability 
                    "entropy": 0.0, # Placeholder, computed below
                    "state_label": f"Maturity: {getattr(eng, '_maturity', 0):.2f}"
                }
                
                # Entropy is tracked in the tracker
                if hasattr(eng, 'entropy_tracker'):
                    # We can't easily get 'current' entropy without text, 
                    # but we can get the average variance or similar if exposed.
                    # For now, let's use stability inverted as a proxy for visual feedback if entropy not available
                    stats["soul"]["entropy"] = 1.0 - getattr(eng, '_base_stability', 0.5)

            # Legacy/Fallback Soul (if V5 not active)
            elif self.core and hasattr(self.core, 'soul'):
                s = self.core.soul.state
                stats["soul"] = {
                    "energy": getattr(s, 'energy', 0.5),
                    "chaos": getattr(s, 'chaos', 0.1),
                    "entropy": 1.0 - getattr(s, 'stability', 0.5),
                    "state_label": "Legacy Soul"
                }
            
            # 3. Neuroplasticity Stats
            if self.core and hasattr(self.core, 'neuroplasticity_v5') and self.core.neuroplasticity_v5:
                # Add a specific field for frontend if it supports it, or append to logs
                active_rules = len(self.core.neuroplasticity_v5.rules)
                stats["neuro"] = {"active_rules": active_rules}

            
            # 3. Recent Logs (Mock or recent memory)
            # If we had a log buffer. For now, show last interactions from memory
            if self.core and hasattr(self.core, 'conversational_memory'):
                mem = self.core.conversational_memory
                # Robust history retrieval (Fallback to .messages)
                msgs = []
                if hasattr(mem, 'messages'):
                    msgs = mem.messages[-5:]
                
                for m in msgs:
                    import datetime
                    m_role = getattr(m, 'role', 'SYSTEM')
                    m_content = getattr(m, 'content', '')
                    m_ts = getattr(m, 'timestamp', None)
                    
                    ts = m_ts.strftime("%H:%M:%S") if m_ts else "--:--"
                    # Truncate content
                    short_content = (m_content[:40] + '..') if len(m_content) > 40 else m_content
                    stats["logs"].append({"time": ts, "msg": f"[{m_role.upper()}] {short_content}"})

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
                    js_val = 'true' if value else 'false'
                    self.bridge.execute_js(f"window.updateStatus('{key}', {js_val})")

            elif msg_type == 'dream_log':
                # Stream dream reasoning to the Dream Journal panel
                import json
                self.bridge.execute_js(f"window.handleDreamLog && window.handleDreamLog({json.dumps(content)})")


        except Exception as e:
            print(f"ChatView: Error handling core output: {e}")
