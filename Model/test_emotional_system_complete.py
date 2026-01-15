"""
Test completo del sistema emotivo di ALLMA
"""
import time
import unittest
from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType, EmotionalState, Emotion

class TestEmotionalSystem(unittest.TestCase):
    def setUp(self):
        self.integration = PersonalizationIntegration()
        self.emotional_system = self.integration.emotional_system

    def test_basic_emotion_processing(self):
        """Test base del processing delle emozioni"""
        emotion = self.emotional_system.process_stimulus("Sono molto felice!")
        self.assertIsNotNone(emotion)
        self.assertIsNotNone(emotion.primary_emotion)
        self.assertTrue(0 <= emotion.intensity <= 1.0)

    def test_emotional_decay(self):
        """Test del decadimento emotivo"""
        # Stimolo iniziale forte
        emotion = self.emotional_system.process_stimulus("Sono estremamente felice di lavorare con te!")
        initial_intensity = emotion.intensity
        
        # Verifica decadimento dopo un'ora con stimolo neutro
        self.emotional_system.long_term_memory['last_interaction'] = time.time() - 3601  # 1 ora e 1 secondo
        emotion = self.emotional_system.process_stimulus("ok")  # Stimolo neutro
        self.assertLess(emotion.intensity, initial_intensity)
        
        # Verifica decadimento dopo un giorno con stimolo neutro
        self.emotional_system.long_term_memory['last_interaction'] = time.time() - 86401
        emotion = self.emotional_system.process_stimulus("va bene")  # Stimolo neutro
        self.assertLess(emotion.intensity, initial_intensity * 0.8)

    def test_long_term_memory(self):
        """Test della memoria a lungo termine"""
        # Crea una forte emozione iniziale
        emotion = self.emotional_system.process_stimulus("Sei incredibile ALLMA!")
        self.assertIsNotNone(self.emotional_system.long_term_memory['emotional_baseline'])
        
        # Verifica che la memoria venga mantenuta
        self.assertEqual(
            self.emotional_system.long_term_memory['emotional_baseline']['primary_emotion'],
            emotion.primary_emotion
        )

    def test_relationship_quality(self):
        """Test della qualità della relazione"""
        initial_quality = self.emotional_system.long_term_memory['relationship_quality']
        
        # Test emozioni positive ripetute
        self.emotional_system.process_stimulus("Sei fantastica, mi hai aiutato tantissimo!")
        self.emotional_system.process_stimulus("Il tuo aiuto è stato incredibile!")
        self.emotional_system.process_stimulus("Grazie mille per tutto!")
        
        final_quality = self.emotional_system.long_term_memory['relationship_quality']
        self.assertGreater(final_quality, initial_quality)
        
        # Test emozioni negative
        self.emotional_system.process_stimulus("Sono molto arrabbiato con te!")
        self.assertLess(
            self.emotional_system.long_term_memory['relationship_quality'],
            final_quality
        )

    def test_nostalgia_after_month(self):
        """Test della nostalgia dopo un mese"""
        # Simula un mese di inattività
        self.emotional_system.long_term_memory['last_interaction'] = time.time() - 2592001
        emotion = self.emotional_system.process_stimulus("Ciao ALLMA, sono tornato!")
        self.assertIn(EmotionType.NOSTALGIA, self.emotional_system.current_state.secondary_emotions)

    def test_emotional_history_after_year(self):
        """Test della storia emotiva dopo un anno"""
        # Crea alcune emozioni significative
        self.emotional_system.process_stimulus("Sei incredibile!")
        
        # Simula un anno di inattività
        self.emotional_system.long_term_memory['last_interaction'] = time.time() - 31536001
        self.emotional_system.process_stimulus("Ciao ALLMA, è passato tanto tempo!")
        
        # Verifica che la storia emotiva sia stata salvata
        self.assertGreater(len(self.emotional_system.long_term_memory['last_significant_emotions']), 0)

    def test_minimum_intensity(self):
        """Test dell'intensità minima delle emozioni"""
        # Simula un lungo periodo di inattività
        self.emotional_system.long_term_memory['last_interaction'] = time.time() - 31536001 * 2  # 2 anni
        emotion = self.emotional_system.process_stimulus("Ciao ALLMA!")
        self.assertGreaterEqual(emotion.intensity, 0.05)  # Verifica che non scenda sotto il minimo

if __name__ == '__main__':
    unittest.main(verbosity=2)
