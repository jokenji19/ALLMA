"""Test del sistema di apprendimento sociale"""

import unittest
from datetime import datetime, timedelta
from Model.incremental_learning.social_learning_system import (
    SocialLearningSystem,
    SocialInteraction,
    SocialBehavior
)

class TestSocialLearningSystem(unittest.TestCase):
    """Test suite per il sistema di apprendimento sociale"""
    
    def setUp(self):
        """Setup per i test"""
        self.system = SocialLearningSystem(
            learning_rate=0.1,
            exploration_rate=0.2,
            memory_size=1000
        )
        
    def test_observe_interaction(self):
        """Verifica l'osservazione di un'interazione"""
        # Osserva un'interazione positiva
        self.system.observe_interaction(
            agent_id="agent1",
            behavior="greet",
            context={"formal": 1.0, "morning": 1.0},
            outcome=0.8
        )
        
        # Verifica che l'interazione sia stata memorizzata
        self.assertEqual(len(self.system.interactions), 1)
        
        # Verifica che il comportamento sia stato creato
        self.assertIn("greet", self.system.behaviors)
        
        # Verifica che le statistiche siano corrette
        behavior = self.system.behaviors["greet"]
        self.assertEqual(behavior.usage_count, 1)
        self.assertGreater(behavior.success_rate, 0)
        
    def test_interaction_memory_limit(self):
        """Verifica il limite della memoria delle interazioni"""
        system = SocialLearningSystem(memory_size=2)
        
        # Aggiungi tre interazioni
        for i in range(3):
            system.observe_interaction(
                agent_id=f"agent{i}",
                behavior="test",
                context={},
                outcome=1.0
            )
            
        # Verifica che solo le ultime due siano mantenute
        self.assertEqual(len(system.interactions), 2)
        self.assertEqual(
            system.interactions[-1].agent_id,
            "agent2"
        )
        
    def test_behavior_selection(self):
        """Verifica la selezione del comportamento"""
        # Osserva alcune interazioni
        contexts = [
            {"formal": 1.0, "morning": 1.0},
            {"formal": 0.0, "evening": 1.0},
            {"informal": 1.0, "morning": 1.0}
        ]
        
        for i, context in enumerate(contexts):
            self.system.observe_interaction(
                agent_id="agent1",
                behavior=f"behavior{i}",
                context=context,
                outcome=0.5 + i * 0.2  # Aumenta il successo
            )
            
        # Seleziona un comportamento in un contesto formale
        behavior_id, params = self.system.interact(
            agent_id="agent1",
            context={"formal": 1.0, "morning": 0.8}
        )
        
        # Verifica che sia stato scelto un comportamento
        self.assertIsNotNone(behavior_id)
        
    def test_feedback_integration(self):
        """Verifica l'integrazione del feedback"""
        # Crea un'interazione
        self.system.observe_interaction(
            agent_id="agent1",
            behavior="greet",
            context={"formal": 1.0},
            outcome=0.5
        )
        
        interaction_id = self.system.interactions[0].interaction_id
        
        # Fornisci feedback
        self.system.receive_feedback(
            interaction_id,
            {"relationship": 0.8, "politeness": 0.9}
        )
        
        # Verifica che il feedback sia stato integrato
        interaction = self.system.interactions[0]
        self.assertIn("relationship", interaction.feedback)
        self.assertIn("politeness", interaction.feedback)
        
        # Verifica che la relazione sia stata aggiornata
        self.assertIn("agent1", self.system.agent_relationships)
        self.assertGreater(
            self.system.agent_relationships["agent1"],
            0
        )
        
    def test_behavior_adaptation(self):
        """Verifica l'adattamento del comportamento"""
        # Crea un comportamento iniziale
        behavior_id = "test_behavior"
        self.system.behaviors[behavior_id] = SocialBehavior(
            behavior_id=behavior_id,
            behavior_type="test",
            parameters={"intensity": 0.5}
        )
        
        # Adatta il comportamento con feedback
        self.system.adapt_behavior(
            behavior_id=behavior_id,
            context={"formal": 1.0},
            feedback={"intensity": 0.8}
        )
        
        # Verifica che i parametri siano stati adattati
        behavior = self.system.behaviors[behavior_id]
        self.assertGreater(
            behavior.parameters["intensity"],
            0.5
        )
        
    def test_context_preference_learning(self):
        """Verifica l'apprendimento delle preferenze contestuali"""
        # Osserva interazioni in contesti diversi
        contexts = [
            {"formal": 1.0, "morning": 1.0},
            {"formal": 1.0, "morning": 1.0},
            {"informal": 1.0, "evening": 1.0}
        ]
        
        outcomes = [0.9, 0.8, 0.3]
        
        for context, outcome in zip(contexts, outcomes):
            self.system.observe_interaction(
                agent_id="agent1",
                behavior="greet",
                context=context,
                outcome=outcome
            )
            
        # Verifica che le preferenze contestuali siano state aggiornate
        self.assertIn("formal", self.system.context_preferences)
        self.assertIn("greet", self.system.context_preferences["formal"])
        
        # Verifica che il comportamento sia preferito in contesto formale
        formal_pref = self.system.context_preferences["formal"]["greet"]
        informal_pref = self.system.context_preferences["informal"]["greet"]
        self.assertGreater(formal_pref, informal_pref)

if __name__ == '__main__':
    unittest.main()
