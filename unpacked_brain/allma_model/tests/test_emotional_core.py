"""Test per il sistema emotivo avanzato."""

import unittest
from unittest.mock import patch, MagicMock
from allma_model.emotional_system.emotional_core import EmotionalCore, EmotionalState

class TestEmotionalCore(unittest.TestCase):
    """Test suite per EmotionalCore."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock del classifier per i test
        self.emotion_patcher = patch('transformers.pipeline')
        self.mock_pipeline = self.emotion_patcher.start()
        
        # Configura il mock per restituire emozioni di test
        def mock_classifier(text):
            if not text:
                return [[{
                    'label': 'neutral',
                    'score': 0.9
                }, {
                    'label': 'joy',
                    'score': 0.05
                }, {
                    'label': 'sadness',
                    'score': 0.05
                }]]
            
            return [[{
                'label': 'joy',
                'score': 0.8
            }, {
                'label': 'neutral',
                'score': 0.1
            }, {
                'label': 'sadness',
                'score': 0.1
            }]]
        
        self.mock_pipeline.return_value = mock_classifier
        
        # Crea EmotionalCore con il mock
        self.emotional_core = EmotionalCore()
        self.emotional_core.emotion_classifier = mock_classifier
        
        self.test_user = "test_user_123"
        
    def tearDown(self):
        """Cleanup dopo i test."""
        self.emotion_patcher.stop()
        
    def test_detect_emotion(self):
        """Test del rilevamento emozioni."""
        # Test rilevamento base
        emotion = self.emotional_core.detect_emotion(
            "Sono molto felice oggi!",
            {"context": "greeting"}
        )
        
        self.assertIsInstance(emotion, EmotionalState)
        self.assertEqual(emotion.primary_emotion, "joy")
        self.assertGreater(emotion.confidence, 0.0)
        self.assertGreater(len(emotion.secondary_emotions), 0)
        
        # Test con testo vuoto
        emotion = self.emotional_core.detect_emotion("")
        self.assertEqual(emotion.primary_emotion, "neutral")
        
        # Test con contesto None
        emotion = self.emotional_core.detect_emotion("Test", None)
        self.assertIsInstance(emotion, EmotionalState)
        
    def test_generate_emotional_response(self):
        """Test della generazione risposta emotiva."""
        # Crea uno stato emotivo di test
        emotion = EmotionalState(
            primary_emotion="joy",
            confidence=0.9,
            secondary_emotions={"neutral": 0.1},
            intensity=0.8,
            context={}
        )
        
        # Test generazione base
        response = self.emotional_core.generate_emotional_response(
            emotion,
            "Ecco la risposta"
        )
        
        self.assertIn("felice", response.lower())
        self.assertIn("Ecco la risposta", response)
        
        # Test con emozione neutra
        emotion.primary_emotion = "neutral"
        response = self.emotional_core.generate_emotional_response(
            emotion,
            "Test neutro"
        )
        self.assertEqual(response, "Test neutro")
        
        # Test con alta intensità
        emotion.intensity = 0.9
        response = self.emotional_core.generate_emotional_response(
            emotion,
            "Test intenso"
        )
        self.assertIn("TEST INTENSO", response.upper())
        
    def test_track_emotional_state(self):
        """Test del tracking dello stato emotivo."""
        # Crea alcuni stati emotivi
        emotions = [
            EmotionalState("joy", 0.8, {}, 0.7, {}),
            EmotionalState("sadness", 0.6, {}, 0.5, {}),
            EmotionalState("joy", 0.9, {}, 0.8, {})
        ]
        
        # Traccia gli stati
        for emotion in emotions:
            self.emotional_core.track_emotional_state(
                self.test_user,
                emotion
            )
            
        # Verifica il tracking
        self.assertIn(self.test_user, self.emotional_core.emotion_history)
        self.assertEqual(
            len(self.emotional_core.emotion_history[self.test_user]),
            3
        )
        
        # Test limite massimo stati
        for _ in range(100):
            self.emotional_core.track_emotional_state(
                self.test_user,
                emotions[0]
            )
            
        self.assertEqual(
            len(self.emotional_core.emotion_history[self.test_user]),
            100
        )
        
    def test_analyze_emotional_trends(self):
        """Test dell'analisi trend emotivi."""
        # Crea una sequenza di stati emotivi
        emotions = [
            EmotionalState("joy", 0.8, {}, 0.7, {}),
            EmotionalState("joy", 0.7, {}, 0.6, {}),
            EmotionalState("sadness", 0.6, {}, 0.5, {})
        ]
        
        for emotion in emotions:
            self.emotional_core.track_emotional_state(
                self.test_user,
                emotion
            )
            
        # Analizza trend
        trends = self.emotional_core.analyze_emotional_trends(self.test_user)
        
        self.assertEqual(trends['dominant_emotion'], 'joy')
        self.assertGreater(trends['average_intensity'], 0.0)
        self.assertIn('joy', trends['emotion_distribution'])
        self.assertIn(trends['intensity_trend'], ['increasing', 'decreasing', 'stable'])
        
        # Test con utente inesistente
        trends = self.emotional_core.analyze_emotional_trends("nonexistent")
        self.assertIsNone(trends['dominant_emotion'])
        self.assertEqual(trends['average_intensity'], 0.0)
        
    def test_edge_cases(self):
        """Test dei casi limite."""
        # Test con errore nel classifier
        self.emotional_core.emotion_classifier = MagicMock(side_effect=Exception("Test error"))
        emotion = self.emotional_core.detect_emotion("Test error")
        self.assertEqual(emotion.primary_emotion, "neutral")
        self.assertEqual(emotion.confidence, 0.0)
        self.assertEqual(len(emotion.secondary_emotions), 0)
        self.assertEqual(emotion.intensity, 0.0)
        
        # Test con risposta vuota
        emotion = EmotionalState("joy", 0.8, {}, 0.7, {})
        response = self.emotional_core.generate_emotional_response(emotion, "")
        self.assertNotEqual(response, "")
        
        # Test con contesto invalido
        emotion = self.emotional_core.detect_emotion("Test", {"invalid": None})
        self.assertIsInstance(emotion, EmotionalState)
        
        # Test analisi trend con pochi dati
        self.emotional_core.track_emotional_state(
            "new_user",
            EmotionalState("joy", 0.8, {}, 0.7, {})
        )
        trends = self.emotional_core.analyze_emotional_trends("new_user")
        self.assertEqual(trends['intensity_trend'], 'stable')

if __name__ == '__main__':
    unittest.main()
