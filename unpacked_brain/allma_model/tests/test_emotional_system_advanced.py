"""
Test del sistema emotivo avanzato
"""

import unittest
from datetime import datetime, timedelta
from allma_model.incremental_learning.emotional_system import (
    EmotionalSystem, Emotion, EmotionType, EmotionalPattern
)

class TestEmotionalSystemAdvanced(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()

    def test_emotion_recognition(self):
        """Test del riconoscimento base delle emozioni"""
        # Test emozione semplice
        emotion = self.emotional_system.process_stimulus("Sono molto felice oggi!")
        self.assertEqual(emotion.primary_emotion, EmotionType.JOY)
        self.assertGreater(emotion.intensity, 0.5)
        
        # Test emozione complessa
        emotion = self.emotional_system.process_stimulus("Sono preoccupato ma anche speranzoso per il futuro")
        self.assertIsNotNone(emotion.secondary_emotions)
        self.assertIn(EmotionType.HOPE, emotion.secondary_emotions)

    def test_emotional_blend(self):
        """Test della miscela di emozioni"""
        emotions = [
            Emotion(EmotionType.JOY, 0.7, 0.8),
            Emotion(EmotionType.HOPE, 0.5, 0.6),
            Emotion(EmotionType.ANXIETY, 0.3, -0.2)
        ]
        
        blend = self.emotional_system.detect_emotional_blend(emotions)
        self.assertIsNotNone(blend)
        self.assertEqual(len(blend), 3)
        # Verifica che JOY sia l'emozione dominante
        self.assertEqual(blend[0][0], EmotionType.JOY)

    def test_emotional_patterns(self):
        """Test del riconoscimento dei pattern emotivi"""
        # Crea una sequenza di emozioni
        emotions = [
            ("Sono felice!", EmotionType.JOY),
            ("Che sorpresa!", EmotionType.SURPRISE),
            ("Sono curioso.", EmotionType.CURIOSITY)
        ]
        
        # Processa la sequenza
        for text, expected_emotion in emotions:
            emotion = self.emotional_system.process_stimulus(text)
            self.assertEqual(emotion.primary_emotion, expected_emotion)
        
        # Verifica che il pattern sia stato rilevato
        self.assertGreater(len(self.emotional_system.emotional_patterns), 0)

    def test_emotional_memory(self):
        """Test della memoria emotiva"""
        # Simula una serie di interazioni
        self.emotional_system.process_stimulus("Sono molto felice!", "situazione_1")
        self.emotional_system.process_stimulus("Mi sento ansioso.", "situazione_2")
        
        # Verifica che le emozioni siano state memorizzate nel contesto
        self.assertGreater(len(self.emotional_system.context_emotions["situazione_1"]), 0)
        self.assertGreater(len(self.emotional_system.context_emotions["situazione_2"]), 0)

    def test_emotional_decay(self):
        """Test del decadimento emotivo"""
        # Crea un'emozione intensa
        emotion = self.emotional_system.process_stimulus("Sono estremamente felice!")
        initial_intensity = emotion.intensity
        
        # Simula il passaggio del tempo
        time_passed = 3600  # 1 ora
        decay_factor = self.emotional_system.calculate_emotional_decay(time_passed)
        
        # Verifica che l'intensità sia diminuita
        self.assertLess(initial_intensity * decay_factor, initial_intensity)

    def test_complex_emotional_response(self):
        """Test della risposta emotiva complessa"""
        # Test con contesto e storia emotiva
        self.emotional_system.process_stimulus("Mi sento sereno", "lavoro")
        self.emotional_system.process_stimulus("Sono un po' preoccupato", "lavoro")
        
        # Test risposta complessa
        emotion = self.emotional_system.process_stimulus(
            "Sono ansioso ma anche motivato per la nuova sfida",
            "lavoro"
        )
        
        # Verifica la presenza di emozioni multiple
        self.assertIsNotNone(emotion.secondary_emotions)
        self.assertGreater(len(emotion.secondary_emotions), 1)

if __name__ == '__main__':
    unittest.main()
