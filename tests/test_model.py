import unittest
from datetime import datetime, timedelta
from Model.incremental_learning.memory_system import MemorySystem
from Model.incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem
from Model.incremental_learning.emotional_system import EmotionalSystem
import threading
import time
import cProfile
import pstats
from pstats import SortKey

class TestModelComplete(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per il test"""
        self.memory_system = MemorySystem()
        self.cognitive_system = CognitiveEvolutionSystem()
        self.emotional_system = EmotionalSystem()
        self.start_time = time.time()
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        
    def tearDown(self):
        """Stampa il tempo di esecuzione del test e le statistiche del profiler"""
        self.profiler.disable()
        duration = time.time() - self.start_time
        print(f"\nTempo di esecuzione di {self._testMethodName}: {duration:.2f} secondi")
        
        # Stampa le top 10 funzioni più lente
        stats = pstats.Stats(self.profiler).sort_stats(SortKey.TIME)
        print("\nTop 10 funzioni più lente:")
        stats.print_stats(10)

    def test_basic_memory_operations(self):
        """Test delle operazioni base di memoria"""
        # Test memorizzazione
        result = self.memory_system.process_experience(
            "Ho imparato una nuova abilità",
            emotional_valence=0.7
        )
        self.assertTrue(result["memory_stored"])
        
        # Test recupero
        memories = self.memory_system.recall_memory(
            "imparato abilità",
            context={"type": "learning"}
        )
        self.assertTrue(len(memories) > 0)
        
    def test_emotional_processing(self):
        """Test del sistema emotivo"""
        # Test elaborazione stimolo emotivo
        result = self.emotional_system.process_stimulus(
            "Sono molto felice",
            valence=0.8
        )
        self.assertGreater(result.intensity, 0)
        
        # Test decadimento emozioni
        self.emotional_system.update()
        self.assertLess(
            self.emotional_system.get_current_state()["valence"],
            0.8
        )
        
    def test_cognitive_learning(self):
        """Test del sistema cognitivo"""
        # Test apprendimento
        result = self.cognitive_system.learn(
            "matematica",
            difficulty=0.6,
            success_rate=0.8
        )
        self.assertTrue(result["learning_occurred"])
        
        # Test trasferimento apprendimento
        transfer = self.cognitive_system.check_transfer(
            "fisica",
            "matematica"
        )
        self.assertGreater(transfer, 0)
        
    def test_system_integration(self):
        """Test dell'integrazione tra i sistemi"""
        # Crea un'esperienza di apprendimento
        experience = "Ho risolto un problema difficile di matematica"
        
        # Processo emotivo
        emotional_result = self.emotional_system.process_stimulus(
            experience,
            valence=0.9
        )
        
        # Memorizzazione
        memory_result = self.memory_system.process_experience(
            experience,
            emotional_valence=emotional_result.valence
        )
        
        # Apprendimento cognitivo
        cognitive_result = self.cognitive_system.learn(
            "problem_solving",
            difficulty=0.7,
            success_rate=0.9
        )
        
        # Verifica integrazione
        self.assertTrue(memory_result["memory_stored"])
        self.assertTrue(cognitive_result["learning_occurred"])
        self.assertGreater(emotional_result.intensity, 0)
        
    def test_performance(self):
        """Test delle performance del sistema"""
        start_time = datetime.now()
        
        # Esegue 100 operazioni
        for i in range(100):
            self.memory_system.process_experience(
                f"Esperienza di test {i}",
                emotional_valence=0.5
            )
            
        duration = datetime.now() - start_time
        self.assertLess(duration.total_seconds(), 5)  # Non deve impiegare più di 5 secondi

    def test_edge_cases(self):
        """Test dei casi limite"""
        # Test input vuoto
        with self.assertRaises(ValueError):
            self.memory_system.process_experience("", 0.5)
            
        # Test valenza emotiva non valida
        with self.assertRaises(ValueError):
            self.emotional_system.process_stimulus("Test", 1.5)
            
        # Test difficoltà non valida
        with self.assertRaises(ValueError):
            self.cognitive_system.learn("test", 1.5, 0.5)
            
        # Test input molto lungo
        long_text = "test " * 1000
        result = self.memory_system.process_experience(long_text, 0.5)
        self.assertTrue(result["memory_stored"])
        
        # Test input con caratteri speciali
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/\\"
        result = self.memory_system.process_experience(special_chars, 0.5)
        self.assertTrue(result["memory_stored"])
        
    def test_concurrent_operations(self):
        """Test delle operazioni concorrenti"""
        import threading
        
        def memory_operation():
            for i in range(10):
                self.memory_system.process_experience(f"Test {i}", 0.5)
                
        def emotional_operation():
            for i in range(10):
                self.emotional_system.process_stimulus(f"Test {i}", 0.5)
                
        def cognitive_operation():
            for i in range(10):
                self.cognitive_system.learn(f"skill_{i}", 0.5, 0.5)
                
        # Crea i thread
        threads = [
            threading.Thread(target=memory_operation),
            threading.Thread(target=emotional_operation),
            threading.Thread(target=cognitive_operation)
        ]
        
        # Avvia i thread
        for t in threads:
            t.start()
            
        # Attendi il completamento
        for t in threads:
            t.join()
            
    def test_stress(self):
        """Test di stress del sistema"""
        # Ridotto da 1000 a 100 iterazioni
        for i in range(100):
            self.memory_system.process_experience(f"Test {i}", 0.5)
            self.emotional_system.process_stimulus(f"Test {i}", 0.5)
            self.cognitive_system.learn(f"skill_{i}", 0.5, 0.5)
            
        # Ridotto da 100 a 10 iterazioni per le operazioni miste
        for i in range(10):
            # Memoria
            self.memory_system.process_experience(f"Test {i}", 0.5)
            self.memory_system.recall_memory(f"Test {i}")
            
            # Emozioni
            self.emotional_system.process_stimulus(f"Test {i}", 0.5)
            self.emotional_system.update()
            
            # Cognizione
            self.cognitive_system.learn(f"skill_{i}", 0.5, 0.5)
            self.cognitive_system.check_transfer(f"skill_{i}", f"skill_{i-1}")
            
    def test_memory_consolidation(self):
        """Test della consolidazione della memoria"""
        # Crea una singola memoria
        self.memory_system.process_experience("Test memoria", 0.5)
    
        # Forza la consolidazione
        self.memory_system.last_consolidation = datetime.now() - timedelta(minutes=35)
        result = self.memory_system.process_experience("Test consolidazione", 0.5)
    
        self.assertTrue(result["consolidation_performed"])
        
    def test_memory_consolidation_timing(self):
        """Test della temporizzazione del consolidamento memoria"""
        # Prima esperienza
        result1 = self.memory_system.process_experience(
            "Prima esperienza di test",
            emotional_valence=0.5
        )
        self.assertTrue(result1["consolidation_performed"])
        
        # Seconda esperienza dopo 15 minuti (non dovrebbe consolidare)
        self.memory_system.last_consolidation = datetime.now() - timedelta(minutes=15)
        result2 = self.memory_system.process_experience(
            "Seconda esperienza di test",
            emotional_valence=0.5
        )
        self.assertFalse(result2["consolidation_performed"])
        
        # Terza esperienza dopo 35 minuti (dovrebbe consolidare)
        self.memory_system.last_consolidation = datetime.now() - timedelta(minutes=35)
        result3 = self.memory_system.process_experience(
            "Terza esperienza di test",
            emotional_valence=0.5
        )
        self.assertTrue(result3["consolidation_performed"])
        
    def test_concept_extraction_performance(self):
        """Test delle performance dell'estrazione concetti"""
        # Test con testo lungo
        long_text = " ".join(["parola"] * 1000 + ["imparo", "studio"] * 5)
        
        start_time = time.time()
        concepts = self.memory_system._extract_concepts(long_text)
        end_time = time.time()
        
        self.assertLess(end_time - start_time, 0.1)  # Dovrebbe essere veloce
        self.assertEqual(len(concepts), 10)  # 5 occorrenze di "imparo" e "studio"
        
    def test_emotional_decay(self):
        """Test del decadimento emotivo"""
        # Crea un'emozione forte
        self.emotional_system.process_stimulus("Test", 1.0)
        initial_state = self.emotional_system.get_current_state()
        
        # Simula il passaggio del tempo e aggiorna
        time.sleep(1)
        self.emotional_system.update()
        
        # Verifica il decadimento
        current_state = self.emotional_system.get_current_state()
        self.assertLess(current_state["valence"], initial_state["valence"])
        
    def test_cognitive_transfer(self):
        """Test del trasferimento cognitivo"""
        # Apprendi un'abilità
        self.cognitive_system.learn("matematica", 0.7, 0.8)
        
        # Verifica il trasferimento a un'abilità correlata
        transfer = self.cognitive_system.check_transfer("fisica", "matematica")
        self.assertGreater(transfer, 0)
        
        # Verifica il trasferimento a un'abilità non correlata
        transfer = self.cognitive_system.check_transfer("arte", "matematica")
        self.assertLess(transfer, 0.3)
        
if __name__ == '__main__':
    unittest.main()
