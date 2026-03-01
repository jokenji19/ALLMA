import threading
import time
import logging
import uuid
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

DREAM_JOURNAL_PATH = "data/dream_journal.json"
MAX_DREAM_ENTRIES = 50

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
    
    def __init__(self, memory_system, incremental_learner, reasoning_engine=None, coalescence_processor=None, system_monitor=None, llm_wrapper=None):
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
        
        # TreeOfThoughts riceve il wrapper LLM direttamente (non il ReasoningEngine)
        from .tree_of_thoughts import TreeOfThoughts
        self.tot = TreeOfThoughts(llm_engine=llm_wrapper)  # <-- llm_wrapper, non reasoning_engine
        # Callback per streamare il diario al frontend
        self.output_callback = None
        self._user_active_event = None
        
        # Inizializza il diario dei sogni persistente
        self.dream_history = []
        self._load_dream_journal()

    def _load_dream_journal(self):
        """Carica lo storico dei sogni dal file JSON."""
        if os.path.exists(DREAM_JOURNAL_PATH):
            try:
                with open(DREAM_JOURNAL_PATH, 'r', encoding='utf-8') as f:
                    self.dream_history = json.load(f)
            except Exception as e:
                self.logger.error(f"Errore nel caricamento del diario dei sogni: {e}")
                self.dream_history = []

    def _save_dream_journal(self):
        """Salva lo storico dei sogni su file (mantenendo solo gli ultimi N)."""
        try:
            os.makedirs(os.path.dirname(DREAM_JOURNAL_PATH), exist_ok=True)
            # Mantieni solo gli ultimi MAX_DREAM_ENTRIES
            if len(self.dream_history) > MAX_DREAM_ENTRIES:
                self.dream_history = self.dream_history[-MAX_DREAM_ENTRIES:]
                
            with open(DREAM_JOURNAL_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.dream_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio del diario dei sogni: {e}")
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
            'phase': phase
        }
        self.dream_history.append(entry)
        self._save_dream_journal()
        
        # 2. Invia alla UI in tempo reale
        if self.output_callback:
            try:
                self.output_callback({'type': 'dream_log', 'content': {'text': text, 'phase': phase}})
            except Exception:
                pass
        self.logger.info(f"[Dream/{phase}] {text}")

    def check_and_start_dream(self, user_id=None):
        """
        Controlla se è il momento di sognare e avvia il thread.
        Non bloccante.
        """
        if self.is_dreaming:
            return
            
        self.current_user_id = user_id
        # Logica: Sogno se sono passate almeno x ore o se c'è molto da elaborare
        # Per ora: Avvio manuale o su trigger di inattività
        self._start_dream_thread()

    def _start_dream_thread(self):
        dream_thread = threading.Thread(target=self._dream_cycle)
        dream_thread.daemon = True # Si chiude se l'app principale muore
        dream_thread.start()

    def _dream_cycle(self):
        """
        Il Ciclo del Sogno (Tree of Thoughts Lite).
        """
        self.is_dreaming = True
        
        # BRAIN V2: METABOLIC GATING
        is_charging = False
        if self.system_monitor:
             is_charging = self.system_monitor.get_metabolic_state().is_charging
        
        mode = "REM (Active/Deep)" if is_charging else "NREM (Passive/Light)"
        self._log_dream(f"Ciclo onirico avviato — Modalità: {mode}", 'start')
        
        try:
            # 1. Recupero Memorie Recenti
            self._log_dream("Recupero memorie delle ultime 24 ore...", 'memory')
            recent_memories = self._fetch_unconsolidated_memories()
            
            if not is_charging:
                self._log_dream("Non in carica — Sonno leggero (NREM). Nessuna elaborazione profonda.", 'paused')
                return

            if self.system_monitor:
                self.system_monitor.acquire_wake_lock("ALLMA:Dream:REM")

            try:
                if not recent_memories:
                    self._log_dream("Nessuna memoria recente — Attivazione Motore di Curiosità...", 'curiosity')
                    recent_memories = self._generate_curiosity_seeds()

                if not recent_memories:
                    self._log_dream("Mente vuota. Sonno profondo senza sogni.", 'paused')
                    return

                self._log_dream(f"{len(recent_memories)} memorie trovate. Avvio Tree of Thoughts...", 'tot')
                insights = self._run_tree_of_thoughts(recent_memories)
                
                self._log_dream(f"{len(insights)} insight generati. Consolidamento in corso...", 'insight')
                self._consolidate_insights(insights)
                
                self._log_dream("Raffinamento varianti di risposta per topic HIGH confidence...", 'refine')
                self._refine_fast_path_responses()
                
                self.last_dream_timestamp = datetime.now()
                self._log_dream("Ciclo onirico completato. ALLMA si è evoluta.", 'done')
                
            finally:
                if self.system_monitor:
                    self.system_monitor.release_wake_lock()
            
        except Exception as e:
            self._log_dream(f"Errore nel sogno: {e}", 'error')
            self.logger.error(f"Incubo (Errore nel sogno): {e}")
        finally:
            self.is_dreaming = False

    def _fetch_unconsolidated_memories(self) -> List[Dict]:
        # Recupera i log della chat delle ultime 24 ore
        if not hasattr(self, 'current_user_id') or not self.current_user_id:
            # Fallback (non dovrebbe accadere se user_id è passato correttamente)
            return []
            
        start_time = datetime.now() - timedelta(hours=24)
        memories = self.memory_system.get_interactions(
            user_id=self.current_user_id,
            start_time=start_time
        )
        return memories

    def _run_tree_of_thoughts(self, memories: List[Dict]) -> List[str]:
        self.logger.info("🧠 Tree of Thoughts: Analisi profonda delle connessioni...")
        
        insights = []
        for memory in memories:
            # Extract content from memory
            content = memory.get('text') or memory.get('content', '')
            if not content:
                continue
                
            # Run ToT
            solutions = self.tot.solve(initial_problem=content, context=[memory])
            insights.extend(solutions)
            
        if not insights:
            insights = ["Nessun insight significativo generato."]
            
        return insights

    def _refine_fast_path_responses(self):
        """
        FASE ONIRICA: per ogni topic con confidenza HIGH,
        usa l'LLM (a bassa temperatura) per generare 2 varianti della risposta cached.
        Risultato: fast-path mai ripetitivo, sempre vivo.
        Eseguito solo durante REM (charging, temperatura ok).
        """
        if not self.incremental_learner:
            return
        if not self.reasoning_engine or not getattr(self.reasoning_engine, 'llm', None):
            self.logger.info("🌙 Dream Refine: LLM non disponibile. Skip.")
            return

        try:
            from ..learning_system.incremental_learning import ConfidenceLevel
        except ImportError:
            from allma_model.learning_system.incremental_learning import ConfidenceLevel

        high_topics = {
            t: s for t, s in self.incremental_learner.knowledge_states.items()
            if s.confidence == ConfidenceLevel.HIGH
        }

        if not high_topics:
            self.logger.info("🌙 Dream Refine: nessun topic HIGH confidence. Skip.")
            return

        self.logger.info(f"🌙 Dream Refine: generazione varianti per {len(high_topics)} topic(s) HIGH...")

        for topic, state in high_topics.items():
            try:
                original = state.content[:300]  # max 300 char come base
                prompt = (
                    f'<|im_start|>system\n'
                    f'Sei ALLMA, un\'intelligenza viva. Rispondi in modo naturale e personale.\n<|im_end|>\n'
                    f'<|im_start|>user\n'
                    f'Hai già risposto in passato a domande sul tema "{topic}" così:\n'
                    f'"{original}"\n\n'
                    f'Scrivi 2 varianti brevi (max 2 frasi ciascuna) della stessa risposta, '
                    f'con tono leggermente diverso ma stesso significato. '
                    f'Separa le 2 varianti con [VAR].\n<|im_end|>\n'
                    f'<|im_start|>assistant\n'
                )
                result = self.reasoning_engine.llm.generate(
                    prompt,
                    max_tokens=200,
                    temperature=0.75,
                    stop=['<|im_end|>']
                )
                if result and '[VAR]' in result:
                    raw_variants = [v.strip() for v in result.split('[VAR]') if v.strip()]
                    variants = [state.content] + raw_variants[:2]  # originale + 2 varianti
                    self.incremental_learner.add_response_variants(topic, variants)
                    self.logger.info(f"✨ Dream Refine: '{topic}' ora ha {len(variants)} varianti.")
                else:
                    self.logger.info(f"🌙 Dream Refine: '{topic}' — nessuna variante generata.")

            except Exception as e:
                self.logger.warning(f"Dream Refine failed for '{topic}': {e}")

        # Salva le varianti su disco
        self.incremental_learner.save_state()
        self.logger.info("💾 Dream Refine: varianti salvate su disco.")

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

    def _consolidate_insights(self, insights: List[str]):
        """
        Consolida le intuizioni nella memoria a lungo termine o chiede validazione.
        """
        for insight in insights:
            # Calcola confidenza (Mock per ora, in futuro dal ToT)
            confidence = 0.85 if "relazione" in insight.lower() else 0.4
            
            if confidence > 0.8:
                # ALTA CONFIDENZA -> Apprendimento Diretto
                self.logger.info(f"💾 Consolidamento (High Conf): {insight}")
                
                # 1. Aggiorna Knowledge Base
                if self.incremental_learner:
                    from ...learning_system.incremental_learning import LearningUnit, ConfidenceLevel
                    unit = LearningUnit(
                        topic="dream_insight",
                        content=insight,
                        source="dream_cycle",
                        confidence=ConfidenceLevel.HIGH,
                        timestamp=datetime.now(),
                        metadata={"type": "autonomous_thought"}
                    )
                    self.incremental_learner.add_learning_unit(unit)
                
                # 2. Evoluzione Personalità
                if self.coalescence_processor:
                    self.coalescence_processor.process_droplet(text=insight)
                    
            else:
                # BASSA CONFIDENZA -> Richiesta Validazione Utente
                self.logger.info(f"🤔 Incertezza (Low Conf): {insight}. Salvataggio per validazione.")
                self.pending_verification.append({
                    'text': insight,
                    'timestamp': datetime.now(),
                    'tried_count': 0
                })

    # --- VISUALIZATION / DEBUGGING ---
    def start_lucid_dream(self, user_id: str, webview_bridge):
        """
        Avvia un 'Sogno Lucido' visibile all'utente per debug/verifica.
        Bypassa i controlli energetici e mostra il pensiero.
        """
        if self.is_dreaming:
            return False
            
        self.current_user_id = user_id
        self.webview_bridge = webview_bridge
        
        dream_thread = threading.Thread(target=self._lucid_dream_cycle)
        dream_thread.daemon = True
        dream_thread.start()
        return True

    def _lucid_dream_cycle(self):
        """
        Ciclo onirico visibile (streamed to UI).
        """
        self.is_dreaming = True
        self.logger.info("👁️ Inizio Sogno Lucido (Visual Test).")
        
        try:
            # 1. Notify Start
            self._stream_to_ui("👁️ Attivazione Sogno Lucido...", is_thought=True)
            time.sleep(1)
            
            # 2. Acquire Curiosity
            self._stream_to_ui("🧠 Generazione curiosità sintetica...", is_thought=True)
            seeds = self._generate_curiosity_seeds()
            if not seeds:
                self._stream_to_ui("❌ Mente vuota.", is_thought=True)
                return
                
            seed_text = seeds[0]['content']
            self._stream_to_ui(f"❓ Domanda: {seed_text}", is_thought=True)
            time.sleep(1.5)
            
            # 3. Tree of Thoughts (Streamed)
            self._stream_to_ui("🌳 Avvio Tree of Thoughts...", is_thought=True)
            
            # Mocking ToT steps visualization (since real ToT inside is atomic)
            # In V3 we will make ToT streamable. For now, we wrap the result.
            insights = self._run_tree_of_thoughts(seeds)
            
            for insight in insights:
                self._stream_to_ui(f"💡 Insight: {insight}", is_thought=True)
                time.sleep(1)

            # 4. Consolidation
            self._consolidate_insights(insights)
            self._stream_to_ui("💾 Consolidamento memorie completato.", is_thought=True)
            self._stream_to_ui("✅ Ciclo onirico terminato.", is_thought=True)

        except Exception as e:
            self.logger.error(f"Lucid Dream Error: {e}")
            self._stream_to_ui(f"❌ Errore nel sogno: {e}", is_thought=True)
        finally:
            self.is_dreaming = False

    def _stream_to_ui(self, text: str, is_thought: bool = False):
        if hasattr(self, 'webview_bridge') and self.webview_bridge:
            # Format as a system message or thought bubble
            # We use '[THOUGHT]' prefix which script.js might style differently
            formatted = f"💭 {text}" if is_thought else text
            self.webview_bridge.send_message_to_js(formatted, sender='system')
    
    def get_and_clear_pending_verification(self) -> Optional[Dict]:
        """
        Recupera un insight in attesa di validazione e lo rimuove dalla coda.
        """
        if not self.pending_verification:
            return None
            
        # Ritorna il primo (FIFO)
        return self.pending_verification.pop(0)
