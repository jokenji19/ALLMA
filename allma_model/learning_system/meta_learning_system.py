
import logging
import time
from typing import Dict, Any, List, Optional
from collections import deque
from dataclasses import dataclass, asdict

from allma_model.core.module_state_manager import ModuleStateManager

class MetaLearningSystem:
    """
    Meta-Learning System (Phase 19)
    ===============================
    "Learning to Learn". Optimizes ALLMA's strategies based on user feedback.
    
    Tracks:
    1. Strategy Success (e.g., Elaboration vs Reflection)
    2. Communication Style Preference (e.g., Visual vs Textual)
    3. User Satisfaction (Implicit/Explicit feedback)
    
    Persists data to SQLite via ModuleStateManager.
    """
    
    def __init__(self, db_path: str = "allma_modules.db"):
        self.logger = logging.getLogger(__name__)
        self.state_manager = ModuleStateManager(db_path)
        self.module_name = "meta_learning_system"
        
        # Core Metrics (Persistent)
        self.style_scores = {
            'visual': 0.5,
            'textual': 0.5,
            'kinesthetic': 0.5, # Interactive/Action-based
            'theoretical': 0.5
        }
        
        self.communication_scores = {
            'direct': 0.5,
            'detailed': 0.5,
            'metaphorical': 0.5
        }
        
        # Recent Feedback Buffer (Short-term memory)
        self.feedback_history = deque(maxlen=20)
        
        # Load persistent state
        self._load_state()

    def process(self, message: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Orchestrator Entry Point (Tier 3).
        Analyzes user input for *implicit feedback* on previous turns.
        Returns *adjustments* for the current response.
        """
        # 1. Analyze Feedback from this message
        self._analyze_feedback(message)
        
        # 2. Determine Optimal Settings for acting/responding now
        best_style = self._get_best_style()
        best_comm = self._get_best_communication()
        
        result = {
            'intent': 'meta_learning',
            'suggested_style': best_style,
            'suggested_comm': best_comm,
            'confidence': max(self.style_scores.values())
        }
        self.logger.info(f"🧠 Meta-Learning Result: {result}")
        return result

    def _analyze_feedback(self, message: str):
        """Detects positive/negative signals in user message."""
        msg_lower = message.lower()
        
        # Negative Signals (Prioritize these to handle negations like "Non ho capito")
        if any(phrase in msg_lower for phrase in ['non ho capito', 'non è chiaro', 'spiega meglio', 'confuso', 'eh?', 'cosa?', 'non capisco']):
            self._update_scores(success=False)
            self.logger.info("📉 Negative Feedback Detected: Adjusting strategies.")
            return # Stop here to avoid triggering positive on "capito" inside "non ho capito"
            
        # Positive Signals
        if any(w in msg_lower for w in ['grazie', 'capito', 'chiaro', 'ottimo', 'brava', 'esatto']):
            # Verify it's not a negation (double check, though return above handles most)
            if 'non ' not in msg_lower: 
                self._update_scores(success=True)
                self.logger.info("📈 Positive Feedback Detected: Reinforcing current strategies.")
            
        # Explicit Requests (Strong Signal)
        if 'esempio' in msg_lower:
            self.style_scores['kinesthetic'] += 0.1
        if 'immagine' in msg_lower or 'vedere' in msg_lower:
            self.style_scores['visual'] += 0.2

        # Normalize
        self._normalize_scores()
        self._save_state()

    def _update_scores(self, success: bool):
        """Updates efficiency scores based on recent performance."""
        # Simple reinforcement learning
        # We assume the "current" dominant style was used recently.
        # In a real system, we'd need to know exactly WHAT was used last turn.
        # For now, we reinforce the *currently highest* traits.
        
        learning_rate = 0.1 if success else -0.15 # Penalize heavily
        
        best_style = self._get_best_style()
        best_comm = self._get_best_communication()
        
        self.style_scores[best_style] = max(0.0, min(1.0, self.style_scores[best_style] + learning_rate))
        self.communication_scores[best_comm] = max(0.0, min(1.0, self.communication_scores[best_comm] + learning_rate))

    def _get_best_style(self) -> str:
        return max(self.style_scores, key=self.style_scores.get)

    def _get_best_communication(self) -> str:
        return max(self.communication_scores, key=self.communication_scores.get)

    def _normalize_scores(self):
        """Keeps scores roughly comparable."""
        # Optional: ensure sum is 1.0 or just clamp? Just clamp in update.
        pass

    def _load_state(self):
        state = self.state_manager.load_state(self.module_name)
        if state:
            self.style_scores = state.get('style_scores', self.style_scores)
            self.communication_scores = state.get('communication_scores', self.communication_scores)

    def _save_state(self):
        state = {
            'style_scores': self.style_scores,
            'communication_scores': self.communication_scores,
            'last_updated': time.time()
        }
        self.state_manager.save_state(self.module_name, state)
