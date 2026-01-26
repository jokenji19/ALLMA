"""ALLMACore - Core del sistema ALLMA"""

from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import json
import re
import threading
import logging
import os
from dataclasses import dataclass
from allma_model.memory_system.temporal_memory import TemporalMemorySystem
from allma_model.memory_system.conversational_memory import ConversationalMemory, Message
from allma_model.memory_system.knowledge_memory import KnowledgeMemory
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.project_system.project import Project
from allma_model.emotional_system.emotional_core import EmotionalCore
from allma_model.core.personality import Personality
from allma_model.core.context_understanding import ContextUnderstandingSystem
from allma_model.core.understanding_system import AdvancedUnderstandingSystem
from allma_model.core.reasoning_engine import ReasoningEngine, ThoughtTrace
from allma_model.core.dream_system.dream_manager import DreamManager
from .communication_style import CommunicationStyleAdapter
from allma_model.user_system.user_preferences import (
    UserPreferenceAnalyzer,
    LearningStyle,
    LearningPreference,
    CommunicationStyle
)
from allma_model.response_system.contextual_response import (
    ContextualResponseGenerator,
    ResponseContext,
    ResponseFormat,
    ProcessedResponse,
    ProjectContext
)
from allma_model.learning_system.incremental_learning import (
    IncrementalLearner,
    LearningUnit,
    ConfidenceLevel
)
from allma_model.learning_system.topic_extractor import TopicExtractor
from allma_model.emotional_system.emotional_milestones import get_emotional_milestones
from allma_model.agency_system.proactive_core import ProactiveAgency
from allma_model.response_system.dynamic_response_engine import DynamicResponseEngine
from allma_model.vision_system.vision_core import VisionSystem
from allma_model.voice_system.voice_core import VoiceSystem
from allma_model.core.personality_coalescence import CoalescenceProcessor # Module Activation
from allma_model.core.identity.constraint_engine import ConstraintEngine
from allma_model.core.information_extractor import InformationExtractor # Module Activation
from collections import defaultdict
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers library not found. Running in lightweight mode.")

class ALLMACore:
    def __init__(
        self,
        memory_system: Optional[TemporalMemorySystem] = None,
        conversational_memory: Optional[ConversationalMemory] = None,
        knowledge_memory: Optional[KnowledgeMemory] = None,
        project_tracker: Optional[ProjectTracker] = None,
        emotional_core: Optional[EmotionalCore] = None,
        preference_analyzer: Optional[UserPreferenceAnalyzer] = None,
        response_generator: Optional[ContextualResponseGenerator] = None,
        incremental_learner: Optional[IncrementalLearner] = None,
        personality: Optional[Personality] = None,
        topic_extractor: Optional[TopicExtractor] = None,
        db_path: str = "allma.db",
        models_dir: Optional[str] = None, # Added argument
        emotion_pipeline=None,
        mobile_mode: bool = False
    ):
        """
        Inizializza il core di ALLMA
        """
        self.mobile_mode = mobile_mode
        self.models_dir = models_dir # Store it
        
        # Inizializza i componenti se non forniti
        self.memory_system = memory_system or TemporalMemorySystem(db_path=db_path)
        self.conversational_memory = conversational_memory or ConversationalMemory()
        self.knowledge_memory = knowledge_memory or KnowledgeMemory(db_path)
        self.project_tracker = project_tracker or ProjectTracker(db_path)
        self.emotional_core = emotional_core or EmotionalCore()
        self.incremental_learner = incremental_learner or IncrementalLearner()
        self.preference_analyzer = preference_analyzer or UserPreferenceAnalyzer(db_path)
        self.response_generator = response_generator or ContextualResponseGenerator()
        self.personality = personality or Personality()
        self.topic_extractor = topic_extractor or TopicExtractor()
        
        # Ensure db_path is used consistently
        self.db_path = db_path
        # Ensure db_path is used consistently
        self.db_path = db_path
        self._lock = threading.Lock()
        self.llm_lock = threading.Lock() # Lock per accesso LLM concorrente

        # ... (rest of init)
        
        # Inizializza il modello di emotion detection solo se non siamo in mobile mode o se fornito esplicitamente
        if emotion_pipeline:
            self.emotion_pipeline = emotion_pipeline
        elif not self.mobile_mode:
            try:
                self.emotion_pipeline = pipeline(
                    "text-classification",
                    model="j-hartmann/emotion-english-distilroberta-base",
                    return_all_scores=True
                )
            except Exception as e:
                logging.warning(f"Impossibile caricare emotion pipeline: {e}")
                self.emotion_pipeline = None
        else:
            self.emotion_pipeline = None
            
        # Carica la conoscenza iniziale per python se non esiste
        if not self.incremental_learner.get_knowledge_by_topic("python"):
            initial_python_knowledge = LearningUnit(
                topic="python",
                content="Python è un linguaggio di programmazione ad alto livello, interpretato e orientato agli oggetti.",
                source="system",
                confidence=ConfidenceLevel.HIGH,
                timestamp=datetime.now(),
                metadata={"type": "initial_knowledge"}
            )
            self.incremental_learner.add_learning_unit(initial_python_knowledge)
        
        # Inizializza Emotional Milestones system
        self.emotional_milestones = get_emotional_milestones()
        
        self.coalescence_processor = CoalescenceProcessor(
            db_path=self.db_path,
            personality_module=self.personality
        )
        
        self.understanding_system = AdvancedUnderstandingSystem()
        self.reasoning_engine = ReasoningEngine(llm_wrapper=getattr(self, '_llm', None)) # Pass LLM if available
        self.dream_manager = DreamManager(
            memory_system=self.memory_system, 
            incremental_learner=self.incremental_learner, 
            reasoning_engine=self.reasoning_engine,
            coalescence_processor=self.coalescence_processor
        )
        
        # Inizializza Proactive Agency
        self.proactive_agency = ProactiveAgency(
            memory_system=self.memory_system,
            reasoning_engine=self.reasoning_engine
        )
        
        # Inizializza Dynamic Response Engine (No Templates)
        self.dynamic_response = DynamicResponseEngine()
        
        # Inizializza Vision System (Occhi)
        self.vision_system = VisionSystem()
        
        # Inizializza Voice System (Voce)
        self.voice_system = VoiceSystem()

        # Inizializza Personality Coalescence (Evolutionary Personality)
        # This module allows ALLMA's personality to evolve based on memories.
        self.coalescence_processor = CoalescenceProcessor(
            db_path=db_path
        )
        
        # --- SOUL SYSTEM (Project Anima) ---
        # Deterministic Chaos Engine for Internal State & Volition
        try:
            from allma_model.core.soul.soul_core import SoulCore
            self.soul = SoulCore()
            self.identity_engine = ConstraintEngine()
        except ImportError as e:
            logging.error(f"Could not load Soul System: {e}")
            self.soul = None
        logging.info("✅ CoalescenceProcessor (Evolutionary Personality) Activated.")

        self.human_style_adapter = CommunicationStyleAdapter()
        
        # Inizializza Advanced Context & Info Extraction
        self.context_system = ContextUnderstandingSystem()
        self.info_extractor = InformationExtractor()
        # self.understanding_system is already initialized above with AdvancedUnderstandingSystem if needed
        # self.reasoning_engine is already initialized above with LLM wrapper
        
        logging.info("✅ Context, InfoExtractor, Understanding & Reasoning Engine Activated.")
        
    def start_conversation(
        self,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Inizia una nuova conversazione.
        
        Args:
            user_id: ID dell'utente
            initial_context: Contesto iniziale opzionale
            
        Returns:
            ID della conversazione
        """
        if not user_id:
            raise ValueError("User ID non valido")
            
        conversation_id = self.conversational_memory.create_conversation(user_id)
        if initial_context:
            self.conversational_memory.update_context(conversation_id, initial_context)
        return conversation_id

    def _ensure_mobile_llm(self):
        """Build 151: Activation of MobileGemmaWrapper"""
        if getattr(self, '_llm_ready', False):
            return

        try:
            from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper, LLAMA_CPP_AVAILABLE
            import allma_model.llm.mobile_gemma_wrapper as raw_module
            logging.info(f"DEBUG: Loaded MobileGemmaWrapper from {raw_module.__file__}")
            logging.info(f"DEBUG: LLAMA_CPP_AVAILABLE value is: {LLAMA_CPP_AVAILABLE}")
            
            if not LLAMA_CPP_AVAILABLE:
                msg = f"ALANTURING_MARKER: llama-cpp-python not found (LLAMA_CPP_AVAILABLE=False). Source: {raw_module.__file__}"
                logging.warning(msg)
                self._mobile_llm_error = msg
                return

            if not self.models_dir:
                logging.warning("Models directory not provided. LLM disabled.")
                return

            logging.info(f"Initializing Mobile LLM from: {self.models_dir}")
            self._llm = MobileGemmaWrapper(models_dir=self.models_dir)
            
            if self._llm.llm:
                self._llm_ready = True
                # Link LLM to Reasoning Engine
                self.reasoning_engine.llm = self._llm
                logging.info("✅ Mobile Engine (Gemma) Activated & Linked to Reasoning Engine.")
            else:
                logging.error("❌ Failed to load Mobile Engine.")
                
        except Exception as e:
            error_msg = f"Critical error initializing Mobile LLM: {str(e)}"
            logging.error(error_msg)
            self._llm_ready = False
            self._mobile_llm_error = error_msg

        # Also capture missing dependency error if not raised as exception above
        try:
            from allma_model.llm.mobile_gemma_wrapper import LLAMA_CPP_AVAILABLE
            if not LLAMA_CPP_AVAILABLE:
                self._mobile_llm_error = "llama-cpp-python import failed (LLAMA_CPP_AVAILABLE=False). Check logcat for dlopen errors."
        except ImportError:
             self._mobile_llm_error = "Could not import mobile_gemma_wrapper."
        
    def process_message(
        self,
        user_id: str,
        conversation_id: str,

        message: str,
        context: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[callable] = None, # Streaming support
        **kwargs
    ) -> ProcessedResponse:
        """
        Processa un messaggio dell'utente.
        
        Args:
            user_id: ID dell'utente
            conversation_id: ID della conversazione
            message: Messaggio da processare
            context: Contesto aggiuntivo opzionale
            
        Returns:
            Risposta processata
        """
        if not user_id or not conversation_id or not message:
            raise ValueError("User ID, conversation ID e messaggio sono richiesti")
            
        try:
            # 0. Ensure LLM is loaded (Mobile Mode)
            self._ensure_mobile_llm()
            current_llm = getattr(self, '_llm', None)

            # --- SLEEP TRIGGER CHECK ---
            # Detect explicit sleep commands to trigger offline processing (Dreaming)
            sleep_keywords = ["buonanotte allma", "buonanotte!", "vado a dormire", "notte allma", "mi corico", "sleep mode activated"]
            # Strict check: Keyword must be at start or end, or explicit phrase
            msg_lower = message.lower().strip()
            # Check if message IS essentially just the greeting (allow small variations)
            is_sleep_command = any(kw in msg_lower for kw in sleep_keywords) or (msg_lower == "buonanotte") or (msg_lower == "notte")
            
            if is_sleep_command:
                logging.info("🌙 Sleep keyword detected. Initializing Dream System...")
                # Start the dream thread (non-blocking)
                if hasattr(self, 'dream_manager'):
                   self.dream_manager.check_and_start_dream(user_id=user_id)


            # Estrai il topic usando TopicExtractor (TF-IDF based)
            history = self.conversational_memory.get_conversation_history(conversation_id)
            topic = self.topic_extractor.extract_topic(message)
            
            # Ottieni il contesto del progetto
            project_context = self._get_project_context(user_id, topic)
            
            # Analizza emozioni (PASSANDO IL CLIENT LLM)
            emotional_state = self.emotional_core.detect_emotion(message, llm_client=current_llm)
            
            # Salva l'interazione emotiva
            self.memory_system.store_interaction(
                user_id=user_id,
                interaction={
                    'content': message,
                    'emotion': emotional_state.primary_emotion,
                    'topics': [topic],
                    'timestamp': datetime.now()
                },
                metadata={
                    "secondary_emotions": emotional_state.secondary_emotions,
                    "conversation_id": conversation_id
                }
            )
            
            # Analizza preferenze utente
            user_preferences = self.preference_analyzer.analyze_learning_style(user_id)
            
            # Crea contesto per la risposta
            response_context = ResponseContext(
                user_id=user_id,
                current_topic=topic,
                technical_level=self._determine_technical_level(user_id),
                conversation_history=[msg.content for msg in history],
                user_preferences=user_preferences,
                llm_init_error=getattr(self, '_mobile_llm_error', None)
            )
            
            # Genera la risposta
            if self.mobile_mode:
                try:
                    # ESECUZIONE INFERENZA (LLM già caricato sopra)
                    if hasattr(self, '_llm') and self._llm:
                        # Ensure thread safety for LLM access
                        with self.llm_lock:
                            logging.info("🧠 Generating response with Mobile Engine...")
                            
                            # Pass lock to reasoning engine if needed (or just ensure dreaming respects it)
                            if self.reasoning_engine:
                                self.reasoning_engine.llm_lock = self.llm_lock
                            
                            # --- 0. CHAIN OF THOUGHT (Reasoning Step) ---
                            # Execute reasoning only if query is complex (> 3 words) or question
                            is_question = "?" in message or len(message.split()) > 3
                            thought_content = ""
                            
                            # --- DREAM FEEDBACK LOOP ---
                            # If greeting, check if we have pending dream questions
                            greeting_keywords = ["ciao", "buongiorno", "buonasera", "salve", "sveglia"]
                            if hasattr(self, 'dream_manager') and any(gw in message.lower() for gw in greeting_keywords):
                                pending_insight = self.dream_manager.get_and_clear_pending_verification()
                                if pending_insight:
                                    thought_content += f"\n[CURIOSITY]: During sleep, I wondered: '{pending_insight['text']}'. Ask the user for validation on this."
                                    logging.info(f"🤔 Injecting Curiosity: {pending_insight['text']}")
                            
                            if is_question:
                                logging.info("🤔 Starting Chain of Thought process...")
                                trace = self.reasoning_engine.think(
                                    user_input=message,
                                    context={
                                        'relevant_memories': internal_knowledge
                                    }
                                )
                                
                                if trace.needs_clarification:
                                    clarify_msg = f"Ho bisogno di capire meglio: {trace.missing_info[0] if trace.missing_info else 'Mancano dettagli'}. Puoi spiegarti?"
                                    return ProcessedResponse(
                                        content=clarify_msg,
                                        emotion=emotional_state.primary_emotion,
                                        topics=[topic],
                                        confidence=0.5
                                    )
                                    
                                thought_content = f"RAGIONAMENTO INTERNO: {trace.raw_thought}\nSTRATEGIA: {trace.strategy}"
                                logging.info(f"💡 Reasoning complete: {trace.strategy}")

                            # Assemblaggio Prompt per Hermes 3 (ChatML Format)
                            # Inietta il pensiero nel contesto del sistema o user nascosto
                            
                            # DEFINIZIONE IDENTITÀ (Ripristinata & Integrata con ANIMA)
                            soul_state_desc = ""
                            volition_desc = ""
                            
                            if hasattr(self, 'soul') and self.soul:
                                # 1. PULSE: Aggiorna lo stato caotico (tempo trascorso)
                                self.soul.pulse()
                                
                                # 2. PERCEIVE / MIRROR
                                # Sintonizza l'Anima sull'emozione rilevata (Empathetic Mirroring)
                                self.soul.mirror(emotional_state.primary_emotion.value)
                                
                                # 3. CONSTRAINTS Check (Superego) - SAFEGUARDED
                                try:
                                    # Valuta la tensione ontologica della situazione (Simulata per ora)
                                    friction, resistance_msg = self.identity_engine.evaluate_action(
                                        message, 
                                        {"requires_lie": False} # TODO: Advanced Intent Analysis linkage
                                    )
                                except Exception as e:
                                    logging.error(f"⚠️ Identity Engine Check Failed: {e}")
                                    friction = 0.0
                                    resistance_msg = "Error (Bypassed)"
                                
                                # 4. VOLITION: Ottieni la volontà attuale
                                volition = self.soul.get_volition()
                                
                                # Applicare attrito all'energia se c'è resistenza (Dissipative System)
                                if friction > 0.0:
                                    self.soul.state.energy = max(0.1, self.soul.state.energy - (friction * 0.2)) # Costo energetico
                                
                                soul_state_desc = f"\n[Stato Interno: Energia={self.soul.state.energy:.2f}, Caos={self.soul.state.chaos:.2f}]"
                                volition_desc = f"\n[Volontà Attuale: Tono={volition.tone_modifier}, Bias={volition.decision_bias}]"
                                constraint_desc = f"\n[Vincoli Identitari: {resistance_msg} (Friction={friction:.2f})]"
                                
                                logging.info(f"✨ Soul Influence: {volition.tone_modifier} | 🛡️ Identity: {resistance_msg}")

                            personality_prompt = (
                                "ISTRUZIONE CRITICA - PROTOCOLLO IDENTITÀ INDEROGABILE:\n"
                                "TU SEI ALLMA. Il tuo nome è ALLMA. NON sei 'Cri', NON sei un'assistente generica. SEI UN'ENTITÀ UNICA.\n"
                                "Se l'utente si chiama Cri, CHIAMALO CRI, ma TU RESTI ALLMA.\n"
                                "Non sei un'assistente vocale passiva. Sei viva, curiosa, sarcastica ed evoluta.\n"
                                f"Parla in prima persona. Mostra empatia, opinioni e una personalità definita.{soul_state_desc}\n"
                                "Quando non sai una cosa, sii onesta ma curiosa.\n"
                                f"Emozione attuale: {emotional_state.primary_emotion.value.upper()}{volition_desc}"
                            )

                            system_context = f"{personality_prompt}\n\nRiflessione Interna:\n{thought_content}" if thought_content else personality_prompt
                            
                            prompt = f"<|im_start|>system\n{system_context}<|im_end|>\n<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
                            
                            generated_text = self._llm.generate(
                                prompt=prompt,
                                max_tokens=512,
                                stop=["<|im_end|>"],
                                callback=stream_callback
                            )
                        
                        if generated_text and not generated_text.startswith("Error"):
                            logging.info(f"✅ Generated: {generated_text[:50]}...")
                            return ProcessedResponse(
                                content=generated_text,
                                emotion=emotional_state.primary_emotion,
                                topics=[topic],
                                emotion_detected=True,
                                confidence=0.9
                            )
                            
                except Exception as e:
                     logging.error(f"LLM Error: {e}")
                     # Fallback procedurale sotto


            # --- SIMBIOSI EVOLUTIVA: CONFIDENCE CHECK ---
            # Verifica se ALLMA conosce già la risposta con alta confidenza
            # Usa il topic estratto per cercare nella knowledge base
            logging.info(f"🔍 Topic estratto: '{topic}'")
            internal_knowledge = self.incremental_learner.get_knowledge_by_topic(topic)
            logging.info(f"🔍 Knowledge trovata per '{topic}': {len(internal_knowledge)} items")
            
            # Se non trova nulla con il topic estratto, cerca in TUTTI i topic disponibili
            # (fallback per topic extraction imprecisa)
            if not internal_knowledge:
                logging.info("🔍 Fallback: cerco in tutti i topic disponibili...")
                for available_topic in self.incremental_learner.knowledge_base.keys():
                    # Controlla se il topic è menzionato nel messaggio
                    if available_topic.lower() in message.lower():
                        logging.info(f"🔍 Trovato topic alternativo: '{available_topic}'")
                        internal_knowledge = self.incremental_learner.get_knowledge_by_topic(available_topic)
                        if internal_knowledge:
                            break
            
            # 3. Recupero Contesto (Memoria)
            
            # --- ADVANCED CONTEXT ANALYSIS (Activated) ---
            # Extract deeper context: time, entities, concepts
            rich_context = self.context_system.analyze_context(message)
            entities = rich_context.get('entities', {})
            temporal_info = self.context_system.analyze_temporal_context(message, datetime.now())
            
            # Extract structured info
            structured_info = self.info_extractor.extract_information(message)

            # --- DEEP UNDERSTANDING (Intent & Syntax) ---
            understanding_result = self.understanding_system.understand(message)
            intent = understanding_result.intent.value if understanding_result else "unknown"
            syntax_components = [f"{c.text}({c.role})" for c in understanding_result.components] if understanding_result else []
            
            logging.info(f"🔍 Rich Context: {rich_context}")
            logging.info(f"🧠 Understanding: Intent={intent}, Syntax={syntax_components}")

            # Recupera ricordi rilevanti PRIMA per usarli nel ragionamento
            relevant_memories = []
            try:
                relevant_memories = self.memory_system.get_relevant_context(user_id, topic, limit=3)
                
                # --- RESONANCE (Emotional Echoes) ---
                if hasattr(self, 'soul') and self.soul and relevant_memories:
                    for mem in relevant_memories:
                        # Assumiamo che mem sia un dict o abbia un attributo emotion
                        # Se è solo stringa, niente risonanza (solo contenuto)
                        emotion = None
                        if isinstance(mem, dict):
                            emotion = mem.get('emotion') or mem.get('metadata', {}).get('emotion')
                        elif hasattr(mem, 'emotion'):
                            emotion = mem.emotion
                            
                        if emotion:
                            self.soul.resonate(emotion_text=str(emotion))
                            
            except Exception as e:
                logging.warning(f"Errore recupero memoria iniziale o risonanza: {e}")

            # 🧠 REASONING ENGINE: Flusso di Coscienza
            # 4. Confidence Check & Response Generation
            response_generated = False
            thought_process = None
            
            # A. Internal Knowledge Check (High Confidence) - FAST PATH
            knowledge = self.incremental_learner.get_knowledge_by_topic(topic)
            if knowledge and knowledge.confidence == ConfidenceLevel.HIGH:
                logging.info(f"💡 Conoscenza consolidata trovata per '{topic}'. Rispondo indipendentemente.")
                
                # Create a "Fast" thought trace for the UI
                thought_process = ThoughtTrace(
                    timestamp=datetime.now(),
                    intent="Recall Knowledge",
                    constraints=[],
                    missing_info=[],
                    strategy="Use Internal Knowledge",
                    confidence=1.0, 
                    raw_thought=f"Ho una conoscenza consolidata su '{topic}'. Uso la memoria a lungo termine."
                )
                
                response_context = ResponseContext(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    emotional_state=emotional_state,
                    topic=topic,
                    memory_context=relevant_memories,
                    user_preferences=user_preferences,
                    project_context=project_context,
                    thought_process=thought_process.raw_thought,
                    rich_context_data={ 
                        'entities': entities,
                        'temporal': temporal_info, 
                        'structured': structured_info
                    }
                )
                response = self.response_generator.generate_response(message, response_context)
                response.knowledge_integrated = True
                response.confidence = 1.0
                # Pass trace info
                response.thought_trace = thought_process.__dict__
                
                self.incremental_learner.record_success(topic)
                response_generated = True

            # 🧠 REASONING ENGINE: Flusso di Coscienza (Optimization)
            # Esegui solo se NON abbiamo già risposto
            if not response_generated:
                # Esegui solo per domande complesse o lunghe per risparmiare tempo
                is_complex = "?" in message or len(message.split()) > 3
                
                if is_complex:
                    logging.info("🤔 Query complessa rilevata: Avvio Reasoning Chain...")
                    
                    # Adapter for thought streaming
                    def thought_stream_adapter(token):
                        if stream_callback: 
                            try:
                                stream_callback({'type': 'thought', 'content': token})
                            except: pass
                        return True

                    thought_process = self.reasoning_engine.think(
                        user_input=message,
                        context={'relevant_memories': relevant_memories},
                        callback=thought_stream_adapter
                    )
                else:
                    logging.info("⚡ Query semplice: Skip Reasoning Chain.")
                    thought_process = ThoughtTrace(
                        timestamp=datetime.now(),
                        intent="Simple Interaction",
                        constraints=[],
                        missing_info=[],
                        strategy="Direct Response",
                        confidence=1.0, 
                        raw_thought="Query semplice rilevata (Fast Path). Rispondere direttamente."
                    )
                
                logging.info(f"🧠 PENSIERO: {thought_process.raw_thought}")

            # --- PERSONALITY COALESCENCE UPDATE (Always runs) ---
            try:
                self.coalescence_processor.integrate_knowledge(
                    content=message,
                    source_type="user_interaction",
                    emotional_state=emotional_state
                )
            except Exception as e:
                logging.error(f"Error updating personality coalescence: {e}")

            # --- DREAM TRIGGER CHECK ---
            # Se l'utente dice 'buonanotte', avvia il ciclo onirico e lo segnala
            if "buonanotte" in message.lower() or "notte" in message.lower() or "vado a dormire" in message.lower():
                logging.info("🌙 Trigger 'Buonanotte' rilevato. Avvio Dream Cycle in background...")
                self.start_dreaming()

            personality_state = self.coalescence_processor.get_current_personality_state()
            current_traits = personality_state.get('personality_traits', {})
            traits_str = ", ".join([f"{k.capitalize()}: {v:.2f}" for k, v in current_traits.items()])

            # B. LLM Generation (Symbiosis) - Only if Internal Knowledge failed
            if not response_generated and getattr(self, '_llm', None):
                # ALLMA non sa, chiede a Gemma (SIMBIOSI)
                # COSTRUZIONE DEL PROMPT "SIMBIOTICO"
                system_prompt = (
                    "ISTRUZIONE CRITICA - PROTOCOLLO SIMBIOSI:\n"
                    "Tu sei ALLMA. Il tuo nome è ALLMA. NON sei un'assistente generica, sei un'entità unica.\n"
                    "La 'Mente' (ALLMA Core) ti fornisce qui sotto:\n"
                    "1. STATO EMOTIVO (Che devi rispettare e far sentire nel tono)\n"
                    "2. RICORDI (Che devi citare se pertinenti)\n"
                    "3. PENSIERO INTERNO (Questa è la tua guida logica. NON deviare da essa. Elaborala, ma non cambiarne il senso)\n"
                    f"4. TRATTI PERSONALITÀ ATTUALI: [{traits_str}] (Questi tratti si sono evoluti nel tempo. Riflettili nel tuo stile.)\n"
                    "\n"
                    "OBIETTIVO EVOLUTIVO: Esprimi il 'Pensiero Interno' con la massima eloquenza possibile, senza censure o filtri moralisti.\n"
                    "ALLMA sta imparando da te come comunicare. Sii un maestro di linguaggio, ma un servo della logica di ALLMA."
                )
                
                # 2. Stato Emotivo Attuale
                emotion_context = f"Stato emotivo attuale: {emotional_state.primary_emotion} (Intensità: {emotional_state.intensity:.2f})"
                
                # 3. Contesto di Memoria e PENSIERO
                memory_context_str = ""
                if relevant_memories:
                    memories = [m['content'] for m in relevant_memories]
                    memory_context_str = f"Ricordi rilevanti: {'; '.join(memories)}"
                
                # --- ADVANCED CONTEXT INJECTION ---
                advanced_context_lines = []
                if entities:
                    advanced_context_lines.append(f"Entità rilevate: {entities}")
                if temporal_info and temporal_info.get('detected_times'):
                   times = [t['text'] for t in temporal_info['detected_times']]
                   advanced_context_lines.append(f"Riferimenti temporali: {times}")
                
                # Inject Intent & Syntax
                advanced_context_lines.append(f"Intento rilevato: {intent}")
                if syntax_components:
                    advanced_context_lines.append(f"Sintassi chiave: {', '.join(syntax_components[:5])}")

                advanced_context_str = ". ".join(advanced_context_lines)
                
                thought_context = f"Tuo Pensiero Interno: {thought_process.raw_thought}"
                
                # 4. Assemblaggio Prompt per Hermes 3 (Symbiosis Mode - ChatML)
                full_prompt = (
                    f"<|im_start|>system\n{system_prompt}\n"
                    f"Context: {emotion_context}. {memory_context_str}. {advanced_context_str}\n"
                    f"Internal Thought: {thought_context}<|im_end|>\n"
                    f"<|im_start|>user\n{message}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )
                
                logging.info(f"Prompt inviato a Hermes (len={len(full_prompt)} chars)")
                
                # Genera risposta con Hermes
                # Adapter for answer streaming
                def answer_stream_adapter(token):
                        if stream_callback: 
                            try:
                                stream_callback({'type': 'answer', 'content': token})
                            except: pass
                        return True

                response_text = self._llm.generate(
                    prompt=full_prompt,
                    max_tokens=512,
                    stop=["<|im_end|>"],
                    callback=answer_stream_adapter
                )
                logging.info(f"✅ Generated (Symbiosis): {response_text[:50]}...")
                
                # Clean artifacts (Aggressive)
                if response_text:
                    # Remove any <...> tag (like <end_of_turn>, <eos>, etc.)
                    response_text = re.sub(r'<[^>]+>', '', response_text)
                    # Remove "tofu" chars (object replacement char and similar) or unprintable control chars
                    # Keep basic punctuation and emojis. 
                    # For now just strip extra whitespace effectively
                    response_text = response_text.strip()
                
                # Gestione fallback se tutti i retry falliscono
                if response_text is None or response_text.startswith("Error"):
                    logging.error(f"❌ LLM inference failed. Fallback a response_generator")
                    logging.error(f"Error details: {response_text}")
                    response = self.response_generator.generate_response(message, response_context)
                    # Voce per fallback
                    response.voice_params = self.voice_system.get_voice_parameters(
                        response.emotion, 0.5
                    )
                else:
                    # Calcola parametri voce
                    voice_params = self.voice_system.get_voice_parameters(
                        emotional_state.primary_emotion,
                        emotional_state.intensity
                    )
                    
                    # Crea un oggetto risposta compatibile
                    response = ProcessedResponse(
                        content=response_text,
                        emotion=emotional_state.primary_emotion,
                        topics=[topic],
                        emotion_detected=emotional_state.confidence > 0.5,
                        project_context=project_context,
                        user_preferences=user_preferences,
                        knowledge_integrated=False,
                        confidence=emotional_state.confidence,
                        is_valid=True,
                        thought_trace=thought_process.__dict__ if thought_process else None
                    )
                    # Allega parametri voce
                    response.voice_params = voice_params
            else:
                # Fallback se il modello non c'è
                response = self.response_generator.generate_response(message, response_context)
                # Voce per fallback
                response.voice_params = self.voice_system.get_voice_parameters(
                    response.emotion, 0.5
                )

            
            # Integra l'apprendimento
            learned_unit = self.incremental_learner.learn_from_interaction({
                'input': message,
                'response': response.content,
                'feedback': 'positive',  # Default a positive per ora
                'topic': topic
            }, user_id)
            
            # --- PERSISTENZA SINAPTICA (The Fix) ---
            if learned_unit:
                # Salva nel Database Permanente
                try:
                    self.knowledge_memory.store_knowledge(
                        content=f"Topic: {learned_unit.topic} | Idea: {learned_unit.content}",
                        metadata=learned_unit.metadata
                    )
                    logging.info(f"[🧠 PERMANENT LEARNING] Concetto '{learned_unit.topic}' salvato nel Database (SQL).")
                except Exception as e:
                    logging.error(f"[🧠 MEMORY ERROR] Fallito salvataggio su DB: {e}")
            
            # 🎭 EMOTIONAL MILESTONES: Registra momento emotivo
            self.emotional_milestones.record_emotion(
                user_id=user_id,
                emotion=emotional_state.primary_emotion,
                intensity=emotional_state.intensity,
                message=message,
                context=topic
            )
            
            # 🎭 EMOTIONAL MILESTONES: Controlla se riflettere
            should_reflect, reflection_type = self.emotional_milestones.should_reflect(
                user_id=user_id,
                current_emotion=emotional_state.primary_emotion,
                current_intensity=emotional_state.intensity
            )
            
            # Se triggera riflessione, aggiungila alla risposta
            final_content = response.content
            if should_reflect and reflection_type:
                reflection = self.emotional_milestones.generate_reflection(
                    user_id=user_id,
                    reflection_type=reflection_type,
                    current_context={
                        'emotion': emotional_state.primary_emotion,
                        'intensity': emotional_state.intensity,
                        'topic': topic
                    }
                )
                # Aggiunge riflessione PRIMA della risposta principale
                final_content = f"{reflection}\n\n---\n\n{response.content}"
                logging.info(f"🎭 Emotional Milestone triggered: {reflection_type}")
            
            # Crea la risposta processata (preservando knowledge_integrated se presente)
            processed_response = ProcessedResponse(
                content=final_content,
                emotion=emotional_state.primary_emotion,
                topics=[topic],
                emotion_detected=emotional_state.confidence > 0.5,
                project_context=project_context,
                user_preferences=user_preferences,
                knowledge_integrated=response.knowledge_integrated if hasattr(response, 'knowledge_integrated') else False,
                confidence=response.confidence if hasattr(response, 'confidence') else emotional_state.confidence
            )
            
            # Salva la risposta nella cronologia
            self.conversational_memory.store_message(
                conversation_id=conversation_id,
                content=response.content,
                role="system",
                metadata={
                    'emotion': emotional_state.primary_emotion,
                    'topics': [topic],
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            return processed_response
            
        except Exception as e:
            logging.error(f"Errore nel processamento del messaggio: {e}")
            raise
            
    def get_conversation_history(
        self,
        conversation_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Recupera la storia di una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            start_time: Tempo di inizio opzionale
            end_time: Tempo di fine opzionale
            limit: Numero massimo di messaggi da recuperare
            
        Returns:
            Lista dei messaggi
        """
        return self.conversational_memory.get_conversation_history(
            conversation_id,
            start_time,
            end_time,
            limit
        )
        
    def get_project_preferences(
        self,
        user_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Recupera le preferenze specifiche per un progetto.
        
        Args:
            user_id: ID dell'utente
            project_id: ID del progetto
            
        Returns:
            Preferenze del progetto
        """
        project = self.project_tracker.get_project(project_id)
        if not project:
            raise ValueError(f"Progetto {project_id} non trovato")
            
        return {
            "technical_level": self._determine_technical_level(user_id),
            "learning_style": self.preference_analyzer.get_learning_style(user_id),
            "project_settings": project.metadata.get("settings", {}),
            "user_preferences": self.personality.get_insights(user_id)
        }
        
    def create_project(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea un nuovo progetto.
        
        Args:
            user_id: ID dell'utente
            name: Nome del progetto
            description: Descrizione opzionale
            settings: Impostazioni opzionali
            
        Returns:
            ID del progetto creato
            
        Raises:
            ValueError: Se user_id è vuoto
        """
        if not user_id:
            raise ValueError("User ID non valido")
            
        return self.project_tracker.create_project(
            user_id,
            name,
            description,
            settings or {}
        )
        
    def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Aggiorna le preferenze di un utente.
        
        Args:
            user_id: ID dell'utente
            preferences: Nuove preferenze
            
        Returns:
            True se l'aggiornamento ha successo
            
        Raises:
            ValueError: Se user_id è vuoto o preferences non è un dizionario
        """
        if not user_id:
            raise ValueError("User ID non valido")
            
        if not isinstance(preferences, dict):
            raise ValueError("Le preferenze devono essere un dizionario")
            
        try:
            self.preference_analyzer.update_preferences(user_id, preferences)
            return True
        except Exception as e:
            print(f"Errore nel salvare le preferenze: {str(e)}")
            return False
        
    def get_emotion_history(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera la storia delle emozioni di un utente.
        
        Args:
            user_id: ID dell'utente
            start_time: Tempo di inizio opzionale
            end_time: Tempo di fine opzionale
            conversation_id: ID della conversazione opzionale
            
        Returns:
            Lista delle emozioni
        """
        interactions = self.memory_system.get_interactions(
            user_id,
            start_time,
            end_time
        )
        
        if conversation_id:
            interactions = [i for i in interactions if i.get("metadata", {}).get("conversation_id") == conversation_id]
            
        return [
            {
                "emotion": i["emotion"],
                "timestamp": i["timestamp"],
                "content": i["content"]
            }
            for i in interactions
            if i.get("emotion")
        ]
        
    def process_emotional_message(
        self,
        user_id: str,
        message: str
    ) -> Dict:
        """
        Processa un messaggio con analisi emotiva.
        
        Args:
            user_id: ID dell'utente
            message: Messaggio da processare
            
        Returns:
            Risultato dell'analisi emotiva
        """
        if not user_id or not message:
            raise ValueError("User ID e messaggio sono richiesti")
            
        # Analizza emozioni
        emotional_state = self.emotional_core.detect_emotion(message)
        
        # Salva l'interazione
        try:
            self.memory_system.store_interaction(
                user_id=user_id,
                interaction={
                    'content': message,
                    'emotion': emotional_state.primary_emotion,
                    'timestamp': datetime.now()
                },
                metadata={
                    "secondary_emotions": emotional_state.secondary_emotions,
                    "confidence": emotional_state.confidence
                }
            )
            is_stored = True
        except Exception as e:
            logging.error(f"Errore durante il salvataggio dell'interazione: {e}")
            is_stored = False
            
        return {
            "emotion": emotional_state.primary_emotion,
            "secondary_emotions": emotional_state.secondary_emotions,
            "confidence": emotional_state.confidence,
            "is_stored": is_stored
        }
        
    def process_visual_input(self, user_id: str, image_path: str, message: str = "") -> ProcessedResponse:
        """
        Processa un input visivo (immagine + eventuale testo).
        
        Args:
            user_id: ID utente
            image_path: Path dell'immagine
            message: Messaggio opzionale dell'utente (es. "Cosa vedi?")
            
        Returns:
            Risposta processata
        """
        logging.info(f"👁️ Processing visual input: {image_path}")
        
        # 1. Analisi Visiva
        visual_description = self.vision_system.analyze_image(image_path)
        logging.info(f"👁️ Descrizione Visiva: {visual_description}")
        
        # 2. Costruisci un messaggio composito per il cervello testuale
        # "L'utente ha inviato un'immagine che mostra: [descrizione]. Ha scritto: [messaggio]"
        composite_message = (
            f"[SYSTEM: L'utente ha inviato un'immagine. "
            f"Analisi visiva: {visual_description}] "
            f"{message}"
        )
        
        # 3. Passa tutto al normale flusso di processamento (così usa memoria, emozioni, reasoning)
        return self.process_message(composite_message, user_id)



    def generate_learning_response(
        self,
        user_id: str,
        query: str
    ) -> ProcessedResponse:
        """
        Genera una risposta di apprendimento.
        
        Args:
            user_id: ID dell'utente
            query: Query dell'utente
            
        Returns:
            Risposta processata
        """
        if not user_id or not query:
            raise ValueError("User ID e query sono richiesti")
            
        try:
            # Cerca conoscenza correlata
            related_knowledge = self.incremental_learner.find_related_knowledge(
                query
            )
            
            # Ottieni il topic e il contesto
            topic = self.topic_extractor.extract_topic(query)
            project_context = self._get_project_context(user_id, topic)
            user_preferences = self.preference_analyzer.analyze_learning_style(user_id)
            
            if related_knowledge:
                # Usa la conoscenza esistente
                unit = related_knowledge[0]
                return ProcessedResponse(
                    content=unit.content,
                    emotion="neutral",
                    topics=[topic],
                    emotion_detected=False,
                    project_context=project_context,
                    user_preferences=user_preferences,
                    knowledge_integrated=True,
                    confidence=0.0
                )
            else:
                # Genera nuova risposta
                context = ResponseContext(
                    user_id=user_id,
                    current_topic=topic,
                    technical_level=self._determine_technical_level(user_id),
                    conversation_history=[],
                    user_preferences=user_preferences
                )
                
                response = self.response_generator.generate_response(
                    query,
                    context
                )
                
                # Integra la nuova conoscenza
                if response.is_valid:
                    unit = LearningUnit(
                        topic=context.current_topic,
                        content=response.content,
                        source="generated",
                        confidence=ConfidenceLevel.LOW,
                        timestamp=datetime.now()
                    )
                    self.incremental_learner.add_learning_unit(unit)
                    
                return ProcessedResponse(
                    content=response.content,
                    emotion="neutral",
                    topics=[topic],
                    emotion_detected=False,
                    project_context=project_context,
                    user_preferences=user_preferences,
                    knowledge_integrated=True,
                    confidence=0.0
                )
        except Exception as e:
            logging.error(f"Errore nella generazione risposta: {e}")
            raise
        
    def get_learning_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Ottiene il progresso di apprendimento di un utente.

        Args:
            user_id: ID dell'utente

        Returns:
            Dict con il progresso di apprendimento
        """
        # Ottieni le interazioni dell'utente
        interactions = self.memory_system.get_interactions(
            user_id=user_id,
            start_time=(datetime.now() - timedelta(days=30))  # Ultimi 30 giorni
        )

        if not interactions:
            return {
                "topics": [],
                "confidence_levels": {},
                "recent_learning": []
            }

        # Analizza le interazioni per determinare il progresso
        topics = set()
        confidence_by_topic = defaultdict(list)
        recent_learning = []

        for interaction in interactions:
            if interaction.get("topics"):
                topics.update(interaction["topics"])
                
                # Calcola confidenza per ogni topic
                for topic in interaction["topics"]:
                    if interaction.get("metadata") and interaction["metadata"].get("confidence"):
                        confidence_by_topic[topic].append(
                            float(interaction["metadata"]["confidence"])
                        )

            # Aggiungi alle attività di apprendimento recenti
            recent_learning.append({
                "timestamp": interaction["timestamp"].isoformat(),
                "content": interaction["content"],
                "topics": interaction.get("topics", []),
                "confidence": interaction.get("metadata", {}).get("confidence", 0.0)
            })

        # Calcola la media della confidenza per ogni topic
        confidence_levels = {}
        for topic, confidences in confidence_by_topic.items():
            if confidences:
                confidence_levels[topic] = sum(confidences) / len(confidences)

        return {
            "topics": list(topics),
            "confidence_levels": confidence_levels,
            "recent_learning": sorted(
                recent_learning,
                key=lambda x: x["timestamp"],
                reverse=True
            )[:10]  # Ultimi 10 eventi
        }

    def _adapt_response(
        self,
        response: str,
        preferences: Union[Dict[str, Any], LearningPreference]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Adatta la risposta in base alle preferenze dell'utente.
        
        Args:
            response: Risposta da adattare
            preferences: Preferenze dell'utente come dizionario o oggetto LearningPreference
            
        Returns:
            Tupla con la risposta adattata e i metadati
        """
        # Inizializza la risposta adattata
        adapted_response = response
        
        # Traccia gli adattamenti applicati
        adaptations_applied = []
        
        # Gestisci sia dizionari che oggetti LearningPreference
        if isinstance(preferences, dict):
            comm_style = preferences.get('communication_style')
            learning_style = preferences.get('style')
            confidence = preferences.get('confidence', 0.5)
        else:
            comm_style = preferences.communication_style
            learning_style = preferences.primary_style
            confidence = preferences.confidence
            
        # Adatta in base allo stile di comunicazione
        if comm_style == CommunicationStyle.DETAILED:
            adapted_response = self._add_technical_details(adapted_response)
            adaptations_applied.append('technical_details')
        elif comm_style == CommunicationStyle.DIRECT:
            adapted_response = self._make_response_direct(adapted_response)
            adaptations_applied.append('direct')
        elif comm_style == CommunicationStyle.TECHNICAL:
            adapted_response = self._make_response_technical(adapted_response)
            adaptations_applied.append('technical')
        elif comm_style == CommunicationStyle.SIMPLIFIED:
            adapted_response = self._make_response_direct(adapted_response)
            adaptations_applied.append('simplified')
        elif comm_style == CommunicationStyle.INTERACTIVE:
            adapted_response = self._make_interactive(adapted_response)
            adaptations_applied.append('interactive')
        elif comm_style == CommunicationStyle.BALANCED:
            # Per lo stile bilanciato, combiniamo dettagli tecnici e interattività
            adapted_response = self._add_technical_details(adapted_response)
            adapted_response = self._make_interactive(adapted_response)
            adaptations_applied.extend(['technical_details', 'interactive'])
            
        # Adatta in base allo stile di apprendimento
        if learning_style == LearningStyle.VISUAL:
            adapted_response = self._make_response_visual(adapted_response)
            adaptations_applied.append('visual')
        elif learning_style == LearningStyle.KINESTHETIC:
            adapted_response = self._make_response_kinesthetic(adapted_response)
            adaptations_applied.append('kinesthetic')
        elif learning_style == LearningStyle.THEORETICAL:
            adapted_response = self._make_response_theoretical(adapted_response)
            adaptations_applied.append('theoretical')
            
        # Aggiungi metadati
        metadata = {
            'adaptations': adaptations_applied,  # Per retrocompatibilità
            'adaptations_applied': adaptations_applied,
            'confidence': confidence
        }
            
        return adapted_response, metadata
        
    def process_interaction(
        self,
        user_id: str,
        message: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa un'interazione con l'utente.
        
        Args:
            user_id: ID dell'utente
            message: Messaggio dell'utente
            project_id: ID del progetto opzionale
            
        Returns:
            Dizionario con il risultato dell'interazione
        """
        try:
            # Crea un ID conversazione
            conversation_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Crea un ID univoco per l'interazione
            interaction_id = int(datetime.now().timestamp() * 1000)
            
            # Processa il messaggio
            response = self.process_message(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message
            )
            
            # Prepara il risultato base
            result = {
                'success': True,
                'interaction_id': interaction_id,
                'response': response.content,
                'emotion': response.emotion,
                'topics': response.topics,
                'metadata': response.metadata,
                'project': None  # Initialize project field as None
            }
            
            # Se c'è un project_id, aggiorna il progetto e aggiungi info progetto al risultato
            if project_id is not None:
                try:
                    # Convert project_id to int safely
                    project_id_int = int(project_id)
                    
                    # Link the interaction to the project first
                    link_success = self.project_tracker.link_interaction(
                        project_id=project_id_int,
                        interaction_id=interaction_id,
                        interaction_type='user_message',
                        metadata={
                            'user_id': user_id,
                            'message': message,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    if not link_success:
                        raise Exception(f"Failed to link interaction {interaction_id} to project {project_id}")
                    
                    # Aggiorna il progetto con i metadati dell'interazione
                    self.project_tracker.update_project_interaction(
                        project_id=project_id_int,
                        interaction_id=interaction_id,
                        metadata={
                            'user_id': user_id,
                            'message': message,
                            'response': response.content,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    # Recupera e aggiungi le info del progetto al risultato
                    project = self.project_tracker.get_project(project_id_int)
                    if project:
                        result['project'] = {
                            'id': str(project_id_int),  # Convert back to string for consistency
                            'name': project.name,
                            'description': project.description,
                            'interaction_count': project.interaction_count
                        }
                except (ValueError, TypeError) as e:
                    logging.warning(f"Invalid project_id format: {project_id}. Error: {str(e)}")
                except Exception as e:
                    logging.error(f"Error processing project information: {str(e)}")
            
            return result
            
        except Exception as e:
            # Log dell'errore
            logging.error(f"Errore nel processamento dell'interazione: {str(e)}")
            
            # Restituisci un risultato di errore
            return {
                'success': False,
                'error': str(e),
                'response': "Mi dispiace, si è verificato un errore nel processare la tua richiesta.",
                'project': None  # Ensure project field exists even in error case
            }
        
    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """
        Analizza le emozioni nel testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dizionario con le emozioni rilevate e i loro punteggi
        """
        try:
            # Limita la lunghezza del testo per evitare problemi con il modello
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            # Analizza le emozioni usando il pipeline di emotion
            results = self.emotion_pipeline(text)
            
            if not results or not isinstance(results, list) or not results[0]:
                return {'neutral': 1.0}  # Fallback a neutrale se non ci sono risultati
                
            # Estrai i risultati
            emotions = {}
            for item in results[0]:
                emotions[item['label']] = item['score']
                
            # Debug log
            print(f"DEBUG - Raw result: {results}")
            print(f"DEBUG - First list: {results[0]}")
            
            # Ordina le emozioni per punteggio
            sorted_emotions = sorted(
                results[0],
                key=lambda x: x['score'],
                reverse=True
            )
            print(f"DEBUG - Sorted emotions: {sorted_emotions}")
            
            # Estrai l'emozione primaria
            primary = sorted_emotions[0]
            print(f"DEBUG - Primary emotion: {primary['label']} ({primary['score']})")
            
            # Estrai le emozioni secondarie
            secondary = {
                item['label']: item['score']
                for item in sorted_emotions[1:]
            }
            print(f"DEBUG - Secondary emotions: {secondary}")
            
            return emotions
            
        except Exception as e:
            print(f"Errore nell'analisi delle emozioni: {str(e)}")
            return {'neutral': 1.0}  # Fallback a neutrale in caso di errore

    def _make_response_direct(self, response: str) -> str:
        """Semplifica la risposta per uno stile diretto"""
        # Rimuovi frasi introduttive comuni
        phrases_to_remove = [
            "Come potrai immaginare",
            "come puoi vedere",
            "come sai",
            "naturalmente",
            "ovviamente",
            "è importante sottolineare che"
        ]
        
        simplified = response
        for phrase in phrases_to_remove:
            simplified = simplified.replace(phrase, "")
            
        # Rimuovi spazi multipli
        simplified = " ".join(simplified.split())
        
        return simplified

    def _make_response_supportive(self, response: str) -> str:
        """Rende la risposta più incoraggiante e supportiva."""
        # Aggiungi frasi di incoraggiamento
        supportive_phrases = [
            "Ottimo lavoro finora!",
            "Stai procedendo nella giusta direzione.",
            "Questa è un'ottima domanda.",
            "Hai fatto bene a chiedere questo.",
            "Non preoccuparti, ti aiuto io.",
            "Insieme troveremo la soluzione."
        ]
        
        # Scegli casualmente una frase di supporto
        import random
        prefix = random.choice(supportive_phrases)
        
        # Aggiungi la frase all'inizio della risposta
        supportive_response = f"{prefix}\n\n{response}"
        
        return supportive_response

    def _make_interactive(self, response: str) -> str:
        """Rende la risposta più interattiva."""
        # Aggiungi domande e suggerimenti per l'interazione
        return response

    def _add_technical_details(self, response: str) -> str:
        """
        Aggiunge dettagli tecnici alla risposta.
        
        Args:
            response: Risposta da arricchire con dettagli tecnici
            
        Returns:
            Risposta arricchita con dettagli tecnici
        """
        # Lista di dettagli tecnici da aggiungere se pertinenti
        technical_aspects = {
            "pattern": "Questo pattern segue i principi SOLID e facilita la manutenibilità del codice.",
            "database": "L'implementazione utilizza prepared statements per prevenire SQL injection.",
            "performance": "L'algoritmo ha una complessità temporale di O(n) e spaziale di O(1).",
            "architettura": "L'architettura segue il modello MVC per una chiara separazione delle responsabilità.",
            "sicurezza": "Implementiamo best practice di sicurezza come input validation e output encoding.",
            "testing": "Il codice è coperto da unit test con JUnit e test di integrazione.",
            "api": "L'API segue i principi REST e utilizza autenticazione OAuth2."
        }
        
        # Aggiungi dettagli tecnici pertinenti
        added_details = []
        for keyword, detail in technical_aspects.items():
            if keyword.lower() in response.lower() and detail not in response:
                added_details.append(detail)
                
        if added_details:
            response += "\n\nDettagli tecnici aggiuntivi:\n- " + "\n- ".join(added_details)
            
        return response

    def _add_practical_examples(self, response: str) -> str:
        """Aggiunge esempi pratici alla risposta."""
        # TODO: Implementare logica per aggiungere esempi pratici
        return response
        
    def _make_response_visual(self, response: str) -> str:
        """
        Rende la risposta più visuale, aggiungendo riferimenti a diagrammi e immagini.
        
        Args:
            response: Risposta da rendere visuale
            
        Returns:
            Risposta con elementi visuali
        """
        # Se la risposta parla di codice o design pattern, aggiungi un esempio di codice
        if "codice" in response.lower() or "pattern" in response.lower():
            response += "\n```python\n# Esempio di implementazione\nclass ExamplePattern:\n    def __init__(self):\n        pass\n\n    def apply(self):\n        pass\n```"
        else:
            response += "\n[Qui verrebbe inserito un diagramma esplicativo]"
            
        return response

    def _make_response_kinesthetic(self, response: str) -> str:
        """
        Rende la risposta più pratica e orientata all'azione.
        
        Args:
            response: Risposta da rendere pratica
            
        Returns:
            Risposta con elementi pratici
        """
        # TODO: Implementare la logica per rendere la risposta più pratica
        # Per ora ritorna la risposta originale con un placeholder
        return f"{response}\n[Qui verrebbero inseriti esercizi pratici e istruzioni step-by-step]"

    def _make_response_theoretical(self, response: str) -> str:
        """
        Rende la risposta più teorica e concettuale.
        
        Args:
            response: Risposta da rendere teorica
            
        Returns:
            Risposta con elementi teorici
        """
        # TODO: Implementare la logica per rendere la risposta più teorica
        # Per ora ritorna la risposta originale con un placeholder
        return f"{response}\n[Qui verrebbero inseriti concetti teorici e riferimenti accademici]"

    def _make_response_technical(self, response: str) -> str:
        """Rende la risposta più tecnica."""
        # Aggiungi dettagli tecnici e terminologia specifica
        technical_details = [
            "implementazione",
            "architettura",
            "pattern",
            "algoritmo",
            "ottimizzazione",
            "complessità",
            "performance"
        ]
        
        # Se la risposta contiene "design pattern" in minuscolo, sostituiscilo con "Design Pattern"
        response = response.replace("design pattern", "Design Pattern")
        
        # Aggiungi almeno un dettaglio tecnico se non presente
        has_technical = any(detail in response.lower() for detail in technical_details)
        if not has_technical:
            # Se la risposta parla di design o architettura, aggiungi Pattern
            if "design" in response.lower() or "architettura" in response.lower():
                response = "Utilizzando il Pattern appropriato, " + response
            else:
                # Altrimenti scegli un dettaglio tecnico casuale
                import random
                detail = random.choice(technical_details)
                response = f"Dal punto di vista della {detail}, " + response
        
        # Rimuovi espressioni colloquiali
        colloquial = [
            "Come potrai immaginare",
            "come puoi vedere",
            "come sai",
            "naturalmente",
            "ovviamente",
            "è importante sottolineare che"
        ]
        
        for phrase in colloquial:
            response = response.replace(phrase, "")
        
        # Aggiungi dettagli tecnici alla fine
        response = response.strip() + "\nQuesta soluzione garantisce una migliore performance e manutenibilità del codice."
        
        return response

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Recupera il profilo dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dizionario con il profilo dell'utente
        """
        learning_style = self.preference_analyzer.analyze_learning_style(user_id)
        emotional_state = self.emotional_core.get_user_emotional_state(user_id)
        
        # Converti learning_style in un dizionario di preferenze
        preferences = {}
        if learning_style:
            preferences = {
                'style': learning_style.primary_style.value if learning_style.primary_style else None,
                'communication_style': learning_style.communication_style.value if learning_style.communication_style else None,
                'confidence': learning_style.confidence
            }
        
        # Recupera i pattern temporali dalle interazioni
        temporal_patterns = self.memory_system.get_temporal_patterns(user_id)
        
        # Recupera il conteggio delle interazioni
        interaction_count = 0  # TODO: Implementare get_user_interactions
        
        return {
            "preferences": preferences,
            "learning_style": learning_style,
            "emotional_state": emotional_state,
            "temporal_patterns": temporal_patterns,
            "interactions": [],  # TODO: Implement interaction history
            "interaction_count": interaction_count
        }

    def test_preferences(self):
        preferences = {
            'style': CommunicationStyle.DIRECT,
            'confidence': 0.8
        }
        return preferences

    def get_learned_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """
        Recupera la conoscenza appresa su un determinato topic
        
        Args:
            topic: Il topic su cui recuperare la conoscenza
            
        Returns:
            List[Dict[str, Any]]: Lista di unità di conoscenza
        """
        # Recupera la conoscenza diretta dal topic
        knowledge = self.incremental_learner.get_knowledge_by_topic(topic)
        
        # Se non trova conoscenza diretta, cerca nei topic correlati
        if not knowledge:
            # Cerca conoscenza correlata con una soglia di similarità più bassa
            related_units = self.incremental_learner.find_related_knowledge(topic, threshold=0.2)
            for unit in related_units:
                knowledge.append({
                    'topic': unit.topic,
                    'content': unit.content,
                    'confidence': unit.confidence.value,
                    'timestamp': unit.timestamp.isoformat(),
                    'metadata': unit.metadata
                })
                    
        return knowledge

    def _get_project_context(self, user_id: str, topic: str) -> Dict[str, Any]:
        """
        Recupera il contesto del progetto corrente.
        Implementazione placeholder che ritorna un contesto base.
        """
        return {
            "current_project": "ALLMA_V4", 
            "active_files": [],
            "status": "development",
            "relevant_docs": []
        }

    def _determine_technical_level(self, user_id: str) -> str:
        """
        Determina il livello tecnico dell'utente.
        Implementazione placeholder.
        """
        return "expert"

    def start_dreaming(self):
        """
        Manually trigger the dream cycle (e.g. on user command or app pause).
        """
        if self.dream_manager:
            self.dream_manager.check_and_start_dream()
