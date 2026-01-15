import unittest
from datetime import datetime
from typing import Dict
from allma_model.incremental_learning.emotional_adaptation_system import EmotionalState
from allma_model.incremental_learning.metacognition_system import MetaCognitionSystem, CognitiveStrategy
from allma_model.incremental_learning.emotional_cognitive_integration import (
    EmotionalCognitiveIntegration,
    CognitiveEmotionalState,
    EmotionalImpact
)

class TestEmotionalCognitiveIntegration(unittest.TestCase):
    def setUp(self):
        self.integration = EmotionalCognitiveIntegration()
        self.metacognition = MetaCognitionSystem()
        
    def test_state_integration(self):
        """Test dell'integrazione dello stato emotivo-cognitivo"""
        emotional_state = EmotionalState(
            valence=0.8,  # Valenza positiva
            arousal=0.6,  # Attivazione moderata
            dominance=0.7  # Buon controllo
        )
        cognitive_load = 0.5  # Carico cognitivo moderato
        context = {"task": "learning", "difficulty": "medium"}
        
        integrated_state = self.integration.integrate_state(
            emotional_state=emotional_state,
            cognitive_load=cognitive_load,
            context=context
        )
        
        # Verifica i componenti dello stato integrato
        self.assertIsInstance(integrated_state, CognitiveEmotionalState)
        self.assertGreater(integrated_state.attention_level, 0.6,
                          "L'attenzione dovrebbe essere alta con questi parametri")
        self.assertGreater(integrated_state.motivation_level, 0.6,
                          "La motivazione dovrebbe essere alta con questi parametri")
        
    def test_strategy_adaptation(self):
        """Test dell'adattamento della strategia"""
        # Test con condizioni ottimali
        optimal_state = CognitiveEmotionalState(
            emotional_state=EmotionalState(valence=0.8, arousal=0.7, dominance=0.8),
            cognitive_load=0.5,
            attention_level=0.9,
            motivation_level=0.9,
            context={"task": "learning"}
        )
        
        strategy = self.integration.adapt_learning_strategy(
            current_state=optimal_state,
            metacognition=self.metacognition
        )
        
        self.assertEqual(strategy.complexity, 'high',
                        "Dovrebbe selezionare una strategia complessa in condizioni ottimali")
        
        # Test con condizioni non ottimali
        suboptimal_state = CognitiveEmotionalState(
            emotional_state=EmotionalState(valence=0.4, arousal=0.3, dominance=0.4),
            cognitive_load=0.8,
            attention_level=0.3,
            motivation_level=0.4,
            context={"task": "learning"}
        )
        
        strategy = self.integration.adapt_learning_strategy(
            current_state=suboptimal_state,
            metacognition=self.metacognition
        )
        
        self.assertEqual(strategy.complexity, 'low',
                        "Dovrebbe selezionare una strategia semplice in condizioni non ottimali")
        
    def test_emotional_impact(self):
        """Test della valutazione dell'impatto emotivo"""
        # Test impatto positivo
        positive_state = CognitiveEmotionalState(
            emotional_state=EmotionalState(valence=0.8, arousal=0.6, dominance=0.7),
            cognitive_load=0.4,
            attention_level=0.8,
            motivation_level=0.8,
            context={}
        )
        
        self.assertEqual(
            self.integration.get_emotional_impact(positive_state),
            EmotionalImpact.POSITIVE,
            "Dovrebbe rilevare un impatto emotivo positivo"
        )
        
        # Test impatto negativo
        negative_state = CognitiveEmotionalState(
            emotional_state=EmotionalState(valence=0.3, arousal=0.8, dominance=0.4),
            cognitive_load=0.7,
            attention_level=0.4,
            motivation_level=0.3,
            context={}
        )
        
        self.assertEqual(
            self.integration.get_emotional_impact(negative_state),
            EmotionalImpact.NEGATIVE,
            "Dovrebbe rilevare un impatto emotivo negativo"
        )
        
    def test_learning_effectiveness(self):
        """Test del calcolo dell'efficacia dell'apprendimento"""
        state = CognitiveEmotionalState(
            emotional_state=EmotionalState(valence=0.8, arousal=0.6, dominance=0.7),
            cognitive_load=0.5,
            attention_level=0.8,
            motivation_level=0.7,
            context={}
        )
        
        effectiveness = self.integration.get_learning_effectiveness(state)
        
        self.assertGreater(effectiveness, 0.6,
                          "L'efficacia dovrebbe essere alta con questi parametri")
        self.assertLessEqual(effectiveness, 1.0,
                           "L'efficacia non dovrebbe superare 1.0")
        
    def test_attention_calculation(self):
        """Test del calcolo dell'attenzione"""
        emotional_state = EmotionalState(valence=0.7, arousal=0.7, dominance=0.6)
        cognitive_load = 0.5
        
        attention = self.integration._calculate_attention(emotional_state, cognitive_load)
        
        self.assertGreaterEqual(attention, 0.0)
        self.assertLessEqual(attention, 1.0)
        self.assertGreater(attention, 0.5,
                          "L'attenzione dovrebbe essere alta con arousal ottimale")
        
    def test_motivation_calculation(self):
        """Test del calcolo della motivazione"""
        emotional_state = EmotionalState(valence=0.8, arousal=0.6, dominance=0.7)
        cognitive_load = 0.4
        
        motivation = self.integration._calculate_motivation(emotional_state, cognitive_load)
        
        self.assertGreaterEqual(motivation, 0.0)
        self.assertLessEqual(motivation, 1.0)
        self.assertGreater(motivation, 0.6,
                          "La motivazione dovrebbe essere alta con valenza positiva e basso carico cognitivo")

if __name__ == '__main__':
    unittest.main()
