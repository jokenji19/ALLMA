"""
Test completo del modello ALLMA
"""
import unittest
from incremental_learning.integrated_allma import IntegratedALLMA
from incremental_learning.memory_system import Memory
from incremental_learning.emotional_system import Emotion
from datetime import datetime
import random

class TestALLMA(unittest.TestCase):
    def setUp(self):
        """Inizializza ALLMA per ogni test"""
        self.allma = IntegratedALLMA()
        
    def test_emotional_processing(self):
        """Test del sistema emotivo"""
        print("\nTest elaborazione emotiva...")
        
        # Test emozioni base
        inputs = {
            "Sono molto felice oggi!": ("gioia", 0.8),
            "Mi sento triste...": ("tristezza", -0.6),
            "Che rabbia!": ("rabbia", -0.7),
            "Ho paura del buio": ("paura", -0.5),
            "Sono sorpreso dal risultato": ("sorpresa", 0.4)
        }
        
        for text, (expected_emotion, expected_valence) in inputs.items():
            emotion = self.allma.emotional_system.process_stimulus(text)
            self.assertIsNotNone(emotion)
            self.assertIsInstance(emotion, Emotion)
            self.assertTrue(-1.0 <= emotion.valence <= 1.0)
            print(f"Input: {text}")
            print(f"Emozione: {emotion.primary_emotion}, Valenza: {emotion.valence:.2f}")
            
    def test_memory_operations(self):
        """Test del sistema di memoria"""
        print("\nTest operazioni di memoria...")
        
        # Test aggiunta memoria
        memories = [
            ("Ho mangiato una pizza", 0.8, {"tipo": "cibo"}),
            ("Ho visto un film", 0.5, {"tipo": "intrattenimento"}),
            ("Ho studiato matematica", 0.3, {"tipo": "studio"}),
            ("Ho fatto una passeggiata", 0.6, {"tipo": "attività"})
        ]
        
        for content, importance, context in memories:
            memory = Memory(
                content=content,
                importance=importance,
                context=context,
                emotional_valence=random.uniform(-1, 1)
            )
            self.allma.memory_system.add_memory(memory.to_dict())
            print(f"Aggiunta memoria: {content}")
            
        # Test recupero memoria
        for content, _, context in memories:
            recalled = self.allma.memory_system.recall_memory(content, context)
            self.assertIsInstance(recalled, list)
            print(f"Recuperate {len(recalled)} memorie per: {content}")
            
    def test_cognitive_processing(self):
        """Test del sistema cognitivo"""
        print("\nTest elaborazione cognitiva...")
        
        inputs = [
            "Python è un linguaggio di programmazione",
            "La Terra gira intorno al Sole",
            "I gatti sono mammiferi",
            "L'acqua bolle a 100 gradi"
        ]
        
        for text in inputs:
            result = self.allma.cognitive_processor.process_input(text)
            self.assertIsInstance(result, dict)
            self.assertIn("concepts", result)
            print(f"Input: {text}")
            print(f"Concetti estratti: {result['concepts']}")
            
    def test_integrated_processing(self):
        """Test dell'integrazione completa"""
        print("\nTest integrazione completa...")
        
        inputs = [
            "Sono felice di aver imparato qualcosa di nuovo",
            "Mi rattrista vedere la povertà nel mondo",
            "Mi arrabbio quando le cose non funzionano",
            "Sono sorpreso di quanto sia facile usare Python"
        ]
        
        for text in inputs:
            result = self.allma.process_input(text)
            self.assertIsInstance(result, dict)
            print(f"\nInput: {text}")
            print(f"Risultato integrazione:")
            print(f"- Concetti: {result['concepts']}")
            print(f"- Contesto emotivo: {result['emotional_context']}")
            print(f"- Confidenza: {result['confidence']:.2f}")
            
    def test_learning_progression(self):
        """Test della progressione dell'apprendimento"""
        print("\nTest progressione apprendimento...")
        
        # Simula una sequenza di interazioni
        interactions = [
            "Mi piace programmare in Python",
            "Python ha molte librerie utili",
            "Sto imparando a usare le classi",
            "La programmazione orientata agli oggetti è interessante"
        ]
        
        learning_levels = []
        for text in interactions:
            result = self.allma.process_input(text)
            learning_levels.append(result["learning_level"])
            print(f"Input: {text}")
            print(f"Livello apprendimento: {result['learning_level']}")
            
        # Verifica che ci sia una progressione
        self.assertTrue(any(b >= a for a, b in zip(learning_levels, learning_levels[1:])))

if __name__ == '__main__':
    unittest.main(verbosity=2)
