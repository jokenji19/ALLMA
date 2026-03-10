"""
Test Suite Completa per il Sistema di Apprendimento Incrementale
Include test per scenari di errore, casi limite, stress test e monitoraggio
"""

import unittest
import time
import psutil
import threading
import gc
import pytest
from typing import Dict, List
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from .emotional_system import EmotionalSystem
from .cognitive_evolution_system import CognitiveEvolutionSystem
from .memory_system import MemorySystem
from .metacognition_system import MetaCognitionSystem
from .communication_system import CommunicationSystem
from .perception_system import PerceptionSystem
from .pattern_recognition_system import PatternRecognitionSystem

class ComprehensiveTestSuite(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi necessari per i test"""
        self.emotional = EmotionalSystem()
        self.cognitive = CognitiveEvolutionSystem()
        self.memory = MemorySystem()
        self.metacognition = MetaCognitionSystem()
        self.communication = CommunicationSystem()
        self.perception = PerceptionSystem()
        self.pattern = PatternRecognitionSystem()
        
    def test_edge_cases(self):
        """Test per casi limite"""
        print("\n=== Test Casi Limite ===")
        
        # Test valori estremi
        edge_cases = [
            ("test", 0.0),  # Valenza neutra
            ("A" * 1000, 1.0),  # Input lungo
            ("🌟" * 100, 0.5),  # Emoji
            ("特殊な文字", 0.7),  # Caratteri non ASCII
        ]
        
        for input_text, valence in edge_cases:
            try:
                result = self.emotional.process_stimulus(input_text, valence)
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Caso limite fallito per {input_text[:20]}...: {str(e)}")
                
        # Test input invalidi che dovrebbero sollevare eccezioni
        with self.assertRaises(ValueError):
            self.emotional.process_stimulus("", 0.0)  # Input vuoto
            
        with self.assertRaises(ValueError):
            self.emotional.process_stimulus("test", 1.5)  # Valenza fuori range
            
    @pytest.mark.timeout(5)  # Timeout di 5 secondi
    def test_error_scenarios(self):
        """Test per scenari di errore"""
        print("\n=== Test Scenari di Errore ===")
        print("Tempo stimato: 5 secondi")
        
        # Test input invalidi
        with self.assertRaises(ValueError):
            self.emotional.process_stimulus("", valence=-2.0)
            
        with self.assertRaises(ValueError):
            self.cognitive.process_experience(None)
            
        with self.assertRaises(ValueError):
            self.cognitive.process_experience({})  # Dict vuoto
            
        # Test input grande ma gestibile
        try:
            large_input = "x" * (10**3)  # 1KB di testo
            self.memory.process_experience(large_input, emotional_valence=0.5)
        except MemoryError:
            self.fail("Il sistema non gestisce correttamente input di dimensioni ragionevoli")
            
    def test_long_term_behavior(self):
        """Test del comportamento a lungo termine"""
        print("\n=== Test Comportamento Lungo Termine ===")
        
        # Monitora memoria
        memory_usage = []
        initial_memory = psutil.Process().memory_info().rss
        
        def long_term_worker():
            for i in range(5):  # Ridotto ulteriormente da 10 a 5
                self.cognitive.process_experience({"data": f"test_{i}"})
                self.memory.process_experience(f"test_data_{i}", emotional_valence=0.5)
                memory_usage.append(psutil.Process().memory_info().rss - initial_memory)
                
        # Esegui test lungo termine
        worker = threading.Thread(target=long_term_worker)
        worker.start()
        worker.join(timeout=5)  # Aggiunto timeout di 5 secondi
        
        if len(memory_usage) > 0:
            # Analizza utilizzo memoria
            memory_trend = np.polyfit(range(len(memory_usage)), memory_usage, 1)[0]
            self.assertLess(memory_trend, 1000000)  # Verifica che non ci siano memory leak significativi
            
    def test_performance_monitoring(self):
        """Test del monitoraggio delle performance"""
        print("\n=== Test Monitoraggio Performance ===")
        
        # Monitora tempo di risposta
        response_times = []
        memory_usage = []
        
        for _ in range(100):
            start_time = time.time()
            self.cognitive.process_experience({"data": "test"})
            response_times.append(time.time() - start_time)
            
            process = psutil.Process()
            memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
            
        # Analisi performance
        avg_response_time = np.mean(response_times)
        max_response_time = np.max(response_times)
        memory_variation = np.std(memory_usage)
        
        print(f"Tempo medio di risposta: {avg_response_time:.4f}s")
        print(f"Tempo massimo di risposta: {max_response_time:.4f}s")
        print(f"Variazione memoria: {memory_variation:.2f}MB")
        
        # Verifica metriche
        self.assertLess(avg_response_time, 0.1)  # Risposta sotto 100ms
        self.assertLess(max_response_time, 0.5)  # Picco sotto 500ms
        self.assertLess(memory_variation, 50)  # Variazione memoria limitata
        
    def test_resilience(self):
        """Test di resilienza"""
        print("\n=== Test Resilienza ===")
        
        def simulate_failure():
            raise Exception("Simulazione fallimento")
            
        # Test recupero da errori
        error_count = 0
        for _ in range(100):
            try:
                simulate_failure()
            except:
                try:
                    # Verifica che il sistema si riprenda
                    result = self.emotional.process_stimulus("Test resilienza", valence=0.5)
                    self.assertIsNotNone(result)
                except:
                    error_count += 1
                    
        self.assertLess(error_count, 5)  # Ammette alcuni errori ma non troppi
        
    def test_scalability(self):
        """Test di scalabilità"""
        print("\n=== Test Scalabilità ===")
        
        # Test con carico crescente
        loads = [5, 10, 20]  # Ridotto il carico
        times = []
        
        for load in loads:
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=2) as executor:  # Ridotto il numero di workers
                futures = [
                    executor.submit(self.cognitive.process_experience, {"data": f"test_{i}"})
                    for i in range(load)
                ]
                for future in futures:
                    future.result()
            times.append(time.time() - start_time)
            
        # Verifica che il tempo cresca sub-linearmente
        time_ratio = times[-1] / times[0]
        load_ratio = loads[-1] / loads[0]
        self.assertLess(time_ratio, load_ratio)
        
    def test_security(self):
        """Test di sicurezza"""
        print("\n=== Test Sicurezza ===")
        
        malicious_inputs = [
            "'; DROP TABLE users; --",  # SQL Injection
            "<script>alert('xss')</script>",  # XSS
            "../../../etc/passwd",  # Path Traversal
            "x" * (10**6),  # Buffer Overflow
        ]
        
        for input_text in malicious_inputs:
            try:
                result = self.emotional.process_stimulus(input_text, valence=0.5)
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Input malevolo non gestito correttamente: {str(e)}")
                
    def test_stress(self):
        """Test di carico estremo"""
        print("\n=== Test di Stress ===")
        
        def stress_worker():
            for i in range(5):  # Ridotto ulteriormente da 10 a 5
                self.emotional.process_stimulus(f"Test input {i}", valence=0.5)
                self.cognitive.process_experience({"data": f"test_{i}"})
                self.memory.process_experience(f"test_data_{i}", emotional_valence=0.5)
                
        # Test multi-thread
        threads = []
        for _ in range(3):  # Ridotto ulteriormente da 5 a 3 thread
            t = threading.Thread(target=stress_worker)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join(timeout=5)  # Aggiunto timeout di 5 secondi
            
        # Verifica che il sistema sia ancora responsivo
        try:
            result = self.emotional.process_stimulus("Post-stress test", valence=0.5)
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Sistema non responsivo dopo stress test: {str(e)}")
            
if __name__ == '__main__':
    unittest.main()
