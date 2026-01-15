"""
Test completo del sistema ALLMA
Include test di integrazione, performance e funzionalità
"""
import unittest
from datetime import datetime
import random
import json
from typing import Dict, List

from incremental_learning.integrated_allma import IntegratedALLMA
from incremental_learning.memory_system import Memory, MemorySystem
from incremental_learning.emotional_system import EmotionalSystem, Emotion
from incremental_learning.cognitive_foundations import EnhancedCognitiveProcessor
from performance_profiler import PerformanceProfiler

class CompleteALLMATest(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per i test"""
        self.allma = IntegratedALLMA()
        self.profiler = PerformanceProfiler()
        
    def test_1_emotional_system(self):
        """Test completo del sistema emotivo"""
        print("\n=== Test Sistema Emotivo ===")
        
        test_cases = [
            ("Sono molto felice oggi!", "gioia", 0.8),
            ("Mi sento triste...", "tristezza", -0.6),
            ("Che rabbia!", "rabbia", -0.7),
            ("Ho paura del buio", "paura", -0.5),
            ("Sono sorpreso dal risultato", "sorpresa", 0.4)
        ]
        
        for text, expected_emotion, expected_valence in test_cases:
            with self.profiler.profile("emotional_processing"):
                emotion = self.allma.emotional_system.process_stimulus(text)
                
            print(f"\nInput: {text}")
            print(f"Emozione rilevata: {emotion.primary_emotion}")
            print(f"Valenza emotiva: {emotion.valence:.2f}")
            
            self.assertIsNotNone(emotion)
            self.assertTrue(-1.0 <= emotion.valence <= 1.0)
            
    def test_2_memory_system(self):
        """Test completo del sistema di memoria"""
        print("\n=== Test Sistema Memoria ===")
        
        # Test memorizzazione
        memories = [
            ("Ho imparato Python", 0.8, {"tipo": "apprendimento"}),
            ("Ho risolto un bug", 0.7, {"tipo": "lavoro"}),
            ("Ho aiutato un collega", 0.6, {"tipo": "sociale"}),
            ("Ho completato il progetto", 0.9, {"tipo": "achievement"})
        ]
        
        for content, importance, context in memories:
            with self.profiler.profile("memory_storage"):
                memory = Memory(
                    content=content,
                    importance=importance,
                    context=context,
                    emotional_valence=random.uniform(-1, 1)
                )
                self.allma.memory_system.add_memory(memory.to_dict())
                print(f"\nMemorizzato: {content}")
                
        # Test recupero
        for content, _, context in memories:
            with self.profiler.profile("memory_retrieval"):
                recalled = self.allma.memory_system.recall_memory(content, context)
                print(f"\nRecuperate {len(recalled)} memorie per: {content}")
                self.assertTrue(len(recalled) > 0)
                
        # Test consolidamento
        with self.profiler.profile("memory_consolidation"):
            self.allma.memory_system._consolidate_memories()
            print("\nConsolidamento memorie completato")
            
    def test_3_cognitive_system(self):
        """Test completo del sistema cognitivo"""
        print("\n=== Test Sistema Cognitivo ===\n")
        
        test_inputs = [
            "Python è un linguaggio di programmazione versatile",
            "La Terra orbita intorno al Sole in un anno",
            "L'apprendimento automatico è un campo dell'intelligenza artificiale",
            "La memoria è fondamentale per l'apprendimento",
            "È frustrante quando il codice non funziona correttamente"
        ]
        
        with self.profiler.profile("cognitive_processing"):
            processor = EnhancedCognitiveProcessor()
            
            for input_text in test_inputs:
                print(f"Input: {input_text}")
                result = processor.process_input(input_text)
                concepts = result['concepts']
                print("Concetti estratti:", concepts)
                print()
                
                # Verifica che i concetti estratti siano validi
                self.assertIsInstance(concepts, list)
                for concept in concepts:
                    self.assertIsInstance(concept, tuple)
                    self.assertEqual(len(concept), 3)
                    self.assertIsInstance(concept[0], str)  # concetto
                    self.assertIsInstance(concept[1], str)  # tipo
                    self.assertIsInstance(concept[2], float)  # confidenza
                    self.assertGreaterEqual(concept[2], 0.0)
                    self.assertLessEqual(concept[2], 1.0)
                
        print("\n=== Report Performance ===")
        
    def test_4_integration(self):
        """Test completo dell'integrazione"""
        print("\n=== Test Integrazione Completa ===")
        
        test_scenarios = [
            "Sono felice di aver imparato a programmare in Python",
            "Mi rattrista vedere codice non ottimizzato",
            "È frustrante quando il codice non funziona",
            "Che gioia quando il test passa al primo tentativo!"
        ]
        
        for text in test_scenarios:
            with self.profiler.profile("complete_processing"):
                result = self.allma.process_input(text)
                
            print(f"\nScenario: {text}")
            print(f"Risultato:")
            print(f"- Concetti: {result['concepts']}")
            print(f"- Contesto emotivo: {result['emotional_context']}")
            print(f"- Confidenza: {result['confidence']:.2f}")
            
            self.assertIsInstance(result, dict)
            self.assertIn("concepts", result)
            self.assertIn("emotional_context", result)
            self.assertIn("confidence", result)
            
    def test_5_learning_progression(self):
        """Test della progressione dell'apprendimento"""
        print("\n=== Test Progressione Apprendimento ===")
        
        learning_sequence = [
            "Inizio a studiare Python",
            "Ho imparato le funzioni base",
            "Sto capendo gli oggetti",
            "Ora so usare le classi",
            "Posso creare progetti complessi"
        ]
        
        learning_levels = []
        for text in learning_sequence:
            with self.profiler.profile("learning_progression"):
                result = self.allma.process_input(text)
                learning_levels.append(result["learning_level"])
                
            print(f"\nInput: {text}")
            print(f"Livello apprendimento: {result['learning_level']}")
            
        # Verifica progressione
        self.assertTrue(any(b >= a for a, b in zip(learning_levels, learning_levels[1:])))
        
    def test_6_stress_test(self):
        """Stress test del sistema"""
        print("\n=== Stress Test ===")
        
        # Genera input casuali
        words = ["Python", "programmare", "felice", "triste", "bug", "successo", 
                "errore", "imparare", "memoria", "emozione", "test", "codice"]
        
        num_tests = 100
        print(f"\nEsecuzione {num_tests} test casuali...")
        
        with self.profiler.profile("stress_test"):
            for i in range(num_tests):
                # Genera frase casuale
                text = " ".join(random.choices(words, k=random.randint(3, 8)))
                result = self.allma.process_input(text)
                
                if i % 10 == 0:
                    print(f"Completati {i} test...")
                    
        print("\nStress test completato")
        
    def tearDown(self):
        """Report finale"""
        print("\n=== Report Performance ===")
        stats = self.profiler.get_statistics()
        
        for operation, metrics in stats.items():
            print(f"\n{operation}:")
            print(f"- Tempo medio: {metrics['avg_time']:.3f}s")
            print(f"- Tempo massimo: {metrics['max_time']:.3f}s")
            print(f"- Uso memoria medio: {metrics['avg_memory']:.2f}MB")
            print(f"- Uso memoria massimo: {metrics['max_memory']:.2f}MB")

if __name__ == '__main__':
    unittest.main(verbosity=2)
