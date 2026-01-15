"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file contains test cases for the Emotional Intelligence System.
Author: Cristof Bano
Created: January 2025

This test suite validates:
- Emotional analysis
- Context awareness
- Response generation
- Emotional memory
"""

import unittest
from datetime import datetime, timedelta
from allma_model.incremental_learning.emotional_system import EmotionalSystem, Emotion

class TestEmotionalSystem(unittest.TestCase):
    def setUp(self):
        self.emotional_system = EmotionalSystem()
        
    def test_process_emotion(self):
        """Testa il processamento delle emozioni"""
        # Test emozione base
        emotion = self.emotional_system.process_emotion("joy", 0.8)
        self.assertEqual(emotion.name, "joy")
        self.assertEqual(emotion.valence, 0.8)
        self.assertGreater(emotion.arousal, 0)
        self.assertGreater(emotion.intensity, 0)
        
        # Test con contesto
        context = {"is_novel": True, "is_social": True}
        emotion = self.emotional_system.process_emotion("surprise", 0.6, context)
        self.assertEqual(emotion.name, "surprise")
        self.assertEqual(emotion.context, context)
        self.assertGreater(emotion.intensity, 0.6)  # Intensità aumentata dal contesto
        
    def test_emotional_state_updates(self):
        """Testa l'aggiornamento dello stato emotivo"""
        # Stato iniziale
        initial_state = self.emotional_system.get_emotional_state()
        self.assertEqual(initial_state['primary_emotion']['name'], "neutral")
        
        # Dopo un'emozione positiva
        self.emotional_system.process_emotion("joy", 0.8)
        state = self.emotional_system.get_emotional_state()
        self.assertEqual(state['primary_emotion']['name'], "joy")
        self.assertGreater(state['mood'], 0)
        
        # Dopo un'emozione negativa
        self.emotional_system.process_emotion("sadness", -0.7)
        state = self.emotional_system.get_emotional_state()
        self.assertEqual(state['primary_emotion']['name'], "sadness")
        self.assertLess(state['mood'], state['primary_emotion']['valence'])
        
    def test_emotion_regulation(self):
        """Testa la regolazione emotiva"""
        # Emozione molto intensa
        emotion = self.emotional_system.process_emotion("anger", 0.9)
        state = self.emotional_system.get_emotional_state()
        
        # Verifica che la regolazione abbia ridotto l'intensità
        self.assertLess(state['primary_emotion']['intensity'], emotion.intensity)
        self.assertGreater(state['stress_level'], 0)
        
        # Test della capacità di regolazione
        initial_capacity = state['regulation_capacity']
        self.emotional_system.process_emotion("fear", 0.8)
        new_state = self.emotional_system.get_emotional_state()
        self.assertLess(new_state['regulation_capacity'], initial_capacity)
        
    def test_emotional_patterns(self):
        """Testa l'analisi dei pattern emotivi"""
        # Aggiungi una sequenza di emozioni
        emotions = [
            ("joy", 0.7),
            ("surprise", 0.5),
            ("joy", 0.8),
            ("sadness", -0.6)
        ]
        
        for name, valence in emotions:
            self.emotional_system.process_emotion(name, valence)
            
        # Analizza i pattern
        patterns = self.emotional_system.analyze_emotional_pattern()
        
        self.assertIn('dominant_emotion', patterns)
        self.assertEqual(patterns['dominant_emotion'], 'joy')
        self.assertIn('emotional_variability', patterns)
        self.assertGreater(patterns['emotional_variability'], 0)
        
    def test_empathy(self):
        """Testa la simulazione dell'empatia"""
        # Prepara lo stato emotivo
        self.emotional_system.process_emotion("joy", 0.6)
        
        # Simula l'empatia per un'emozione osservata
        observed_emotion = {
            'name': 'sadness',
            'valence': -0.7,
            'intensity': 0.8
        }
        
        empathic_emotion, understanding = self.emotional_system.simulate_empathy(observed_emotion)
        
        # Verifica la risposta empatica
        self.assertEqual(empathic_emotion.name, "empathic_sadness")
        self.assertLess(empathic_emotion.valence, 0)
        self.assertGreater(understanding, 0)
        self.assertLess(understanding, 1)
        
    def test_emotional_memory(self):
        """Testa la memoria emotiva"""
        # Aggiungi alcune emozioni
        self.emotional_system.process_emotion("joy", 0.8)
        self.emotional_system.process_emotion("sadness", -0.6)
        
        # Verifica che le emozioni siano state memorizzate
        self.assertGreater(len(self.emotional_system.emotional_memory), 0)
        
        # Verifica che le emozioni siano ordinate temporalmente
        self.assertGreater(
            self.emotional_system.emotional_memory[-1].timestamp,
            self.emotional_system.emotional_memory[0].timestamp
        )
        
    def test_stress_management(self):
        """Testa la gestione dello stress"""
        # Stato iniziale
        initial_state = self.emotional_system.get_emotional_state()
        initial_stress = initial_state['stress_level']
        
        # Aggiungi emozioni negative intense
        self.emotional_system.process_emotion("fear", -0.9)
        self.emotional_system.process_emotion("anger", -0.8)
        
        # Verifica l'aumento dello stress
        high_stress_state = self.emotional_system.get_emotional_state()
        self.assertGreater(high_stress_state['stress_level'], initial_stress)
        
        # Aggiungi emozioni positive per ridurre lo stress
        self.emotional_system.process_emotion("joy", 0.8)
        self.emotional_system.process_emotion("trust", 0.7)
        
        # Verifica la riduzione dello stress
        final_state = self.emotional_system.get_emotional_state()
        self.assertLess(final_state['stress_level'], high_stress_state['stress_level'])
        
    def test_emotional_energy(self):
        """Testa la gestione dell'energia emotiva"""
        # Stato iniziale
        initial_state = self.emotional_system.get_emotional_state()
        initial_energy = initial_state['emotional_energy']
        
        # Processa molte emozioni intense
        for _ in range(5):
            self.emotional_system.process_emotion("anger", -0.9)
            
        # Verifica il consumo di energia
        depleted_state = self.emotional_system.get_emotional_state()
        self.assertLess(depleted_state['emotional_energy'], initial_energy)
        
        # Recupero con emozioni positive
        self.emotional_system.process_emotion("joy", 0.8)
        recovered_state = self.emotional_system.get_emotional_state()
        self.assertGreater(recovered_state['emotional_energy'], depleted_state['emotional_energy'])

if __name__ == '__main__':
    unittest.main()
