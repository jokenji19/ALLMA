"""Test del sistema integrato emotivo-sociale"""

import unittest
from datetime import datetime
import numpy as np
from allma_model.incremental_learning.emotional_social_system import (
    EmotionalSocialSystem,
    EmotionalSocialContext
)
from allma_model.incremental_learning.emotional_adaptation_system import EmotionalState

class TestEmotionalSocialSystem(unittest.TestCase):
    """Test suite per il sistema integrato emotivo-sociale"""
    
    def setUp(self):
        """Setup per i test"""
        self.system = EmotionalSocialSystem(
            emotional_learning_rate=0.1,
            social_learning_rate=0.1,
            memory_size=1000
        )
        
    def test_initial_state(self):
        """Verifica lo stato iniziale del sistema"""
        self.assertEqual(self.system.emotional_weight, 0.5)
        self.assertEqual(self.system.social_weight, 0.5)
        self.assertEqual(len(self.system.context_memory), 0)
        
    def test_process_interaction(self):
        """Verifica il processamento di un'interazione"""
        emotional_stimulus = {
            "valence": 0.7,
            "arousal": 0.3,
            "dominance": 0.6
        }
        social_context = {
            "formal": 1.0,
            "cooperative": 1.0
        }
        
        emotional_state, behavior = self.system.process_interaction(
            agent_id="agent1",
            emotional_stimulus=emotional_stimulus,
            social_context=social_context
        )
        
        # Verifica che sia stato creato un contesto
        self.assertIn("agent1", self.system.context_memory)
        
        # Verifica che lo stato emotivo sia valido
        self.assertTrue(0 <= emotional_state.valence <= 1)
        self.assertTrue(0 <= emotional_state.arousal <= 1)
        self.assertTrue(0 <= emotional_state.dominance <= 1)
        
        # Verifica che sia stato selezionato un comportamento
        self.assertIsInstance(behavior, str)
        
    def test_feedback_integration(self):
        """Verifica l'integrazione del feedback"""
        # Prima interazione
        self.system.process_interaction(
            agent_id="agent1",
            emotional_stimulus={"valence": 0.7, "arousal": 0.3, "dominance": 0.6},
            social_context={"formal": 1.0}
        )
        
        # Fornisci feedback positivo
        emotional_feedback = {
            "valence": 0.8,
            "arousal": 0.4,
            "dominance": 0.7,
            "effectiveness": 0.9
        }
        social_feedback = {
            "relationship": 0.8,
            "trust": 0.9,
            "effectiveness": 0.8
        }
        
        initial_emotional_weight = self.system.emotional_weight
        
        self.system.receive_feedback(
            agent_id="agent1",
            emotional_feedback=emotional_feedback,
            social_feedback=social_feedback
        )
        
        # Verifica che i pesi siano stati aggiornati
        self.assertNotEqual(
            self.system.emotional_weight,
            initial_emotional_weight
        )
        
    def test_context_evolution(self):
        """Verifica l'evoluzione del contesto"""
        agent_id = "agent1"
        context = {"formal": 1.0, "cooperative": 1.0}
        
        # Simula una serie di interazioni
        for i in range(5):
            self.system.process_interaction(
                agent_id=agent_id,
                emotional_stimulus={
                    "valence": 0.6 + i * 0.05,
                    "arousal": 0.4,
                    "dominance": 0.5
                },
                social_context=context
            )
            
            # Fornisci feedback positivo
            self.system.receive_feedback(
                agent_id=agent_id,
                emotional_feedback={
                    "valence": 0.7 + i * 0.05,
                    "arousal": 0.4,
                    "dominance": 0.5,
                    "effectiveness": 0.8
                },
                social_feedback={
                    "relationship": 0.8,
                    "trust": 0.8,
                    "effectiveness": 0.8
                }
            )
            
            # Adatta il comportamento
            self.system.adapt_behavior(
                agent_id=agent_id,
                context=context,
                feedback={
                    "trust": 0.8,
                    "relationship": 0.8,
                    "effectiveness": 0.8
                }
            )
            
        context_obj = self.system.context_memory[agent_id]
        
        # Verifica che il contesto si sia evoluto
        self.assertGreater(context_obj.trust_level, 0.5)
        self.assertGreater(context_obj.relationship_strength, 0.5)
        self.assertGreater(context_obj.shared_experiences, 0)
        
    def test_behavior_adaptation(self):
        """Verifica l'adattamento del comportamento"""
        agent_id = "agent1"
        context = {"formal": 1.0, "cooperative": 1.0}
        
        # Prima interazione
        emotional_state, behavior = self.system.process_interaction(
            agent_id=agent_id,
            emotional_stimulus={"valence": 0.7, "arousal": 0.3, "dominance": 0.6},
            social_context=context
        )
        
        # Adatta il comportamento
        self.system.adapt_behavior(
            agent_id=agent_id,
            context=context,
            feedback={
                "trust": 0.8,
                "relationship": 0.9,
                "effectiveness": 0.8
            }
        )
        
        # Verifica che il contesto sia stato aggiornato
        context_obj = self.system.context_memory[agent_id]
        self.assertGreater(context_obj.trust_level, 0.5)
        self.assertGreater(context_obj.relationship_strength, 0.5)
        
    def test_response_integration(self):
        """Verifica l'integrazione delle risposte"""
        agent_id = "agent1"
        
        # Crea un contesto con alta fiducia
        context = EmotionalSocialContext(
            emotional_state=EmotionalState(
                valence=0.5,
                arousal=0.5,
                dominance=0.5,
                context={}
            ),
            social_context={},
            interaction_history=[],
            relationship_strength=0.8,
            trust_level=0.9,
            shared_experiences=5
        )
        
        # Integra le risposte
        integrated_state = self.system._integrate_responses(
            emotional_response=EmotionalState(
                valence=0.8,
                arousal=0.3,
                dominance=0.6,
                context={}
            ),
            behavior_id="test_behavior",
            context=context
        )
        
        # Verifica che l'integrazione rifletta l'alta fiducia
        self.assertGreater(
            integrated_state.valence,
            context.emotional_state.valence
        )

if __name__ == '__main__':
    unittest.main()
