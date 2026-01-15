"""Test per il sistema di generazione risposte contestuali."""

import unittest
from datetime import datetime
from Model.response_system.contextual_response import (
    ContextualResponseGenerator,
    ResponseContext,
    TechnicalLevel,
    ResponseFormat
)
from Model.user_system.user_preferences import LearningStyle, LearningPreference

class TestContextualResponse(unittest.TestCase):
    """Test per ContextualResponseGenerator."""
    
    def setUp(self):
        """Setup per i test."""
        self.generator = ContextualResponseGenerator()
        self.test_user = "test_user_123"
        
    def test_generate_response(self):
        """Test della generazione di risposte."""
        # Configura preferenze utente
        user_preferences = LearningPreference(
            primary_style=LearningStyle.THEORETICAL,
            confidence=0.8,
            last_updated=datetime.now()
        )
        
        # Crea contesto
        context = ResponseContext(
            user_id=self.test_user,
            current_topic="python basics",
            technical_level=TechnicalLevel.INTERMEDIATE,
            conversation_history=[],
            user_preferences=user_preferences
        )
        
        # Genera risposta
        response = self.generator.generate_response(
            "Come funziona un ciclo for?",
            context
        )
        
        # Verifica che la risposta sia appropriata
        self.assertIsInstance(response.content, str)
        self.assertTrue(len(response.content) > 0)
        self.assertEqual(response.technical_level, TechnicalLevel.INTERMEDIATE)
        
    def test_adapt_technical_level(self):
        """Test dell'adattamento del livello tecnico."""
        # Test con utente principiante
        context = ResponseContext(
            user_id=self.test_user,
            current_topic="python basics",
            technical_level=TechnicalLevel.BEGINNER,
            conversation_history=[],
            user_preferences=None
        )
        
        response = self.generator.generate_response(
            "Cos'è una variabile?",
            context
        )
        
        self.assertEqual(response.technical_level, TechnicalLevel.BEGINNER)
        self.assertFalse(response.includes_advanced_concepts)
        
        # Test con utente avanzato
        context.technical_level = TechnicalLevel.ADVANCED
        response = self.generator.generate_response(
            "Spiegami il decorator pattern",
            context
        )
        
        self.assertEqual(response.technical_level, TechnicalLevel.ADVANCED)
        self.assertTrue(response.includes_advanced_concepts)
        
    def test_context_awareness(self):
        """Test della consapevolezza del contesto."""
        # Crea storia conversazione
        context = ResponseContext(
            user_id=self.test_user,
            current_topic="python functions",
            technical_level=TechnicalLevel.INTERMEDIATE,
            conversation_history=[
                "Come si definisce una funzione?",
                "def my_function():",
                "Come posso aggiungere parametri?"
            ],
            user_preferences=None
        )
        
        # La risposta dovrebbe riferirsi al contesto precedente
        response = self.generator.generate_response(
            "Puoi farmi un altro esempio?",
            context
        )
        
        self.assertIn("parametr", response.content.lower())
        self.assertTrue(response.references_previous_context)
        
    def test_edge_cases(self):
        """Test dei casi limite."""
        # Test con contesto vuoto
        context = ResponseContext(
            user_id=self.test_user,
            current_topic="",
            technical_level=TechnicalLevel.INTERMEDIATE,
            conversation_history=[],
            user_preferences=None
        )
        
        response = self.generator.generate_response(
            "Aiuto generico",
            context
        )
        
        self.assertEqual(response.format, ResponseFormat.BALANCED)
        self.assertEqual(response.technical_level, TechnicalLevel.INTERMEDIATE)
        
        # Test con query non valida
        response = self.generator.generate_response(
            "",
            context
        )
        
        self.assertFalse(response.is_valid)
        self.assertIn("error", response.content.lower())
        
if __name__ == '__main__':
    unittest.main()
