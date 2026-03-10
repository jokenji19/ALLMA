import unittest
from datetime import datetime, timedelta
import os
from allma_model.incremental_learning.enhanced_memory_system import (
    EnhancedMemorySystem,
    MemoryItem,
    WorkingMemory,
    ShortTermMemory,
    LongTermMemory,
    AssociativeMemory
)

class TestEnhancedMemorySystem(unittest.TestCase):
    def setUp(self):
        self.memory_system = EnhancedMemorySystem()
        
    def test_working_memory_capacity(self):
        """Verifica che la working memory rispetti il limite di capacità"""
        wm = WorkingMemory(capacity=3)
        
        # Aggiungi più items della capacità
        for i in range(5):
            item = MemoryItem(
                content=f"Test {i}",
                timestamp=datetime.now(),
                importance=0.5,
                emotional_intensity=0.5,
                associations=set(["test"]),
                recall_count=0,
                last_recall=datetime.now(),
                memory_strength=1.0,
                context={}
            )
            wm.add_item(item)
            
        # Verifica che la lunghezza non superi la capacità
        self.assertEqual(len(wm.items), 3)
        
    def test_short_term_retention(self):
        """Verifica che la short term memory mantenga gli items solo per il tempo specificato"""
        stm = ShortTermMemory(retention_time=timedelta(seconds=1))
        
        # Aggiungi un item
        item = MemoryItem(
            content="Test",
            timestamp=datetime.now() - timedelta(seconds=2),  # 2 secondi fa
            importance=0.5,
            emotional_intensity=0.5,
            associations=set(["test"]),
            recall_count=0,
            last_recall=datetime.now() - timedelta(seconds=2),
            memory_strength=1.0,
            context={}
        )
        stm.add_item(item)
        
        # Verifica che l'item sia stato rimosso durante il cleanup
        recent_items = stm.get_recent_items()
        self.assertEqual(len(recent_items), 0)
        
    def test_long_term_memory_strength(self):
        """Verifica il calcolo della forza della memoria"""
        ltm = LongTermMemory()
        
        # Crea un item con recall multipli
        item = MemoryItem(
            content="Test",
            timestamp=datetime.now() - timedelta(hours=24),
            importance=0.8,
            emotional_intensity=0.7,
            associations=set(["test"]),
            recall_count=3,
            last_recall=datetime.now() - timedelta(hours=12),
            memory_strength=1.0,
            context={}
        )
        
        strength = ltm.get_memory_strength(item)
        self.assertTrue(0 <= strength <= 1)
        
        # Verifica che il richiamo rafforzi la memoria
        ltm.recall_item(item)
        new_strength = ltm.get_memory_strength(item)
        self.assertTrue(new_strength > strength)
        
    def test_associative_memory(self):
        """Verifica il funzionamento della memoria associativa"""
        am = AssociativeMemory()
        
        # Crea alcune associazioni
        am.add_association("gatto", "animale", 0.8)
        am.add_association("gatto", "peloso", 0.6)
        am.add_association("cane", "animale", 0.8)
        
        # Trova concetti simili
        similar = am.get_similar_concepts("gatto", threshold=0.5)
        self.assertTrue(len(similar) > 0)
        
    def test_full_system_integration(self):
        """Verifica l'integrazione di tutti i componenti"""
        # Processa un input
        result = self.memory_system.process_input(
            "Il gatto e il cane sono animali domestici",
            importance=0.8,
            emotional_intensity=0.7
        )
        
        self.assertIn("working_memory", result)
        self.assertIn("short_term", result)
        self.assertIn("associations_made", result)
        
        # Richiama memorie correlate
        recall_result = self.memory_system.recall_related({"gatto", "animale"})
        self.assertIn("items", recall_result)
        self.assertIn("concepts_found", recall_result)
        self.assertIn("memories_recalled", recall_result)
        
    def test_memory_persistence(self):
        """Verifica il salvataggio e caricamento dello stato della memoria"""
        # Aggiungi alcuni dati
        self.memory_system.process_input(
            "Test memory persistence",
            importance=0.8,
            emotional_intensity=0.7
        )
        
        # Salva lo stato
        test_file = "test_memory_state.json"
        self.memory_system.save_state(test_file)
        
        # Crea un nuovo sistema e carica lo stato
        new_system = EnhancedMemorySystem()
        new_system.load_state(test_file)
        
        # Verifica che i dati siano stati preservati
        self.assertEqual(
            len(new_system.working_memory.items),
            len(self.memory_system.working_memory.items)
        )
        
        # Pulisci
        os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
