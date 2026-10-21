
import logging
import time
import hashlib
import re
import math
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
        from .tool_strategy_learning import ToolStrategyLearning
        self.tool_learning = ToolStrategyLearning(self.state_manager)
        self.module_name = "meta_learning_system"
        self._user_id = None
        
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
        context = context or {}
        self._select_user(context.get('user_id'))
        before = (dict(self.style_scores), dict(self.communication_scores), list(self.feedback_history))
        self._analyze_feedback(message, context)
        if before != (self.style_scores, self.communication_scores, list(self.feedback_history)):
            try:
                self._save_state()
            except Exception:
                self.style_scores, self.communication_scores = before[:2]
                self.feedback_history = deque(before[2], maxlen=20)
                raise
        
        # 2. Determine Optimal Settings for acting/responding now
        best_style = self._get_best_style()
        best_comm = self._get_best_communication()
        
        result = {
            'intent': 'meta_learning',
            'suggested_style': best_style if max(self.style_scores.values()) > .55 else None,
            'suggested_comm': best_comm if not context.get('personality_expression_applied') and max(self.communication_scores.values()) > .55 else None,
            'communication_owner': 'personality' if context.get('personality_expression_applied') else 'meta_learning',
            'confidence': max(*self.style_scores.values(), *self.communication_scores.values())
        }
        self.logger.info(f"🧠 Meta-Learning Result: {result}")
        return result

    def _select_user(self, user_id):
        user_id = str(user_id) if user_id else None
        if user_id == self._user_id:
            return
        self._user_id = user_id
        self.module_name = ('meta_learning_system:' + hashlib.sha256(user_id.encode()).hexdigest()
                            if user_id else 'meta_learning_system')
        self.style_scores = {key: .5 for key in self.style_scores}
        self.communication_scores = {key: .5 for key in self.communication_scores}
        self.feedback_history.clear()
        self._load_state()

    def _analyze_feedback(self, message, context):
        text = message.lower()
        # Mentioning an image or an example is not a communication preference.
        explicit = {
            'kinesthetic': r'\b(?:fammi|mostrami|usa|vorrei|voglio) (?:un |degli |anche )?esempi?\b',
            'visual': r'\b(?:mostrami|usa|vorrei|voglio) (?:un |una |delle )?(?:immagin[ei]|diagramm[ai])\b',
        }
        for style, pattern in explicit.items():
            if re.search(pattern, text) and not re.search(r'\bnon\b', text):
                self.style_scores[style] = min(1., self.style_scores[style] + .1)
        for comm, pattern in {
            'direct': r'\b(?:rispondi|sii) (?:in breve|brevemente|conciso|concisa)\b',
            'detailed': r'\b(?:spiega|rispondi) (?:in dettaglio|dettagliatamente)\b',
            'metaphorical': r'\b(?:usa|spiega con) (?:una |delle )?metafor[ae]\b',
        }.items():
            if not context.get('personality_expression_applied') and re.search(pattern, text) and not re.search(r'\bnon\b', text):
                self.communication_scores[comm] = min(1., self.communication_scores[comm] + .1)

        # Reward only strategies actually included in the preceding valid answer.
        applied = context.get('applied_style')
        event = context.get('feedback_event')
        if not isinstance(applied, dict) or not event or event in self.feedback_history:
            return
        from allma_model.learning_system.answer_recall import feedback_kind
        kind = feedback_kind(message)
        if not kind:
            return
        rate = .1 if kind == 'positive' else -.15
        for scores, key in [(self.style_scores, 'suggested_style'),
                            (self.communication_scores, 'suggested_comm')]:
            if key == 'suggested_comm' and context.get('personality_expression_applied'):
                continue
            value = applied.get(key)
            if value in scores:
                scores[value] = max(0., min(1., scores[value] + rate))
        self.feedback_history.append(event)

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
        if not isinstance(state, dict):
            return
        for field in ('style_scores', 'communication_scores'):
            saved = state.get(field)
            if isinstance(saved, dict):
                scores = getattr(self, field)
                for key in scores:
                    value = saved.get(key)
                    if isinstance(value, (int, float)) and math.isfinite(value):
                        scores[key] = max(0., min(1., value))
        events = state.get('feedback_history', [])
        if isinstance(events, list):
            self.feedback_history.extend(v for v in events[-20:] if isinstance(v, str))

    def _save_state(self):
        state = {
            'style_scores': self.style_scores,
            'communication_scores': self.communication_scores,
            'feedback_history': list(self.feedback_history),
            'last_updated': time.time()
        }
        if not self.state_manager.save_state(self.module_name, state):
            raise OSError('Unable to persist communication preferences')
