import unittest
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Aggiungi il percorso della directory Model al PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from Model.incremental_learning.meta_learning_system import MetaLearningSystem
from Model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem, Pattern
from Model.incremental_learning.curiosity_system import CuriosityDrive
from Model.incremental_learning.contextual_learning_system import ContextualLearningSystem
from Model.incremental_learning.emotional_system import EmotionalSystem, Emotion, EmotionType
from Model.incremental_learning.memory_system import MemorySystem
from Model.incremental_learning.reasoning_system import ReasoningSystem
from Model.incremental_learning.communication_system import CommunicationSystem

class TestALLMAIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi principali"""
        self.meta_learning = MetaLearningSystem()
        self.pattern_recognition = PatternRecognitionSystem()
        self.curiosity = CuriosityDrive()
        self.contextual_learning = ContextualLearningSystem()
        self.emotional = EmotionalSystem()
        self.memory = MemorySystem()
        self.reasoning = ReasoningSystem()
        self.communication = CommunicationSystem()
        
        # Registra tutti i sistemi con il meta-learning
        self.meta_learning.register_system(self.pattern_recognition, "pattern_recognition")
        self.meta_learning.register_system(self.curiosity, "curiosity")
        self.meta_learning.register_system(self.contextual_learning, "contextual_learning")
        self.meta_learning.register_system(self.emotional, "emotional")
        self.meta_learning.register_system(self.memory, "memory")
        self.meta_learning.register_system(self.reasoning, "reasoning")
        self.meta_learning.register_system(self.communication, "communication")

    def test_system_initialization(self):
        """Verifica che tutti i sistemi siano inizializzati correttamente"""
        self.assertIsNotNone(self.meta_learning)
        self.assertIsNotNone(self.pattern_recognition)
        self.assertIsNotNone(self.curiosity)
        self.assertIsNotNone(self.contextual_learning)
        self.assertIsNotNone(self.emotional)
        self.assertIsNotNone(self.memory)
        self.assertIsNotNone(self.reasoning)
        self.assertIsNotNone(self.communication)

    def test_meta_learning_registration(self):
        """Verifica che tutti i sistemi siano registrati correttamente"""
        state = self.meta_learning.get_system_state()
        self.assertIn("pattern_recognition", state)
        self.assertIn("curiosity", state)
        self.assertIn("contextual_learning", state)
        self.assertIn("emotional", state)
        self.assertIn("memory", state)
        self.assertIn("reasoning", state)
        self.assertIn("communication", state)

    def test_learning_cycle(self):
        """Testa un ciclo completo di apprendimento"""
        content = "Questa è una frase di test per il ciclo di apprendimento"
        print("\n=== Input dell'utente ===")
        print(f"Frase: '{content}'")
        
        # Pattern Recognition
        print("\n=== Pattern Recognition ===")
        patterns = self.pattern_recognition.analyze_pattern(content)
        print(f"Pattern trovati: {patterns}")
        self.assertIsNotNone(patterns)
        
        # Curiosity
        print("\n=== Analisi Curiosità ===")
        unknown_concepts = self.curiosity.detect_unknown_concepts(content, {})
        print(f"Concetti sconosciuti trovati: {unknown_concepts}")
        self.assertIsNotNone(unknown_concepts)
        
        # Contextual Learning
        print("\n=== Apprendimento Contestuale ===")
        context = self.contextual_learning.process_input(content)
        print(f"Contesto generato: {context}")
        self.assertIsNotNone(context)
        
        # Emotional Response
        print("\n=== Risposta Emotiva ===")
        emotion = self.emotional.process_stimulus(content)
        print(f"Emozione generata: {emotion}")
        print(f"- Emozione primaria: {emotion.primary_emotion}")
        print(f"- Intensità: {emotion.intensity}")
        print(f"- Valenza: {emotion.valence}")
        if emotion.secondary_emotions:
            print(f"- Emozioni secondarie: {emotion.secondary_emotions}")
        self.assertIsNotNone(emotion)
        self.assertIsInstance(emotion, Emotion)
        self.assertIsInstance(emotion.primary_emotion, EmotionType)
        self.assertGreaterEqual(emotion.intensity, 0.05)
        self.assertLessEqual(emotion.intensity, 1.0)
        self.assertGreaterEqual(emotion.valence, -1.0)
        self.assertLessEqual(emotion.valence, 1.0)
        
        # Memory Storage
        print("\n=== Memorizzazione ===")
        memory_item = {'content': content, 'context': context}
        self.memory.add_memory(memory_item)
        print(f"Memorizzato: {memory_item}")
        
        # Reasoning
        print("\n=== Ragionamento ===")
        understanding = self.reasoning.process_input(content)
        print(f"Comprensione: {understanding}")
        self.assertIsNotNone(understanding)
        
        # Communication
        print("\n=== Generazione Risposta ===")
        response = self.communication.generate_response(content, emotion=emotion)
        print(f"Risposta generata: {response.content}")
        print(f"Stile comunicativo: {response.style}")
        print(f"Contesto risposta: {response.context}")
        self.assertIsNotNone(response)
        
        # Meta Learning
        print("\n=== Meta-Apprendimento ===")
        learning_result = self.meta_learning.learn(content, context)
        print(f"Risultato apprendimento: {learning_result}")
        self.assertIsNotNone(learning_result)
        self.assertIn("strategy", learning_result)
        self.assertIn("success", learning_result)

    def test_system_interaction(self):
        """Testa l'interazione tra i vari sistemi"""
        # Input di test
        content = "Questa è una frase di test per l'interazione tra sistemi"
        
        # Test Pattern Recognition -> Curiosity
        patterns = self.pattern_recognition.analyze_pattern(content)
        self.assertIsNotNone(patterns)
        unknown_patterns = self.curiosity.detect_unknown_concepts(content, patterns)
        self.assertIsNotNone(unknown_patterns)
        
        # Test Curiosity -> Contextual Learning
        context = self.contextual_learning.process_input(content)
        self.assertIsNotNone(context)
        
        # Test Contextual Learning -> Emotional
        emotional_response = self.emotional.process_stimulus(content)
        self.assertIsNotNone(emotional_response)
        self.assertIsInstance(emotional_response, Emotion)
        self.assertIsInstance(emotional_response.primary_emotion, EmotionType)
        self.assertGreaterEqual(emotional_response.intensity, 0.05)
        self.assertLessEqual(emotional_response.intensity, 1.0)
        self.assertGreaterEqual(emotional_response.valence, -1.0)
        self.assertLessEqual(emotional_response.valence, 1.0)
        
        # Test Emotional -> Memory
        memory_item = {
            'content': content,
            'context': context,
            'emotion': emotional_response.primary_emotion.value
        }
        self.memory.add_memory(memory_item)
        
        # Test Memory -> Reasoning
        understanding = self.reasoning.process_input(content)
        self.assertIsNotNone(understanding)
        
        # Test Reasoning -> Communication
        response = self.communication.generate_response(content, emotion=emotional_response)
        self.assertIsNotNone(response)
        
        # Test Communication -> Meta Learning
        learning_result = self.meta_learning.learn(content, context)
        self.assertIsNotNone(learning_result)
        self.assertIn("strategy", learning_result)
        self.assertIn("success", learning_result)

    def test_system_interaction(self):
        """Testa l'interazione tra i vari sistemi"""
        # Input di test
        content = "Questa è una frase di test per l'interazione tra sistemi"
        
        # Test Pattern Recognition -> Curiosity
        patterns = self.pattern_recognition.analyze_pattern(content)
        self.assertIsNotNone(patterns)
        unknown_patterns = self.curiosity.detect_unknown_concepts(content, patterns)
        self.assertIsNotNone(unknown_patterns)
        
        # Test Curiosity -> Contextual Learning
        context = self.contextual_learning.process_input(content)
        self.assertIsNotNone(context)
        
        # Test Contextual Learning -> Emotional
        emotional_response = self.emotional.process_stimulus(content)
        self.assertIsNotNone(emotional_response)
        self.assertIsInstance(emotional_response, Emotion)
        self.assertIsInstance(emotional_response.primary_emotion, EmotionType)
        self.assertGreaterEqual(emotional_response.intensity, 0.05)
        self.assertLessEqual(emotional_response.intensity, 1.0)
        self.assertGreaterEqual(emotional_response.valence, -1.0)
        self.assertLessEqual(emotional_response.valence, 1.0)
        
        # Test Emotional -> Memory
        memory_item = {
            'content': content,
            'context': context,
            'emotion': emotional_response.primary_emotion.value
        }
        self.memory.add_memory(memory_item)
        
        # Test Memory -> Reasoning
        understanding = self.reasoning.process_input(content)
        self.assertIsNotNone(understanding)
        
        # Test Reasoning -> Communication
        response = self.communication.generate_response(content, emotion=emotional_response)
        self.assertIsNotNone(response)
        
        # Test Communication -> Meta Learning
        learning_result = self.meta_learning.learn(content, context)
        self.assertIsNotNone(learning_result)
        self.assertIn("strategy", learning_result)
        self.assertIn("success", learning_result)

    def test_error_handling_pattern_recognition(self):
        """Testa la gestione degli errori per pattern_recognition"""
        with self.assertRaises(ValueError):
            self.pattern_recognition.analyze_pattern(None)
            
    def test_error_handling_curiosity(self):
        """Testa la gestione degli errori per curiosity"""
        with self.assertRaises(ValueError):
            self.curiosity.detect_unknown_concepts(None, {})
            
    def test_error_handling_contextual_learning(self):
        """Testa la gestione degli errori per contextual_learning"""
        with self.assertRaises(ValueError):
            self.contextual_learning.process_input(None)
            
    def test_error_handling_emotional(self):
        """Testa la gestione degli errori per emotional"""
        with self.assertRaises(ValueError):
            self.emotional.process_stimulus(None)
            
    def test_error_handling_memory(self):
        """Testa la gestione degli errori per memory"""
        with self.assertRaises(ValueError):
            self.memory.add_memory({'content': None, 'context': {}})
            
    def test_error_handling_reasoning(self):
        """Testa la gestione degli errori per reasoning"""
        with self.assertRaises(ValueError):
            self.reasoning.process_input(None)
            
    def test_error_handling_communication(self):
        """Testa la gestione degli errori per communication"""
        with self.assertRaises(ValueError):
            self.communication.generate_response(None, emotion=None)
            
    def test_error_handling_meta_learning(self):
        """Testa la gestione degli errori per meta_learning"""
        with self.assertRaises(ValueError):
            self.meta_learning.learn(None, None)

    def test_performance_metrics(self):
        """Testa le metriche di performance"""
        # Esegui alcune operazioni di apprendimento
        for i in range(5):
            content = f"Test content {i}"
            context = {"type": "test", "iteration": i}
            self.meta_learning.learn(content, context)
        
        # Ottieni le metriche
        insights = self.meta_learning.analyze_learning_process()
        
        # Verifica che ci siano insights per ogni sistema
        system_names = {insight.system_name for insight in insights}
        expected_systems = {"pattern_recognition", "curiosity", "contextual_learning", 
                          "emotional", "memory", "reasoning", "communication"}
        
        self.assertTrue(all(sys in system_names for sys in expected_systems))
        
        # Verifica che ogni insight abbia valori validi
        for insight in insights:
            self.assertIsNotNone(insight.value)
            self.assertGreaterEqual(insight.confidence, 0.0)
            self.assertLessEqual(insight.confidence, 1.0)

    def test_emotion(self):
        """Testa l'oggetto Emotion"""
        emotion = Emotion(
            primary_emotion=EmotionType.JOY,
            intensity=0.5,
            valence=0.5
        )
        self.assertIsNotNone(emotion)
        self.assertEqual(emotion.primary_emotion, EmotionType.JOY)

if __name__ == '__main__':
    unittest.main()
