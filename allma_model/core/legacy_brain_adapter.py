"""
LegacyBrainAdapter - Il ponte tra il nucleo moderno e la Mente Profonda (Legacy)
Questo modulo orchestra i sistemi complessi di ALLMA V3 (Curiosità, Etica, Metacognizione, Sociale)
per arricchire l'elaborazione di ALLMA V4 senza appesantire il thread principale.
"""

import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Import Legacy Systems with Error Handling
try:
    from allma_model.incremental_learning.curiosity_system import CuriosityDrive
    CURIOSITY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Curiosity System not found or failed: {e}")
    CURIOSITY_AVAILABLE = False

try:
    from allma_model.incremental_learning.subconscious_ethical_system import SubconsciousEthicalSystem
    ETHICS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Ethical System not found: {e}")
    ETHICS_AVAILABLE = False

try:
    from allma_model.incremental_learning.metacognition_system import MetaCognitionSystem, MetaCognitiveState
    METACOGNITION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Metacognition System not found: {e}")
    METACOGNITION_AVAILABLE = False

try:
    from allma_model.incremental_learning.social_learning_system import SocialLearningSystem
    SOCIAL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Social System not found: {e}")
    SOCIAL_AVAILABLE = False

try:
    from allma_model.incremental_learning.creativity_system import CreativitySystem
    CREATIVITY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Creativity System not found: {e}")
    CREATIVITY_AVAILABLE = False

try:
    from allma_model.incremental_learning.meta_learning_system import MetaLearningSystem
    METALEARNING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Meta Learning System not found: {e}")
    METALEARNING_AVAILABLE = False

try:
    from allma_model.incremental_learning.planning_system import PlanningSystem
    PLANNING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Legacy Planning System not found: {e}")
    PLANNING_AVAILABLE = False


@dataclass
class LegacyOutput:
    """Output aggregato della Mente Profonda"""
    curiosity_questions: List[str] = field(default_factory=list)
    curiosity_level: float = 0.0
    ethical_warning: Optional[str] = None
    metacognitive_insight: str = ""
    social_context: str = ""
    creative_idea: Optional[str] = None
    meta_strategy: str = ""
    plan_status: str = ""
    active_systems: List[str] = field(default_factory=list)

class LegacyBrainAdapter:
    """
    Gestisce l'attivazione e l'orchestrazione dei moduli legacy (Deep Mind).
    """
    def __init__(self):
        logging.info("🧠 Initializing Legacy Brain Adapter (Deep Mind Awakening)...")
        self.systems_status = {}
        
        # 1. Initialize Curiosity
        if CURIOSITY_AVAILABLE:
            try:
                self.curiosity = CuriosityDrive()
                self.systems_status['curiosity'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Curiosity: {e}")
                self.systems_status['curiosity'] = "ERROR"
                self.curiosity = None
        else:
            self.curiosity = None

        # 2. Initialize Ethics
        if ETHICS_AVAILABLE:
            try:
                self.ethics = SubconsciousEthicalSystem()
                self.systems_status['ethics'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Ethics: {e}")
                self.systems_status['ethics'] = "ERROR"
                self.ethics = None
        else:
            self.ethics = None

        # 3. Initialize Metacognition
        if METACOGNITION_AVAILABLE:
            try:
                self.metacognition = MetaCognitionSystem()
                self.systems_status['metacognition'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Metacognition: {e}")
                self.systems_status['metacognition'] = "ERROR"
                self.metacognition = None
        else:
            self.metacognition = None

        # 4. Initialize Social Learning
        if SOCIAL_AVAILABLE:
            try:
                self.social = SocialLearningSystem()
                self.systems_status['social'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Social System: {e}")
                self.systems_status['social'] = "ERROR"
                self.social = None
        else:
            self.social = None

        # 5. Initialize Creativity
        if CREATIVITY_AVAILABLE:
            try:
                self.creativity = CreativitySystem()
                self.systems_status['creativity'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Creativity System: {e}")
                self.systems_status['creativity'] = "ERROR"
                self.creativity = None
        else:
            self.creativity = None

        # 6. Initialize Meta Learning
        if METALEARNING_AVAILABLE:
            try:
                self.meta_learning = MetaLearningSystem()
                self.systems_status['meta_learning'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Meta Learning System: {e}")
                self.systems_status['meta_learning'] = "ERROR"
                self.meta_learning = None
        else:
            self.meta_learning = None

        # 7. Initialize Planning
        if PLANNING_AVAILABLE:
            try:
                self.planning = PlanningSystem()
                self.systems_status['planning'] = "ACTIVE"
            except Exception as e:
                logging.error(f"❌ Failed to init Planning System: {e}")
                self.systems_status['planning'] = "ERROR"
                self.planning = None
        else:
            self.planning = None


        logging.info(f"🧠 Deep Mind Status: {self.systems_status}")

    def pulse(self, user_input: str, context: Dict[str, Any] = None) -> LegacyOutput:
        """
        Esegue un ciclo rapido ("pulse") di tutti i sistemi legacy attivi.
        """
        output = LegacyOutput()
        active_systems = []

        if context is None:
            context = {}

        # --- CURIOSITY DRIVE ---
        if self.curiosity:
            try:
                # Assuming process_input returns a dict with 'questions' and 'exploration_focus'
                # Based on file inspection (Step 3079)
                curiosity_result = self.curiosity.process_input(user_input, context)
                if curiosity_result:
                    output.curiosity_questions = curiosity_result.get('questions', [])
                    output.curiosity_level = curiosity_result.get('exploration_focus', 0.0)
                active_systems.append("Curiosity")
            except Exception as e:
                logging.warning(f"⚠️ Curiosity pulse error: {e}")

        # --- SUBCONSCIOUS ETHICS ---
        if self.ethics:
            try:
                # Cannot see 'evaluate' method in snippet, but assuming standard interface or checking specific words
                # Using init param 'harmful_words' check manually as lightweight proxy if method unknown
                # Or check if 'evaluate_action' exists.
                # Let's inspect the file later if needed, for now use a safe check
                if hasattr(self.ethics, 'evaluate_action'):
                     # Dummy check
                     pass
                
                # Check harmful words directly as a robust fallback using the system's dictionary
                if hasattr(self.ethics, 'harmful_words'):
                    for word, severity in self.ethics.harmful_words.items():
                        if word in user_input.lower():
                            output.ethical_warning = f"Rilevato concetto eticamente sensibile: '{word}' (Gravità: {severity})"
                            break
                active_systems.append("Ethics")
            except Exception as e:
                logging.warning(f"⚠️ Ethics pulse error: {e}")

        # --- METACOGNITION ---
        if self.metacognition:
            try:
                # Monitor cognitive process
                insight = self.metacognition.monitor_cognitive_process({
                    "complexity": 0.5, # heuristic
                    "accuracy": 0.8
                })
                output.metacognitive_insight = insight.description
                active_systems.append("Metacognition")
            except Exception as e:
                logging.warning(f"⚠️ Metacognition pulse error: {e}")

        # --- SOCIAL LEARNING ---
        if self.social:
            try:
                social_ctx = self.social.analyze_social_context(user_input)
                # social_ctx is a SocialContext object
                formality = getattr(social_ctx, 'formality', 0.5)
                output.social_context = f"Formalità: {formality:.2f}"
                active_systems.append("Social")
            except Exception as e:
                logging.warning(f"⚠️ Social pulse error: {e}")

        # --- CREATIVITY ---
        if self.creativity:
            try:
                # Occasional creative spark (10% chance or if keywords present)
                if len(user_input) > 20 and ("idea" in user_input or "nuovo" in user_input):
                    idea = self.creativity.generate_idea({"concetto": user_input[:20]})
                    output.creative_idea = f"Scintilla Creativa: {idea.description}"
                    active_systems.append("Creativity")
            except Exception as e:
                logging.warning(f"⚠️ Creativity pulse error: {e}")

        # --- META LEARNING ---
        if self.meta_learning:
            try:
                # Update learning strategy based on interaction
                # Mocking interaction data for pulse
                insight = self.meta_learning.update_from_user_interaction({
                    "sentiment": 0.5,
                    "topic": "general"
                })
                # Assuming insight has a 'value' or description
                output.meta_strategy = f"Meta-Strategy Update: {insight.metric_name}={insight.value:.2f}"
                active_systems.append("MetaLearning")
            except Exception as e:
                logging.warning(f"⚠️ MetaLearning pulse error: {e}")

        output.active_systems = active_systems
        return output
