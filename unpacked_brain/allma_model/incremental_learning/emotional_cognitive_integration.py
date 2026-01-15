"""
Sistema di Integrazione Emotivo-Cognitivo
Gestisce l'integrazione tra il sistema emotivo e quello cognitivo per un apprendimento più naturale
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from enum import Enum

from allma_model.incremental_learning.emotional_adaptation_system import EmotionalState, EmotionalResponse
from allma_model.incremental_learning.metacognition_system import MetaCognitionSystem, CognitiveStrategy

class EmotionalImpact(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

@dataclass
class CognitiveEmotionalState:
    """Stato combinato emotivo-cognitivo"""
    emotional_state: EmotionalState
    cognitive_load: float  # 0-1, carico cognitivo attuale
    attention_level: float  # 0-1, livello di attenzione
    motivation_level: float  # 0-1, livello di motivazione
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)

class EmotionalCognitiveIntegration:
    """Sistema di integrazione emotivo-cognitivo"""
    
    def __init__(self, 
                 emotional_weight: float = 0.3,
                 cognitive_weight: float = 0.7):
        """
        Inizializza il sistema di integrazione
        
        Args:
            emotional_weight: Peso del fattore emotivo (0-1)
            cognitive_weight: Peso del fattore cognitivo (0-1)
        """
        self.emotional_weight = emotional_weight
        self.cognitive_weight = cognitive_weight
        self.state_history: List[CognitiveEmotionalState] = []
        self.learning_thresholds = {
            'optimal_cognitive_load': 0.7,
            'min_attention': 0.4,
            'min_motivation': 0.5
        }
        
    def integrate_state(self, 
                       emotional_state: EmotionalState,
                       cognitive_load: float,
                       context: Dict[str, Any]) -> CognitiveEmotionalState:
        """
        Integra lo stato emotivo e cognitivo
        
        Args:
            emotional_state: Stato emotivo corrente
            cognitive_load: Carico cognitivo corrente
            context: Contesto corrente
            
        Returns:
            Stato integrato emotivo-cognitivo
        """
        # Calcola il livello di attenzione basato su stato emotivo e carico cognitivo
        attention = self._calculate_attention(emotional_state, cognitive_load)
        
        # Calcola il livello di motivazione
        motivation = self._calculate_motivation(emotional_state, cognitive_load)
        
        # Crea il nuovo stato
        new_state = CognitiveEmotionalState(
            emotional_state=emotional_state,
            cognitive_load=cognitive_load,
            attention_level=attention,
            motivation_level=motivation,
            context=context
        )
        
        # Aggiorna la storia
        self.state_history.append(new_state)
        if len(self.state_history) > 1000:
            self.state_history = self.state_history[-1000:]
            
        return new_state
        
    def adapt_learning_strategy(self, 
                              current_state: CognitiveEmotionalState,
                              metacognition: MetaCognitionSystem) -> CognitiveStrategy:
        """
        Adatta la strategia di apprendimento in base allo stato emotivo-cognitivo
        
        Args:
            current_state: Stato emotivo-cognitivo corrente
            metacognition: Sistema metacognitivo
            
        Returns:
            Strategia cognitiva adattata
        """
        # Valuta le condizioni di apprendimento
        learning_conditions = self._evaluate_learning_conditions(current_state)
        
        # Seleziona la strategia appropriata
        if learning_conditions['optimal']:
            # Condizioni ottimali: strategia complessa
            return metacognition.select_strategy(complexity='high')
        elif learning_conditions['adequate']:
            # Condizioni adeguate: strategia moderata
            return metacognition.select_strategy(complexity='medium')
        else:
            # Condizioni non ottimali: strategia semplice
            return metacognition.select_strategy(complexity='low')
            
    def _calculate_attention(self, 
                           emotional_state: EmotionalState,
                           cognitive_load: float) -> float:
        """Calcola il livello di attenzione"""
        # L'attenzione è massima quando l'intensità emotiva è ottimale
        optimal_intensity = 0.7
        attention = 1.0 - abs(emotional_state.intensity - optimal_intensity)
        
        # Il carico cognitivo riduce l'attenzione se troppo alto
        if cognitive_load > self.learning_thresholds['optimal_cognitive_load']:
            attention *= (1.0 - (cognitive_load - self.learning_thresholds['optimal_cognitive_load']))
            
        return max(0.0, min(1.0, attention))
        
    def _calculate_motivation(self,
                            emotional_state: EmotionalState,
                            cognitive_load: float) -> float:
        """Calcola il livello di motivazione"""
        # La motivazione è influenzata da:
        # - Valenza emotiva positiva
        # - Intensità emotiva moderata
        # - Complessità ottimale
        
        motivation = (
            0.4 * emotional_state.valence +          # Emozioni positive aumentano la motivazione
            0.3 * (1.0 - abs(0.7 - emotional_state.intensity)) +  # Intensità moderata è ottimale
            0.3 * (1.0 - abs(0.6 - emotional_state.complexity))   # Complessità moderata è ottimale
        )
        
        # Il carico cognitivo troppo alto riduce la motivazione
        if cognitive_load > self.learning_thresholds['optimal_cognitive_load']:
            motivation *= (1.0 - (cognitive_load - self.learning_thresholds['optimal_cognitive_load']))
            
        return max(0.0, min(1.0, motivation))
        
    def _evaluate_learning_conditions(self,
                                   state: CognitiveEmotionalState) -> Dict[str, bool]:
        """Valuta le condizioni di apprendimento"""
        conditions = {
            'optimal': False,
            'adequate': False
        }
        
        # Condizioni ottimali
        if (state.attention_level > 0.7 and
            state.motivation_level > 0.7 and
            state.cognitive_load < self.learning_thresholds['optimal_cognitive_load']):
            conditions['optimal'] = True
            conditions['adequate'] = True
            
        # Condizioni adeguate
        elif (state.attention_level > self.learning_thresholds['min_attention'] and
              state.motivation_level > self.learning_thresholds['min_motivation']):
            conditions['adequate'] = True
            
        return conditions
        
    def get_emotional_impact(self, state: CognitiveEmotionalState) -> EmotionalImpact:
        """Valuta l'impatto emotivo sullo stato di apprendimento"""
        if (state.emotional_state.valence > 0.6 and 
            state.motivation_level > 0.6):
            return EmotionalImpact.POSITIVE
        elif (state.emotional_state.valence < 0.4 or 
              state.motivation_level < 0.4):
            return EmotionalImpact.NEGATIVE
        else:
            return EmotionalImpact.NEUTRAL
            
    def get_learning_effectiveness(self, state: CognitiveEmotionalState) -> float:
        """Calcola l'efficacia dell'apprendimento dato lo stato corrente"""
        return (
            self.emotional_weight * (
                0.4 * max(0, state.emotional_state.valence) +
                0.3 * state.emotional_state.arousal +
                0.3 * state.emotional_state.dominance
            ) +
            self.cognitive_weight * (
                0.4 * state.attention_level +
                0.3 * state.motivation_level +
                0.3 * (1.0 - state.cognitive_load)
            )
        )

    def process_emotion(self, stimulus: Dict) -> Dict:
        """
        Processa uno stimolo emotivo e aggiorna lo stato emotivo-cognitivo
        
        Args:
            stimulus: Dizionario con il contenuto e i parametri emotivi
            
        Returns:
            Dict con lo stato emotivo aggiornato
        """
        # Crea lo stato emotivo dal stimulus
        emotional_state = EmotionalState(
            intensity=stimulus.get('arousal', 0.5),
            valence=stimulus.get('valence', 0.5),
            complexity=0.5,  # Valore default per il test
            category='neutral'
        )
        
        # Integra con lo stato cognitivo
        integrated_state = self.integrate_state(
            emotional_state=emotional_state,
            cognitive_load=0.5,  # Valore default per il test
            context={'content': stimulus.get('content', '')}
        )
        
        # Restituisce la risposta
        return {
            'emotional_state': {
                'valence': emotional_state.valence,
                'intensity': emotional_state.intensity
            },
            'attention': integrated_state.attention_level,
            'motivation': integrated_state.motivation_level
        }
