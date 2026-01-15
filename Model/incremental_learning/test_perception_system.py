import unittest
from datetime import datetime, timedelta
from .perception_system import (
    PerceptionSystem, InputType, AttentionLevel, PatternType,
    Percept, Pattern, WorkingMemoryItem
)

class TestPerceptionSystem(unittest.TestCase):
    def setUp(self):
        self.perception = PerceptionSystem(working_memory_size=5)
        
    def test_process_input(self):
        """Testa l'elaborazione dell'input"""
        # Test input testuale
        text_input = "Questo è un test"
        percept = self.perception.process_input(text_input, InputType.TEXT)
        
        self.assertIsInstance(percept, Percept)
        self.assertEqual(percept.input_type, InputType.TEXT)
        self.assertTrue(0 <= percept.confidence <= 1)
        
        # Test input pattern
        pattern_input = [1, 2, 3]
        percept = self.perception.process_input(pattern_input, InputType.PATTERN)
        
        self.assertIsInstance(percept, Percept)
        self.assertEqual(percept.input_type, InputType.PATTERN)
        
    def test_attention_system(self):
        """Testa il sistema di attenzione"""
        # Imposta i punti di focus
        focus_points = {
            "test": 0.8,
            "importante": 0.4
        }
        self.perception.update_attention(focus_points)
        
        # Verifica i livelli di attenzione
        level = self.perception.get_attention_level("test")
        self.assertEqual(level, AttentionLevel.HIGH)
        
        level = self.perception.get_attention_level("importante")
        self.assertEqual(level, AttentionLevel.MEDIUM)
        
        level = self.perception.get_attention_level("irrilevante")
        self.assertEqual(level, AttentionLevel.LOW)
        
    def test_pattern_recognition(self):
        """Testa il riconoscimento dei pattern"""
        # Pattern sequenziale
        elements = [1, 2, 3]
        pattern = self.perception.recognize_pattern(elements, PatternType.SEQUENTIAL)
        
        self.assertIsInstance(pattern, Pattern)
        self.assertEqual(pattern.pattern_type, PatternType.SEQUENTIAL)
        self.assertEqual(pattern.frequency, 1)
        
        # Riconosci lo stesso pattern di nuovo
        pattern2 = self.perception.recognize_pattern(elements, PatternType.SEQUENTIAL)
        self.assertEqual(pattern2.frequency, 2)
        
    def test_working_memory(self):
        """Testa la memoria di lavoro"""
        # Aggiungi elementi alla memoria di lavoro
        for i in range(6):  # Supera la dimensione massima
            percept = self.perception.process_input(
                f"test{i}",
                InputType.TEXT
            )
            
        # Verifica che la memoria mantenga solo gli elementi più prioritari
        snapshot = self.perception.get_working_memory_snapshot()
        self.assertLessEqual(len(snapshot), 5)
        
    def test_context_integration(self):
        """Testa l'integrazione del contesto"""
        # Imposta il contesto
        context = {
            "topic": "test",
            "priority": "high"
        }
        self.perception.integrate_context(context)
        
        # Processa un input correlato al contesto
        percept = self.perception.process_input(
            "questo è un test importante",
            InputType.TEXT
        )
        
        # Verifica che il contesto influenzi la priorità
        snapshot = self.perception.get_working_memory_snapshot()
        self.assertTrue(any(item.content == percept for item in snapshot))
        
    def test_pattern_types(self):
        """Testa i diversi tipi di pattern"""
        # Pattern sequenziale
        seq_elements = [1, 2, 3]
        seq_pattern = self.perception.recognize_pattern(
            seq_elements,
            PatternType.SEQUENTIAL
        )
        self.assertEqual(seq_pattern.pattern_type, PatternType.SEQUENTIAL)
        
        # Pattern strutturale
        class TestStruct:
            def __init__(self):
                self.a = 1
                self.b = 2
                
        struct_elements = [TestStruct()]
        struct_pattern = self.perception.recognize_pattern(
            struct_elements,
            PatternType.STRUCTURAL
        )
        self.assertEqual(struct_pattern.pattern_type, PatternType.STRUCTURAL)
        
        # Pattern temporale
        time_elements = [0.1, 0.2, 0.3]  # intervalli in secondi
        temp_pattern = self.perception.recognize_pattern(
            time_elements,
            PatternType.TEMPORAL
        )
        self.assertEqual(temp_pattern.pattern_type, PatternType.TEMPORAL)
        
    def test_confidence_evaluation(self):
        """Testa la valutazione della confidenza"""
        # Test con input testuale vuoto
        percept = self.perception.process_input("", InputType.TEXT)
        self.assertEqual(percept.confidence, 0.0)
        
        # Test con input testuale valido
        percept = self.perception.process_input("test valido", InputType.TEXT)
        self.assertGreater(percept.confidence, 0.5)
        
        # Test con pattern
        percept = self.perception.process_input([1, 2, 3], InputType.PATTERN)
        self.assertGreater(percept.confidence, 0.0)
        
    def test_memory_priority(self):
        """Testa la prioritizzazione della memoria"""
        # Imposta un punto di focus
        self.perception.update_attention({"importante": 1.0})
        
        # Aggiungi elementi con priorità diverse
        percept1 = self.perception.process_input(
            "test normale",
            InputType.TEXT
        )
        percept2 = self.perception.process_input(
            "test importante",
            InputType.TEXT
        )
        
        # Verifica che gli elementi siano ordinati per priorità
        snapshot = self.perception.get_working_memory_snapshot()
        self.assertEqual(len(snapshot), 2)
        self.assertGreaterEqual(snapshot[0].priority, snapshot[1].priority)
        
    def test_temporal_decay(self):
        """Testa il decadimento temporale della memoria"""
        # Aggiungi un elemento
        percept = self.perception.process_input(
            "test",
            InputType.TEXT
        )
        
        # Simula il passaggio del tempo
        snapshot = self.perception.get_working_memory_snapshot()
        for item in snapshot:
            item.timestamp = datetime.now() - timedelta(seconds=1000)
            item.ttl = 0
            
        # Verifica che l'elemento sia stato rimosso o abbia priorità bassa
        self.perception._reprioritize_working_memory()
        new_snapshot = self.perception.get_working_memory_snapshot()
        self.assertTrue(
            len(new_snapshot) == 0 or
            all(item.priority < 0.5 for item in new_snapshot)
        )
        
if __name__ == '__main__':
    unittest.main()
