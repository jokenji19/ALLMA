"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file contains test cases for the ALLMA core model.
Author: Cristof Bano
Created: January 2025
"""

import unittest
from datetime import datetime
import os
import sys
from typing import Dict, List, Optional

# Aggiungi il percorso root al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incremental_learning.training.allma_core import ALLMA
from incremental_learning.training.tokenizer import ALLMATokenizer

class TestALLMA(unittest.TestCase):
    def setUp(self):
        """Inizializza il modello per i test."""
        self.model = ALLMA()
        
    def test_model_initialization(self):
        """Test 1: Verifica inizializzazione corretta del modello"""
        self.assertEqual(self.model.embedding_dim, 256)
        self.assertIsNotNone(self.model.emotional_system)
        self.assertIsNotNone(self.model.memory)
        
    def test_tokenizer(self):
        """Test 2: Verifica funzionamento tokenizer"""
        test_text = "Ciao mondo!"
        self.model.tokenizer = ALLMATokenizer()
        tokens = self.model.tokenizer.tokenize(test_text)
        self.assertIsInstance(tokens, list)
        self.assertEqual(len(tokens), 3)  # "Ciao", "mondo", "!"
        self.assertEqual(tokens, ["Ciao", "mondo", "!"])
        
    def test_emotional_system(self):
        """Test 3: Verifica sistema emotivo"""
        test_input = "Sono molto felice oggi!"
        initial_emotion = self.model.emotional_system.get_current_emotion()
        emotional_state = self.model.emotional_system.process_emotion(test_input, valence=0.8)
        self.assertIsInstance(emotional_state, dict)
        self.assertIn("emotion", emotional_state)
        
    def test_memory_system(self):
        """Test 4: Verifica sistema di memoria"""
        test_input = "Ricorda questo."
        test_output = "Ok, lo ricorderò."
        self.model.memory.add_interaction(test_input, test_output)
        self.assertEqual(len(self.model.memory.memories), 1)
        
    def test_forward_pass(self):
        """Test 5: Verifica forward pass del modello"""
        test_input = "Come stai?"
        try:
            response = self.model.chat(test_input, temperature=0.7)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
        except Exception as e:
            self.fail(f"Errore durante la generazione: {str(e)}")
            
    def test_learning(self):
        """Test 6: Verifica capacità di apprendimento"""
        input_text = "Impara questo."
        try:
            loss = self.model.learn(input_text, 0.5)
            self.assertIsInstance(loss, float)
            self.assertGreaterEqual(loss, 0)
        except Exception as e:
            self.fail(f"Errore durante il training: {str(e)}")
            
    def test_emotional_learning(self):
        """Test 7: Verifica apprendimento con feedback emotivo"""
        test_input = "Questo è un test positivo!"
        initial_value = self.model.emotional_system.emotion_value
        self.model.emotional_system.process_emotion(test_input, valence=0.9)
        final_value = self.model.emotional_system.emotion_value
        self.assertGreater(final_value, initial_value)
        
    def test_conversation_context(self):
        """Test 8: Verifica gestione del contesto conversazionale"""
        input_text = "Mi ricordo di te."
        try:
            response = self.model.chat(input_text, temperature=0.7)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
        except Exception as e:
            self.fail(f"Errore durante la conversazione: {str(e)}")
            
if __name__ == '__main__':
    unittest.main()
