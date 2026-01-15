"""Test per il sistema di analisi preferenze utente."""

import unittest
from datetime import datetime
from allma_model.user_system.user_preferences import UserPreferenceAnalyzer, LearningStyle, ResponseStyle

class TestUserPreferences(unittest.TestCase):
    """Test per UserPreferenceAnalyzer."""
    
    def setUp(self):
        """Setup per i test."""
        self.analyzer = UserPreferenceAnalyzer()
        self.test_user = "test_user_123"
        
    def test_analyze_learning_style(self):
        """Test dell'analisi dello stile di apprendimento."""
        # Aggiungi interazioni di test
        interactions = [
            ("Mi puoi mostrare un esempio di codice?", "request_example"),
            ("Puoi spiegarmi il concetto in dettaglio?", "request_explanation"),
            ("Preferisco imparare passo dopo passo", "learning_preference"),
            ("Mi serve un esempio pratico", "request_example")
        ]
        
        for text, interaction_type in interactions:
            self.analyzer.record_interaction(
                self.test_user,
                text,
                interaction_type
            )
            
        # Analizza lo stile
        style = self.analyzer.analyze_learning_style(self.test_user)
        
        self.assertIsNotNone(style)
        self.assertEqual(style.primary_style, LearningStyle.KINESTHETIC)
        self.assertGreater(style.confidence, 0.0)
        
    def test_adapt_response_style(self):
        """Test dell'adattamento dello stile di risposta."""
        # Aggiungi interazioni per stile pratico
        interactions = [
            "Mi puoi mostrare un esempio di codice?",
            "Vorrei vedere del codice pratico",
            "Preferisco esempi di codice",
            "Mi serve un esempio concreto"
        ]
        
        for text in interactions:
            self.analyzer.record_interaction(
                self.test_user,
                text,
                "request_example"
            )
        
        # Test con stile pratico
        style = self.analyzer.adapt_response_style(
            self.test_user,
            "Come funziona un ciclo for?"
        )
        
        self.assertEqual(style.format, ResponseStyle.CODE_FIRST)
        self.assertTrue(style.include_examples)
        
        # Test con stile teorico
        self.analyzer.update_user_preference(
            self.test_user,
            LearningStyle.THEORETICAL
        )
        
        style = self.analyzer.adapt_response_style(
            self.test_user,
            "Come funziona l'ereditarietà?"
        )
        
        self.assertEqual(style.format, ResponseStyle.CONCEPT_FIRST)
        self.assertTrue(style.include_references)
        
    def test_track_topic_preferences(self):
        """Test del tracking delle preferenze per topic."""
        # Aggiungi interazioni con topic
        interactions = [
            ("Python è il mio linguaggio preferito", "language_preference", "python"),
            ("Mi piace molto il machine learning", "topic_interest", "ml"),
            ("Python è fantastico", "positive_feedback", "python")
        ]
        
        for text, interaction_type, topic in interactions:
            self.analyzer.record_topic_interaction(
                self.test_user,
                text,
                interaction_type,
                topic
            )
            
        # Verifica preferenze
        preferences = self.analyzer.get_topic_preferences(self.test_user)
        
        self.assertIn("python", preferences)
        self.assertGreater(preferences["python"], preferences["ml"])
        
    def test_edge_cases(self):
        """Test dei casi limite."""
        # Test con utente inesistente
        style = self.analyzer.analyze_learning_style("nonexistent_user")
        self.assertEqual(style.primary_style, LearningStyle.BALANCED)
        
        # Test con nessuna interazione
        style = self.analyzer.adapt_response_style(
            self.test_user,
            "Test query"
        )
        self.assertEqual(style.format, ResponseStyle.BALANCED)
        
if __name__ == '__main__':
    unittest.main()
