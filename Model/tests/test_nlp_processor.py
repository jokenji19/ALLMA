import unittest
from datetime import datetime
from ..core.nlp_processor import NLPProcessor

class TestNLPProcessor(unittest.TestCase):
    def setUp(self):
        """Inizializza il processor per ogni test"""
        self.processor = NLPProcessor()

    def test_text_preprocessing(self):
        """Test del preprocessing del testo"""
        # Test con testo normale
        text = "Ciao, come stai? Io sto MOLTO bene!!!"
        processed = self.processor.preprocess_text(text)
        self.assertIsInstance(processed, str)
        self.assertNotEqual(processed, text)  # Dovrebbe essere normalizzato
        
        # Test con testo multilingua
        text_multi = "Hello! Ciao! ¡Hola!"
        processed_multi = self.processor.preprocess_text(text_multi)
        self.assertIsInstance(processed_multi, str)
        
        # Test con caratteri speciali
        text_special = "email@test.com #hashtag @mention"
        processed_special = self.processor.preprocess_text(text_special)
        self.assertIsInstance(processed_special, str)

    def test_language_detection(self):
        """Test del rilevamento della lingua"""
        # Test italiano
        it_text = "Questo è un testo in italiano"
        lang_it = self.processor.detect_language(it_text)
        self.assertEqual(lang_it, 'it')
        
        # Test inglese
        en_text = "This is an English text"
        lang_en = self.processor.detect_language(en_text)
        self.assertEqual(lang_en, 'en')
        
        # Test spagnolo
        es_text = "Este es un texto en español"
        lang_es = self.processor.detect_language(es_text)
        self.assertEqual(lang_es, 'es')

    def test_sentiment_analysis(self):
        """Test dell'analisi del sentiment"""
        # Test sentiment positivo
        pos_text = "Sono molto felice e soddisfatto!"
        pos_sentiment = self.processor.analyze_sentiment(pos_text)
        self.assertGreater(pos_sentiment['positive'], 0.5)
        
        # Test sentiment negativo
        neg_text = "Sono molto deluso e arrabbiato."
        neg_sentiment = self.processor.analyze_sentiment(neg_text)
        self.assertGreater(neg_sentiment['negative'], 0.5)
        
        # Test sentiment neutro
        neu_text = "Oggi è giovedì."
        neu_sentiment = self.processor.analyze_sentiment(neu_text)
        self.assertGreater(neu_sentiment['neutral'], 0.5)

    def test_entity_recognition(self):
        """Test del riconoscimento delle entità"""
        text = "Mario Rossi lavora per Google a Milano"
        entities = self.processor.extract_entities(text)
        
        self.assertIn('person', entities)
        self.assertIn('organization', entities)
        self.assertIn('location', entities)
        
        self.assertIn('Mario Rossi', entities['person'])
        self.assertIn('Google', entities['organization'])
        self.assertIn('Milano', entities['location'])

    def test_topic_extraction(self):
        """Test dell'estrazione dei topic"""
        text = """L'intelligenza artificiale sta rivoluzionando il modo in cui 
                 lavoriamo. Machine learning e deep learning sono tecnologie chiave."""
        
        topics = self.processor.extract_topics(text)
        
        self.assertIsInstance(topics, list)
        self.assertTrue(any('intelligenza artificiale' in topic.lower() for topic in topics))
        self.assertTrue(any('machine learning' in topic.lower() for topic in topics))

    def test_text_similarity(self):
        """Test della similarità testuale"""
        text1 = "Il gatto dorme sul divano"
        text2 = "Un gatto sta dormendo sul divano"
        text3 = "Il cane corre nel parco"
        
        # Test similarità alta
        sim_high = self.processor.compute_similarity(text1, text2)
        self.assertGreater(sim_high, 0.8)
        
        # Test similarità bassa
        sim_low = self.processor.compute_similarity(text1, text3)
        self.assertLess(sim_low, 0.5)

    def test_intent_classification(self):
        """Test della classificazione degli intent"""
        # Test domanda
        question = "Qual è la capitale dell'Italia?"
        intent_q = self.processor.classify_intent(question)
        self.assertEqual(intent_q, 'question')
        
        # Test affermazione
        statement = "Roma è la capitale dell'Italia."
        intent_s = self.processor.classify_intent(statement)
        self.assertEqual(intent_s, 'statement')
        
        # Test comando
        command = "Mostrami la mappa dell'Italia."
        intent_c = self.processor.classify_intent(command)
        self.assertEqual(intent_c, 'command')

    def test_text_summarization(self):
        """Test della summarizzazione del testo"""
        long_text = """
        L'intelligenza artificiale (IA) è la simulazione dell'intelligenza umana 
        nei computer programmati per pensare e apprendere. Il termine specifico 
        di IA si applica quando una macchina imita funzioni cognitive associate 
        alla mente umana, come l'apprendimento e la risoluzione dei problemi.
        Un aspetto fondamentale dell'IA è il machine learning, che si concentra 
        sullo sviluppo di programmi informatici in grado di accedere ai dati e 
        di apprendere autonomamente.
        """
        
        summary = self.processor.summarize_text(long_text)
        
        self.assertIsInstance(summary, str)
        self.assertLess(len(summary), len(long_text))
        self.assertIn('intelligenza artificiale', summary.lower())

    def test_error_handling(self):
        """Test della gestione degli errori"""
        # Test con input vuoto
        with self.assertRaises(ValueError):
            self.processor.preprocess_text("")
            
        # Test con input None
        with self.assertRaises(TypeError):
            self.processor.detect_language(None)
            
        # Test con testo troppo corto
        result = self.processor.extract_topics("Ciao")
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
