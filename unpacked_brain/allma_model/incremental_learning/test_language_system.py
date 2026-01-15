import unittest
from language_system import LanguageSystem
import locale

class TestLanguageSystem(unittest.TestCase):
    def setUp(self):
        self.lang_system = LanguageSystem()

    def test_language_initialization(self):
        """Test dell'inizializzazione della lingua"""
        # Verifica che il sistema abbia una lingua predefinita
        self.assertIsNotNone(self.lang_system.current_language)
        
        # Verifica che la lingua sia tra quelle disponibili
        current_lang_code = list(self.lang_system.available_languages.keys())[
            list(self.lang_system.available_languages.values()).index(
                self.lang_system.current_language
            )
        ]
        self.assertIn(current_lang_code, ["en", "it", "es"])

    def test_language_switching(self):
        """Test del cambio lingua"""
        # Cambia in italiano
        self.lang_system.set_language("it")
        self.assertEqual(
            self.lang_system.get_response("greeting"),
            "Ciao! Come posso aiutarti oggi?"
        )

        # Cambia in inglese
        self.lang_system.set_language("en")
        self.assertEqual(
            self.lang_system.get_response("greeting"),
            "Hi! How can I help you today?"
        )

        # Cambia in spagnolo
        self.lang_system.set_language("es")
        self.assertEqual(
            self.lang_system.get_response("greeting"),
            "¡Hola! ¿Cómo puedo ayudarte hoy?"
        )

    def test_fallback_language(self):
        """Test del fallback su lingua non supportata"""
        # Prova a impostare una lingua non supportata
        self.lang_system.set_language("fr")  # francese non supportato
        # Dovrebbe fallback su inglese
        self.assertEqual(
            self.lang_system.get_response("greeting"),
            "Hi! How can I help you today?"
        )

    def test_cultural_context(self):
        """Test del contesto culturale"""
        # Test formato italiano (formale)
        self.lang_system.set_language("it")
        self.assertTrue(self.lang_system.current_language["context"].formal_style)
        
        # Test formato inglese (informale)
        self.lang_system.set_language("en")
        self.assertFalse(self.lang_system.current_language["context"].formal_style)

if __name__ == '__main__':
    unittest.main()
