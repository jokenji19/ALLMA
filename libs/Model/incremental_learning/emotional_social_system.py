"""
Sistema integrato di Adattamento Emotivo e Apprendimento Sociale
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from Model.incremental_learning.emotional_adaptation_system import (
    EmotionalAdaptationSystem,
    EmotionalState,
    EmotionalResponse
)
from Model.incremental_learning.social_learning_system import (
    SocialLearningSystem,
    SocialInteraction,
    SocialBehavior
)

@dataclass
class EmotionalSocialContext:
    """Contesto integrato emotivo-sociale"""
    emotional_state: EmotionalState
    social_context: Dict[str, float]
    interaction_history: List[str]
    relationship_strength: float
    trust_level: float
    shared_experiences: int

class EmotionalSocialSystem:
    """Sistema integrato di adattamento emotivo e apprendimento sociale"""
    
    def __init__(self,
                 emotional_learning_rate: float = 0.1,
                 social_learning_rate: float = 0.1,
                 memory_size: int = 1000):
        """
        Inizializza il sistema integrato
        
        Args:
            emotional_learning_rate: Tasso di apprendimento emotivo
            social_learning_rate: Tasso di apprendimento sociale
            memory_size: Dimensione della memoria
        """
        self.emotional_system = EmotionalAdaptationSystem(
            learning_rate=emotional_learning_rate
        )
        self.social_system = SocialLearningSystem(
            learning_rate=social_learning_rate,
            memory_size=memory_size
        )
        
        # Pesi di integrazione
        self.emotional_weight = 0.5
        self.social_weight = 0.5
        
        # Memoria contestuale
        self.context_memory: Dict[str, EmotionalSocialContext] = {}
        
    def process_interaction(self,
                          agent_id: str,
                          emotional_stimulus: Dict[str, float],
                          social_context: Dict[str, float]) -> Tuple[EmotionalState, str]:
        """
        Processa un'interazione integrando risposta emotiva e sociale
        
        Args:
            agent_id: ID dell'agente con cui si interagisce
            emotional_stimulus: Stimolo emotivo
            social_context: Contesto sociale
            
        Returns:
            Tupla (stato emotivo risultante, comportamento scelto)
        """
        # Recupera o crea il contesto
        context = self._get_or_create_context(agent_id)
        
        # Processa la risposta emotiva
        emotional_response = self.emotional_system.process_emotion(
            stimulus_id=f"int_{agent_id}",
            current_state=context.emotional_state,
            context=social_context
        )
        
        # Seleziona il comportamento sociale
        behavior_id, behavior_params = self.social_system.interact(
            agent_id=agent_id,
            context=social_context
        )
        
        # Integra le risposte
        integrated_state = self._integrate_responses(
            emotional_response,
            behavior_id,
            context
        )
        
        # Aggiorna il contesto
        self._update_context(
            agent_id,
            integrated_state,
            behavior_id,
            social_context
        )
        
        return integrated_state, behavior_id
        
    def receive_feedback(self,
                        agent_id: str,
                        emotional_feedback: Dict[str, float],
                        social_feedback: Dict[str, float]) -> None:
        """
        Riceve e processa il feedback per entrambi i sistemi
        
        Args:
            agent_id: ID dell'agente
            emotional_feedback: Feedback emotivo
            social_feedback: Feedback sociale
        """
        # Estrai l'efficacia dal feedback emotivo
        effectiveness = emotional_feedback.pop("effectiveness", 0.5)
        
        # Aggiorna il sistema emotivo
        self.emotional_system.update_adaptation(
            stimulus_id=f"int_{agent_id}",
            initial_state=self.context_memory[agent_id].emotional_state,
            response_state=EmotionalState(**emotional_feedback),
            effectiveness=effectiveness
        )
        
        # Aggiorna il sistema sociale
        self.social_system.receive_feedback(
            interaction_id=f"int_{agent_id}",
            feedback=social_feedback
        )
        
        # Aggiorna i pesi di integrazione
        self._update_integration_weights(
            effectiveness,
            social_feedback.get("effectiveness", 0.5)
        )
        
    def adapt_behavior(self,
                      agent_id: str,
                      context: Dict[str, float],
                      feedback: Dict[str, float]) -> None:
        """
        Adatta il comportamento in base al feedback
        
        Args:
            agent_id: ID dell'agente
            context: Contesto dell'interazione
            feedback: Feedback ricevuto
        """
        # Adatta il comportamento sociale
        self.social_system.adapt_behavior(
            behavior_id=f"int_{agent_id}",
            context=context,
            feedback=feedback
        )
        
        # Aggiorna il contesto emotivo-sociale
        if agent_id in self.context_memory:
            context_obj = self.context_memory[agent_id]
            
            # Calcola gli incrementi basati sul feedback
            trust_increment = feedback.get("trust", 0.0) * 0.2
            relationship_increment = feedback.get("relationship", 0.0) * 0.2
            
            # Aggiorna i livelli con incrementi significativi
            context_obj.trust_level = min(
                1.0,
                context_obj.trust_level + trust_increment
            )
            context_obj.relationship_strength = min(
                1.0,
                context_obj.relationship_strength + relationship_increment
            )
            
    def get_state(self) -> Dict:
        """Restituisce lo stato corrente del sistema emotivo-sociale"""
        interactions = []
        for agent_id, context in self.context_memory.items():
            interactions.append({
                "agent_id": agent_id,
                "emotional_state": vars(context.emotional_state),
                "social_context": context.social_context,
                "relationship_strength": context.relationship_strength,
                "trust_level": context.trust_level,
                "shared_experiences": context.shared_experiences
            })
            
        return {
            "interactions": interactions,
            "emotional_weight": self.emotional_weight,
            "social_weight": self.social_weight
        }
        
    def _get_or_create_context(self, agent_id: str) -> EmotionalSocialContext:
        """Recupera o crea un nuovo contesto per un agente"""
        if agent_id not in self.context_memory:
            self.context_memory[agent_id] = EmotionalSocialContext(
                emotional_state=EmotionalState(
                    valence=0.5,
                    arousal=0.5,
                    dominance=0.5,
                    context={}
                ),
                social_context={},
                interaction_history=[],
                relationship_strength=0.5,
                trust_level=0.5,
                shared_experiences=0
            )
        return self.context_memory[agent_id]
        
    def _integrate_responses(self,
                           emotional_response: EmotionalState,
                           behavior_id: str,
                           context: EmotionalSocialContext) -> EmotionalState:
        """Integra le risposte emotiva e sociale"""
        # Calcola i pesi dinamici
        trust_factor = context.trust_level
        relationship_factor = context.relationship_strength
        experience_factor = min(1.0, context.shared_experiences / 10)
        
        # Adatta i pesi base
        emotional_weight = self.emotional_weight * (1 + trust_factor * 0.2)
        social_weight = self.social_weight * (1 + relationship_factor * 0.2)
        
        # Normalizza i pesi
        total_weight = emotional_weight + social_weight
        emotional_weight /= total_weight
        social_weight /= total_weight
        
        # Integra gli stati
        return EmotionalState(
            valence=(
                emotional_response.valence * emotional_weight +
                context.emotional_state.valence * social_weight
            ),
            arousal=(
                emotional_response.arousal * emotional_weight +
                context.emotional_state.arousal * social_weight
            ),
            dominance=(
                emotional_response.dominance * emotional_weight +
                context.emotional_state.dominance * social_weight
            ),
            context=emotional_response.context.copy()
        )
        
    def _update_context(self,
                       agent_id: str,
                       emotional_state: EmotionalState,
                       behavior_id: str,
                       social_context: Dict[str, float]) -> None:
        """Aggiorna il contesto emotivo-sociale"""
        context = self.context_memory[agent_id]
        
        # Aggiorna lo stato emotivo
        context.emotional_state = emotional_state
        
        # Aggiorna il contesto sociale
        context.social_context.update(social_context)
        
        # Aggiorna la storia delle interazioni
        context.interaction_history.append(behavior_id)
        if len(context.interaction_history) > 10:
            context.interaction_history.pop(0)
            
        # Incrementa le esperienze condivise
        context.shared_experiences += 1
        
    def _update_integration_weights(self,
                                  emotional_effectiveness: float,
                                  social_effectiveness: float) -> None:
        """Aggiorna i pesi di integrazione"""
        # Calcola la differenza di efficacia
        effectiveness_diff = emotional_effectiveness - social_effectiveness
        
        # Aggiusta i pesi (max ±10% per volta)
        adjustment = min(0.1, abs(effectiveness_diff)) * np.sign(effectiveness_diff)
        
        self.emotional_weight = min(0.8, max(0.2, self.emotional_weight + adjustment))
        self.social_weight = 1.0 - self.emotional_weight
