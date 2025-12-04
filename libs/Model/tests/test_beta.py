import unittest
from Model.core.language_system import LanguageSystem
from Model.core.understanding_system import AdvancedUnderstandingSystem
from Model.core.response_system import AdvancedResponseSystem, EmotionalTone

class TestBetaSystem(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per ogni test."""
        self.language_system = LanguageSystem()

    def test_emotional_understanding_complex(self):
        """Test approfondito della comprensione emotiva."""
        test_cases = [
            ("Sono molto felice oggi!", EmotionalTone.POSITIVE),
            ("Mi sento davvero triste e solo", EmotionalTone.NEGATIVE),
            ("Sono preoccupato per l'esame", EmotionalTone.CONCERNED),
            ("Sono arrabbiato e deluso", EmotionalTone.NEGATIVE),
            ("Non sono per niente contento di questo", EmotionalTone.NEGATIVE),
            ("Mi sento ansioso ma anche speranzoso", EmotionalTone.CONCERNED),
        ]
        
        for input_text, expected_emotion in test_cases:
            response = self.language_system.process_input(input_text)
            self.assertEqual(
                response.understanding.emotional_tone,
                expected_emotion,
                f"Per '{input_text}' mi aspettavo {expected_emotion} ma ho ottenuto {response.understanding.emotional_tone}"
            )

    def test_learning_complex(self):
        """Test approfondito delle capacità di apprendimento."""
        # Sequenza di input per testare l'apprendimento
        inputs = [
            "Mi chiamo Marco e sono uno sviluppatore",
            "Lavoro con Java",
            "Mi piace programmare videogiochi",
            "Il mio gatto si chiama Luna",
            "È una gatta molto giocherellona",
            "Le piace dormire sul divano"
        ]
        
        # Concetti che ci aspettiamo vengano appresi
        expected_concepts = {
            'marco', 'sviluppatore', 'java', 'programmare', 'videogiochi',
            'gatto', 'luna', 'giocherellona', 'dormire', 'divano'
        }
        
        # Processa gli input
        learned_concepts = set()
        for input_text in inputs:
            response = self.language_system.process_input(input_text)
            for word in response.understanding.new_words:
                learned_concepts.add(word.lower())
        
        # Verifica l'apprendimento
        learning_ratio = len(learned_concepts.intersection(expected_concepts)) / len(expected_concepts)
        self.assertGreaterEqual(
            learning_ratio, 0.7,
            f"Il sistema ha appreso solo il {learning_ratio*100}% dei concetti attesi"
        )

    def test_context_maintenance_complex(self):
        """Test approfondito del mantenimento del contesto."""
        # Sequenza di input con contesto correlato
        inputs = [
            "Mi chiamo Alice",
            "Ho 25 anni"
        ]
        
        # Processa gli input
        context = {}
        for input_text in inputs:
            response = self.language_system.process_input(input_text)
            context = response.context
        
        # Verifica che le informazioni chiave siano mantenute nel contesto
        expected_words = {'alice', 'chiamo', 'anni'}
        context_words = set(word.lower() for word in context.get('entities', {}).keys())
        
        self.assertTrue(
            expected_words.issubset(context_words),
            f"Alcune parole del contesto sono state perse: {expected_words - context_words}"
        )

    def test_grammar_understanding_complex(self):
        """Test approfondito della comprensione grammaticale."""
        # Input con struttura grammaticale complessa
        input_text = "Il gatto nero mangia il pesce rosso"
        response = self.language_system.process_input(input_text)
        
        # Verifica che i ruoli grammaticali siano corretti
        components = response.understanding.components
        
        # Verifica che le parole chiave siano state identificate correttamente
        nouns = [comp.text.lower() for comp in components if comp.type == 'nome']
        expected_nouns = ['gatto', 'pesce']
        
        self.assertTrue(
            all(noun in nouns for noun in expected_nouns),
            f"Per '{input_text}', non tutti i valori attesi {expected_nouns} sono stati trovati in {nouns}"
        )

    def test_response_generation_complex(self):
        """Test approfondito della generazione delle risposte."""
        # Test di risposte a diversi tipi di input
        test_cases = [
            ("Ho capito!", ["prego", "disponibile", "piacere"]),
            ("Mille grazie!", ["prego", "disponibile", "piacere"])
        ]
        
        for input_text, expected_keywords in test_cases:
            response = self.language_system.process_input(input_text)
            response_text = response.response_text.lower()
            
            self.assertTrue(
                any(keyword in response_text for keyword in expected_keywords),
                f"La risposta '{response_text}' non contiene nessuna delle parole chiave attese {expected_keywords}"
            )

if __name__ == '__main__':
    unittest.main()
