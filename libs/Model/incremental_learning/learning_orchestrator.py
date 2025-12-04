"""
Orchestrator per il coordinamento dei sistemi di apprendimento
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np

from meta_learning_system import MetaLearningSystem
from emotional_social_system import EmotionalSocialSystem
from pattern_recognition_system import PatternRecognitionSystem

@dataclass
class LearningEvent:
    """Evento di apprendimento che include tutti gli aspetti"""
    timestamp: datetime
    content: Any
    context: Dict[str, float]
    emotional_state: Dict[str, float]
    social_context: Dict[str, float]
    meta_strategy: str
    patterns_detected: List[str]
    success_level: float
    feedback: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte l'evento in un dizionario serializzabile"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "context": self.context,
            "emotional_state": self.emotional_state,
            "social_context": self.social_context,
            "meta_strategy": self.meta_strategy,
            "patterns_detected": self.patterns_detected,
            "success_level": self.success_level,
            "feedback": self.feedback
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LearningEvent':
        """Crea un evento da un dizionario"""
        timestamp = datetime.fromisoformat(data["timestamp"])
        del data["timestamp"]
        return cls(timestamp=timestamp, **data)

class LearningEventEncoder(json.JSONEncoder):
    """Encoder personalizzato per gli eventi di apprendimento"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, LearningEvent):
            return obj.to_dict()
        return super().default(obj)

class LearningOrchestrator:
    """Orchestratore dei sistemi di apprendimento"""
    
    def __init__(self,
                 emotional_social_weight: float = 0.4,
                 meta_learning_weight: float = 0.3,
                 pattern_weight: float = 0.3):
        """
        Inizializza l'orchestratore
        
        Args:
            emotional_social_weight: Peso del sistema emotivo-sociale
            meta_learning_weight: Peso del sistema di meta-apprendimento
            pattern_weight: Peso del sistema di riconoscimento pattern
        """
        # Inizializza i sistemi
        self.emotional_social = EmotionalSocialSystem()
        self.meta_learning = MetaLearningSystem()
        self.pattern_recognition = PatternRecognitionSystem()
        
        # Pesi dei sistemi
        self.weights = {
            "emotional_social": emotional_social_weight,
            "meta_learning": meta_learning_weight,
            "pattern": pattern_weight
        }
        
        # Storia degli eventi
        self.learning_history: List[LearningEvent] = []
        
    def process_learning_event(self,
                             content: Any,
                             context: Dict[str, float],
                             agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processa un evento di apprendimento coordinando tutti i sistemi
        
        Args:
            content: Contenuto da apprendere
            context: Contesto generale
            agent_id: ID dell'agente (se applicabile)
            
        Returns:
            Risultati dell'elaborazione
        """
        # Step 1: Pattern Recognition (usa le features del contesto)
        context_features = list(context.values())
        if not context_features:
            context_features = [0.5]  # Default se non ci sono features
        patterns = self.pattern_recognition.recognize_pattern(context_features)
        
        # Step 2: Meta-Learning Strategy Selection
        meta_strategy = self.meta_learning.learn(
            content=str(content),
            context=context,
            difficulty=context.get("difficulty", 0.5)
        )
        
        # Step 3: Emotional-Social Processing
        emotional_state, behavior = self.emotional_social.process_interaction(
            agent_id=agent_id or "system",
            emotional_stimulus=self._extract_emotional_features(content, context),
            social_context=self._extract_social_features(context)
        )
        
        # Step 4: Integrate Responses
        success_level = self._calculate_success(
            patterns=patterns,
            meta_strategy=meta_strategy["strategy_used"],
            emotional_state=emotional_state,
            meta_success=meta_strategy["success_level"]
        )
        
        # Crea l'evento
        event = LearningEvent(
            timestamp=datetime.now(),
            content=content,
            context=context.copy(),
            emotional_state=emotional_state.__dict__,
            social_context=self._extract_social_features(context),
            meta_strategy=meta_strategy["strategy_used"],
            patterns_detected=patterns,
            success_level=success_level,
            feedback={}
        )
        
        # Memorizza l'evento
        self.learning_history.append(event)
        
        return {
            "success_level": success_level,
            "patterns": patterns,
            "strategy": meta_strategy["strategy_used"],
            "emotional_state": emotional_state.__dict__,
            "behavior": behavior
        }
        
    def provide_feedback(self,
                        event_index: int,
                        feedback: Dict[str, Any]) -> None:
        """
        Fornisce feedback per un evento di apprendimento
        
        Args:
            event_index: Indice dell'evento
            feedback: Feedback per i vari aspetti
        """
        if 0 <= event_index < len(self.learning_history):
            event = self.learning_history[event_index]
            
            # Aggiorna l'evento con il feedback
            event.feedback = feedback
            
            # Distribuisci il feedback ai sistemi
            if "emotional_social" in feedback:
                self.emotional_social.receive_feedback(
                    agent_id="system",
                    emotional_feedback=feedback["emotional_social"].get("emotional", {}),
                    social_feedback=feedback["emotional_social"].get("social", {})
                )
                
            if "meta_learning" in feedback:
                # Usa il metodo learn per aggiornare la strategia
                self.meta_learning.learn(
                    content=str(event.content),
                    context=event.context,
                    difficulty=event.context.get("difficulty", 0.5)
                )
                
            if "pattern" in feedback:
                # Aggiorna i pattern usando il riconoscimento
                self.pattern_recognition.recognize_pattern(
                    list(event.context.values())
                )
                
    def analyze_learning_trends(self) -> Dict[str, Any]:
        """
        Analizza i trend di apprendimento
        
        Returns:
            Analisi dei trend
        """
        if not self.learning_history:
            return {
                "average_success": 0.0,
                "trend": "no_data",
                "patterns": [],
                "strategies": {},
                "emotional_social": {}
            }
            
        # Calcola statistiche di base
        success_levels = [e.success_level for e in self.learning_history]
        avg_success = np.mean(success_levels)
        
        # Analizza il trend
        if len(success_levels) > 1:
            trend = np.polyfit(range(len(success_levels)), success_levels, 1)[0]
            trend_direction = "improving" if trend > 0 else "declining"
        else:
            trend_direction = "stable"
            
        # Analizza i pattern più frequenti
        all_patterns = [p for e in self.learning_history for p in e.patterns_detected]
        pattern_counts = {}
        for p in all_patterns:
            pattern_counts[p] = pattern_counts.get(p, 0) + 1
            
        # Analizza le strategie
        strategy_stats = {}
        for e in self.learning_history:
            if e.meta_strategy not in strategy_stats:
                strategy_stats[e.meta_strategy] = {
                    "count": 0,
                    "success_sum": 0.0
                }
            stats = strategy_stats[e.meta_strategy]
            stats["count"] += 1
            stats["success_sum"] += e.success_level
            
        # Calcola l'efficacia media delle strategie
        for s in strategy_stats.values():
            s["average_success"] = s["success_sum"] / s["count"]
            
        return {
            "average_success": avg_success,
            "trend": trend_direction,
            "patterns": sorted(
                pattern_counts.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            "strategies": {
                k: v["average_success"]
                for k, v in strategy_stats.items()
            }
        }
        
    def save_state(self, filepath: str) -> None:
        """
        Salva lo stato dell'orchestratore
        
        Args:
            filepath: Percorso del file
        """
        state = {
            "weights": self.weights,
            "history": self.learning_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, cls=LearningEventEncoder)
            
    def load_state(self, filepath: str) -> None:
        """
        Carica lo stato dell'orchestratore
        
        Args:
            filepath: Percorso del file
        """
        with open(filepath, 'r') as f:
            state = json.load(f)
            
        self.weights = state["weights"]
        self.learning_history = [LearningEvent.from_dict(event_data) for event_data in state["history"]]
        
    def _extract_emotional_features(self,
                                  content: Any,
                                  context: Dict[str, float]) -> Dict[str, float]:
        """Estrae features emotive dal contenuto e contesto"""
        # Implementazione base - da espandere
        return {
            "valence": context.get("valence", 0.5),
            "arousal": context.get("arousal", 0.5),
            "dominance": context.get("dominance", 0.5)
        }
        
    def _extract_social_features(self,
                               context: Dict[str, float]) -> Dict[str, float]:
        """Estrae features sociali dal contesto"""
        # Implementazione base - da espandere
        return {
            "formal": context.get("formal", 0.5),
            "cooperative": context.get("cooperative", 0.5)
        }
        
    def _calculate_success(self,
                         patterns: List[str],
                         meta_strategy: str,
                         emotional_state: Any,
                         meta_success: float) -> float:
        """Calcola il livello di successo complessivo"""
        # Contributo del pattern recognition
        pattern_success = len(patterns) / 10.0  # Esempio semplificato
        
        # Contributo emotivo-sociale
        emotional_success = (
            emotional_state.valence +
            emotional_state.arousal +
            emotional_state.dominance
        ) / 3.0
        
        # Integra i contributi usando i pesi
        return min(1.0, max(0.0,
            pattern_success * self.weights["pattern"] +
            meta_success * self.weights["meta_learning"] +
            emotional_success * self.weights["emotional_social"]
        ))
