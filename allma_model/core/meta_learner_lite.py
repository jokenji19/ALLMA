"""
MetaLearnerLite - Lightweight adaptive learning without ML

PHASE 24: Tier 3 Module Integration
Refactored from MetaLearningSystem (995 lines with PyTorch) to rule-based system.
NO ML libraries, pure Python logic, mobile-optimized.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from collections import deque
import time
from allma_model.core.module_state_manager import ModuleStateManager


@dataclass
class LearningStrategy:
    """Simple learning strategy."""
    name: str
    success_rate: float = 0.5  # Exponential moving average
    usage_count: int = 0
    context_types: List[str] = None
    
    def __post_init__(self):
        if self.context_types is None:
            self.context_types = []


class MetaLearnerLite:
    """
    Lightweight adaptive learning system.
    Selects best learning strategy based on context without ML.
    
    Cost: ~60ms
    Priority: MEDIUM (6/10)
    """
    
    def __init__(self, max_history: int = 50):
        # 3 core strategies (simplified from original)
        self.strategies = {
            'elaboration': LearningStrategy(
                name='elaboration',
                context_types=['understanding', 'explanation', 'concept']
            ),
            'repetition': LearningStrategy(
                name='repetition',
                context_types=['practice', 'memorization', 'drill']
            ),
            'reflection': LearningStrategy(
                name='reflection',
                context_types=['analysis', 'evaluation', 'synthesis']
            )
        }
        
        # Recent experiences (circular buffer)
        self.experiences = deque(maxlen=max_history)
        
        # Current active strategy
        self.current_strategy = 'elaboration'
        
        # Consecutive failures per strategy
        self.failure_counts = {name: 0 for name in self.strategies}
        
        # Persistence
        self.state_manager = ModuleStateManager()
        self._load_state()

    def _load_state(self):
        """Restore state from DB."""
        state = self.state_manager.load_state('meta_learner_lite')
        if state:
            self.current_strategy = state.get('current_strategy', 'elaboration')
            loaded_strategies = state.get('strategies', {})
            
            for name, data in loaded_strategies.items():
                if name in self.strategies:
                    self.strategies[name].success_rate = data['success_rate']
                    self.strategies[name].usage_count = data['usage_count']

    def _save_state(self):
        """Save current state to DB."""
        state = {
            'current_strategy': self.current_strategy,
            'strategies': {
                name: {
                    'success_rate': s.success_rate,
                    'usage_count': s.usage_count
                }
                for name, s in self.strategies.items()
            }
        }
        self.state_manager.save_state('meta_learner_lite', state)
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with learning strategy and hints
        """
        # Detect learning intent
        if not self._is_learning_context(user_input, context):
            return {}  # Not a learning scenario
        
        # Select best strategy
        strategy_name = self._select_strategy(user_input, context)
        strategy = self.strategies[strategy_name]
        
        # Track usage
        strategy.usage_count += 1
        
        # Generate adaptation hints
        hints = self._generate_hints(strategy, context)
        
        return {
            'strategy': strategy_name,
            'hints': hints,
            'success_rate': strategy.success_rate
        }
    
    def _is_learning_context(self, text: str, context: Dict) -> bool:
        """Detects if this is a learning-related interaction."""
        learning_keywords = [
            'impara', 'studia', 'capire', 'spiegare', 'come funziona',
            'perché', 'esempio', 'pratica', 'esercizio'
        ]
        
        text_lower = text.lower()
        return any(kw in text_lower for kw in learning_keywords)
    
    def _select_strategy(self, text: str, context: Dict) -> str:
        """
        Rule-based strategy selection (NO ML).
        
        Rules:
        1. If asking "why/how" → elaboration
        2. If asking for practice → repetition  
        3. If asking opinion/analysis → reflection
        4. Default: best performing strategy
        """
        text_lower = text.lower()
        
        # Rule 1: Elaboration for understanding
        if any(word in text_lower for word in ['perché', 'come', 'spiega']):
            return 'elaboration'
        
        # Rule 2: Repetition for practice
        if any(word in text_lower for word in ['pratica', 'esercizio', 'ripeti']):
            return 'repetition'
        
        # Rule 3: Reflection for analysis
        if any(word in text_lower for word in ['analizza', 'valuta', 'pensa', 'rifletti']):
            return 'reflection'
        
        # Rule 4: Use best performing strategy
        return self._get_best_strategy()
    
    def _get_best_strategy(self) -> str:
        """Returns strategy with highest success rate."""
        best_name = 'elaboration'
        best_score = -1.0
        
        for name, strategy in self.strategies.items():
            # Penalize strategies with recent failures
            penalty = self.failure_counts[name] * 0.1
            score = strategy.success_rate - penalty
            
            if score > best_score:
                best_score = score
                best_name = name
        
        return best_name
    
    def _generate_hints(self, strategy: LearningStrategy, context: Dict) -> List[str]:
        """Generates hints for effective learning."""
        hints = []
        
        if strategy.name == 'elaboration':
            hints.append("Fornisci spiegazioni dettagliate con esempi")
            hints.append("Connetti concetti nuovi a conoscenze esistenti")
        elif strategy.name == 'repetition':
            hints.append("Ripeti concetti chiave in modi diversi")
            hints.append("Usa esempi multipli per rafforzare")
        elif strategy.name == 'reflection':
            hints.append("Incoraggia pensiero critico")
            hints.append("Chiedi all'utente di valutare e sintetizzare")
        
        return hints
    
    def update_success(self, strategy_name: str, success: bool):
        """
        Updates strategy success rate based on feedback.
        
        Args:
            strategy_name: Name of strategy used
            success: Whether it was successful
        """
        if strategy_name not in self.strategies:
            return
        
        strategy = self.strategies[strategy_name]
        
        # Exponential moving average (alpha=0.2)
        new_value = 1.0 if success else 0.0
        strategy.success_rate = 0.8 * strategy.success_rate + 0.2 * new_value
        
        # Track consecutive failures
        if success:
            self.failure_counts[strategy_name] = 0
        else:
            self.failure_counts[strategy_name] += 1
        
        # Record experience
        self.experiences.append({
            'strategy': strategy_name,
            'success': success,
            'timestamp': time.time()
        })
        
        # Persist state
        self._save_state()
    
    def get_learning_summary(self) -> Dict:
        """Returns summary of learning performance."""
        if not self.experiences:
            return {'status': 'no_data'}
        
        # Calculate recent success rate
        recent = list(self.experiences)[-20:]  # Last 20
        recent_successes = sum(1 for exp in recent if exp['success'])
        recent_rate = recent_successes / len(recent) if recent else 0.0
        
        # Find best/worst strategies
        sorted_strategies = sorted(
            self.strategies.items(),
            key=lambda x: x[1].success_rate,
            reverse=True
        )
        
        return {
            'total_experiences': len(self.experiences),
            'recent_success_rate': recent_rate,
            'best_strategy': sorted_strategies[0][0],
            'worst_strategy': sorted_strategies[-1][0],
            'strategies': {
                name: {
                    'success_rate': s.success_rate,
                    'usage_count': s.usage_count
                }
                for name, s in self.strategies.items()
            }
        }
