import unittest
from datetime import datetime
from ..core.cognitive_processor import EnhancedCognitiveProcessor

class TestEnhancedCognitiveProcessor(unittest.TestCase):
    def setUp(self):
        """Inizializza il processor per ogni test"""
        self.processor = EnhancedCognitiveProcessor()

    def test_process_input(self):
        """Test elaborazione input"""
        # Test input testuale con contesto
        text_input = "Mi piace programmare in Python e sviluppare software"
        context = {
            'previous_understanding': 0.8,
            'topic_history': ['programmazione', 'tecnologia']
        }
        
        result = self.processor.process_input(text_input, context=context)
        
        self.assertIsNotNone(result)
        self.assertIn('topics', result)
        self.assertIn('complexity', result)
        self.assertIn('understanding_level', result)
        self.assertIn('concepts', result)
        self.assertIn('context_analysis', result)
        self.assertIn('multimodal_confidence', result)

    def test_extract_topics(self):
        """Test estrazione topics"""
        # Test con topic di programmazione
        text = "Sto sviluppando un programma in Python per debuggare il codice"
        topics = self.processor.extract_topics(text)
        self.assertIn('programmazione', topics)
        
        # Test con topic di emozioni
        text = "Provo una forte emozione e il mio stato d'animo è molto positivo"
        topics = self.processor.extract_topics(text)
        self.assertIn('emozioni', topics)

    def test_extract_concepts(self):
        """Test estrazione concetti"""
        text = "La funzione implementa un loop per l'analisi dei dati"
        concepts = self.processor.extract_concepts(text)
        
        # Verifica che vengano trovati i concetti di programmazione
        found_concepts = [concept[0] for concept in concepts]
        self.assertTrue(any(concept in ['funzione', 'loop'] for concept in found_concepts))
        
        # Verifica il formato dei concetti
        for concept in concepts:
            self.assertEqual(len(concept), 3)  # (termine, tipo, confidenza)
            self.assertIsInstance(concept[2], float)
            self.assertGreaterEqual(concept[2], self.processor.concept_confidence_threshold)

    def test_calculate_concept_confidence(self):
        """Test calcolo confidenza concetti"""
        text = "Python è un linguaggio di programmazione molto potente"
        confidence = self.processor._calculate_concept_confidence("Python", text)
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_analyze_complexity(self):
        """Test analisi complessità"""
        # Test testo semplice
        simple_text = "Ciao come stai?"
        simple_complexity = self.processor._analyze_complexity(simple_text)
        
        # Test testo complesso
        complex_text = """L'implementazione dell'algoritmo di machine learning 
                         richiede una profonda comprensione dei paradigmi di 
                         programmazione object-oriented e delle strutture dati avanzate."""
        complex_complexity = self.processor._analyze_complexity(complex_text)
        
        self.assertGreater(complex_complexity, simple_complexity)

    def test_multimodal_confidence(self):
        """Test confidenza multimodale"""
        concepts = [
            ("Python", "programmazione.linguaggi", 0.8),
            ("loop", "programmazione.concetti", 0.7)
        ]
        
        context_analysis = {
            'text_analysis': {'confidence': 0.9},
            'image_analysis': {'confidence_scores': [0.8, 0.7, 0.9]}
        }
        
        confidence = self.processor._calculate_multimodal_confidence(
            concepts, context_analysis)
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_error_handling(self):
        """Test gestione errori"""
        # Test con input None
        with self.assertRaises(AttributeError):
            self.processor.extract_concepts(None)
            
        # Test con testo vuoto
        empty_result = self.processor.extract_topics("")
        self.assertEqual(empty_result, [])

if __name__ == '__main__':
    unittest.main()
