import unittest
from datetime import datetime, timedelta
import os
import json
from allma_model.memory_system.temporal_memory import TemporalMemorySystem

class TestTemporalMemorySystem(unittest.TestCase):
    def setUp(self):
        """Setup per ogni test"""
        self.test_db = "test_memory.db"
        self.memory_system = TemporalMemorySystem(db_path=self.test_db)
        self.test_user_id = "test_user_123"
        
    def tearDown(self):
        """Pulizia dopo ogni test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_store_interaction(self):
        """Test della memorizzazione di un'interazione"""
        interaction = {
            'content': 'Test di una conversazione sul machine learning',
            'context': {'topic': 'ML', 'subtopic': 'testing'},
            'emotion': 'neutral'
        }
        
        # Test memorizzazione
        success = self.memory_system.store_interaction(self.test_user_id, interaction)
        self.assertTrue(success)
        
        # Verifica che l'interazione sia stata memorizzata
        patterns = self.memory_system.get_temporal_patterns(self.test_user_id)
        self.assertIsNotNone(patterns)

    def test_temporal_patterns(self):
        """Test dell'analisi dei pattern temporali"""
        # Crea una serie di interazioni in orari diversi
        times = [
            datetime.now() - timedelta(hours=i)
            for i in range(24)
        ]
        
        for t in times:
            interaction = {
                'content': f'Test interaction at {t}',
                'context': {'time': t.isoformat()},
                'emotion': 'neutral'
            }
            self.memory_system.store_interaction(self.test_user_id, interaction)
        
        patterns = self.memory_system.get_temporal_patterns(self.test_user_id)
        
        self.assertIsNotNone(patterns)
        self.assertIn('hour_distribution', patterns)
        self.assertIn('day_distribution', patterns)
        self.assertIn('frequency', patterns)

    def test_relevant_context(self):
        """Test del recupero del contesto rilevante"""
        # Crea alcune interazioni con contenuti diversi
        interactions = [
            {
                'content': 'Parliamo di machine learning e neural networks',
                'context': {'topic': 'ML'},
                'emotion': 'excited'
            },
            {
                'content': 'Il tempo oggi è bellissimo',
                'context': {'topic': 'weather'},
                'emotion': 'happy'
            },
            {
                'content': 'Deep learning è un sottocampo del machine learning',
                'context': {'topic': 'ML'},
                'emotion': 'neutral'
            }
        ]
        
        for interaction in interactions:
            self.memory_system.store_interaction(self.test_user_id, interaction)
        
        # Cerca contesto rilevante per ML
        relevant = self.memory_system.get_relevant_context(
            self.test_user_id,
            "Vorrei sapere di più sul machine learning"
        )
        
        self.assertGreater(len(relevant), 0)
        # Verifica che le interazioni su ML siano più rilevanti
        self.assertIn('machine learning', relevant[0]['content'].lower())

    def test_hour_distribution(self):
        """Test della distribuzione oraria"""
        current_hour = datetime.now().hour
        
        # Crea più interazioni nell'ora corrente
        for _ in range(5):
            interaction = {
                'content': 'Test interaction',
                'context': {},
                'emotion': 'neutral'
            }
            self.memory_system.store_interaction(self.test_user_id, interaction)
        
        patterns = self.memory_system.get_temporal_patterns(self.test_user_id)
        hour_dist = patterns['hour_distribution']
        
        # Verifica che l'ora corrente abbia la frequenza più alta
        self.assertIn(str(current_hour), hour_dist)
        current_hour_freq = hour_dist[str(current_hour)]
        self.assertEqual(current_hour_freq, 1.0)  # Dovrebbe essere 100%

    def test_interaction_frequency(self):
        """Test del calcolo della frequenza delle interazioni"""
        # Crea interazioni con intervalli regolari
        base_time = datetime.now()
        times = [
            base_time - timedelta(hours=i*2)  # ogni 2 ore
            for i in range(5)
        ]
        
        for t in times:
            interaction = {
                'content': f'Test interaction at {t}',
                'context': {'time': t.isoformat()},
                'emotion': 'neutral',
                'timestamp': t  # Passa esplicitamente il timestamp
            }
            self.memory_system.store_interaction(self.test_user_id, interaction)
        
        patterns = self.memory_system.get_temporal_patterns(self.test_user_id)
        frequency = patterns['frequency']
        
        # Verifica che la media sia circa 2 ore
        self.assertAlmostEqual(frequency['average_gap_hours'], 2.0, delta=0.5)

    def test_error_handling(self):
        """Test della gestione degli errori"""
        # Test con interazione malformata
        bad_interaction = {
            'content': None,
            'context': 'not_a_dict',
            'emotion': 123  # dovrebbe essere una stringa
        }
        
        # Non dovrebbe sollevare eccezioni
        success = self.memory_system.store_interaction(self.test_user_id, bad_interaction)
        self.assertFalse(success)
        
        # Test con user_id None
        success = self.memory_system.store_interaction(None, {})
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
