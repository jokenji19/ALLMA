import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

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
    
    def __init__(self, memory_system, incremental_learner, reasoning_engine=None, coalescence_processor=None, system_monitor=None):
        self.memory_system = memory_system
        self.incremental_learner = incremental_learner
        self.reasoning_engine = reasoning_engine
        self.coalescence_processor = coalescence_processor
        self.system_monitor = system_monitor # BRAIN V2
        self.logger = logging.getLogger(__name__)
        self.is_dreaming = False
        self.last_dream_timestamp = datetime.now()
        self.pending_verification = [] # Insights needing user validation ("Curiosity")
        
        # Initialize Tree of Thoughts
        from .tree_of_thoughts import TreeOfThoughts
        self.tot = TreeOfThoughts(llm_engine=reasoning_engine)

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
        self.logger.info(f"🌙 Inizio Fase Onirica (Dream Cycle). Mode: {mode}")
        
        try:
            # 1. Recupero Memorie Recenti (Diurno)
            # Simula il consolidamento ippocampale
            recent_memories = self._fetch_unconsolidated_memories()
            
            # --- PASSIVE MODE (Always Check) ---
            # Even in passive mode we could do light housekeeping, but for now we skip ToT
            if not is_charging:
                self.logger.info("🌙 Passive Sleep (Not Charging): Skipping Deep Analysis to save energy.")
                # Future: Add light consolidation here (e.g. database vacuum, index reorg)
                return

            # --- DEEP REM MODE (Charging Only) ---
            # CRITICAL: Acquire WakeLock to keep CPU running if screen turns off
            # This ensures "Tree of Thoughts" completes even in Doze mode.
            if self.system_monitor:
                self.system_monitor.acquire_wake_lock("ALLMA:Dream:REM")

            try:
                # --- CURIOSITY ENGINE ---
                if not recent_memories:
                    self.logger.info("🌙 Nessuna memoria recente. Attivazione Motore di Curiosità...")
                    recent_memories = self._generate_curiosity_seeds()

                if not recent_memories:
                    self.logger.info("🌙 Mente vuota. Sonno profondo senza sogni.")
                    return

                # 2. Tree of Thoughts (Deep Reflection)
                insights = self._run_tree_of_thoughts(recent_memories)
                
                # 3. Consolidamento & Validazione
                self._consolidate_insights(insights)
                
                self.last_dream_timestamp = datetime.now()
                self.logger.info("☀️ Fase Onirica completata. ALLMA si è evoluta.")
                
            finally:
                # ALWAYS release lock
                if self.system_monitor:
                    self.system_monitor.release_wake_lock()
            
        except Exception as e:
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
