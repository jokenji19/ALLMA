import unittest
from datetime import datetime
from Model.incremental_learning.emotional_system import EmotionalSystem
from Model.incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem
from Model.incremental_learning.memory_system import MemorySystem

class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()
        self.cognitive_system = CognitiveEvolutionSystem()
        self.memory_system = MemorySystem()

    def test_full_experience_processing(self):
        """Test dell'integrazione completa tra tutti i sistemi"""
        # Input iniziale
        experience_text = "Ho fatto una scoperta importante che mi ha reso molto felice"
        emotional_valence = 0.9
        
        # 1. Processo emotivo
        emotion = self.emotional_system.process_stimulus(experience_text, emotional_valence)
        self.assertIsNotNone(emotion)
        self.assertGreater(emotion.intensity, 0)
        
        # 2. Processo cognitivo
        cognitive_experience = {
            "input": experience_text,
            "type": "discovery",
            "context": {"emotional_state": emotion.to_dict()}
        }
        cognitive_result = self.cognitive_system.process_experience(cognitive_experience)
        self.assertGreater(cognitive_result, 0)
        
        # 3. Memorizzazione
        memory_result = self.memory_system.process_experience(
            experience_text,
            emotional_valence=emotional_valence
        )
        self.assertTrue(memory_result["memory_stored"])
        
        # 4. Verifica della coerenza tra i sistemi
        # Recupera la memoria
        memories = self.memory_system.recall_memory(
            query="scoperta importante",
            context={"emotional_valence": emotional_valence}
        )
        self.assertGreater(len(memories), 0)
        
        # Verifica che l'emozione sia stata preservata
        retrieved_memory = memories[0]
        self.assertAlmostEqual(
            retrieved_memory["emotional_valence"],
            emotional_valence,
            places=1
        )
        
    def test_learning_transfer(self):
        """Test del trasferimento di apprendimento tra sistemi"""
        # Sequenza di esperienze correlate
        experiences = [
            ("Ho imparato una nuova tecnica", 0.6),
            ("Ho applicato la tecnica con successo", 0.8),
            ("Ho insegnato la tecnica a qualcun altro", 0.7)
        ]
        
        cognitive_improvements = []
        emotional_intensities = []
        memory_consolidations = []
        
        for text, valence in experiences:
            # Processo emotivo
            emotion = self.emotional_system.process_stimulus(text, valence)
            emotional_intensities.append(emotion.intensity)
            
            # Processo cognitivo
            cognitive_result = self.cognitive_system.process_experience({
                "input": text,
                "type": "learning",
                "context": {"emotional_state": emotion.to_dict()}
            })
            cognitive_improvements.append(cognitive_result)
            
            # Memorizzazione
            memory_result = self.memory_system.process_experience(text, valence)
            memory_consolidations.append(memory_result["memory_stored"])
            
        # Verifica il miglioramento progressivo
        self.assertTrue(all(cognitive_improvements[i] <= cognitive_improvements[i+1] 
                          for i in range(len(cognitive_improvements)-1)))
        
        # Verifica la coerenza emotiva
        self.assertTrue(all(emotional_intensities))
        
        # Verifica la memorizzazione
        self.assertTrue(all(memory_consolidations))
        
    def test_error_propagation(self):
        """Test che gli errori vengano gestiti correttamente tra i sistemi"""
        invalid_inputs = [
            "",  # Stringa vuota
            None,  # None
            "  ",  # Solo spazi
        ]
        
        for invalid_input in invalid_inputs:
            # Tutti i sistemi dovrebbero sollevare ValueError
            with self.assertRaises(ValueError):
                self.emotional_system.process_stimulus(invalid_input, 0.5)
                
            with self.assertRaises(ValueError):
                self.cognitive_system.process_experience({
                    "input": invalid_input,
                    "type": "test"
                })
                
            with self.assertRaises(ValueError):
                self.memory_system.process_experience(invalid_input, 0.5)

if __name__ == '__main__':
    unittest.main()
