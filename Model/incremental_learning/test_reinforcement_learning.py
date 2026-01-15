"""
Test del Sistema di Apprendimento per Rinforzo
"""

import unittest
from reinforcement_learning_system import ReinforcementLearningSystem

class TestReinforcementLearning(unittest.TestCase):
    def setUp(self):
        self.rl_system = ReinforcementLearningSystem()
        
    def test_learning_from_experience(self):
        """Testa la capacità di imparare dalle esperienze"""
        # Simula un ambiente semplice di apprendimento
        states = ["fame", "sazio"]
        actions = ["mangia", "gioca", "dorme"]
        
        # Prima esperienza: mangiare quando si ha fame (positiva)
        self.rl_system.observe_outcome("fame", "mangia", 1.0, "sazio")
        
        # Seconda esperienza: giocare quando si ha fame (negativa)
        self.rl_system.observe_outcome("fame", "gioca", -0.5, "fame")
        
        # Verifica che il sistema preferisca mangiare quando ha fame
        action = self.rl_system.choose_action("fame", actions)
        self.assertEqual(action, "mangia")
        
    def test_exploration_decay(self):
        """Testa che il tasso di esplorazione diminuisca con l'esperienza"""
        initial_exploration = self.rl_system.exploration_rate
        
        # Simula alcune esperienze
        for _ in range(10):
            self.rl_system.observe_outcome("test", "action", 0.5, "test")
            
        # Verifica che l'esplorazione sia diminuita
        self.assertLess(self.rl_system.exploration_rate, initial_exploration)
        
    def test_reflection_capabilities(self):
        """Testa la capacità di riflettere sulle esperienze"""
        # Aggiunge alcune esperienze
        self.rl_system.observe_outcome("test", "action1", 1.0, "test")
        self.rl_system.observe_outcome("test", "action2", -0.5, "test")
        
        # Ottiene insights dalle esperienze
        insights = self.rl_system.reflect_on_experiences()
        
        # Verifica che ci siano informazioni utili
        self.assertIn('avg_reward', insights)
        self.assertIn('successful_actions', insights)
        self.assertIn('improvement_needed', insights)
        
    def test_learning_rate_adaptation(self):
        """Testa l'adattamento del tasso di apprendimento"""
        initial_learning_rate = self.rl_system.learning_rate
        
        # Simula esperienze con alta varianza
        for _ in range(15):
            reward = 1.0 if _ % 2 == 0 else -1.0
            self.rl_system.observe_outcome("test", "action", reward, "test")
            self.rl_system.adapt_learning_rate()
            
        # Verifica che il learning rate si sia adattato
        self.assertNotEqual(self.rl_system.learning_rate, initial_learning_rate)
        
    def test_no_initial_bias(self):
        """Verifica che il sistema parta senza pregiudizi"""
        actions = ["A", "B", "C"]
        
        # Prima di qualsiasi esperienza, le scelte dovrebbero essere casuali
        choices = [self.rl_system.choose_action("test", actions) for _ in range(100)]
        
        # Verifica che tutte le azioni siano state scelte almeno una volta
        for action in actions:
            self.assertIn(action, choices)
            
if __name__ == '__main__':
    unittest.main()
