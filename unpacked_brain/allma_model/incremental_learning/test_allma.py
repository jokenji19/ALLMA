import sys
import os
import unittest
import torch
import time
from pathlib import Path

from allma_model.incremental_learning.training.allma_core import (
    ALLMA, ALLMATokenizer, Memory, 
    EmotionalSystem
)

class TestALLMA(unittest.TestCase):
    def setUp(self):
        """Inizializza ALLMA e i suoi componenti per i test"""
        self.tokenizer = ALLMATokenizer()
        self.model = ALLMA()
        self.memory = Memory(content="", importance=0.0, timestamp=time.time(), context={})
        self.emotional_system = EmotionalSystem()

    def test_tokenizer(self):
        """Testa il tokenizer"""
        print("\nTest Tokenizer...")
        test_text = "Ciao, come stai?"
        tokens = self.tokenizer(test_text)
        decoded = self.tokenizer.decode(tokens)
        print(f"Testo originale: {test_text}")
        print(f"Tokens: {tokens}")
        print(f"Testo decodificato: {decoded}")
        self.assertIsInstance(tokens, torch.Tensor)
        self.assertTrue(len(tokens.shape) == 1)  # Should be a 1D tensor

    def test_emotional_system(self):
        """Testa il sistema emotivo"""
        print("\nTest Sistema Emotivo...")
        self.emotional_system.update(
            stimulus="Test input",
            feedback=0.8,
            learning_success=0.9
        )
        print(f"Stato emotivo: {self.emotional_system.emotions}")
        self.assertIsInstance(self.emotional_system.emotions, dict)

    def test_memory_system(self):
        """Testa il sistema di memoria"""
        print("\nTest Sistema di Memoria...")
        
        test_input = "Come funziona la memoria?"
        test_output = "La memoria è un sistema complesso..."
        
        # Test aggiunta alla memoria
        self.memory.add_interaction(test_input, test_output)
        recent = self.memory.get_recent_interactions(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], (test_input, test_output))
        print(f"Memoria a breve termine: {recent}")
        
        # Test consolidamento memoria
        self.memory.consolidate_memories()
        self.assertEqual(len(self.memory.short_term), 0)
        self.assertEqual(len(self.memory.long_term), 1)
        
        # Test limite capacità
        for i in range(1100):  # Superiore alla capacità
            self.memory.add_interaction(f"Input {i}", f"Output {i}")
        
        # Verifica che la memoria a breve termine non superi la capacità
        self.assertLessEqual(len(self.memory.short_term), self.memory.capacity)
        
        # Test pulizia memoria
        self.memory.clear()
        self.assertEqual(len(self.memory.short_term), 0)
        self.assertEqual(len(self.memory.long_term), 0)

    def test_learning_system(self):
        """Testa il sistema di apprendimento avanzato"""
        print("\nTest Sistema di Apprendimento...")
        
        # Test di apprendimento base
        input_text = "Ciao, come stai?"
        target_output = "Sto bene, grazie! E tu?"
        
        # Prima risposta (dovrebbe essere casuale o predefinita)
        initial_response = self.model.chat(input_text)
        print(f"Risposta iniziale: {initial_response}")
        
        # Facciamo un po' di training
        print("\nInizio training...")
        successes = []
        for _ in range(5):
            success = self.model.learn(input_text, target_output, feedback=0.8)
            successes.append(success)
            print(f"Step di training completato - Successo: {success:.3f}")
        
        # Verifica che il successo medio aumenti
        avg_success = sum(successes) / len(successes)
        print(f"Successo medio: {avg_success:.3f}")
        self.assertTrue(avg_success > 0.2)  # Dovrebbe esserci almeno un minimo di apprendimento
        
        # Test dell'influenza emotiva
        print("\nTest influenza emotiva...")
        self.model.emotional_system.update("Test positivo", 1.0, 0.9)  # Stato emotivo positivo
        success_happy = self.model.learn(input_text, target_output, feedback=0.8)
        
        self.model.emotional_system.update("Test negativo", -0.5, 0.3)  # Stato emotivo negativo
        success_sad = self.model.learn(input_text, target_output, feedback=0.8)
        
        print(f"Successo con emozione positiva: {success_happy:.3f}")
        print(f"Successo con emozione negativa: {success_sad:.3f}")
        self.assertTrue(success_happy > success_sad)  # L'apprendimento dovrebbe essere migliore in stato positivo
        
        # Test del curriculum learning
        print("\nTest curriculum learning...")
        self.model.developmental_age = 50.0  # Simuliamo un'età di sviluppo avanzata
        variations = set()
        for _ in range(5):
            variation = self.model._create_input_variation(input_text)
            variations.add(variation)
            print(f"Variazione generata: {variation}")
        
        # Dovrebbe generare almeno alcune variazioni diverse
        self.assertTrue(len(variations) > 1)
        
        # Test risposta finale
        print("\nTest risposta finale...")
        final_response = self.model.chat(input_text)
        print(f"Risposta finale: {final_response}")
        
        # La risposta finale dovrebbe essere diversa da quella iniziale
        self.assertNotEqual(initial_response, final_response)
        print("\nTest sistema di apprendimento completato!")

    def test_complete_interaction(self):
        """Testa un'interazione completa"""
        print("\nTest Interazione Completa...")
        
        test_input = "Ciao! Sono nuovo qui."
        print(f"Input: {test_input}")
        
        # Test chat
        response = self.model.chat(test_input)
        print(f"Risposta: {response}")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
        # Test apprendimento
        target = "Benvenuto! Piacere di conoscerti."
        success = self.model.learn(test_input, target, feedback=0.8)
        self.assertIsInstance(success, float)
        self.assertTrue(0 <= success <= 1)
        
        # Test memoria
        recent = self.memory.get_recent_interactions(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0][0], test_input)
        
        # Test emozioni
        emotion = self.model.emotional_system.get_current_emotion()
        self.assertIsInstance(emotion, str)

if __name__ == '__main__':
    unittest.main(verbosity=2)
