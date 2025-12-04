import unittest
from datetime import datetime
from Model.core.context_understanding import ContextUnderstandingSystem

class TestContextUnderstanding(unittest.TestCase):
    def setUp(self):
        self.context_system = ContextUnderstandingSystem()
        
    def test_multilingual_analysis(self):
        """Test analisi multilingua"""
        # Test italiano
        result_it = self.context_system.analyze_multilingual_input(
            "Sono molto felice oggi!"
        )
        self.assertEqual(result_it['detected_language'], 'it')
        self.assertIn('english_translation', result_it)
        self.assertIn('emotions', result_it)
        self.assertIn('confidence', result_it)
        
        # Test inglese
        result_en = self.context_system.analyze_multilingual_input(
            "I am very happy today!"
        )
        self.assertEqual(result_en['detected_language'], 'en')
        self.assertIn('emotions', result_en)
        self.assertIn('confidence', result_en)
        
        # Test input vuoto
        result_empty = self.context_system.analyze_multilingual_input("")
        self.assertIn('error', result_empty)
        
        # Test input non valido
        result_invalid = self.context_system.analyze_multilingual_input("😊")
        self.assertIn('error', result_invalid)
        
    def test_emotion_analysis(self):
        """Test analisi delle emozioni"""
        # Test emozioni positive
        result_happy = self.context_system.analyze_emotions(
            "I am extremely happy and excited about this!"
        )
        self.assertGreater(result_happy['score'], 0.5)
        
        # Test emozioni negative
        result_sad = self.context_system.analyze_emotions(
            "I am feeling very sad and depressed."
        )
        self.assertGreater(result_sad['score'], 0.5)
        
        # Test testo neutro
        result_neutral = self.context_system.analyze_emotions(
            "The weather is cloudy today."
        )
        self.assertIn('label', result_neutral)
        
    def test_translation(self):
        """Test traduzione"""
        # Test traduzione italiano -> inglese
        result_it_en = self.context_system.translate_text(
            "Sono molto felice oggi!",
            source_lang='it',
            target_lang='en'
        )
        self.assertEqual(result_it_en, "I am very happy today!")
        
        # Test stessa lingua
        result_same = self.context_system.translate_text(
            "Hello world!",
            source_lang='en',
            target_lang='en'
        )
        self.assertEqual(result_same, "Hello world!")
        
        # Test lingua non supportata
        result_unsupported = self.context_system.translate_text(
            "こんにちは",
            source_lang='ja',
            target_lang='en'
        )
        self.assertEqual(result_unsupported, "こんにちは")  # Ritorna testo originale
        
    def test_temporal_analysis(self):
        """Test analisi temporale"""
        reference_time = datetime(2025, 1, 21, 12, 0)
        
        # Test italiano
        result_it = self.context_system.analyze_temporal_context(
            "Ci vediamo domani alle 15:00",
            reference_time
        )
        self.assertTrue(len(result_it['detected_times']) > 0)
        first_time_it = result_it['detected_times'][0]
        self.assertEqual(first_time_it['timeframe'], 'future')
        
        # Test inglese
        result_en = self.context_system.analyze_temporal_context(
            "See you tomorrow at 3 PM",
            reference_time
        )
        self.assertTrue(len(result_en['detected_times']) > 0)
        first_time_en = result_en['detected_times'][0]
        self.assertEqual(first_time_en['timeframe'], 'future')
        
        # Test riferimenti multipli
        result_multi = self.context_system.analyze_temporal_context(
            "Yesterday I was happy, today I am sad, but tomorrow will be better",
            reference_time
        )
        self.assertEqual(len(result_multi['detected_times']), 3)
        
    def test_context_memory(self):
        """Test memoria del contesto"""
        # Test aggiunta contesti
        memory_ids = []
        for i in range(150):  # Testiamo con più contesti per verificare che non ci siano limiti
            context = {
                'text_analysis': {
                    'original_text': f'Test {i}',
                    'detected_language': 'en'
                }
            }
            memory_id = self.context_system.add_to_context_memory(context)
            self.assertIsNotNone(memory_id, "Il contesto dovrebbe essere sempre aggiunto")
            memory_ids.append(memory_id)
            
        # Verifica che tutti i contesti siano stati memorizzati
        self.assertEqual(len(memory_ids), 150, "Tutti i contesti dovrebbero essere memorizzati")
        self.assertEqual(len(self.context_system.context_memory), 150, "La memoria dovrebbe contenere tutti i contesti")
        
        # Verifica che ogni contesto abbia un ID univoco
        unique_ids = set(memory_ids)
        self.assertEqual(len(unique_ids), 150, "Ogni contesto dovrebbe avere un ID univoco")
        
        # Verifica che ogni contesto abbia un timestamp
        for context in self.context_system.context_memory:
            self.assertIn('timestamp', context, "Ogni contesto dovrebbe avere un timestamp")
            self.assertIsInstance(context['timestamp'], str, "Il timestamp dovrebbe essere una stringa")
            
    def test_context_memory_management(self):
        """Test gestione della memoria contestuale"""
        # Test aggiunta contesti
        initial_contexts = [
            {'text': 'Test 1', 'type': 'message'},
            {'text': 'Test 2', 'type': 'response'},
            {'text': 'Test 3', 'type': 'message'}
        ]
        
        # Aggiungi i contesti iniziali
        memory_ids = []
        for context in initial_contexts:
            memory_id = self.context_system.add_to_context_memory(context)
            self.assertIsNotNone(memory_id)
            memory_ids.append(memory_id)
            
        # Verifica che tutti i contesti siano stati memorizzati
        self.assertEqual(len(self.context_system.context_memory), 3)
        
        # Verifica che i contesti abbiano gli ID corretti
        for i, context in enumerate(self.context_system.context_memory):
            self.assertEqual(context['id'], memory_ids[i])
            
        # Verifica ricerca contesti
        search_results = self.context_system.search_context('Test 2')
        self.assertGreater(len(search_results), 0)
        self.assertEqual(search_results[0]['text'], 'Test 2')

    def test_complete_context_analysis(self):
        """Test analisi completa del contesto"""
        # Test solo testo
        result_text = self.context_system.analyze_complete_context(
            text="Sono molto felice oggi!"
        )
        self.assertIn('text_analysis', result_text)
        self.assertIn('temporal_analysis', result_text)
        self.assertIn('detected_language', result_text['text_analysis'])
        self.assertIn('emotions', result_text['text_analysis'])
        
        # Test senza input
        result_empty = self.context_system.analyze_complete_context()
        self.assertEqual(len(result_empty), 0)
        
        # Test con input invalido
        result_invalid = self.context_system.analyze_complete_context(
            text="",
            image_path="nonexistent.jpg"
        )
        self.assertIn('image_analysis', result_invalid)
        self.assertIn('error', result_invalid['image_analysis'])
        self.assertEqual(result_invalid['image_analysis']['error'], "Impossibile caricare l'immagine")
        
    def test_visual_context_analysis(self):
        """Test analisi del contesto visivo"""
        import os
        import numpy as np
        from PIL import Image
        
        # Crea un'immagine di test
        width, height = 400, 300
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[100:200, 150:250] = [255, 255, 255]  # Rettangolo bianco
        
        # Salva l'immagine
        test_image_path = "test_image.jpg"
        Image.fromarray(image).save(test_image_path)
        
        try:
            # Test analisi immagine
            result = self.context_system.analyze_visual_context(test_image_path)
            self.assertIn('objects', result)
            self.assertIn('scene_type', result)
            self.assertIn('colors', result)
            self.assertIn('confidence', result)
            
            # Test estrazione testo
            result_text = self.context_system.extract_text_from_image(test_image_path)
            self.assertIsInstance(result_text, dict)
            self.assertIn('text', result_text)
            self.assertIn('confidence', result_text)
            
            # Test memoria visiva
            memory_result = self.context_system.visual_memory.store_visual_memory(
                image_path=test_image_path,
                context={'timestamp': datetime.now().isoformat()}
            )
            self.assertTrue(memory_result['success'])
            self.assertIn('memory_id', memory_result)
            
        finally:
            # Pulizia
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
                
    def test_contextual_search(self):
        """Test ricerca contestuale"""
        # Aggiungi alcuni contesti di test
        contexts = [
            {
                'text': "I love programming with ALLMA",
                'timestamp': datetime.now().isoformat(),
                'emotions': {'label': 'joy', 'score': 0.8},
                'language': 'en'
            },
            {
                'text': "The weather is nice today",
                'timestamp': datetime.now().isoformat(),
                'emotions': {'label': 'neutral', 'score': 0.6},
                'language': 'en'
            },
            {
                'text': "Mi piace programmare con ALLMA",
                'timestamp': datetime.now().isoformat(),
                'emotions': {'label': 'joy', 'score': 0.9},
                'language': 'it'
            }
        ]
        
        for ctx in contexts:
            self.context_system.add_to_context_memory(ctx)
            
        # Test ricerca per testo
        allma_results = self.context_system.search_context('ALLMA')
        self.assertEqual(len(allma_results), 2)
        self.assertTrue(any('love programming' in r['text'] for r in allma_results))
        self.assertTrue(any('piace programmare' in r['text'] for r in allma_results))
        
        # Test ricerca per emozione
        joy_results = self.context_system.search_context('joy')
        self.assertEqual(len(joy_results), 2)
        
        # Test ricerca per testo in una lingua specifica
        weather_results = self.context_system.search_context('weather')
        self.assertEqual(len(weather_results), 1)
        self.assertEqual(weather_results[0]['text'], "The weather is nice today")

    def test_error_handling(self):
        """Test gestione degli errori"""
        # Test input non valido per analisi emozioni
        result = self.context_system.analyze_emotions(None)
        self.assertEqual(result['label'], 'unknown')
        self.assertEqual(result['score'], 0.0)
        
        # Test input non valido per traduzione
        result = self.context_system.translate_text(None, 'en', 'it')
        self.assertIsNone(result)
        
        # Test lingua non supportata per analisi temporale
        result = self.context_system.analyze_temporal_context(
            "明日会いましょう",  # Testo in giapponese
            datetime.now()
        )
        self.assertEqual(len(result['detected_times']), 0)
        self.assertEqual(len(result['temporal_relations']), 0)
        self.assertIn('reference_time', result)

    def test_context_integration(self):
        """Test integrazione dei contesti"""
        # Crea contesti di test
        text_context = {
            'text': "I am happy to be here",
            'emotions': {'label': 'joy', 'score': 0.9},
            'language': 'en',
            'timestamp': datetime.now().isoformat()
        }
        
        temporal_context = {
            'text': "See you tomorrow at 3 PM",
            'detected_times': [
                {'timeframe': 'future', 'time': '15:00'}
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        # Integra i contesti
        integrated = self.context_system.integrate_contexts([
            text_context,
            temporal_context
        ])
        
        # Verifica l'integrazione
        self.assertIn('emotions', integrated)
        self.assertIn('detected_times', integrated)
        self.assertEqual(integrated['emotions'], text_context['emotions'])
        self.assertEqual(
            integrated['detected_times'],
            temporal_context['detected_times']
        )

if __name__ == '__main__':
    unittest.main()
