import unittest
from datetime import datetime
from Model.core.extraction import InformationExtractor

class TestInformationExtractor(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per ogni test"""
        self.extractor = InformationExtractor()
        
    def test_pattern_extraction(self):
        """Testa l'estrazione di pattern comuni"""
        # Test con vari pattern
        test_text = """
        Contattami a test@email.com o al numero 123-456-7890.
        Visita il sito https://www.example.com
        Appuntamento il 15/01/2024 alle 14:30
        Il prezzo è 99.99
        """
        
        result = self.extractor._extract_patterns(test_text)
        
        # Verifica che tutti i pattern siano stati trovati
        self.assertIn('email', result)
        self.assertIn('phone', result)
        self.assertIn('url', result)
        self.assertIn('date', result)
        self.assertIn('time', result)
        self.assertIn('number', result)
        
        # Verifica i valori estratti
        self.assertEqual(result['email'], ['test@email.com'])
        self.assertEqual(result['phone'], ['123-456-7890'])
        self.assertEqual(result['url'], ['https://www.example.com'])
        self.assertEqual(result['date'], ['15/01/2024'])
        self.assertEqual(result['time'], ['14:30'])
        self.assertEqual(result['number'], ['99.99'])
        
    def test_entity_extraction(self):
        """Testa l'estrazione di entità"""
        test_text = "Mario Rossi lavora come sviluppatore presso Google a Milano"
        print(f"\nTesting entity extraction with text: {test_text}")
        
        result = self.extractor._extract_entities(test_text)
        print(f"Extraction result: {result}")
        
        # Verifica le categorie di entità
        self.assertIn('person', result)
        self.assertIn('location', result)
        self.assertIn('organization', result)
        
        # Verifica che le entità siano state categorizzate correttamente
        self.assertIn('Mario Rossi', result['person'])
        self.assertIn('Milano', result['location'])
        self.assertIn('Google', result['organization'])
        
    def test_text_extraction(self):
        """Testa l'estrazione completa da testo"""
        test_text = """
        Mario Rossi (mario.rossi@example.com)
        Sviluppatore Senior presso Google
        Milano, Italia
        Tel: 123-456-7890
        """
        
        result = self.extractor.extract_from_text(test_text)
        
        # Verifica i campi principali
        self.assertIn('patterns', result)
        self.assertIn('entities', result)
        self.assertIn('keywords', result)
        self.assertIn('sentiment', result)
        self.assertIn('timestamp', result)
        
        # Verifica che il timestamp sia recente
        self.assertIsInstance(result['timestamp'], datetime)
        self.assertGreater(result['timestamp'], datetime(2025, 1, 1))
        
    def test_relationship_extraction(self):
        """Testa l'estrazione di relazioni"""
        test_text = "Mario Rossi lavora presso Google. Anna Bianchi vive a Milano."
        
        relationships = self.extractor.extract_relationships(test_text)
        
        # Verifica che le relazioni siano state estratte
        self.assertTrue(len(relationships) > 0)
        
        # Verifica il formato delle relazioni
        for rel in relationships:
            self.assertEqual(len(rel), 3)  # (entità1, relazione, entità2)
            self.assertIsInstance(rel[0], str)
            self.assertIsInstance(rel[1], str)
            self.assertIsInstance(rel[2], str)
            
    def test_image_extraction(self):
        """Testa l'estrazione da immagini"""
        # Test con un'immagine di test
        test_image = "test_documents/test.png"
        
        try:
            result = self.extractor.extract_from_image(test_image)
            
            # Verifica i campi principali
            self.assertIn('ocr_text', result)
            self.assertIn('visual_objects', result)
            self.assertIn('scene_description', result)
            self.assertIn('text_in_image', result)
            self.assertIn('timestamp', result)
            
        except FileNotFoundError:
            self.skipTest("File di test non trovato")
            
    def test_invalid_input(self):
        """Testa la gestione di input non validi"""
        # Test con testo vuoto
        result_empty = self.extractor.extract_from_text("")
        self.assertEqual(result_empty['patterns'], {})
        self.assertEqual(result_empty['entities'], 
                        {category: [] for category in self.extractor.entity_categories})
        
        # Test con testo None
        with self.assertRaises(TypeError):
            self.extractor.extract_from_text(None)
            
        # Test con path immagine non esistente
        with self.assertRaises(FileNotFoundError):
            self.extractor.extract_from_image("nonexistent.png")
            
    def test_sentiment_analysis(self):
        """Testa l'analisi del sentiment"""
        # Test con testo positivo
        positive_text = "Sono molto felice e soddisfatto del risultato!"
        positive_result = self.extractor._analyze_sentiment(positive_text)
        self.assertGreater(positive_result.get('positive', 0), 0.5)
        
        # Test con testo negativo
        negative_text = "Sono molto deluso e arrabbiato per questo fallimento."
        negative_result = self.extractor._analyze_sentiment(negative_text)
        self.assertGreater(negative_result.get('negative', 0), 0.5)
        
    def test_advanced_pattern_extraction(self):
        """Testa l'estrazione di pattern avanzati"""
        test_text = """
        Codice fiscale: RSSMRA80A01H501S
        Partita IVA: IT12345678901
        IBAN: IT60X0542811101000000123456
        Coordinate GPS: 45.4642° N, 9.1900° E
        """
        
        result = self.extractor._extract_patterns(test_text)
        
        # Verifica pattern fiscali
        self.assertIn('codice_fiscale', result)
        self.assertIn('partita_iva', result)
        self.assertIn('iban', result)
        self.assertIn('gps', result)
        
        # Verifica i valori
        self.assertEqual(result['codice_fiscale'], ['RSSMRA80A01H501S'])
        self.assertEqual(result['partita_iva'], ['IT12345678901'])
        self.assertEqual(result['iban'], ['IT60X0542811101000000123456'])
        self.assertTrue(any('45.4642' in gps for gps in result['gps']))

    def test_multilingual_extraction(self):
        """Testa l'estrazione multilingua"""
        texts = {
            'it': "Mario Rossi vive a Milano e lavora per Google",
            'en': "John Smith lives in London and works for Google",
            'es': "Juan García vive en Madrid y trabaja para Google"
        }
        
        for lang, text in texts.items():
            result = self.extractor.extract_from_text(text, language=lang)
            
            # Verifica che le entità siano state estratte correttamente
            self.assertIn('entities', result)
            entities = result['entities']
            
            # Verifica che ci sia almeno una persona e una località
            self.assertTrue(any(entities['person']))
            self.assertTrue(any(entities['location']))
            self.assertIn('Google', entities['organization'])

    def test_contextual_extraction(self):
        """Testa l'estrazione con contesto"""
        context = {
            'domain': 'tech',
            'previous_entities': {'organization': ['Apple', 'Microsoft']},
            'location': 'Silicon Valley'
        }
        
        test_text = "L'azienda ha rilasciato un nuovo prodotto. Il CEO ha fatto l'annuncio."
        
        result = self.extractor.extract_from_text(test_text, context=context)
        
        # Verifica che il contesto influenzi l'estrazione
        self.assertIn('entities', result)
        self.assertIn('relationships', result)
        self.assertIn('domain_specific', result)

    def test_temporal_extraction(self):
        """Testa l'estrazione di informazioni temporali"""
        test_text = """
        La riunione è fissata per domani alle 15:00.
        Il progetto deve essere completato entro la fine del mese.
        L'evento si è svolto la settimana scorsa.
        """
        
        result = self.extractor.extract_from_text(test_text)
        
        # Verifica l'estrazione temporale
        self.assertIn('temporal', result['entities'])
        self.assertIn('15:00', result['entities']['temporal'])
        
    if __name__ == '__main__':
        unittest.main()
