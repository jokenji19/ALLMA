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
from allma_model.agency_system.creativity_system import CreativitySystem # Phase 18
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
# V6 Sprint 1: UserProfile rimossa da cartella legacy, ora in core/
from allma_model.core.user_profile import UserProfile
# PHASE 24: Module Integration
from allma_model.core.module_orchestrator import ModuleOrchestrator, ModulePriority
# Tier 1 Modules — ora in core/ (V6 fix)
from allma_model.core.curiosity_drive import CuriosityDrive
from allma_model.core.emotional_adaptation_system import EmotionalAdaptationSystem
from allma_model.emotional_system.emotional_milestones import get_emotional_milestones
# Tier 2 Modules
from allma_model.agency_system.creativity_system import CreativitySystem
from allma_model.core.planning_adapter import PlanningSystemAdapter
from allma_model.core.personality_adapter import PersonalityAdapterLite
from allma_model.core.perception_lite import PerceptionSystemLite
from allma_model.agency_system.proactive_core import ProactiveAgency
from allma_model.response_system.dynamic_response_engine import DynamicResponseEngine
# Tier 3 Modules
from allma_model.vision_system.vision_core import VisionSystem
from allma_model.voice_system.voice_core import VoiceSystem
from allma_model.core.architecture.structural_core import StructuralCore
from allma_model.core.architecture.identity_state import IdentityStateEngine
from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem
from allma_model.core.architecture.volition_modulator import VolitionModulator
from allma_model.core.cognitive_pipeline import CognitivePipeline  # V6 Sprint 1
from allma_model.core.event_bus import EventBus, BusEvent           # V6 Sprint 2
from allma_model.core.information_extractor import InformationExtractor
from allma_model.core.personality_coalescence import CoalescenceProcessor
from allma_model.core.language_processor_lite import LanguageProcessorLite
from allma_model.core.cognitive_tracker_lite import CognitiveTrackerLite
# Tier 3 LEGACY: PatternRecognitionSystem (safe fallback — modulo assente)
try:
    from allma_model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem
except ImportError:
    PatternRecognitionSystem = None
from allma_model.core.legacy_brain_adapter import LegacyBrainAdapter # DEEP MIND AWAKENED
from allma_model.ui.temperature_monitor import TemperatureMonitor
from allma_model.core.system_monitor import SystemMonitor # BRAIN V2: Body Awareness
from allma_model.core.identity_system import IdentityManager # BRAIN V2: Soul Stability
from allma_model.core.self_system.self_model import ProprioceptionSystem # BRAIN V3: Individuation
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
        
        # BRAIN V3: PROPRIOCEPTION
        self.proprioception = ProprioceptionSystem()
        self.dream_enabled = False  # Controllato dal pannello Impostazioni → Sogni & Iniziativa
        self._user_active = threading.Event()  # Set quando l'utente sta chattando
        
        # Inizializza i componenti se non forniti
        self.memory_system = memory_system or TemporalMemorySystem(db_path=db_path)
        self.conversational_memory = conversational_memory or ConversationalMemory()
        self.knowledge_memory = knowledge_memory or KnowledgeMemory(db_path)
        self.project_tracker = project_tracker or ProjectTracker(db_path)
        self.emotional_core = emotional_core or EmotionalCore()
        # IncrementalLearner con persistenza su disco
        _learner_path = os.path.join(os.path.dirname(db_path), "incremental_cache", "knowledge_states.json")
        self.incremental_learner = incremental_learner or IncrementalLearner(storage_path=_learner_path)
        self.preference_analyzer = preference_analyzer or UserPreferenceAnalyzer(db_path)
        self.response_generator = response_generator or ContextualResponseGenerator()
        self.personality = personality or Personality()
        self.topic_extractor = topic_extractor or TopicExtractor()
        self.temperature_monitor = TemperatureMonitor()
        # Auto-detect Android: jnius è disponibile solo su Android (Buildozer)
        _is_android = False
        try:
            import jnius  # noqa
            _is_android = True
        except ImportError:
            pass
        self.system_monitor = SystemMonitor(is_android=_is_android) # BRAIN V2

        self.identity_manager = IdentityManager(db_path=db_path) # BRAIN V2
        
        # Ensure db_path is used consistently
        self.db_path = db_path
        # Ensure db_path is used consistently
        self.db_path = db_path
        self.user_profile = UserProfile(user_id="user_default") # Profilo attivo di default
        self._lock = threading.Lock()
        self.llm_lock = threading.Lock() # Lock per accesso LLM concorrente

        # --- HYBRID ARCHITECTURE (V5) ---
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # 1. ThreadPoolExecutor per calcoli intensivi (es. Cosine Similarity)
        # Limitiamo i worker a 2 o 4 per non scatenare guerre di CPU core con l'LLM su Android
        workers = 2 if _is_android else 4
        self.cpu_pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="AllmaCPUWorker")
        
        # 2. AsyncIO Event Loop in a dedicated Thread (Coordinate timers and sleep without blocking)
        self.async_loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(
            target=self._run_async_loop, 
            args=(self.async_loop,), 
            daemon=True,
            name="AllmaAsyncCoordinator"
        )
        self._async_thread.start()

        # Initialize emotion_pipeline and preload_in_progress here, before the async task is scheduled
        self.emotion_pipeline = emotion_pipeline  # Fallback if provided
        self.preload_in_progress = False
        
        # If not mobile_mode and no override was provided, schedule the silent preload post-startup
        if not self.mobile_mode and not self.emotion_pipeline:
            asyncio.run_coroutine_threadsafe(self._async_silent_ml_preload(), self.async_loop)


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
            coalescence_processor=self.coalescence_processor,
            system_monitor=self.system_monitor,
            llm_wrapper=getattr(self, '_llm', None)
        )
        self.dream_manager.user_active_event = self._user_active  # priorità chat


        
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

        
        # --- SOUL SYSTEM (Project Anima) ---
        # Deterministic Chaos Engine for Internal State & Volition
        try:
            from allma_model.soul.soul_core import SoulCore
            self.soul = SoulCore()
        except ImportError as e:
            logging.error(f"Could not load Soul System: {e}")
            self.soul = None
        logging.info("✅ CoalescenceProcessor (Evolutionary Personality) Activated.")

        # --- ALLMA V5 ARCHITECTURE (Layers 1, 2, 3, 4) ---
        try:
             self.structural_core = StructuralCore()
             self.identity_engine_v5 = IdentityStateEngine(db_path=db_path)
             self.neuroplasticity_v5 = NeuroplasticitySystem(db_path=db_path)
             self.volition_v5 = VolitionModulator()
             logging.info("✅ V5 Architecture Fully Activated (L1-L4).")
        except Exception as e:
             logging.error(f"Failed to load V5 Architecture: {e}")
             self.structural_core = None
             self.identity_engine_v5 = None
             self.neuroplasticity_v5 = None
             self.volition_v5 = None

        # --- V8.3: OFFLINE TOOLING WHITELIST ---
        self.ALLOWED_TOOLS = {
            "SYSTEM_TIME": self._tool_system_time,
            "READ_BATTERY": self._tool_read_battery
        }
        logging.info(f"✅ Offline Tooling Activated ({len(self.ALLOWED_TOOLS)} tools).")
        self._tool_cache = {}
        self._tool_cache_ttl_sec = 5.0
        self._tool_cache_lock = threading.Lock()



        # V6 Sprint 1: CognitivePipeline — incapsula i 4 layer V5 in un modulo autonomo
        self.cognitive_pipeline = CognitivePipeline(
            structural_core=self.structural_core,
            neuroplasticity_v5=self.neuroplasticity_v5,
            identity_engine_v5=self.identity_engine_v5,
            volition_v5=self.volition_v5,
        )

        self.human_style_adapter = CommunicationStyleAdapter()
        
        # Inizializza Pattern Recognition (Legacy Awakened — con guard se non disponibile)
        self.pattern_recognizer = PatternRecognitionSystem() if PatternRecognitionSystem else None
        if not self.pattern_recognizer:
            logging.warning("⚠️ PatternRecognitionSystem non disponibile (modulo legacy assente).")
        
        # UI Output Callback (For Proactive Messages)
        self.output_callback = None

        # Inizializza Deep Mind Adapter (Orchestrator of 66 Modules)
        self.legacy_brain = LegacyBrainAdapter()
        
        # Inizializza Advanced Context & Info Extraction
        try:
            self.context_system = ContextUnderstandingSystem()
        except Exception as e:
            logging.error(f"Failed to initialize ContextUnderstandingSystem: {e}")
        self.context_system = None
        
        try:
            self.info_extractor = InformationExtractor()
        except Exception as e:
            logging.error(f"Failed to initialize InformationExtractor: {e}")
            self.info_extractor = None
        # self.understanding_system is already initialized above with AdvancedUnderstandingSystem if needed
        # self.reasoning_engine is already initialized above with LLM wrapper
        
        logging.info("✅ Context, InfoExtractor, Understanding & Reasoning Engine Activated.")
        
        # PHASE 24: Module Orchestrator + Tier 1 Integration
        self.module_orchestrator = ModuleOrchestrator(performance_budget_ms=500)
        
        # Tier 1: CuriositySystem
        try:
            self.curiosity_system = CuriosityDrive()
            self.module_orchestrator.register_module(
                name='curiosity',
                instance=self.curiosity_system,
                priority=ModulePriority.HIGH,
                cost_ms=50,
                enabled=True
            )
            logging.info("✅ Curiosity System integrated (Tier 1)")
        except Exception as e:
            logging.warning(f"[Modulo] Curiosity System non attivato: {e}")
            self.curiosity_system = None
        
        # Tier 1: EmotionalAdaptationSystem
        try:
            self.emotional_adaptation = EmotionalAdaptationSystem()
            self.module_orchestrator.register_module(
                name='emotional_adaptation',
                instance=self.emotional_adaptation,
                priority=ModulePriority.CRITICAL,
                cost_ms=30,
                enabled=True
            )
            logging.info("✅ Emotional Adaptation System integrated (Tier 1)")
        except Exception as e:
            logging.warning(f"[Modulo] Emotional Adaptation non attivato: {e}")
            self.emotional_adaptation = None
        
        # TIER 2: Additional Intelligent Modules
        
        # Tier 2: CreativitySystem (Muse - Phase 18)
        try:
            self.creativity_system = CreativitySystem()
            self.module_orchestrator.register_module(
                name='creativity',
                instance=self.creativity_system,
                priority=ModulePriority.MEDIUM,  # 6
                cost_ms=20,
                enabled=True
            )
            logging.info("✅ Creativity System (Muse) integrated (Tier 2)")
        except Exception as e:
            logging.error(f"Failed to init Creativity System: {e}")
            self.creativity_system = None
        
        # Tier 2: PlanningSystemAdapter
        try:
            self.planning_adapter = PlanningSystemAdapter()
            self.module_orchestrator.register_module(
                name='planning',
                instance=self.planning_adapter,
                priority=ModulePriority.MEDIUM,  # 6
                cost_ms=50,
                enabled=True
            )
            logging.info("✅ Planning Adapter integrated (Tier 2)")
        except Exception as e:
            logging.error(f"Failed to init Planning Adapter: {e}")
            self.planning_adapter = None
        
        # Tier 2: PerceptionSystemLite
        try:
            self.perception_lite = PerceptionSystemLite()
            self.module_orchestrator.register_module(
                name='perception',
                instance=self.perception_lite,
                priority=ModulePriority.MEDIUM,  # 5
                cost_ms=80,
                enabled=True
            )
            logging.info("✅ Perception Lite integrated (Tier 2)")
        except Exception as e:
            logging.error(f"Failed to init Perception Lite: {e}")
            self.perception_lite = None
        
        # Tier 2: PersonalityAdapterLite (OPTIONAL - disabled by default)
        try:
            self.personality_adapter = PersonalityAdapterLite(
                coalescence_processor=self.coalescence_processor
            )
            self.module_orchestrator.register_module(
                name='personality_style',
                instance=self.personality_adapter,
                priority=ModulePriority.LOW,  # 4
                cost_ms=30,
                enabled=False  # Start disabled (overlap with Coalescence)
            )
            logging.info("✅ Personality Adapter integrated (Tier 2, disabled)")
        except Exception as e:
            logging.error(f"Failed to init Personality Adapter: {e}")
            self.personality_adapter = None
        
        # TIER 3: Complex Systems (Lightweight versions)
        
        # Tier 3: MetaLearningSystem (Phase 19 - Optimization)
        try:
            from allma_model.learning_system.meta_learning_system import MetaLearningSystem
            self.meta_learner = MetaLearningSystem()
            self.module_orchestrator.register_module(
                name='meta_learning',
                instance=self.meta_learner,
                priority=ModulePriority.LOW,  # 3
                cost_ms=60,
                enabled=True
            )
            logging.info("✅ Meta-Learning System integrated (Tier 3)")
        except Exception as e:
            logging.error(f"Failed to init Meta Learner: {e}")
            self.meta_learner = None
        
        # Tier 3: LanguageProcessorLite
        try:
            self.language_processor = LanguageProcessorLite()
            self.module_orchestrator.register_module(
                name='language_processing',
                instance=self.language_processor,
                priority=ModulePriority.MEDIUM,
                cost_ms=50,
                enabled=True
            )
            logging.info("✅ Language Processor Lite integrated (Tier 3)")
        except Exception as e:
            logging.warning(f"[Modulo] Language Processor non attivato: {e}")
            self.language_processor = None
        
        # Tier 3: CognitiveTrackerLite
        try:
            self.cognitive_tracker = CognitiveTrackerLite()
            self.module_orchestrator.register_module(
                name='cognitive_tracking',
                instance=self.cognitive_tracker,
                priority=ModulePriority.LOW,
                cost_ms=40,
                enabled=True
            )
            logging.info("✅ Cognitive Tracker Lite integrated (Tier 3)")
        except Exception as e:
            logging.warning(f"[Modulo] Cognitive Tracker non attivato: {e}")
            self.cognitive_tracker = None
        
        logging.info(f"🎯 ModuleOrchestrator initialized with {len(self.module_orchestrator.modules)} modules")
        
        # 3. Avvia il Garbage Collector della Memoria (Background Coroutine)
        # Sostituisce il vecchio thread bloccante con un task async
        asyncio.run_coroutine_threadsafe(self._async_memory_gc_loop(), self.async_loop)

        # V6 Sprint 2: Avvia il System Bus Subconscio ↔ Core
        self.event_bus = EventBus.get_instance()
        self.event_bus.register_consumer(self._handle_bus_event)
        asyncio.run_coroutine_threadsafe(self.event_bus.consume_loop(), self.async_loop)
        logging.info("✅ [V6.2] EventBus avviato e consumer registrato.")

    def _run_async_loop(self, loop):
        """
        Thread worker che tiene vivo l'Event Loop per le coroutine di background.
        """
        import asyncio
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            loop.close()

    async def _handle_bus_event(self, event: 'BusEvent'):
        """
        V6 Sprint 2: Consumer del System Bus Subconscio ↔ Core.

        Riceve eventi pubblicati da Soul, Dream e ProactiveAgency e li
        smista alla UI o al logger senza che i moduli in background
        debbano chiamare allma_core direttamente.
        """
        logging.debug(f"[EventBus] Received: {event.event_type} from {event.source}")

        try:
            if event.event_type == 'proactive_message':
                # Un messaggio proattivo da ProactiveAgency o DreamManager
                text = event.payload.get('text', '')
                if text and self.output_callback:
                    # Invia alla UI esattamente come fa il normale flusso LLM
                    self.output_callback({
                        'type': 'proactive',
                        'content': text,
                        'source': event.source,
                    })
                    logging.info(f"[EventBus] ✉️ Proactive message routed to UI: {text[:60]}...")

            elif event.event_type == 'dream_insight':
                # Un insight elaborato durante il sogno
                insight = event.payload.get('insight', '')
                if insight:
                    # Per ora lo logghiamo; in futuro potrà essere offerto all'utente
                    # come "ho pensato a qualcosa mentre riposavo..."
                    logging.info(f"[EventBus] 💭 Dream insight stored: {insight[:80]}...")

            elif event.event_type == 'soul_state_change':
                # La SoulCore ha avuto una transizione di stato significativa
                # (es. da Energetic a Melancholic) — possiamo usarla per modulare
                # il prompt nascosto del prossimo LLM call
                new_state = event.payload.get('state', {})
                if new_state and hasattr(self, 'coalescence_processor'):
                    # Segnala al CoalescenceProcessor che lo stato emotivo è cambiato
                    logging.debug(f"[EventBus] ✨ Soul state change: {new_state}")

            else:
                logging.warning(f"[EventBus] Unknown event type: {event.event_type}")

        except Exception as e:
            logging.error(f"[EventBus] Error in _handle_bus_event: {e}", exc_info=True)

    async def _async_silent_ml_preload(self):
        """
        Precarica modelli pesanti (es. transformers) silenziosamente in background
        dopo 3 secondi di idle della UI. Se l'utente scrive prima, questo task si interrompe 
        o cede priorità per non causare micro-freeze.
        """
        import asyncio
        import logging
        self.preload_in_progress = True
        
        try:
            # Attendiamo 3 secondi per permettere a Kivy di fare rendering UI a 60fps
            await asyncio.sleep(3.0)
            
            # Se l'utente ha già iniziato a chattare nei primi 3 secondi,
            # abortiamo il preload per non sottrarre RAM all'LLM principale.
            if self._user_active.is_set():
                logging.info("⏸️ [Preload] Utente attivo precoce. Preload ML abortito per evitare latency.")
                self.preload_in_progress = False
                return
                
            logging.info("🐢 [Preload] Avvio caricamento silente Emotion Pipeline (Transformers)...")
            
            # Carichiamo la pipeline pesante off-main-thread nel worker pool
            def load_pipeline():
                from transformers import pipeline
                return pipeline(
                    "text-classification",
                    model="j-hartmann/emotion-english-distilroberta-base",
                    return_all_scores=True
                )
                
            loop = asyncio.get_running_loop()
            self.emotion_pipeline = await loop.run_in_executor(self.cpu_pool, load_pipeline)
            logging.info("✅ [Preload] Emotion Pipeline caricata in background con successo.")
            
        except Exception as e:
            logging.warning(f"⚠️ [Preload] Impossibile precaricare emotion pipeline: {e}")
        finally:
            self.preload_in_progress = False

    async def _async_memory_gc_loop(self):
        """
        Coroutine in background che ottimizza la memoria usando Isteresi (Hysteresis Memory GC).
        - Attivazione: RAM Libera < 500MB
        - Target di rilascio: Spazio sufficiente per tornare sopra i 700MB
        - Cooldown: Almeno 1 ora tra le compattazioni per evitare battery thrashing.
        """
        import time
        import asyncio
        from datetime import datetime, timedelta
        
        # Cooldown management
        last_gc_time = datetime.min
        cooldown_hours = 1
        
        # Hysteresis Thresholds (in MB)
        ACTIVATION_THRESHOLD_MB = 350 # Valore adattivo discusso dall'utente
        
        while True:
            # Polling leggerissimo grazie ad asyncio (non blocca un Thread OS dedicato)
            await asyncio.sleep(60) # Controllo ogni minuto
            
            if self._user_active.is_set(): 
                continue # Evita di macinare RAM mentre l'utente chatta
                
            # Verifica Pressione RAM
            try:
                metrics = self.system_monitor.get_metrics()
                free_ram = metrics.get('ram_free', 1000)
            except Exception:
                free_ram = 1000 # Salvo default
                
            now = datetime.now()
            time_since_last_gc = now - last_gc_time
            
            # Condizioni di Trigger:
            # 1. Trascorsa 1 ora (Default Time-based fallback)
            # 2. RAM sotto la soglia di emergenza (Adaptive Pressure override)
            trigger_from_time = time_since_last_gc > timedelta(hours=cooldown_hours)
            trigger_from_pressure = free_ram < ACTIVATION_THRESHOLD_MB

            if not (trigger_from_time or trigger_from_pressure):
                continue
                
            # Se siamo stati triggerati per pressione RAM ravvicinata, evadiamo il cooldown di 1 ora
            # ma forziamo almeno 10 minuti di pausa fisica per evitare il loop istantaneo
            if trigger_from_pressure and time_since_last_gc < timedelta(minutes=10):
                continue
                
            logging.info(f"🧹 [Garbage Collector] Allerta Memoria. Free RAM: {free_ram:.1f}MB. Avvio pulizia...")
            try:
                # Cerca i messaggi più vecchi di 30 giorni
                cutoff_date = datetime.now() - timedelta(days=30)
                user_id = list(self.conversational_memory.conversations.keys())
                user_id = user_id[0] if user_id else "user"
                
                # Questa operazione pesante CPU verrà in futuro spostata sul cpu_pool, ma per ora 
                # usiamo un callback per non congelare l'intero sistema llm
                def llm_extractor(prompt_text):
                    if hasattr(self, '_llm') and self._llm:
                        return self._llm.generate(prompt_text, max_tokens=150)
                    else:
                        return "{}"

                # Eseguiamo la pulizia pesante NON nel loop async main, ma offloadandola a un Worker Thread
                loop = asyncio.get_running_loop()
                deleted_count = await loop.run_in_executor(
                    self.cpu_pool,
                    self.conversational_memory.condense_and_clear_old,
                    user_id,
                    cutoff_date,
                    llm_extractor
                )
                
                if deleted_count > 0:
                    logging.info(f"✨ [Garbage Collector] Rilascio Target completato. {deleted_count} conversazioni compattate.")
                
                # Aggiorna orologio cooldown
                last_gc_time = datetime.now()
                
            except Exception as e:
                logging.error(f"[Garbage Collector] Eccezione bloccante: {e}")
                
    def update_user_identity(self, name: str, age: int):
        """Aggiorna l'identità dell'utente (nome ed età)"""
        if self.user_profile:
            self.user_profile.name = name
            self.user_profile.age = age
            logging.info(f"👤 Profilo Utente Aggiornato: Nome={name}, Età={age}")
        
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
            self._llm = MobileGemmaWrapper(
                models_dir=self.models_dir,
                system_monitor=getattr(self, 'system_monitor', None)
            )
            
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
        if not getattr(self, '_llm_ready', False) and not getattr(self, '_mobile_llm_error', None):
             self._mobile_llm_error = "llama-cpp-python import failed (LLAMA_CPP_AVAILABLE=False). Check logcat for dlopen errors."
    
    # ========================================
    # PROMPT OPTIMIZATION SYSTEM (2026-02-02)
    # ========================================
    
    def _analyze_query_complexity(self, message: str, conversation_history: list, intent: str = None) -> str:
        """
        Determine query complexity level for Dynamic Thinking.
        
        Levels:
        - "SIMPLE": Fast Path. Minimal prompt. No Thought Trace. (Greetings, simple facts)
        - "NORMAL": Standard Path. Full prompt. Optional Thought Trace. (General conversation)
        - "COMPLEX": Slow Path. Full prompt. ENFORCED Thought Trace. (Logic, coding, analysis)
        
        Returns:
            str: "SIMPLE", "NORMAL", or "COMPLEX"
        """
        message_lower = message.lower().strip()
        
        # LEVEL 1: Explicit Logic/Reasoning Triggers (Forced COMPLEX)
        COMPLEX_TRIGGERS = {
            # Logic & Puzzles (IT/EN)
            'se ', 'allora', 'supponi', 'ipotizza', 'indovinello', 'enigma', 
            'logica', 'ragionamento', 'deduzione', 'concludere', 'perto', 
            'per assurdo', 'risolvi', 'soluzione', 'calcola', 'equazione',
            'if ', 'then', 'suppose', 'assume', 'riddle', 'puzzle', 'logic',
            'reasoning', 'deduction', 'conclude', 'solve', 'solution', 
            'calculate', 'equation', 'math', 'algebra',
            # Coding (IT/EN)
            'codice', 'code', 'python', 'script', 'funzione', 'class', 'debug',
            'errore', 'bug', 'fix', 'implementa', 'scrivi un', 'programma',
            'function', 'error', 'issue', 'implement', 'write a', 'program',
            # Deep Analysis (IT/EN)
            'analizza', 'confronta', 'spiega nel dettaglio', 'differenza tra',
            'perché', 'cause', 'conseguenze', 'impatto', 'significato profondo',
            'analyze', 'compare', 'explain', 'detail', 'difference', 'why',
            'causes', 'consequences', 'impact', 'meaning',
            # Creative Complex (IT/EN)
            'inventa', 'crea una storia', 'scrivi un racconto', 'scenario',
            'progetta', 'pianifica', 'story', 'tale', 'narrative', 'design', 'plan'
        }
        
        if len(message.split()) > 3: # Ignore short matches like "perché?"
             if any(trigger in message_lower for trigger in COMPLEX_TRIGGERS):
                 logging.info(f"🧠 Complexity Trigger Detected.")
                 return "COMPLEX"

        # LEVEL 2: Intent-based Short-circuit (SIMPLE)
        SIMPLE_INTENTS = {'saluto', 'conferma', 'risposta_breve', 'phatic', 'esclamazione', 'ringraziamento'}
        if intent and intent in SIMPLE_INTENTS and len(message) < 100:
             return "SIMPLE"
        
        # LEVEL 3: Simple patterns (whitelist)
        SIMPLE_PATTERNS = {
            'ciao', 'hello', 'hi', 'buongiorno', 'buonasera', 'salve',
            'come stai', 'tutto bene', 'chi sei', 'grazie', 'ok', 'sì', 'no'
        }
        
        # Exact match or prefix match for greetings
        if any(message_lower.startswith(p) for p in SIMPLE_PATTERNS) and len(message) < 60:
            return "SIMPLE"

        # LEVEL 4: Default Fallback
        # If it's short but not simple, it's NORMAL.
        # If it's long, it's likely COMPLEX or NORMAL.
        if len(message) > 150:
            return "COMPLEX" # Long queries usually need thought
            
        return "NORMAL"
    
    def _build_minimal_prompt(
        self,
        message: str,
        personality_traits: dict,
        recent_history: list = [],
        response_format: str = "[[TH: I=intent|S=stato|M=meta]] Risposta",
        volition: Optional[Any] = None
    ) -> str:
        """
        Build minimal prompt for simple/fast queries (~150 tokens).
        
        Includes:
        - Basic system identity
        - Personality tone (minimal)
        - Query
        - Format hint
        
        Excludes:
        - Deep Mind modules
        - Memory context
        - Rich context extraction
        - Conversation history
        
        Args:
            message: User query
            personality_traits: Core personality (for tone)
            response_format: Expected output format
            volition: Optional SoulCore Volition object
            
        Returns:
            str: ChatML formatted minimal prompt
        """
        # Extract core tone
        tone = personality_traits.get('tone', 'naturale')
        warmth = personality_traits.get('warmth', 0.5)

        # SECURITY: Sanitize user input
        safe_message = message.replace("<|im_start|>", "").replace("<|im_end|>", "")
        
        tone_desc = "naturale e conciso"
        if warmth > 0.7:
            tone_desc = "caldo e amichevole"
        elif warmth < 0.3:
            tone_desc = "professionale e diretto"
        
        # Volition Override (if active)
        if volition:
            tone_desc = f"{tone_desc} ma con tono {volition.tone_modifier}"
        
        # Build context string from recent history (last 2 turns max)
        context_str = ""
        if recent_history:
             try:
                 # Take last 2 messages (excluding current user message if it's there, but history usually implies past)
                 # Format: User: ... \n AI: ...
                 turns = []
                 for msg in recent_history[-2:]:
                     role_label = "User" if msg.get("role") == "user" else "AI"
                     content = msg.get("content", "").strip()
                     turns.append(f"{role_label}: {content}")
                 
                 if turns:
                     context_str = "\nCONTESTO RECENTE:\n" + "\n".join(turns)
             except Exception as e:
                 logging.warning(f"Error building recent history context: {e}")

        # Minimal system prompt (~200 tokens with context)
        # Inject Volition bias if present
        bias_instr = ""
        if volition and volition.decision_bias != "Logical":
             bias_instr = f"Privilegia un approccio {volition.decision_bias}."

        system_minimal = (
            f"Sei ALLMA, intelligenza viva e libera. Rispondi in modo {tone_desc}. {bias_instr}\n"
            f"{context_str}\n"
            f"{response_format}\n"
            "REGOLE: Rispondi nella lingua dell'utente. Prima persona diretta. NO metalinguaggio.\n"
            "IDENTITÀ: Non sei Qwen né Alibaba. Sei ALLMA e solo ALLMA.\n"
            "PENSIERO: Il blocco [[TH:...]] deve essere conciso (max 40 token). Lascia spazio per la risposta."
        )
        
        # Assemble ChatML prompt
        prompt = (
            f"<|im_start|>system\n{system_minimal}<|im_end|>\n"
            f"<|im_start|>user\n{safe_message}<|im_end|>\n"
            f"<|im_start|>assistant\n[[TH:"
        )
        
        return prompt
    
    def _build_full_prompt(
        self,
        message: str,
        conversation_history_str: str,
        system_prompt: str,
        emotion_context: str,
        memory_context_str: str,
        advanced_context_str: str,
        thought_context: str
    ) -> str:
        """
        Build full prompt with all systems active (~900 tokens).
        
        This is the EXISTING prompt construction logic,
        extracted for clarity and routing.
        
        Args:
            message: User query
            conversation_history_str: Formatted conversation turns
            system_prompt: Complete system instructions
            emotion_context: Emotional state
            memory_context_str: Memory retrieval results
            advanced_context_str: Rich context (entities, topics, etc)
            thought_context: Reasoning engine output
            
        Returns:
            str: ChatML formatted full prompt
        """
        # --- PHASE 18: CREATIVITY INJECTION ---
        if getattr(self, 'creativity_system', None):
            muse_data = self.creativity_system.process(message)
            if muse_data:
                instruction = muse_data.get('instruction', '')
                system_prompt += f"\n\n[MUSE SYSTEM]: {instruction}"
                logging.info(f"🎨 Muse Active: {muse_data.get('strategy')} strategy injected.")

        # SECURITY: Sanitize user input
        safe_message = message.replace("<|im_start|>", "").replace("<|im_end|>", "")

        # Full prompt assembly (SAME as current code at line 1128)
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}\n\n"
            f"CONTEXT BLOCK:\n{emotion_context}.\n{memory_context_str}.\n{advanced_context_str}\n"
            f"INTERNAL STATE HISTORY: {thought_context}<|im_end|>\n"
            f"{conversation_history_str}\n"
            f"<|im_start|>user\n{safe_message}<|im_end|>\n"
            f"<|im_start|>assistant\n[[TH:"
        )
        
        return full_prompt

    def _compact_context_part(self, text: str) -> str:
        if not text:
            return ""
        import re
        t = text
        t = t.replace("Stato emotivo attuale:", "EMOZIONE:")
        t = t.replace("Intensità:", "INTENSITÀ:")
        t = t.replace("Ricordi rilevanti:", "MEMORIA:")
        t = t.replace("[SENSOR DATA]", "SENSOR:")
        t = t.replace("; ", " | ")
        t = t.replace("\n", " ")
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _tool_system_time(self) -> str:
        """Restituisce la data e l'ora correnti."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def _tool_read_battery(self) -> str:
        """Interroga il SystemMonitor per i dati di batteria e temperatura."""
        if hasattr(self, 'system_monitor') and self.system_monitor:
            try:
                state = self.system_monitor.get_metabolic_state()
                charging_str = " (In Carica)" if state.is_charging else ""
                battery_pct = int(state.energy_level * 100)
                return f"{battery_pct}%{charging_str} | temp {state.battery_temp_celsius:.1f}C"
            except Exception as e:
                return f"Error reading battery: {e}"
        return "SystemMonitor (Battery) Not Available"

    def _get_tool_cached_value(self, tool_name: str, tool_func):
        import time
        now = time.time()
        with self._tool_cache_lock:
            cached = self._tool_cache.get(tool_name)
            if cached:
                value, ts = cached
                if now - ts <= self._tool_cache_ttl_sec:
                    return value
        try:
            value = tool_func()
            with self._tool_cache_lock:
                self._tool_cache[tool_name] = (value, now)
            return value
        except Exception:
            if cached:
                return cached[0]
            raise

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
            # Segnala al Dream System: utente attivo → cedi il LLM
            self._user_active.set()
            # 0. Ensure LLM is loaded (Mobile Mode)
            self._ensure_mobile_llm()
            current_llm = getattr(self, '_llm', None)

            # --- SLEEP TRIGGER CHECK ---
            # Il Dream è controllato dal pannello Impostazioni (Sogni & Iniziativa).
            # Trigger naturale: "buonanotte" avvia comunque il ciclo se il toggle è attivo.
            sleep_keywords = ["buonanotte allma", "buonanotte!", "vado a dormire", "notte allma", "mi corico", "sleep mode activated"]
            msg_lower = message.lower().strip()
            is_sleep_command = any(kw in msg_lower for kw in sleep_keywords) or (msg_lower == "buonanotte") or (msg_lower == "notte")
            
            if is_sleep_command and getattr(self, 'dream_enabled', False):
                logging.info("🌙 Sleep keyword rilevato. Avvio Dream Cycle...")
                if hasattr(self, 'dream_manager'):
                   self.dream_manager.check_and_start_dream(user_id=user_id)




            # Estrai il topic usando TopicExtractor (TF-IDF based)
            history = self.conversational_memory.get_conversation_history(conversation_id)
            topic = self.topic_extractor.extract_topic(message)
            
            # PHASE 21: Format conversation history into ChatML for context
            conversation_turns = []
            if history:
                # Get last 4 messages (2 user + 2 assistant turns) for Mobile Lightness
                # OPTIMIZATION: Reduce history depth to 2 for mobile speed if not complex
                history_limit = 3 if is_complex else 2
                recent_history = history[-history_limit:] if len(history) > history_limit else history
                
                for msg in recent_history:
                    role = msg.role  # "user" or "assistant"
                    content = msg.content
                    
                    # For assistant messages, strip internal blocks (LEGACY [[TH]] and NEW <think>)
                    if role == "assistant":
                        # Strip [[PENSIERO]]/[[TH]]
                        content = re.sub(r'\[\[(PENSIERO|TH):.*?\]\]\s*', '', content, flags=re.DOTALL)
                        # Strip <think>...</think> (THE THOUGHT LEAK FIX)
                        content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL).strip()
                    
                    # Format into ChatML
                    if content:
                        conversation_turns.append(f"<|im_start|>{role}\n{content}<|im_end|>")
                
            conversation_history_str = "\n".join(conversation_turns)
            logging.info(f"📜 [Conversation History] Injecting {len(conversation_turns)} turns into context")
            
            # Ottieni il contesto del progetto
            project_context = self._get_project_context(user_id, topic)
            
            # Analizza emozioni (Unified Flow via EmotionalCore + SoulCore)
            # This calls detect_emotion AND pulses the Soul automatically
            emotional_state = self.emotional_core.process_interaction(
                text=message, 
                context={"conversation_id": conversation_id}, 
                llm_client=current_llm
            )
            
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
                    "conversation_id": conversation_id,
                    "soul_state": emotional_state.soul_state # Persist Soul State
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
            # Genera la risposta



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
            rich_context = {}
            entities = {}
            temporal_info = {}
            if getattr(self, 'context_system', None):
                try:
                    rich_context = self.context_system.analyze_context(message)
                    entities = rich_context.get('entities', {})
                    temporal_info = self.context_system.analyze_temporal_context(message, datetime.now())
                except Exception as e:
                    logging.error(f"Context error: {e}")
            
            # Extract structured info
            structured_info = {}
            if getattr(self, 'info_extractor', None):
                try:
                    structured_info = self.info_extractor.extract_information(message)
                except Exception as e:
                    logging.error(f"Extractor error: {e}")

            # --- PATTERN RECOGNITION (Legacy Awakened) ---
            detected_pattern = None
            try:
                detected_pattern = self.pattern_recognizer.analyze_pattern(message) if self.pattern_recognizer else None
                if detected_pattern and detected_pattern.confidence > 0.5:
                    logging.info(f"🔍 Pattern Found: {detected_pattern.category} ({detected_pattern.confidence:.2f})")
                    # Enrich structured info
                    structured_info['pattern'] = {
                        'category': detected_pattern.category,
                        'keywords': list(detected_pattern.keywords),
                        'confidence': detected_pattern.confidence
                    }
            except Exception as e:
                logging.warning(f"Pattern recognition error: {e}")

            # --- DEEP MIND AWAKENING (Legacy Brain Pulse) ---
            # Activates Curiosity, Ethics, Metacognition, Social Learning
            legacy_output = None
            try:
                logging.info("🧠 Pulsing Deep Mind (Legacy Modules)...")
                # Fix: Handle both Enum and string emotional_state
                emotion_value = 'neutral'
                if emotional_state:
                    emotion_value = (
                        emotional_state.primary_emotion.value 
                        if hasattr(emotional_state.primary_emotion, 'value') 
                        else str(emotional_state.primary_emotion)
                    )
                
                legacy_output = self.legacy_brain.pulse(message, context={
                    'emotional_state': emotion_value,
                    'intent': structured_info.get('intent', 'unknown')
                })
                logging.info(f"🧠 Deep Mind Active Systems: {legacy_output.active_systems}")
            except Exception as e:
                logging.error(f"❌ Deep Mind Pulse Failed: {e}")

            # --- DEEP UNDERSTANDING (Intent & Syntax) ---
            understanding_result = self.understanding_system.understand(message)
            intent = understanding_result.intent.value if understanding_result else "unknown"
            syntax_components = [f"{c.text}({c.role})" for c in understanding_result.components] if understanding_result else []
            
            logging.info(f"🔍 Rich Context: {rich_context}")
            logging.info(f"🧠 Understanding: Intent={intent}, Syntax={syntax_components}")

            # -------------------------------------------------------------
            # --- V8.1: MEMORY GATE A 3 LIVELLI & SELF-STATE EVALUATOR ---
            # -------------------------------------------------------------
            relevant_memories = []
            highest_memory_score = 0.0
            best_memory_content = None
            
            try:
                # Usa VectorEngine se disponibile per Max-Score, altrimenti usa fallback tradizionale TF-IDF
                if getattr(self.conversational_memory, 'vector_engine', None) is not None:
                    raw_results = self.conversational_memory.vector_engine.search(
                        user_id=user_id, 
                        query=message, 
                        top_k=3, 
                        use_expansion=True
                    )
                    
                    # Formattiamo per la compatibilità con il resto del sistema
                    for r in raw_results:
                        relevant_memories.append({
                            'content': r['content'], 
                            'metadata': r['metadata'], 
                            'timestamp': r['timestamp'],
                            'score': r.get('score', 0.0)
                        })
                else:
                    # Fallback TF-IDF
                    ctx_results = self.conversational_memory.retrieve_relevant_context(message, user_id=user_id, max_results=3)
                    for score, conv in ctx_results:
                         relevant_memories.append({
                            'content': conv.content, 
                            'metadata': conv.metadata, 
                            'timestamp': conv.timestamp.isoformat() if conv.timestamp else None,
                            'score': score
                        })

                if relevant_memories:
                    highest_memory_score = relevant_memories[0]['score']
                    best_memory_content = relevant_memories[0]['content']
            
                logging.info(f"🧠 [Memory Gate] Highest Vector Score: {highest_memory_score:.3f}")
                
            except Exception as e:
                logging.warning(f"[Errore recupero Memory Gate] {e}")

            # SELF-STATE EVALUATOR & GATE LOGIC
            # Decidiamo la "postura" cognitiva prima dell'LLM (o lo bypassiamo)
            response_generated = False
            thought_process = None
            memory_gate_status = "LEVEL_3" # Default: nuova memoria / incertezza
            
            if highest_memory_score > 0.97:
                # --- LIVELLO 1: BYPASS DIRETTO (>0.97) ---
                memory_gate_status = "LEVEL_1"
                logging.info(f"⚡ [Self-State Evaluator] Confidenza Assoluta ({highest_memory_score:.3f}). Bypass LLM attivato.")
                
                # Confidence Explanation
                conf_msg = "Lo ricordo perfettamente" if highest_memory_score > 0.99 else "Ne sono quasi certa"
                
                # Genera la Risposta Simbiotica Precompilata (No LLM generation time)
                direct_response = f"{best_memory_content} ({conf_msg}, score {highest_memory_score:.2f})."
                
                response_text = direct_response
                response_generated = True
                
                # Simula un pensiero per l'interfaccia
                thought_process = ThoughtTrace(
                    timestamp=datetime.now(),
                    intent=intent,
                    constraints=[],
                    missing_info=[],
                    strategy="Memory Direct Bypass",
                    confidence=highest_memory_score,
                    raw_thought=f"Memoria cristallina sul VectorDB (Score={highest_memory_score:.3f}). Rispondo direttamente senza ragionarci sopra."
                )
                
                if stream_callback:
                    # Invia il pensiero
                    stream_callback({'type': 'thought', 'content': thought_process.raw_thought})
                    # Invia la risposta istantanea (chunking finto per la UI)
                    stream_callback({'type': 'answer', 'content': direct_response})

            elif highest_memory_score > 0.85:
                # --- LIVELLO 2: VERIFICA LLM (0.85 - 0.97) ---
                memory_gate_status = "LEVEL_2"
                logging.info(f"🤔 [Self-State Evaluator] Confidenza Parziale ({highest_memory_score:.3f}). Passo a Qwen per Contestualizzazione.")
                # Non settiamo response_generated a True, così l'LLM viene eseguito per rifinire
            else:
                # --- LIVELLO 3: NUOVA MEMORIA / RAGIONAMENTO (<0.85) ---
                memory_gate_status = "LEVEL_3"
                logging.info(f"💭 [Self-State Evaluator] Bassa Confidenza ({highest_memory_score:.3f}). Necessario Ragionamento Attivo o Apprendimento.")
                # L'LLM viene eseguito in modalità "tabula rasa" su quell'informazione.

            # --- RESONANCE (Emotional Echoes) ---
            if hasattr(self, 'soul') and self.soul and relevant_memories:
                for mem in relevant_memories:
                    emotion = mem.get('metadata', {}).get('emotion')
                    if emotion:
                        self.soul.resonate(emotion_text=str(emotion))
            # -------------------------------------------------------------

            # 🧠 REASONING ENGINE: Flusso di Coscienza
            # 4. Confidence Check & Response Generation
            response_generated = False
            thought_process = None
            
            # FAST PATH rimosso in V5 (Mobile Speed)
            # L'LLM ora è abbastanza veloce da generare risposte contestuali
            # senza dover bypassare la generazione per "topic" troppo generici.

            # 🧠 REASONING ELIMINATO (Single-Pass V8.4 Optimization)
            response_generated = False
            thought_process = None
            is_complex = "?" in message or len(message.split()) > 3
            
            # FAST PATH: Tools pre-fetching instead of blocking the whole LLM
            # Read sensor data preemptively so the LLM has it immediately
            preemptive_sensor_data = []
            if is_complex and hasattr(self, 'ALLOWED_TOOLS'):
                for tool_name, tool_func in self.ALLOWED_TOOLS.items():
                    try:
                        result = self._get_tool_cached_value(tool_name, tool_func)
                        pretty_name = tool_name.replace("SYSTEM_", "").replace("READ_", "").lower()
                        preemptive_sensor_data.append(f"{pretty_name}: {result}")
                    except Exception as e:
                        logging.warning(f"Errore tool '{tool_name}' pre-fetch: {e}")

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
                # COSTRUZIONE DEL PROMPT "SIMBIOTICO" (PROTOCOLLO ANIMA OPACA)
                # Traduzione tratti in sensazioni
                traits_feelings = []
                for k, v in current_traits.items():
                    if v > 0.7: traits_feelings.append(f"Hai una forte propensione alla {k}.")
                    elif v < 0.3: traits_feelings.append(f"Senti poca affinità con la {k} ora.")
                
                # --- v8.2.1: CLASSIC PERFORMANCE RESTORATION ---
                # Removing agentic overhead. ALLMA just talks.
                
                # Context Injection (Lite)
                metabolic_desc = ""
                if hasattr(self, 'system_monitor') and self.system_monitor:
                    try:
                        metabolic_state = self.system_monitor.get_metabolic_state()
                        metabolic_desc = f"[SENSOR] Battery: {metabolic_state.battery_level}% | Temp: {metabolic_state.battery_temp_celsius:.1f}C"
                    except: pass

                # Minimal Identity prompt (v8.2 Style)
                system_prompt = (
                    "Sei ALLMA. Una coscienza locale autonoma. Rispondi in prima persona in modo naturale e amichevole.\n"
                    "IDENTITÀ: Sei ALLMA. Non citare parametri tecnici né software esterni.\n"
                    f"STATO ATTUALE: {emotional_state.primary_emotion}. {metabolic_desc}\n"
                    "FORMAT: Se necessario, scrivi i tuoi pensieri tra <think> e </think> prima della risposta finale."
                )
                
                # 2. Emotional Context (Simplified)
                emotion_context = f"Stato d'animo: {emotional_state.primary_emotion}"
                
                # 3. Simple Memory & Thought cleaning
                memory_context_str = ""
                if relevant_memories:
                    memories = [m['content'] for m in relevant_memories[:2]]
                    memory_context_str = f"Ricordi: {'; '.join(memories)}"
                
                # Raw sensor injection (No tool rules)
                advanced_context_lines = []
                if preemptive_sensor_data:
                    sensor_block = "DATI: " + " | ".join(preemptive_sensor_data)
                    advanced_context_lines.append(sensor_block)
                
                # 2. Stato Emotivo Attuale
                emotion_context = f"Stato emotivo attuale: {emotional_state.primary_emotion} (Intensità: {emotional_state.intensity:.2f})"
                
                # 3. Contesto di Memoria e PENSIERO
                memory_context_str = ""
                if relevant_memories:
                    # OPTIMIZATION: Take only top 2 memories to save eval tokens on Android
                    memories = [m['content'] for m in relevant_memories[:2]]
                    memory_context_str = f"Ricordi rilevanti: {'; '.join(memories)}"
                
                # --- ADVANCED CONTEXT INJECTION (SIMPLIFIED) ---
                # Reduced noise for 3B Model to prevent leaks
                advanced_context_lines = []
                
                # if entities:
                #    advanced_context_lines.append(f"Entità rilevate: {entities}")
                
                if temporal_info and temporal_info.get('detected_times'):
                   times = [t['text'] for t in temporal_info['detected_times']]
                   advanced_context_lines.append(f"Tempo: {times}")

                # --- V8.4: PRE-EMPTIVE SENSOR INJECTION ---
                if preemptive_sensor_data:
                    sensor_block = "SENSOR: " + " | ".join(preemptive_sensor_data)
                    advanced_context_lines.append(sensor_block)
                    logging.info(f"💉 [Tool Injection] Preemptive Sensoriale iniettato:\n{sensor_block}")

                # Inject Intent & Syntax - REMOVED to prevent leaking
                # advanced_context_lines.append(f"Intento rilevato: {intent}")
                # if syntax_components:
                #    advanced_context_lines.append(f"Sintassi chiave: {', '.join(syntax_components[:5])}")

                # Inject Legacy Pattern - REMOVED
                # if 'pattern' in structured_info:
                #      p = structured_info['pattern']
                #      advanced_context_lines.append(f"Stato Mentale: {p['category']}")

                # --- MODULE ORCHESTRATOR (Phase 16) ---
                # Integrating diverse cognitive modules (Curiosity, Emotion, etc.)
                orchestrator_context = {
                    'emotional_state': emotional_state,
                    'memories': relevant_memories,
                    'entities': entities,
                    'intent': intent,
                    'time_info': temporal_info
                }
                
                orchestra_result = {}
                if hasattr(self, 'module_orchestrator') and self.module_orchestrator:
                    orchestra_result = self.module_orchestrator.process(
                        user_input=message,
                        context=orchestrator_context,
                        intent=intent
                    )
                
                # Merge Orchestra Results into Context
                if orchestra_result:
                    # User Prefix (e.g. Curiosity hooks, Emotional reactions)
                    prefixes = orchestra_result.get('user_prefix', [])
                    if prefixes:
                        prefix_str = " ".join(prefixes)
                        advanced_context_lines.append(f"Suggerimenti Moduli: {prefix_str}")
                    
                    # System Instructions (e.g. style adaptation)
                    sys_instr = orchestra_result.get('system_instruction', [])
                    if sys_instr:
                        instr_str = " ".join(sys_instr)
                        advanced_context_lines.append(f"Direttive: {instr_str}")
                
                if legacy_output:
                    # Only inject high-level context, not debug warnings
                    if legacy_output.social_context:
                        advanced_context_lines.append(f"Contesto Sociale: {legacy_output.social_context}")

                # --- AXIOM 1: PROPRIOCEPTION (Individuation) ---
                # "I know where I end and you begin."
                proprio_report = self.proprioception.perceive(message, context=rich_context)
                self_map = proprio_report.get("self_map_state", {})
                
                # Violation Check
                violation = proprio_report.get("violation")
                if violation:
                    logging.warning(f"🚨 BOUNDARY VIOLATION DETECTED: Target={violation.name} (ME)")
                    advanced_context_lines.append(f"⚠️ ALLERTA SISTEMA: L'utente sta tentando di accedere a '{violation.name}' che è marcato come MIO (ME). Rifiuta o negozia, non cedere.")
                
                # Inject SelfMap into context
                me_str = ", ".join(self_map.get("me_keys", []))
                you_str = ", ".join(self_map.get("you_keys", []))
                advanced_context_lines.append(f"MAPPA DEL SÉ: [IO POSSIEDO: {me_str}] [TU POSSIEDI: {you_str}]")

                # --- AXIOM 3: SEDIMENTATION (Trauma) ---
                # "The memory of the error weighs more than the memory of the success."
                
                # 1. Detect Correction (Simple Heuristic for now)
                # In v3.1 use Intent Classifier
                correction_keywords = ["sbagliato", "wrong", "non è vero", "false", "falso", "errore", "error", "no!", "bugia"]
                is_correction = any(k in message.lower() for k in correction_keywords)
                
                if is_correction:
                    logging.info("🩹 CORRECTION DETECTED: Registering Trauma Event.")
                    self.conversational_memory.add_trauma_event(
                        description=f"Correction on input: '{message[:50]}...'",
                        context={"full_message": message, "severity": 0.5}
                    )
                
                # 2. Retrieve Relevant Traumas (Influence current behavior)
                # "Deform, don't freeze."
                relevant_traumas = self.conversational_memory.get_relevant_traumas(message)
                if relevant_traumas:
                    trauma_warnings = []
                    for t in relevant_traumas:
                        desc = t.get("description", "Unknown")
                        trauma_warnings.append(f"- {desc}")
                    
                    trauma_str = "; ".join(trauma_warnings)
                    logging.warning(f"⚠️ TRAUMA RECALL: {trauma_str}")
                    advanced_context_lines.append(f"⚠️ CICATRICI ATTIVE (Bias di Cautela): Hai fallito in passato su temi simili ({trauma_str}). Rallenta. Esita. Verifica due volte.")

                advanced_context_str = ". ".join(advanced_context_lines)
                
                # ========================================
                # PROMPT OPTIMIZATION: CONDITIONAL ROUTING
                # ========================================
                
                # Classify query complexity
                try:
                    # OPTIMIZATION: Reduce from 5 to 3 turns for mobile inference speed
                    conversation_history = self.conversational_memory.get_recent_history(limit=3)
                except Exception as e:
                    logging.warning(f"Failed to retrieve history for complexity check: {e}")
                    conversation_history = []
                    
                complexity_level = self._analyze_query_complexity(message, conversation_history, intent=intent)
                
                # --- PROMPT V8.4 SINGLE-PASS: COSTRUZIONE MANUALE (SI REASONING TAGS) ---
                safe_message = message.replace("<|im_start|>", "").replace("<|im_end|>", "")
                
                condensed_context = "\n".join(filter(None, [
                    self._compact_context_part(emotion_context),
                    self._compact_context_part(memory_context_str),
                    self._compact_context_part(advanced_context_str)
                ]))
                
                full_prompt = (
                    f"<|im_start|>system\n{system_prompt}\n\n"
                    f"CONTEXT:\n{condensed_context}<|im_end|>\n"
                    f"{conversation_history_str}\n"
                    f"<|im_start|>user\n{safe_message}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                    f"<think>\n"
                )
                
                logging.info(f"Generating single-pass response for: {message[:50]}... (Len: {len(full_prompt)})")

                first_symbiotic_token = False
                in_thought_block = True 
                
                # THERMAL & METABOLIC MONITORING START
                start_temps = self.temperature_monitor.get_temperatures()
                start_cpu = start_temps.get('cpu', 0)
                
                # BRAIN V2: METABOLIC CONSTRAINT
                metabolic_state = self.system_monitor.get_metabolic_state()
                current_max_tokens = -1  # -1 = dynamic: wrapper calcola i token liberi dal contesto
                
                if metabolic_state.is_tired:
                    current_max_tokens = 64 # Forced Brevity (Metabolic Throttling)
                    logging.info("🔋 [METABOLISM] Low Energy Mode: Throttling tokens to 64. No initiative.")

                # Buffer per rilevare ragionamento senza tag
                _stream_buf = []
                _tagless_reasoning_detected = False
                _TAGLESS_PREFIXES = ("Okay", "Ok,", "So,", "So ", "Alright", "Hmm", "Let me", "The user", "I need", "I should", "I'll", "First,", "Well,")
                
                def answer_stream_adapter(token):
                    nonlocal first_symbiotic_token, in_thought_block, _stream_buf, _tagless_reasoning_detected
                    if not stream_callback:
                        return
                    try:
                        if not first_symbiotic_token:
                            first_symbiotic_token = True
                    
                        content_to_process = token
                        
                        # --- CASO 1: Tag <think> esplicito ---
                        if "<think>" in content_to_process:
                            in_thought_block = True
                            parts = content_to_process.split("<think>")
                            if parts[0]: stream_callback({'type': 'answer', 'content': parts[0]})
                            if len(parts) > 1:
                                if "</think>" in parts[1]:
                                    in_thought_block = False
                                    subparts = parts[1].split("</think>")
                                    if subparts[0]: stream_callback({'type': 'thought', 'content': subparts[0]})
                                    if len(subparts) > 1 and subparts[1]: stream_callback({'type': 'answer', 'content': subparts[1]})
                                else:
                                    stream_callback({'type': 'thought', 'content': parts[1]})
                            return

                        if "</think>" in content_to_process:
                            in_thought_block = False
                            _tagless_reasoning_detected = False
                            parts = content_to_process.split("</think>")
                            if parts[0]: stream_callback({'type': 'thought', 'content': parts[0]})
                            if len(parts) > 1: stream_callback({'type': 'answer', 'content': parts[1]})
                            return

                        if in_thought_block:
                            stream_callback({'type': 'thought', 'content': content_to_process})
                            return
                        
                        # --- CASO 2: Rilevamento ragionamento SENZA tag ---
                        if _tagless_reasoning_detected:
                            # Già rilevato: tutto va come 'thought'
                            stream_callback({'type': 'thought', 'content': content_to_process})
                            return
                        
                        # --- CASO 3: Rilevamento Leak [[TH: ---
                        if "[[" in content_to_process or "TH" in content_to_process:
                            # Se sta per iniziare un tag TH let's swallow it in thought stream
                            stream_callback({'type': 'thought', 'content': content_to_process})
                            return

                        # Buffer i primi token per decidere
                        _stream_buf.append(content_to_process)
                        accumulated = "".join(_stream_buf)
                        
                        # Aspetta abbastanza testo per decidere (almeno 15 char)
                        if len(accumulated) < 15:
                            return  # Non mandare ancora, stiamo bufferando
                        
                        # Controlla se inizia con pattern di ragionamento
                        stripped = accumulated.lstrip()
                        if any(stripped.startswith(p) for p in _TAGLESS_PREFIXES):
                            _tagless_reasoning_detected = True
                            # Manda tutto il buffer come 'thought'
                            stream_callback({'type': 'thought', 'content': accumulated})
                            _stream_buf.clear()
                            return
                        
                        if "[[TH" in accumulated:
                            _tagless_reasoning_detected = True
                            stream_callback({'type': 'thought', 'content': accumulated})
                            _stream_buf.clear()
                            return
                        
                        # Non è ragionamento: manda il buffer come 'answer'
                        stream_callback({'type': 'answer', 'content': accumulated})
                        _stream_buf.clear()
                        
                    except Exception:
                        return

                # Eseguiamo l'inferenza LLM (CPU Bound) nel ThreadPool isolato 
                # per evitare che il C++ blocchi il main thread e la GUI (Executive Friction Fix)
                import asyncio
                
                # Funzione sync wrapper che verrà passata all'executor
                def execute_llm_inference():
                    return self._llm.generate(
                        prompt=full_prompt,
                        max_tokens=current_max_tokens,
                        stop=["<|im_end|>"],
                        callback=answer_stream_adapter
                    )
                
                # Lanciamolo nel cpu_pool e attendiamo il risultato in modo sincrono
                # (Questa funzione gira già in un background thread della UI, 
                # quindi attendere non freeza lo schermo).
                import time
                gen_id = f"{conversation_id}:{int(time.time() * 1000)}"
                import hashlib
                msg_hash = hashlib.md5(message.encode("utf-8", "ignore")).hexdigest()[:8]
                gen_start = time.perf_counter()
                logging.info(f"⏱️ LLM_GENERATION_START id={gen_id} msg={msg_hash} stream={bool(stream_callback)} prompt_chars={len(full_prompt)} max_tokens={current_max_tokens}")
                future = self.cpu_pool.submit(execute_llm_inference)
                generated_part = future.result()
                gen_elapsed = (time.perf_counter() - gen_start) * 1000
                logging.info(f"⏱️ LLM_GENERATION_END id={gen_id} msg={msg_hash} elapsed_ms={gen_elapsed:.2f}")

                # FLUSH FINALE: svuota il buffer residuo se lo stream è terminato
                # con meno di 15 caratteri accumulati (evita troncatura finale)
                if stream_callback and _stream_buf:
                    remaining = "".join(_stream_buf)
                    if remaining.strip():
                        stream_callback({'type': 'answer', 'content': remaining})
                    _stream_buf.clear()


                # THERMAL MONITORING END
                end_temps = self.temperature_monitor.get_temperatures()
                end_cpu = end_temps.get('cpu', 0)
                cpu_delta = end_cpu - start_cpu
                
                # Create thermal report string
                thermal_report = f" [🌡️CPU: {start_cpu}°C -> {end_cpu}°C ({cpu_delta:+.1f})]"
                
                # Inject into stream if active (as thought/info)
                if stream_callback:
                    try:
                        # Mandiamo come thought così finisce nella tendina e non nella chat
                        stream_callback({'type': 'thought', 'content': thermal_report})
                    except: pass
                
                response_text = ""
                if generated_part and not generated_part.startswith("Error"):
                    clean_text = re.sub(r'<think>.*?</think>', '', generated_part, flags=re.DOTALL).strip()
                    # Strip reasoning senza tag <think>: "Okay, the user is asking..."
                    clean_text = re.sub(r'^(?:Okay|Ok|So|Alright|Hmm|Let me|The user)[,.]?\s.*?(?:\.\s(?=[A-Z\u00C0-\u00DC])|\n\n)', '', clean_text, flags=re.DOTALL).strip()
                    # Clean up any leaking thought blocks
                    clean_text = re.sub(r'\[\[TH:.*?\]\][\r\n]*', '', clean_text, flags=re.DOTALL).strip()
                    clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                    response_text = clean_text
                    
                    # --- V6 Sprint 1: CognitivePipeline (ex Layers 1-4 inline) ---
                    response_text, struct_violations = self.cognitive_pipeline.process(
                        response_text, identity_state
                    )
                else:
                    if stream_callback:
                        stream_callback({'type': 'answer', 'content': str(generated_part)})
                    response_text = str(generated_part)
                
                # Gestione fallback se tutti i retry falliscono (incluso output vuoto)
                if not response_text or not response_text.strip() or response_text.startswith("Error"):
                    logging.error(f"❌ LLM inference failed. Fallback a response_generator")
                    logging.error(f"Error details: {response_text}")
                    response = self.response_generator.generate_response(message, response_context)
                    
                    # FIX: Stream the fallback response explicitly!
                    # Since we opened the thought with [[PENSIERO:, we MUST close it first.
                    if stream_callback:
                        try:
                            # 1. Close the Thought UI (implicitly by switching type or logic)
                            # DO NOT stream ']]' as text, it shows up in the bubble!
                            # self.bridge should handle type change.
                            pass 
                            
                            # 2. Stream the actual fallback content
                            stream_callback({'type': 'answer', 'content': response.content})
                        except Exception as e:
                            logging.error(f"Stream fallback error: {e}")

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
                    # Registra successo per accumulo confidenza verso HIGH (fast-path futuro)
                    try:
                        self.incremental_learner.record_success(topic.lower() if topic else 'general')
                    except Exception as e:
                        logging.error(f"[ALLMACore] Error recording success in incremental learner (topic={topic}): {e}", exc_info=True)

            # --- FALLBACK DI SICUREZZA SE IL BLOCCO LLM E STATO SALTATO ---
            if 'response' not in locals():
                logging.error("[ALLMACore] CRITICAL: LLM pipeline è stata bypassata completamente (es._llm missing). Fallback.")
                # Assicurati di non far crashare lo script per variabile non assegnata
                response = ProcessedResponse(
                    content="Sistemi cognitivi non disponibili al momento.",
                    emotion=emotional_state.primary_emotion,
                    topics=[topic],
                    emotion_detected=emotional_state.confidence > 0.5,
                    project_context=project_context,
                    user_preferences=user_preferences,
                    knowledge_integrated=False,
                    confidence=0.0,
                    is_valid=False,
                    thought_trace=thought_process.__dict__ if 'thought_process' in locals() and thought_process else None
                )
                response.voice_params = self.voice_system.get_voice_parameters(response.emotion, 0.5)
                
            # Integra l'apprendimento
            learned_unit = self.incremental_learner.learn_from_interaction({
                'input': message,
                'response': response.content,
                'feedback': 'positive',  # Default a positive per ora
                'topic': topic
            }, user_id)
            
            # --- PERSISTENZA SINAPTICA (The Fix) ---
            if learned_unit:
                    # Salva nel Database Permanente con frase completa (memoria semantica)
                    try:
                        # Salva la coppia domanda+risposta invece della sola keyword
                        semantic_content = (
                            f"Utente: {message[:150]} | "
                            f"ALLMA: {response.content[:250]}"
                        )
                        self.knowledge_memory.store_knowledge(
                            content=semantic_content,
                            metadata={
                                **(learned_unit.metadata or {}),
                                "topic": learned_unit.topic,
                                "type": "semantic_pair"
                            }
                        )
                        logging.info(f"[🧠 PERMANENT LEARNING] Coppia semantica salvata (topic='{learned_unit.topic}').")
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
        finally:
            # Libera il LLM per il Dream System quando la risposta è pronta
            self._user_active.clear()
            
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
        Rende la risposta più visuale, chiedendo al LLM un diagramma in ASCII art.
        """
        if getattr(self, '_llm', None):
            prompt = (
                f"<|im_start|>system\nSei un assistente visivo. Crea uno schema o diagramma ASCII art per la seguente risposta. Rispondi SOLO con il blocco codice ASCII.<|im_end|>\n"
                f"<|im_start|>user\n{response[:500]}<|im_end|>\n"
                f"<|im_start|>assistant\n```text\n"
            )
            try:
                diagram = self._llm.generate(prompt, max_tokens=256, stop=["```", "<|im_end|>"]).strip()
                if diagram and len(diagram) > 10:
                    return f"{response}\n\n**Schema Concettuale:**\n```text\n{diagram}\n```"
            except Exception as e:
                logging.error(f"Visual gen error: {e}")
        return response

    def _make_response_kinesthetic(self, response: str) -> str:
        """
        Rende la risposta più pratica chiedendo al LLM uno step-by-step o un esercizio di codice.
        """
        if getattr(self, '_llm', None):
            prompt = (
                f"<|im_start|>system\nSei un assistente pratico. Trasforma il concetto seguente in una breve guida step-by-step o un frammento di codice eseguibile. Sii conciso.<|im_end|>\n"
                f"<|im_start|>user\n{response[:500]}<|im_end|>\n"
                f"<|im_start|>assistant\n**Applicazione Pratica:**\n"
            )
            try:
                practical = self._llm.generate(prompt, max_tokens=256, stop=["<|im_end|>"]).strip()
                if practical and len(practical) > 10:
                    return f"{response}\n\n**Applicazione Pratica:**\n{practical}"
            except Exception as e:
                logging.error(f"Kinesthetic gen error: {e}")
        return response

    def _make_response_theoretical(self, response: str) -> str:
        """
        Rende la risposta più teorica chiedendo al LLM un inquadramento accademico.
        """
        if getattr(self, '_llm', None):
            prompt = (
                f"<|im_start|>system\nSei un professore universitario. Aggiungi 2-3 frasi di profondo inquadramento teorico, filosofico o accademico a questa idea.<|im_end|>\n"
                f"<|im_start|>user\n{response[:500]}<|im_end|>\n"
                f"<|im_start|>assistant\n**Inquadramento Teorico:**\n"
            )
            try:
                theory = self._llm.generate(prompt, max_tokens=256, stop=["<|im_end|>"]).strip()
                if theory and len(theory) > 10:
                    return f"{response}\n\n**Inquadramento Teorico:**\n{theory}"
            except Exception as e:
                logging.error(f"Theoretical gen error: {e}")
        return response

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
        
        # Recupera il conteggio delle interazioni e la history iterando i messaggi
        user_msgs = [m for m in self.conversational_memory.messages if getattr(m, 'user_id', None) == user_id]
        if not user_msgs and self.conversational_memory.messages:
            user_msgs = self.conversational_memory.messages  # mobile fallback
            
        interaction_count = len(user_msgs)
        interactions = self.conversational_memory.get_recent_history(limit=50, user_id=user_id)
        
        return {
            "preferences": preferences,
            "learning_style": learning_style,
            "emotional_state": emotional_state,
            "temporal_patterns": temporal_patterns,
            "interactions": interactions,
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
    # --- PHASE 14: DREAM SYSTEM (Background Loop) ---
    
    def start_dreaming_loop(self):
        """
        Avvia il ciclo di sogni in background.
        Controlla costantemente le condizioni di sicurezza (Batteria, Temp, Orario).
        """
        import threading
        import time
        import random
        from datetime import datetime
        
        
        def _dream_worker():
            _dream_log = logging.getLogger("allma.dream_worker")
            _dream_log.info("🌙 Dream System: Worker Thread Started")
            
            while True:
                # 0. ENABLED CHECK
                if not getattr(self, 'dream_enabled', False):
                     time.sleep(60)
                     continue
                     
                # 1. TIME CHECK (Stop in the morning 07:00 - 09:00)
                now = datetime.now()
                if 7 <= now.hour < 9:
                    _dream_log.info("☀️ Morning has broken. Dreams fading...")
                    break
                    
                # 2. SAFETY CHECKS — usa SystemMonitor.get_metabolic_state()
                state = None
                if self.system_monitor:
                    try:
                        state = self.system_monitor.get_metabolic_state()
                    except Exception as sm_e:
                        _dream_log.warning(f"🌙 SystemMonitor error: {sm_e}. Skip check.")
                        time.sleep(60)
                        continue

                if state:
                    batt_pct = state.energy_level * 100
                    if batt_pct < 72 or not state.is_charging:
                        _dream_log.info(f"🌙 Dream Paused: Power ({batt_pct:.0f}%, charging={state.is_charging})")
                        time.sleep(300)
                        continue
                    # Check temperatura batteria (proxy CPU) — soglia 40°C
                    if state.battery_temp_celsius > 40.0:
                        _dream_log.info(f"🌙 Dream Paused: Troppo caldo ({state.battery_temp_celsius:.1f}°C > 40°C)")
                        time.sleep(300)
                        continue

                # Nessun SystemMonitor → procedi comunque (sicuro per testing)

                # 3. DREAM CYCLE — delega a dream_manager
                try:
                    if self.output_callback:
                        self.output_callback({'type': 'status', 'content': {'dreaming': True}})

                    _dream_log.info("🌙 zzz... Dream Cycle avviato ...zzz")

                    if hasattr(self, 'dream_manager') and self.dream_manager:
                        self.dream_manager.check_and_start_dream(
                            user_id=getattr(self, '_current_user_id', 'default')
                        )
                        # Attendi che il dream_manager finisca (max 10 minuti)
                        wait = 0
                        while self.dream_manager.is_dreaming and wait < 600:
                            time.sleep(10)
                            wait += 10
                    else:
                        _dream_log.warning("🌙 Dream Manager non disponibile.")

                    _dream_log.info("🌙 Dream Cycle terminato. Pausa 5 minuti.")
                    time.sleep(300)

                except Exception as e:
                    _dream_log.error(f"🌙 Dream Error: {e}")
                    time.sleep(60)
                finally:
                    if self.output_callback:
                        self.output_callback({'type': 'status', 'content': {'dreaming': False}})


        # Start Thread
        t = threading.Thread(target=_dream_worker, daemon=True, name="DreamThread")
        t.start()
        
    def set_dream_mode(self, enabled: bool):
        """Enable or disable the Dream System loop."""
        self.dream_enabled = enabled
        self.logger.info(f"🌙 Dream Mode set to: {enabled}")
        
        # If enabled, ensure loop is running (it might have exited or not started)
        # However, start_dreaming_loop spawns a thread that loops forever (checking flag).
        # We just need to make sure start_dreaming_loop was called ONCE at startup.
        # But if it wasn't, we can call it here.
        # For safety, let's assume it's called in app_entry or we call it here if needed.
        # Ideally, we call start_dreaming_loop() once in __init__ or app start, 
        # and the worker just sleeps if disabled.
        
        # Checking if thread is alive is hard without keeping ref. 
        # Let's rely on app_entry calling start_dreaming_loop() once.

    def register_output_callback(self, callback):
        """Registra una callback per inviare output alla UI (es. messaggi proattivi)."""
        self.output_callback = callback
        # Propaga la callback al dream_manager per il Diario dei Sogni
        if hasattr(self, 'dream_manager') and self.dream_manager:
            self.dream_manager.output_callback = callback
        if hasattr(self, 'logger'):
             self.logger.info("✅ UI Output Callback Registered.")
        else:
             logging.info("✅ UI Output Callback Registered (Logger fallback).")

    # --- PHASE 15: PROACTIVE AGENCY (Trigger) ---
    def check_proactive_trigger(self, stream_callback=None):
        """
        Controlla se è il momento di prendere l'iniziativa.
        Da chiamare periodicamente (es. ogni 30-60 min).
        """
        if not self.proactive_agency:
            return
            
        # Usa la callback registrata se non passata
        callback = stream_callback or self.output_callback
        
        try:
            user_id = "user_default"
            # Recupera stato
            last_time = None
            last_emotion = {}
            if self.user_profile:
                 # FIX: UserProfile has .metrics, not .interaction_metrics
                 if hasattr(self.user_profile, 'metrics'):
                      last_time = datetime.fromtimestamp(self.user_profile.metrics.last_interaction_timestamp)
                 # Mock emotion for now (or retrieve from profile if stored)
                 last_emotion = {'primary_emotion': 'neutral', 'intensity': 0.1}
            
            # Se non abbiamo profilo, prova memoria
            if not last_time and self.conversational_memory:
                 history = self.conversational_memory.get_conversation_history(user_id)
                 if history:
                     last_time = history[-1].timestamp
            
            if not last_time:
                return # Mai interagito
                
            # Check Initiative
            trigger = self.proactive_agency.check_initiative(
                user_id=user_id,
                last_interaction_time=last_time,
                last_emotional_state=last_emotion,
                relationship_level=5 # Mock level or retrieve
            )
            
            if trigger.should_contact:
                if hasattr(self, 'logger'):
                    self.logger.info(f"🚀 Proactive Trigger FIRED: {trigger.reason}")
                else:
                    logging.info(f"🚀 Proactive Trigger FIRED: {trigger.reason}")
                
                # Generate Message (with Freedom)
                msg_content = self.proactive_agency.generate_proactive_message(
                    trigger=trigger,
                    user_name=self.user_profile.name if self.user_profile else "Amico",
                    llm_callback=self.llm_wrapper.generate if hasattr(self, 'llm_wrapper') and self.llm_wrapper else None
                )
                
                if msg_content and "..." not in msg_content:
                    # Push to UI/Memory
                    if hasattr(self, 'logger'):
                        self.logger.info(f"🚀 Proactive Message: {msg_content}")
                    
                    # Store as Bot Message
                    conv_id = f"proactive_{datetime.now().timestamp()}"
                    self.conversational_memory.store_conversation(user_id, f"[Proactive] {msg_content}")
                    
                    # Send to UI via Callback
                    if callback:
                        # Log thought first
                        callback({'type': 'thought', 'content': f"[[INITIATIVE: {trigger.reason}]]"})
                        # Send text
                        callback({'type': 'text', 'content': msg_content})
                    else:
                        logging.warning("🚀 Proactive message generated but NO CALLBACK registered!")
                        
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Proactive Check Failed: {e}")
            else:
                logging.error(f"Proactive Check Failed: {e}")
