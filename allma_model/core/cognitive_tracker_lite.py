"""
CognitiveTrackerLite - Simple skill progression tracking

PHASE 24: Tier 3 Module Integration
Simplified from CognitiveEvolutionSystem (361 lines, 10 abilities) to 3 core abilities.
Tracks user skill progress without complex transfer learning.
"""

from typing import Dict, Any
from allma_model.core.module_state_manager import ModuleStateManager


class CognitiveTrackerLite:
    """
    Lightweight cognitive ability tracker.
    Tracks 3 core abilities: understanding, creativity, memory.
    
    Cost: ~40ms
    Priority: LOW (4/10)
    """
    
    def __init__(self, db_path="allma_modules.db"):
        # 3 core abilities (simplified from 10)
        self.abilities = {
            'understanding': 0.5,  # Comprehension level
            'creativity': 0.5,     # Creative thinking
            'memory': 0.5          # Context retention
        }
        
        # Track improvement trends
        self.interaction_count = 0
        self.successful_interactions = 0
        self.feedback_events = {}
        
        # Persistence
        self.state_manager = ModuleStateManager(db_path)
        self._load_state()

    def _load_state(self):
        """Restore state from DB."""
        state = self.state_manager.load_state('cognitive_tracker_lite')
        if isinstance(state, dict):
            import math
            saved = state.get('abilities')
            if isinstance(saved, dict):
                for key in self.abilities:
                    value = saved.get(key)
                    if isinstance(value, (int, float)) and math.isfinite(value):
                        self.abilities[key] = max(0., min(1., value))
            for key in ('interaction_count', 'successful_interactions'):
                value = state.get(key)
                if isinstance(value, int) and value >= 0:
                    setattr(self, key, value)
            events = state.get('feedback_events')
            if isinstance(events, dict):
                self.feedback_events = {key: value for key, value in list(events.items())[-1000:]
                                        if isinstance(key, str) and isinstance(value, bool)}

    def _save_state(self):
        """Save current state to DB."""
        state = {
            'abilities': self.abilities,
            'interaction_count': self.interaction_count,
            'successful_interactions': self.successful_interactions,
            'feedback_events': self.feedback_events
        }
        if not self.state_manager.save_state('cognitive_tracker_lite', state):
            raise OSError('Unable to persist cognitive tracking')
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with current abilities and growth suggestions
        """
        # Detect which ability is being exercised
        primary_ability = self._detect_primary_ability(user_input)
        
        # Get current proficiency
        current_level = self.abilities[primary_ability]
        
        # Suggest area for growth
        weakest = self._find_weakest_ability()
        
        self.interaction_count += 1
        try:
            self._save_state()
        except Exception:
            self.interaction_count -= 1
            raise
        
        return {
            'abilities': self.abilities.copy(),
            'primary_ability': primary_ability,
            'suggested_focus': weakest,
            'overall_progress': self._calculate_progress()
        }
    
    def _detect_primary_ability(self, text: str) -> str:
        """
        Detects which cognitive ability is being used.
        
        Returns:
            Name of primary ability ('understanding', 'creativity', 'memory')
        """
        text_lower = text.lower()
        
        # Creativity indicators
        creative_words = ['crea', 'inventa', 'immagina', 'idea', 'originale']
        if any(word in text_lower for word in creative_words):
            return 'creativity'
        
        # Memory indicators
        memory_words = ['ricorda', 'ricordo', 'ricordavi', 'precedente', 'prima']
        if any(word in text_lower for word in memory_words):
            return 'memory'
        
        # Default: understanding
        return 'understanding'
    
    def _find_weakest_ability(self) -> str:
        """Returns the ability with lowest proficiency."""
        return min(self.abilities.items(), key=lambda x: x[1])[0]
    
    def _calculate_progress(self) -> float:
        """
        Calculates overall cognitive progress.
        
        Returns:
            Float from 0.0 to 1.0
        """
        if self.interaction_count == 0:
            return 0.0
        
        # Average of all abilities
        avg_ability = sum(self.abilities.values()) / len(self.abilities)
        
        # Factor in success rate
        success_rate = min(1., self.successful_interactions / self.interaction_count)
        
        # Weighted average
        progress = 0.7 * avg_ability + 0.3 * success_rate
        
        return min(1.0, progress)
    
    def record_feedback(self, user_id, event, ability, success):
        """One observation per answer, including corrections; idempotent after restart."""
        import hashlib
        key = hashlib.sha256(f'{user_id}:{event}:{ability}'.encode()).hexdigest()
        previous = self.feedback_events.get(key)
        if previous is success:
            return False
        before = (dict(self.abilities), self.successful_interactions, dict(self.feedback_events))
        if previous is True:
            self.successful_interactions = max(0, self.successful_interactions - 1)
        self.feedback_events[key] = success
        self.feedback_events = dict(list(self.feedback_events.items())[-1000:])
        try:
            self.update_ability(ability, success)
        except Exception:
            self.abilities, self.successful_interactions, self.feedback_events = before
            raise
        return True

    def update_ability(self, ability_name: str, success: bool, difficulty: float = 0.5):
        """
        Updates ability based on interaction outcome.
        
        Args:
            ability_name: Which ability to update
            success: Whether interaction was successful
            difficulty: Difficulty level (0-1)
        """
        if ability_name not in self.abilities:
            return
        
        current = self.abilities[ability_name]
        
        if success:
            # Increase ability (more for harder tasks)
            increase = 0.05 * (1 + difficulty)
            self.abilities[ability_name] = min(1.0, current + increase)
            self.successful_interactions += 1
        else:
            # Decrease ability slightly
            decrease = 0.02
            self.abilities[ability_name] = max(0.0, current - decrease)

        self._save_state()
    
    def get_cognitive_state(self) -> Dict:
        """Returns current cognitive state summary."""
        return {
            'abilities': self.abilities.copy(),
            'strongest': max(self.abilities.items(), key=lambda x: x[1])[0],
            'weakest': self._find_weakest_ability(),
            'overall_progress': self._calculate_progress(),
            'total_interactions': self.interaction_count
        }
