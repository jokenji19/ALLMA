import unittest
import sys
import os

# Aggiungi il percorso della cartella incremental_learning al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incremental_learning.emotional_system import EmotionalSystem
from incremental_learning.memory_system import Memory
from incremental_learning.curiosity_system import CuriosityDrive
from incremental_learning.natural_trainer import NaturalTrainer

class TestIncrementalLearningSystem(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()
        self.memory = Memory()
        self.curiosity = CuriosityDrive()
        self.trainer = NaturalTrainer()

    def test_system_integration(self):
        # Test input
        test_input = "Mi piace molto la fotografia di paesaggio"
        
        # Test curiosity system
        curiosity_response = self.curiosity.process_input(test_input)
        self.assertIsNotNone(curiosity_response)
        self.assertIn('questions', curiosity_response)
        self.assertIn('exploration_focus', curiosity_response)
        
        # Test emotional system
        emotional_state = self.emotional_system.process_emotion(test_input)
        self.assertIsNotNone(emotional_state)
        self.assertTrue(0 <= emotional_state.get('valence', 0) <= 1)
        
        # Test memory system
        self.memory.add_interaction(test_input, "Che bello! Anche io amo la fotografia di paesaggio")
        recent = self.memory.get_recent_interactions(1)
        self.assertEqual(len(recent), 1)
        self.assertIn(test_input, recent[0])
        
        # Test natural trainer
        trainer_response = self.trainer.process_input(test_input)
        self.assertIsNotNone(trainer_response)
        self.assertIn('emotional_state', trainer_response)
        self.assertIn('curiosity_response', trainer_response)

if __name__ == '__main__':
    unittest.main()
