import unittest
from datetime import datetime, timedelta
from Model.incremental_learning.memory_system import MemorySystem

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        self.memory_system = MemorySystem()

    def test_process_experience_valid(self):
        """Test che il sistema gestisca correttamente esperienze valide"""
        result = self.memory_system.process_experience(
            "Ho imparato una nuova abilità",
            emotional_valence=0.7
        )
        self.assertTrue(result["memory_stored"])
        
    def test_process_experience_empty(self):
        """Test che il sistema gestisca correttamente esperienze vuote"""
        with self.assertRaises(ValueError):
            self.memory_system.process_experience("", 0.5)
            
    def test_process_experience_invalid_valence(self):
        """Test che il sistema gestisca correttamente valenze emotive non valide"""
        with self.assertRaises(ValueError):
            self.memory_system.process_experience("Test", 1.5)
            
    def test_memory_consolidation(self):
        """Test che le memorie vengano consolidate correttamente"""
        # Simula il passaggio del tempo
        self.memory_system.last_consolidation = datetime.now() - timedelta(minutes=10)
        
        result = self.memory_system.process_experience(
            "Un'esperienza importante",
            emotional_valence=0.9
        )
        self.assertTrue(result["memory_stored"])
        
        # Forza il consolidamento
        self.memory_system._consolidate_memories()
        self.assertTrue(self.memory_system.last_consolidation > datetime.now() - timedelta(seconds=1))

    def test_memory_retrieval(self):
        """Test che le memorie possano essere recuperate correttamente"""
        experience = "Un'esperienza unica e memorabile"
        self.memory_system.process_experience(experience, 0.8)
        
        # Cerca di recuperare la memoria
        memories = self.memory_system.recall_memory(
            query="esperienza memorabile",
            context={"emotional_valence": 0.8}
        )
        self.assertGreater(len(memories), 0)
        self.assertIn(experience, [m["content"] for m in memories])
        
    def test_memory_performance(self):
        """Test delle performance del sistema di memoria"""
        start_time = datetime.now()
        
        # Inserisci 100 memorie
        for i in range(100):
            self.memory_system.process_experience(
                f"Memoria di test numero {i}",
                emotional_valence=0.5
            )
            
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Il tempo medio per memoria dovrebbe essere ragionevole
        avg_time_per_memory = processing_time / 100
        self.assertLess(avg_time_per_memory, 0.1)  # Meno di 100ms per memoria
        
        # Verifica l'uso della memoria
        stats = self.memory_system.get_memory_stats()
        self.assertLessEqual(stats["total_memories"], 100)

if __name__ == '__main__':
    unittest.main()
