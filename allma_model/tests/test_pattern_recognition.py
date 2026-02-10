"""
Test del sistema di riconoscimento pattern
"""

import unittest
from unittest.mock import Mock
import numpy as np
from datetime import datetime
from allma_model.incremental_learning.pattern_recognition_system import (
    PatternRecognitionSystem,
    Pattern,
    PatternMatch,
    Subtopic
)

class TestPatternRecognition(unittest.TestCase):
    def setUp(self):
        """Setup per i test."""
        self.system = PatternRecognitionSystem()
        if not hasattr(self.system, "nlp") or self.system.nlp is None:
            raise unittest.SkipTest("NLP non disponibile")
        # Reset delle keywords per ogni test
        self.system.sentiment_keywords = {
            'positive': {'contento', 'felice', 'bene', 'ottimo', 'eccellente', 'piace', 'positivo', 'funziona', 'successo'},
            'negative': {'male', 'pessimo', 'terribile', 'negativo', 'errore', 'problema', 'difficile', 'sbagliato', 'brutto'}
        }
        self.system.stemmed_positive = {self.system.stemmer.stem(word) for word in self.system.sentiment_keywords['positive']}
        self.system.stemmed_negative = {self.system.stemmer.stem(word) for word in self.system.sentiment_keywords['negative']}

    def test_behavior_recognition(self):
        # Test riconoscimento comportamentale
        text1 = "Mi sento molto frustrato quando questo succede"
        text2 = "Questa situazione mi fa arrabbiare"
        text3 = "Non mi piace quando accade questo"
        
        # Analizza i pattern comportamentali
        pattern1 = self.system.analyze_pattern(text1)
        pattern2 = self.system.analyze_pattern(text2)
        pattern3 = self.system.analyze_pattern(text3)
        
        # Verifica che i pattern siano stati riconosciuti correttamente
        self.assertEqual(pattern1.category, "negative_emotion")
        self.assertEqual(pattern2.category, "negative_emotion")
        self.assertEqual(pattern3.category, "negative_emotion")
        
        # Verifica la similarità tra i pattern
        similarity = self.system.calculate_pattern_similarity(pattern1, pattern2)
        self.assertGreater(similarity, 0.7)  # Alta similarità attesa
        
    def test_theme_analysis(self):
        """Test analisi temi"""
        texts = [
            "Mi piace molto programmare in Python",
            "Java è un ottimo linguaggio di programmazione",
            "Sto imparando a programmare in C++"
        ]
        
        # Analizza i temi
        themes = self.system.analyze_themes(texts)
        
        # Verifica che il tema principale sia stato identificato
        self.assertTrue(any(t.category == 'programming' or t.category == 'programmazione' for t in themes))
        
        # Verifica che ci sia almeno un tema con confidence alta
        self.assertTrue(any(t.confidence >= 0.5 for t in themes))
        
    def test_sentiment_analysis(self):
        # Test analisi del sentiment
        text1 = "Sono molto contento del risultato!"
        text2 = "Non mi piace per niente questo approccio."
        text3 = "Il sistema funziona come previsto."
        
        # Analizza il sentiment
        sentiment1 = self.system.analyze_sentiment(text1)
        sentiment2 = self.system.analyze_sentiment(text2)
        sentiment3 = self.system.analyze_sentiment(text3)
        
        # Stampa i risultati
        print(f"\nText 1: {text1}")
        print(f"Sentiment 1: {sentiment1.category} (confidence: {sentiment1.confidence})")
        print(f"Keywords 1: {sentiment1.keywords}")
        
        print(f"\nText 2: {text2}")
        print(f"Sentiment 2: {sentiment2.category} (confidence: {sentiment2.confidence})")
        print(f"Keywords 2: {sentiment2.keywords}")
        
        print(f"\nText 3: {text3}")
        print(f"Sentiment 3: {sentiment3.category} (confidence: {sentiment3.confidence})")
        print(f"Keywords 3: {sentiment3.keywords}")
        
        # Verifica i valori di sentiment
        self.assertEqual(sentiment1.category, "positive")  # Positivo
        self.assertEqual(sentiment2.category, "negative")  # Negativo
        self.assertEqual(sentiment3.category, "positive")  # Positivo
        
    def test_pattern_learning(self):
        # Test apprendimento pattern
        text = "Mi piace molto programmare"
        
        # Apprende un nuovo pattern
        pattern = self.system.learn_pattern(text, "test_category")
        
        # Verifica che il pattern sia stato appreso
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.category, "test_category")
        
        # Verifica il riconoscimento del pattern
        similar_patterns = self.system._find_similar_patterns(
            pattern.embedding,
            self.system._extract_linguistic_features(self.system.nlp(text)),
            0.5
        )
        self.assertGreater(len(similar_patterns), 0)
        
    def test_pattern_evolution(self):
        # Test evoluzione dei pattern nel tempo
        text1 = "Mi piace programmare"
        text2 = "Adoro scrivere codice"
        
        # Apprende pattern iniziale
        pattern = self.system.learn_pattern(text1, "programming")
        initial_confidence = pattern.confidence
        
        # Aggiorna il pattern con nuovo esempio
        pattern = self.system.learn_pattern(text2, "programming")
        
        # Verifica che il pattern si sia evoluto
        self.assertNotEqual(pattern.confidence, initial_confidence)
        
    def test_pattern_validation(self):
        # Test validazione pattern
        text = "Mi piace programmare"
        pattern = self.system.learn_pattern(text, "test_category")
        
        # Cerca pattern simili
        similar_patterns = self.system._find_similar_patterns(
            pattern.embedding,
            self.system._extract_linguistic_features(self.system.nlp(text)),
            0.5
        )
        
        # Verifica i risultati della validazione
        self.assertGreater(len(similar_patterns), 0)
        self.assertGreater(similar_patterns[0].confidence, 0.5)
        
    def test_text_similarity(self):
        """Test per verificare la similarità tra testi"""
        # Inizializza un sistema reale invece del mock per questo test
        system = PatternRecognitionSystem()
        
        # Test con frasi molto simili
        text1 = "Mi piace molto programmare in Python"
        text2 = "Mi piace programmare usando Python"
        similarity = system.calculate_similarity(text1, text2)
        self.assertGreaterEqual(similarity, 0.5, "Frasi simili dovrebbero avere similarità >= 0.5")
        
        # Test con frasi correlate ma non identiche
        text3 = "Python è un linguaggio di programmazione"
        text4 = "Java è un linguaggio di programmazione"
        similarity = system.calculate_similarity(text3, text4)
        self.assertGreaterEqual(similarity, 0.3, "Frasi correlate dovrebbero avere similarità >= 0.3")
        
        # Test con frasi diverse
        text5 = "Mi piace il gelato alla fragola"
        text6 = "Il tempo oggi è molto bello"
        similarity = system.calculate_similarity(text5, text6)
        self.assertLess(similarity, 0.3, "Frasi diverse dovrebbero avere similarità < 0.3")
        
    def test_topic_extraction(self):
        """Test per l'estrazione dei topic dai testi"""
        # Inizializza un sistema reale invece del mock per questo test
        system = PatternRecognitionSystem()
        
        # Test con testi sulla programmazione
        texts = [
            "Mi piace programmare in Python e Java",
            "La programmazione è un'attività creativa",
            "Sto imparando a sviluppare software"
        ]
        
        # Analizza i temi
        themes = system.analyze_themes(texts)
        
        # Verifica che il tema principale sia stato identificato
        programming_themes = [t for t in themes if t.category == 'programmazione']
        self.assertTrue(len(programming_themes) > 0, "Il tema 'programmazione' dovrebbe essere identificato")
        self.assertGreaterEqual(programming_themes[0].confidence, 0.5, "Il tema dovrebbe avere confidence >= 0.5")
        
        # Verifica che le parole chiave siano state estratte
        expected_keywords = {'programmare', 'programmazione', 'python', 'java', 'sviluppare'}  # Parole originali
        actual_keywords = set()
        for theme in themes:
            actual_keywords.update(theme.keywords)
        
        self.assertTrue(
            any(keyword in actual_keywords for keyword in expected_keywords),
            f"Almeno alcune delle parole chiave attese {expected_keywords} dovrebbero essere presenti in {actual_keywords}"
        )
        
        # Test con testi sull'apprendimento
        texts = [
            "Sto studiando nuovi concetti",
            "L'apprendimento è un processo continuo",
            "Mi piace imparare cose nuove"
        ]
        
        # Analizza i temi
        themes = system.analyze_themes(texts)
        
        # Verifica che il tema dell'apprendimento sia stato identificato
        learning_themes = [t for t in themes if t.category == 'apprendimento']
        self.assertTrue(len(learning_themes) > 0, "Il tema 'apprendimento' dovrebbe essere identificato")
        self.assertGreaterEqual(learning_themes[0].confidence, 0.5, "Il tema dovrebbe avere confidence >= 0.5")
        
if __name__ == '__main__':
    unittest.main()
