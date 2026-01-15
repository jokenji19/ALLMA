import unittest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core.personalization_integration import PersonalizationIntegration
from core.document_processor import DocumentProcessor
from core.extraction import InformationExtractor
from core.nlp_processor import NLPProcessor
from core.personality_coalescence import CoalescenceProcessor
from core.memory_system.memory_manager import AdvancedMemorySystem

class TestEndToEndIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per ogni test"""
        self.memory = AdvancedMemorySystem()
        self.personalization = PersonalizationIntegration(memory_system=self.memory)
        self.doc_processor = DocumentProcessor()
        self.extractor = InformationExtractor()
        self.nlp = NLPProcessor()
        self.personality = CoalescenceProcessor()
        
    def test_complete_conversation_flow(self):
        """Testa un flusso completo di conversazione con multiple interazioni"""
        # Simula una serie di interazioni che costruiscono una conversazione completa
        conversation = [
            {
                'input': 'Ciao! Mi chiamo Marco e sono nuovo qui.',
                'expected_entities': ['marco', 'nuovo'],
                'context': {
                    'time_of_day': 'morning', 
                    'mood': 'positive',
                    'emotional_state': {
                        'primary_emotion': 'joy',
                        'intensity': 0.8,
                        'valence': 0.7,
                        'arousal': 0.6,
                        'dominance': 0.5
                    }
                }
            },
            {
                'input': 'Lavoro come sviluppatore a Milano.',
                'expected_entities': ['lavoro', 'sviluppatore', 'milano'],
                'context': {
                    'time_of_day': 'morning', 
                    'mood': 'neutral',
                    'emotional_state': {
                        'primary_emotion': 'neutral',
                        'intensity': 0.6,
                        'valence': 0.5,
                        'arousal': 0.4,
                        'dominance': 0.5
                    }
                }
            },
            {
                'input': 'Mi piacerebbe imparare di più sull\'intelligenza artificiale.',
                'expected_topics': ['intelligenza', 'artificiale', 'imparare'],
                'context': {
                    'time_of_day': 'morning', 
                    'mood': 'curious',
                    'emotional_state': {
                        'primary_emotion': 'curiosity',
                        'intensity': 0.9,
                        'valence': 0.8,
                        'arousal': 0.7,
                        'dominance': 0.6
                    }
                }
            }
        ]
        
        # Processa la conversazione e verifica la coerenza delle risposte
        memory_nodes = []
        for interaction in conversation:
            result = self.personalization.process_interaction(
                interaction['input'], 
                interaction['context']
            )
            
            # Verifica che le parole chiave siano state estratte correttamente
            if 'expected_entities' in interaction:
                extracted_info = self.extractor.extract_from_text(interaction['input'])
                keywords = extracted_info['keywords']
                for entity in interaction['expected_entities']:
                    self.assertIn(entity.lower(), [k.lower() for k in keywords])
            
            # Verifica che i topic siano stati identificati correttamente
            if 'expected_topics' in interaction:
                extracted_info = self.extractor.extract_from_text(interaction['input'])
                topics = extracted_info['keywords']
                for topic in interaction['expected_topics']:
                    self.assertIn(topic.lower(), [t.lower() for t in topics])
            
            # Salva il nodo di memoria per verificare la connessione tra le interazioni
            if 'memory' in result and 'memory_node_id' in result['memory']:
                memory_nodes.append(result['memory']['memory_node_id'])
        
        # Verifica che ci siano connessioni tra i nodi di memoria
        if len(memory_nodes) > 1:
            for i in range(len(memory_nodes) - 1):
                connections = self.memory.get_connections(memory_nodes[i])
                self.assertIn(memory_nodes[i+1], connections)
        
        # Verifica le statistiche della memoria
        memory_stats = self.memory.get_memory_stats()
        self.assertGreater(memory_stats['total_nodes'], 0)
        self.assertGreater(memory_stats['connections_created'], 0)
        self.assertGreater(memory_stats['memory_health'], 0.5)
        self.assertGreater(memory_stats['avg_emotional_intensity'], 0)
        
        # Verifica che l'intensità emotiva sia stata registrata correttamente
        for node_id in memory_nodes:
            node = self.memory.get_node(node_id)
            self.assertIsNotNone(node.emotional_state)
            self.assertGreater(node.emotional_state['intensity'], 0)
        
    def test_error_recovery(self):
        """Testa la capacità del sistema di recuperare da errori"""
        # Test di recupero da errore di memoria piena
        with patch('core.memory_system.memory_manager.AdvancedMemorySystem.add_memory', side_effect=[MemoryError, True]):
            result = self.personalization.process_interaction(
                "Questo è un test di recupero da errore",
                {'time_of_day': 'morning'}
            )
            self.assertIn('understanding', result)
        
        # Test di recupero da errore di file corrotto
        with patch('core.document_processor.DocumentProcessor.process_document', 
                  side_effect=[IOError("File corrotto"), {'text': 'contenuto recuperato'}]):
            try:
                # Prima chiamata dovrebbe fallire
                self.doc_processor.process_document("test_doc.txt")
            except IOError:
                pass  # Ci aspettiamo questo errore
            
            # Seconda chiamata dovrebbe avere successo
            result = self.doc_processor.process_document("test_doc.txt")
            self.assertEqual(result['text'], 'contenuto recuperato')
        
        # Test di recupero da timeout di rete
        with patch('core.nlp_processor.NLPProcessor.extract_entities', 
                  side_effect=[TimeoutError, {'person': [], 'location': [], 'organization': ['Test']}]):
            try:
                # Prima chiamata dovrebbe fallire
                self.nlp.extract_entities("Test di timeout")
            except TimeoutError:
                pass  # Ci aspettiamo questo errore
            
            # Seconda chiamata dovrebbe avere successo
            result = self.nlp.extract_entities("Test di timeout")
            self.assertIn('organization', result)

    def test_high_load_processing(self):
        """Testa il sistema sotto carico intenso"""
        # Prepara un grande numero di input da processare
        inputs = [
            f"Questo è il messaggio di test numero {i}" 
            for i in range(100)
        ]
        
        # Processa gli input in parallelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(
                lambda x: self.personalization.process_interaction(x, {'parallel': True}),
                inputs
            ))
        
        # Verifica che tutti gli input siano stati processati
        self.assertEqual(len(results), len(inputs))
        for result in results:
            self.assertIn('understanding', result)

    def test_async_module_synchronization(self):
        """Testa la sincronizzazione tra moduli in scenari asincroni"""
        async def async_test():
            # Simula operazioni asincrone parallele
            tasks = [
                # Task 1: Processamento documento
                asyncio.create_task(self._async_document_processing()),
                # Task 2: Analisi del testo
                asyncio.create_task(self._async_text_analysis()),
                # Task 3: Aggiornamento memoria
                asyncio.create_task(self._async_memory_update())
            ]
            
            # Attendi che tutti i task siano completati
            results = await asyncio.gather(*tasks)
            
            # Verifica che tutti i task siano stati completati con successo
            for result in results:
                self.assertTrue(result['success'])
                
            # Verifica la coerenza dei dati tra i moduli
            self.assertEqual(
                results[0]['document_id'],
                results[1]['analyzed_document']
            )
            self.assertEqual(
                results[1]['memory_node'],
                results[2]['updated_node']
            )
        
        # Esegui il test asincrono
        asyncio.run(async_test())

    async def _async_document_processing(self):
        """Simula il processamento asincrono di un documento"""
        await asyncio.sleep(0.1)  # Simula lavoro asincrono
        return {
            'success': True,
            'document_id': 'doc123',
            'content': 'Contenuto processato'
        }

    async def _async_text_analysis(self):
        """Simula l'analisi asincrona del testo"""
        await asyncio.sleep(0.2)  # Simula lavoro asincrono
        return {
            'success': True,
            'analyzed_document': 'doc123',
            'memory_node': 'node456',
            'analysis': 'Analisi completata'
        }

    async def _async_memory_update(self):
        """Simula l'aggiornamento asincrono della memoria"""
        await asyncio.sleep(0.1)  # Simula lavoro asincrono
        return {
            'success': True,
            'updated_node': 'node456',
            'status': 'Memoria aggiornata'
        }

if __name__ == '__main__':
    unittest.main()
