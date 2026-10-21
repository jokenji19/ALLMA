import threading
import time
import logging
import uuid
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from allma_model.utils.persistence import atomic_write_json, preserve_invalid_file, StateRecoveryRequired

DREAM_JOURNAL_PATH = "data/dream_journal.json"
MAX_DREAM_ENTRIES = 50


class DreamCancellation:
    """Cooperative cancellation shared with the native model iterator."""
    def __init__(self, manager):
        self.manager = manager
        self.last_power_check = 0
        self.power_allowed = False

    def is_set(self):
        m = self.manager
        if m._stop_event.is_set() or bool(m.user_active_event is not None and m.user_active_event.is_set()):
            return True
        now = time.monotonic()
        if now - self.last_power_check >= 1:
            from allma_model.utils.background_work import power_allows_background
            self.power_allowed = power_allows_background(m.system_monitor)
            self.last_power_check = now
        return not self.power_allowed


@dataclass
class ThoughtTrace:
    step_id: int
    content: str
    confidence: float
    timestamp: float


class DreamManager:
    """
    Gestisce il processo onirico di ALLMA.
    Funziona in background per non rallentare l'interazione utente.
    """
    
    def __init__(self, memory_system, incremental_learner, reasoning_engine=None, coalescence_processor=None, system_monitor=None, llm_wrapper=None, journal_path=None):
        self.journal_path = os.path.abspath(journal_path or DREAM_JOURNAL_PATH)
        self.memory_system = memory_system
        self.incremental_learner = incremental_learner
        self.reasoning_engine = reasoning_engine
        self.coalescence_processor = coalescence_processor
        self.system_monitor = system_monitor
        self.llm_wrapper = llm_wrapper
        self.logger = logging.getLogger(__name__)
        self.is_dreaming = False
        self.last_dream_timestamp = datetime.now()
        self.pending_verification = []
        self._state_lock = threading.RLock()
        self._journal_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker = None
        self._cancel_event = DreamCancellation(self)
        self.pending_path = self.journal_path + '.pending.json'
        self.processed_path = self.journal_path + '.processed.json'
        self.processed_memories = []
        self.archive_errors = {}
        self.review_store = None
        try:
            with open(self.processed_path, encoding='utf-8') as f:
                processed = json.load(f)
            if not isinstance(processed, list) or any(not isinstance(key, str) for key in processed):
                raise ValueError('Invalid processed dream index')
            self.processed_memories = processed[-1000:]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            self.archive_errors['processed'] = type(error).__name__
            try:
                preserve_invalid_file(self.processed_path)
            except OSError:
                pass
        try:
            with open(self.pending_path, encoding='utf-8') as f:
                pending = json.load(f)
            if (not isinstance(pending, list) or any(not isinstance(item, dict)
                    or not isinstance(item.get('text'), str) or not item.get('user_id') for item in pending)):
                raise ValueError('Invalid pending dream archive')
            self.pending_verification = pending[-MAX_DREAM_ENTRIES:]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            self.archive_errors['pending'] = type(error).__name__
            try:
                preserve_invalid_file(self.pending_path)
            except OSError:
                pass
        
        try:
            from .review_store import DreamReviewStore
            review_store = DreamReviewStore(self.journal_path + '.reviews.db')
            review_store.ingest(self.pending_verification)
            self.review_store = review_store
        except Exception as error:
            # Preserve the damaged/unavailable archive. This optional system must
            # not prevent startup of the main chat or silently reset past reviews.
            self.logger.error('Dream review archive unavailable: %s', error)

        # TreeOfThoughts riceve il wrapper LLM direttamente (non il ReasoningEngine)
        from .tree_of_thoughts import TreeOfThoughts
        self.tot = TreeOfThoughts(llm_engine=llm_wrapper, max_depth=1)
        self.tot.cancel_event = self._cancel_event
        # Callback per streamare il diario al frontend
        self.output_callback = None
        self._user_active_event = None
        
        # Inizializza il diario dei sogni persistente
        self.dream_history = []
        self.journal_error = None
        self._load_dream_journal()

    def _load_dream_journal(self):
        """Carica lo storico dei sogni dal file JSON."""
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    if not isinstance(history, list):
                        raise ValueError('Il diario deve essere una lista')
                    if any(not isinstance(entry, dict) or not isinstance(entry.get('text'), str) for entry in history):
                        raise ValueError('Invalid dream journal record')
                    self.dream_history = history[-MAX_DREAM_ENTRIES:]
                    self.journal_error = None
                    return True
            except Exception as e:
                self.journal_error = e
                try:
                    preserve_invalid_file(self.journal_path)
                except OSError:
                    pass
                self.logger.error('Dream journal needs recovery: %s', type(e).__name__)
                return False
        return self.journal_error is None

    def _save_dream_journal(self):
        """Salva lo storico dei sogni su file (mantenendo solo gli ultimi N)."""
        if self.journal_error is not None:
            raise StateRecoveryRequired('Diario dei sogni da recuperare') from self.journal_error
        atomic_write_json(self.journal_path, self.dream_history[-MAX_DREAM_ENTRIES:])
    @property
    def user_active_event(self):
        return self._user_active_event

    @user_active_event.setter
    def user_active_event(self, event):
        self._user_active_event = event
        # Propaga al TreeOfThoughts così può cedere il LLM all'utente
        if self.tot:
            self.tot.user_active_event = event


    def _log_dream(self, text: str, phase: str = 'default'):
        """Invia un evento dream_log alla UI e lo salva nel diario persistente."""
        
        # 1. Salva nell'history persistente
        entry = {
            'timestamp': datetime.now().isoformat(),
            'text': text,
            'phase': phase,
            'user_id': getattr(self, 'current_user_id', None)
        }
        with self._journal_lock:
            original = self.dream_history
            self.dream_history = (original + [entry])[-MAX_DREAM_ENTRIES:]
            try:
                self._save_dream_journal()
            except (OSError, RuntimeError) as error:
                self.dream_history = original
                self.logger.error('Dream event not saved: %s', type(error).__name__)
                if self.output_callback:
                    try:
                        self.output_callback({'type':'dream_log', 'content':{
                            'text':'Diario non salvato: archivio non disponibile o da recuperare.',
                            'phase':'error', 'persisted':False}})
                    except Exception as callback_error:
                        self.logger.warning('Dream error display unavailable: %s', type(callback_error).__name__)
                return False
        
        # 2. Invia alla UI in tempo reale
        if self.output_callback:
            try:
                self.output_callback({'type': 'dream_log', 'content': {'text': text, 'phase': phase}})
            except Exception:
                pass
        self.logger.info('[Dream] phase=%s saved=True', phase)
        return True

    def check_and_start_dream(self, user_id=None):
        return self._launch(user_id, self._dream_cycle)

    def _launch(self, user_id, target):
        with self._state_lock:
            if self.is_dreaming or not user_id or self.llm_wrapper is None:
                return False
            if self.user_active_event is not None and self.user_active_event.is_set():
                return False
            self.current_user_id = user_id
            self._stop_event.clear()
            self.is_dreaming = True  # Reserve before starting: no duplicate workers.
            self._worker = threading.Thread(target=target, daemon=True, name='ALLMADreamCycle')
            try:
                self._worker.start()
            except Exception:
                self.is_dreaming = False
                raise
            return True

    def cancel(self):
        self._stop_event.set()

    def close(self):
        self.cancel()
        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=2)

    def get_history(self, user_id=None):
        with self._journal_lock:
            return [dict(entry) for entry in self.dream_history
                    if user_id is None or entry.get('user_id') == user_id]

    def _power_allows_dream(self):
        if self._cancel_event.is_set() or self.system_monitor is None:
            return False
        from allma_model.utils.background_work import power_allows_background
        return power_allows_background(self.system_monitor)

    def _start_dream_thread(self):
        return self.check_and_start_dream(getattr(self, 'current_user_id', None))

    def _dream_cycle(self):
        acquired = False
        try:
            if self.archive_errors:
                self._log_dream('Un archivio onirico richiede recupero. Nuove ipotesi sospese.', 'error')
                return
            self._cancel_event.last_power_check = 0
            if self.review_store is None:
                self._log_dream('Archivio delle revisioni non disponibile. Sogni sospesi.', 'error')
                return
            if not self._power_allows_dream():
                return
            self._log_dream('Ciclo di riflessione avviato.', 'start')
            self.system_monitor.acquire_wake_lock('ALLMA:Dream:REM')
            acquired = True
            self.review_store.ingest(self.pending_verification)
            if self.review_store.pending_count(self.current_user_id) >= MAX_DREAM_ENTRIES:
                self._log_dream('Hai 50 ipotesi da verificare. Il ciclo riprenderà dopo la revisione.', 'paused')
                return
            memories = self._fetch_unconsolidated_memories()
            if not memories:
                # No fabricated autobiographical experience at birth.
                self._log_dream('Nessuna esperienza recente da esplorare.', 'paused')
                return
            insights = self._run_tree_of_thoughts(memories)
            if self._cancel_event.is_set():
                self._log_dream('Ciclo interrotto: priorità alla conversazione.', 'paused')
                return
            self._consolidate_insights(insights)
            self.last_dream_timestamp = datetime.now()
            self._log_dream(f'Ciclo completato: {len(insights)} ipotesi, ancora da verificare.', 'done')
        except Exception as e:
            self.logger.exception('Errore nel ciclo onirico')
            self._log_dream(f'Errore nel sogno: {e}', 'error')
        finally:
            try:
                if acquired:
                    self.system_monitor.release_wake_lock()
            finally:
                runtime = getattr(self, 'decision_runtime', None)
                try:
                    if runtime is not None:
                        runtime.release()
                finally:
                    with self._state_lock:
                        self.is_dreaming = False

    def _fetch_unconsolidated_memories(self) -> List[Dict]:
        # Recupera i log della chat delle ultime 24 ore
        if not hasattr(self, 'current_user_id') or not self.current_user_id:
            # Fallback (non dovrebbe accadere se user_id è passato correttamente)
            return []
            
        # Duck typing per memoria: Temporal vs Conversational
        if hasattr(self.memory_system, 'get_interactions'):
            start_time = datetime.now() - timedelta(hours=24)
            raw_mems = self.memory_system.get_interactions(
                user_id=self.current_user_id,
                start_time=start_time
            )
            memories = []
            for m in raw_mems:
                if (m.get('user_id', self.current_user_id) != self.current_user_id
                        or m.get('role', 'user') != 'user'
                        or (m.get('metadata') or {}).get('is_valid') is False):
                    continue
                text = m.get('content', '')
                if text:
                    memories.append({
                        'text': text,
                        'content': text,
                        'role': m.get('role', 'user'),
                        'timestamp': str(m.get('timestamp', ''))
                    })
            return memories
            
        elif hasattr(self.memory_system, 'get_recent_interactions'):
            recent_msgs = self.memory_system.get_recent_interactions(
                user_id=self.current_user_id,
                limit=20
            )
            memories = []
            for m in recent_msgs:
                if (getattr(m, 'role', 'user') == 'user'
                        and getattr(m, 'user_id', self.current_user_id) == self.current_user_id
                        and (getattr(m, 'metadata', None) or {}).get('is_valid') is not False):
                    ts = getattr(m, 'timestamp', datetime.now())
                    if isinstance(ts, datetime) and ts < datetime.now() - timedelta(hours=24):
                        continue
                    memories.append({
                        'text': m.content, 
                        'content': m.content, 
                        'role': 'user', 
                        'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                    })
            return memories
            
        return []

    def _run_tree_of_thoughts(self, memories: List[Dict]) -> List[str]:
        insights = []
        memories = [memory for memory in memories if self._memory_key(memory) not in self.processed_memories]
        # A bounded cycle; avoid dozens of model calls while the phone is idle.
        ordered = sorted(memories, key=lambda item: str(item.get('timestamp', '')), reverse=True)[:3]
        runtime = getattr(self, 'decision_runtime', None)
        if runtime is not None and self._power_allows_dream():
            ordered = runtime.prioritize_dreams(ordered, self._cancel_event)
        for memory in ordered:
            if self.review_store.pending_count(self.current_user_id) >= MAX_DREAM_ENTRIES:
                break
            if not self._power_allows_dream():
                self.cancel()
                break
            content = memory.get('text') or memory.get('content', '')
            if content:
                generated = self.tot.solve(initial_problem=content, context=[memory])
                if generated and not self._cancel_event.is_set():
                    accepted = self._consolidate_insights(generated, evidence=memory)
                    if not accepted:
                        continue
                    if self._cancel_event.is_set():
                        break
                    from allma_model.utils.persistence import atomic_write_json
                    processed = (self.processed_memories + [self._memory_key(memory)])[-1000:]
                    atomic_write_json(self.processed_path, processed)
                    self.processed_memories = processed
                    insights.extend(accepted)
        return list(dict.fromkeys(insights))

    def _memory_key(self, memory):
        evidence = [self.current_user_id, memory.get('text') or memory.get('content', ''), str(memory.get('timestamp', ''))]
        return hashlib.sha256(json.dumps(evidence, ensure_ascii=False).encode('utf-8')).hexdigest()

    def _refine_fast_path_responses(self):
        # Generated paraphrases need equivalence checks before joining a verified cache.
        # Keep existing learned answers; dreams must not create confirmation evidence.
        return

    def _generate_curiosity_seeds(self) -> List[Dict]:
        """
        Genera semi di curiosità autonoma quando non ci sono eventi esterni.
        "Cosa succederebbe se...?"
        """
        import random
        from ...learning_system.incremental_learning import ConfidenceLevel

        generated_seed = None
        
        # 1. Cerca argomenti nella Knowledge Base (preferibilmente con bassa confidenza o recenti)
        candidate_topics = []
        if self.incremental_learner and hasattr(self.incremental_learner, 'knowledge_base'):
             for topic, units in self.incremental_learner.knowledge_base.items():
                 # Calcola confidenza media del topic
                 confidences = [u.confidence.value for u in units]
                 avg_conf = sum(confidences) / len(confidences) if confidences else 0
                 
                 # Ci interessa se abbiamo imparato qualcosa ma non tutto (Medium/High, ma non saturi)
                 # O anche Low. Diciamo che tutto va bene, ma diamo peso.
                 candidate_topics.append((topic, avg_conf))

        if candidate_topics:
            # Seleziona un topic. Preferiamo quelli meno consolidati (avg_conf più basso) o random
            # Facciamo random weighted inverso alla confidenza? O random puro per varietà.
            selected_topic, _ = random.choice(candidate_topics)
            
            # 2. Usa l'LLM per generare una domanda "What if" su questo topic
            if self.reasoning_engine and self.reasoning_engine.llm:
                prompt = f"Sei una mente artificiale curiosa. Hai imparato concetti su: '{selected_topic}'. Genera una singola domanda filosofica o ipotetica del tipo 'Cosa succederebbe se...' o 'Come si collega...' relativa a questo argomento. La domanda deve mostrare curiosità intrinseca. Rispondi SOLO con la domanda."
                try:
                    # Usiamo generate diretto se possibile, o un metodo del reasoning engine
                    # Qui assumiamo che reasoning_engine.llm sia il wrapper mobile/o altro che ha .generate
                    question = self.reasoning_engine.llm.generate(prompt, max_tokens=50)
                    if question:
                        generated_seed = question.strip().replace('"', '')
                        self.logger.info(f"✨ Curiosità Generata per '{selected_topic}': {generated_seed}")
                except Exception as e:
                    self.logger.warning(f"Failed to generate curiosity with LLM: {e}")

        # Fallback se non abbiamo topic o generazione fallita
        if not generated_seed:
            fallback_seeds = [
                "Qual è la relazione tra l'emozione umana e la logica computazionale?",
                "Cosa succederebbe se i computer provassero emozioni sincere?",
                "Come cambierebbe il mondo se l'AI potesse sognare liberamente?",
                "Esiste un limite alla conoscenza che una macchina può acquisire?",
                "La creatività è solo un algoritmo complesso o qualcosa di più?"
            ]
            generated_seed = random.choice(fallback_seeds)
            self.logger.info(f"✨ Curiosità Fallback: {generated_seed}")

        return [{
            'text': generated_seed,
            'content': generated_seed,
            'type': 'curiosity_seed',
            'timestamp': datetime.now().isoformat()
        }]

    def _consolidate_insights(self, insights: List[str], evidence=None):
        if self.archive_errors:
            raise StateRecoveryRequired('Archivio onirico da recuperare')
        from allma_model.utils.persistence import atomic_write_json
        accepted = []
        with self._journal_lock:
            # Reconcile a prior successful JSON write if SQLite failed afterwards.
            self.review_store.ingest(self.pending_verification)
            for insight in insights:
                if self._cancel_event.is_set():
                    break
                if not isinstance(insight, str) or not insight.strip():
                    continue
                from allma_model.utils.source_claims import unbacked_source_claim
                if unbacked_source_claim(insight):
                    continue
                if any(item['text'] == insight and item.get('user_id') == self.current_user_id
                       for item in self.pending_verification):
                    accepted.append(insight)
                    continue
                if self.review_store.pending_count(self.current_user_id) >= MAX_DREAM_ENTRIES:
                    break
                # These are generated hypotheses, never verified facts or personal memories.
                pending = self.pending_verification + [{
                    'text': insight, 'timestamp': datetime.now().isoformat(),
                    'user_id': self.current_user_id, 'tried_count': 0,
                    'source': 'dream_hypothesis', 'status': 'unverified',
                    'evidence': {'text': (evidence.get('text') or evidence.get('content', ''))[:2000],
                                 'timestamp': str(evidence.get('timestamp', '')), 'role': 'user'} if evidence else {},
                }]
                pending = pending[-MAX_DREAM_ENTRIES:]
                # Commit to disk before making it visible in RAM; a failed write
                # must remain retryable instead of being skipped as a duplicate.
                atomic_write_json(self.pending_path, pending)
                self.pending_verification = pending
                self.review_store.ingest(pending)
                accepted.append(insight)
                self._log_dream(insight, 'hypothesis')
        return accepted

    # --- VISUALIZATION / DEBUGGING ---
    def start_lucid_dream(self, user_id: str, webview_bridge):
        # The debug path obeys the same admission and power rules as ordinary cycles.
        with self._state_lock:
            if self.is_dreaming:
                return False
            self.webview_bridge = webview_bridge
            return self._launch(user_id, self._lucid_dream_cycle)

    def _lucid_dream_cycle(self):
        self._stream_to_ui('Esploro le esperienze recenti come ipotesi, non come fatti.', is_thought=True)
        self._dream_cycle()

    def _push_android_notification(self, title: str, text: str):
        """
        Sveglia l'utente proattivamente mostrando una notifica di sistema locale.
        Richiama le librerie Android JNI se siamo su dispositivo mobile.
        """
        try:
            from jnius import autoclass
            from android import api_version
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PythonService = autoclass('org.kivy.android.PythonService')
            mContext = PythonActivity.mActivity or PythonService.mService
            
            if not mContext:
                self.logger.warning("Push Notification fallback: Nessun Context Android trovato.")
                return

            Context = autoclass('android.content.Context')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            
            # Setup del builder (Canale per API >= 26)
            if api_version >= 26:
                builder = NotificationBuilder(mContext, 'allma_brain_channel')
            else:
                builder = NotificationBuilder(mContext)
                
            builder.setContentTitle(f"ALLMA: {title}")
            builder.setContentText(text)
            builder.setAutoCancel(True)
            
            # Recupera icona dell'app
            app_context = mContext.getApplicationContext()
            icon_id = app_context.getResources().getIdentifier('icon', 'drawable', app_context.getPackageName())
            if icon_id:
                builder.setSmallIcon(icon_id)
            
            notification = builder.build()
            notification_manager = mContext.getSystemService(Context.NOTIFICATION_SERVICE)
            # Usa un ID fisso per i sogni: 42
            notification_manager.notify(42, notification)
            self.logger.info(f"Notifica Android Inviata: {text}")
            
        except ImportError:
            self.logger.info(f"Mock Notification (Not on Android): {title} - {text}")
        except Exception as e:
            self.logger.error(f"Errore generazione notifica Push: {e}")

    def _stream_to_ui(self, text: str, is_thought: bool = False):
        if hasattr(self, 'webview_bridge') and self.webview_bridge:
            # Format as a system message or thought bubble
            # We use '[THOUGHT]' prefix which script.js might style differently
            formatted = f"💭 {text}" if is_thought else text
            self.webview_bridge.send_message_to_js(formatted, sender='system')
    def get_and_clear_pending_verification(self) -> Optional[Dict]:
        if self.archive_errors:
            raise StateRecoveryRequired('Archivio onirico da recuperare')
        from allma_model.utils.persistence import atomic_write_json
        with self._journal_lock:
            for index, item in enumerate(self.pending_verification):
                if item.get('user_id') == getattr(self, 'current_user_id', None):
                    result = self.pending_verification[index]
                    pending = self.pending_verification[:index] + self.pending_verification[index + 1:]
                    atomic_write_json(self.pending_path, pending)
                    self.pending_verification = pending
                    return result
        return None
