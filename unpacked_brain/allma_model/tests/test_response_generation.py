"""
Test del sistema di generazione delle risposte
"""

import unittest
from datetime import datetime
from allma_model.incremental_learning.response_generation_system import (
    ResponseGenerator, ResponseStyle, ResponseTemplate,
    EmotionType, EmotionalSystem, PatternRecognitionSystem, UserProfile
)

class TestResponseGeneration(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()
        self.pattern_recognition = PatternRecognitionSystem()
        self.response_generator = ResponseGenerator(
            self.emotional_system,
            self.pattern_recognition
        )
        self.user_profile = UserProfile("test_user")

    def test_template_matching(self):
        """Test della selezione dei template appropriati"""
        template = ResponseTemplate(
            style=ResponseStyle.FORMAL,
            patterns=["Test {action}"],
            context_requirements={"action"},
            emotion_compatibility={EmotionType.NEUTRAL},
            min_formality=0.5,
            max_formality=0.8,
            technical_level=0.6
        )
        
        # Test match contesto
        self.assertTrue(template.matches_context({"action": "test"}))
        self.assertFalse(template.matches_context({"wrong": "test"}))
        
        # Test match emozione
        self.assertTrue(template.matches_emotion(EmotionType.NEUTRAL))
        self.assertFalse(template.matches_emotion(EmotionType.JOY))
        
        # Test match stile
        self.assertTrue(template.matches_style(0.6, 0.5))
        self.assertFalse(template.matches_style(0.9, 0.5))

    def test_response_generation(self):
        """Test della generazione delle risposte"""
        context = {
            "intent": "greeting",
            "action": "salutare",
            "technical_detail": "analisi completata",
            "data": "risultati",
            "emotion": "felicità",
            "situation": "successo"
        }
        
        # Test generazione con profilo formale
        self.user_profile.update_from_interaction({
            "formality_feedback": 0.8,
            "technical_feedback": 0.7
        })
        response = self.response_generator.generate_response(
            context, self.user_profile, EmotionType.NEUTRAL
        )
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_style_adaptation(self):
        """Test dell'adattamento dello stile"""
        # Feedback positivo per stile formale
        self.response_generator.adapt_to_feedback({
            "style_feedback": "FORMAL",
            "score": 1.0
        })
        
        # Verifica che il sistema si sia adattato
        self.assertGreater(
            self.response_generator.style_adaptation["FORMAL"],
            0
        )
        
        # Feedback negativo per stile tecnico
        self.response_generator.adapt_to_feedback({
            "style_feedback": "TECHNICAL",
            "score": -1.0
        })
        
        # Verifica che il sistema si sia adattato
        self.assertLess(
            self.response_generator.style_adaptation["TECHNICAL"],
            0
        )

    def test_context_memory(self):
        """Test della memoria del contesto"""
        context = {
            "topic": "test",
            "action": "verify"
        }
        
        # Genera una risposta e verifica che venga memorizzata
        response = self.response_generator.generate_response(
            context, self.user_profile
        )
        
        # Verifica che il contesto sia stato memorizzato
        self.assertIn("topic", self.response_generator.context_memory)
        self.assertIn("action", self.response_generator.context_memory)
        
        # Verifica che la cronologia sia limitata
        for _ in range(15):  # Più del limite di 10
            self.response_generator.generate_response(
                context, self.user_profile
            )
        
        # Verifica che la memoria mantenga solo le ultime 10 interazioni
        self.assertLessEqual(
            len(self.response_generator.context_memory["topic"]),
            10
        )

    def test_response_coherence(self):
        """Test della coerenza delle risposte"""
        context1 = {
            "intent": "greeting",
            "action": "salutare",
            "emotion": "felicità",
            "situation": "incontro"
        }
        
        context2 = {
            "intent": "greeting",
            "action": "salutare",
            "emotion": "tristezza",
            "situation": "addio"
        }
        
        # Genera risposte per contesti diversi
        response1 = self.response_generator.generate_response(
            context1, self.user_profile, EmotionType.JOY
        )
        response2 = self.response_generator.generate_response(
            context2, self.user_profile, EmotionType.SADNESS
        )
        
        # Verifica che le risposte siano diverse per contesti diversi
        self.assertNotEqual(response1, response2)
        
        # Verifica che le risposte siano coerenti con lo stesso contesto
        response3 = self.response_generator.generate_response(
            context1, self.user_profile, EmotionType.JOY
        )
        self.assertNotEqual(response1, response3)  # Dovrebbero variare ma essere coerenti

    def test_emotional_integration(self):
        """Test dell'integrazione con il sistema emotivo"""
        # Test con emozione esplicita
        context = {
            "emotion": "gioia",
            "situation": "successo",
            "intent": "congratulazioni"
        }
        
        response = self.response_generator.generate_response(
            context, self.user_profile, EmotionType.JOY
        )
        self.assertIsNotNone(response)
        
        # Test con emozione dal sistema emotivo
        self.emotional_system.process_stimulus("Sono molto felice!")
        response = self.response_generator.generate_response(
            context, self.user_profile
        )
        self.assertIsNotNone(response)

if __name__ == '__main__':
    unittest.main()
