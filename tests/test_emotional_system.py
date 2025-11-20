import unittest
from datetime import datetime
from Model.incremental_learning.emotional_system import EmotionalSystem, EmotionType, Emotion

class TestEmotionalSystem(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()

    def test_process_stimulus_valid(self):
        """Test che il sistema gestisca correttamente stimoli validi"""
        result = self.emotional_system.process_stimulus("Sono molto felice", 0.8)
        self.assertIsInstance(result, Emotion)
        self.assertEqual(result.valence, 0.8)
        
    def test_process_stimulus_empty(self):
        """Test che il sistema gestisca correttamente stimoli vuoti"""
        with self.assertRaises(ValueError):
            self.emotional_system.process_stimulus("", 0.5)
            
    def test_process_stimulus_invalid_valence(self):
        """Test che il sistema gestisca correttamente valenze non valide"""
        with self.assertRaises(ValueError):
            self.emotional_system.process_stimulus("Test", 1.5)
            
    def test_emotion_decay(self):
        """Test che le emozioni decadano correttamente nel tempo"""
        emotion = self.emotional_system.process_stimulus("Test", 1.0)
        initial_intensity = emotion.intensity
        emotion.timestamp = datetime(2024, 1, 1)  # Simula un'emozione vecchia
        current_intensity = emotion.get_current_intensity()
        self.assertLess(current_intensity, initial_intensity)

if __name__ == '__main__':
    unittest.main()
