"""
Test di integrazione completo per i sistemi ALLMA
"""

import unittest
from datetime import datetime
import torch
from allma_model.incremental_learning.curiosity_system import CuriosityDrive
from allma_model.incremental_learning.emotional_system import EmotionalSystem, EmotionType, Emotion, EmotionalState
from allma_model.incremental_learning.subconscious_ethical_system import SubconsciousEthicalSystem, EthicalContext
from allma_model.incremental_learning.memory_system import MemorySystem, MemoryItem

class TestALLMAIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi principali"""
        self.curiosity = CuriosityDrive()
        self.emotional = EmotionalSystem()
        self.ethical = SubconsciousEthicalSystem()
        self.memory = MemorySystem()

    def test_curiosity_system(self):
        """Test del sistema di curiosità"""
        # Test elaborazione input
        input_text = "Mi piace molto la fotografia di paesaggio"
        result = self.curiosity.process_input(input_text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('questions', result)
        self.assertGreater(len(result['questions']), 0)
        
        # Test evoluzione curiosità
        self.curiosity.curiosity_evolution.evolve(self.curiosity.development_state)
        self.assertGreater(self.curiosity.development_state['knowledge_level'], 0.3)

    def test_emotional_system(self):
        """Test del sistema emotivo"""
        # Test processamento emozione
        emotion = self.emotional.process_emotion(
            name='joy',
            valence=0.8,
            context={"situation": "learning"}
        )
        self.assertIsInstance(emotion, Emotion)
        self.assertEqual(emotion.primary_emotion, EmotionType.JOY)
        self.assertGreater(emotion.intensity, 0)

        # Test regolazione emotiva
        self.emotional.current_state = EmotionalState(primary_emotion=emotion)
        regulated = self.emotional.regulate_emotion(emotion)
        self.assertIsInstance(regulated, Emotion)
        self.assertLessEqual(regulated.intensity, emotion.intensity)

    def test_ethical_system(self):
        """Test del sistema etico"""
        # Test valutazione etica
        context = EthicalContext(
            action_type="response",
            potential_impact=0.5,
            involved_entities=["user"],
            timestamp=datetime.now().timestamp(),
            context_data={"topic": "fotografia"}
        )
        
        intuition = self.ethical.process_action(
            "Vorrei aiutarti a migliorare le tue foto",
            context
        )
        
        self.assertGreater(intuition.strength, 0)
        self.assertEqual(intuition.nature, "supportive")

    def test_memory_system(self):
        """Test del sistema di memoria"""
        # Test memorizzazione esperienza
        content = "L'utente ha mostrato interesse per la fotografia di paesaggio"
        self.memory.process_experience(
            content=content,
            emotional_valence=0.7,
            context={"topic": "fotografia", "interaction_type": "learning"}
        )

        # Test recupero memoria
        recalled = self.memory.recall_memory(
            query="fotografia paesaggio",
            context={"topic": "fotografia"}
        )
        self.assertGreater(len(recalled), 0)

    def test_system_integration(self):
        """Test dell'integrazione tra tutti i sistemi"""
        # Input utente simulato
        user_input = "Vorrei imparare a fotografare meglio i paesaggi al tramonto"
        
        # 1. Processo emotivo
        emotion = self.emotional.process_emotion(
            name='anticipation',
            valence=0.6,
            context={"situation": "learning"}
        )
        
        # 2. Valutazione etica
        ethical_context = EthicalContext(
            action_type="learning",
            potential_impact=0.3,
            involved_entities=["user"],
            timestamp=datetime.now().timestamp(),
            context_data={"topic": "fotografia"}
        )
        ethical_intuition = self.ethical.process_action(user_input, ethical_context)
        
        # 3. Generazione curiosità
        curiosity_response = self.curiosity.process_input(user_input)
        
        # 4. Memorizzazione esperienza
        self.memory.process_experience(
            content=user_input,
            emotional_valence=emotion.valence,
            context={
                "topic": "fotografia",
                "ethical_evaluation": ethical_intuition.nature,
                "curiosity_questions": curiosity_response['questions']
            }
        )
        
        # Verifica integrazione
        self.assertIsNotNone(emotion)
        self.assertIsNotNone(ethical_intuition)
        self.assertIsNotNone(curiosity_response)
        
        # Verifica memoria
        memories = self.memory.recall_memory("fotografia tramonto")
        self.assertGreater(len(memories), 0)

    def test_learning_cycle(self):
        """Test del ciclo di apprendimento completo"""
        initial_knowledge = self.curiosity.development_state['knowledge_level']
        
        # Simula una sessione di apprendimento
        for _ in range(5):
            # Input simulato con progressione
            inputs = [
                "Base della fotografia paesaggistica",
                "Tecniche di composizione avanzate",
                "Uso dei filtri ND",
                "Post-produzione paesaggi",
                "Tecniche di fotografia notturna"
            ]
            
            for input_text in inputs:
                # Processo completo
                emotion = self.emotional.process_emotion(
                    name='joy',
                    valence=0.7,
                    context={"situation": "learning"}
                )
                ethical_intuition = self.ethical.process_action(
                    input_text,
                    EthicalContext(
                        action_type="learning",
                        potential_impact=0.4,
                        involved_entities=["user"],
                        timestamp=datetime.now().timestamp(),
                        context_data={"topic": "fotografia"}
                    )
                )
                
                self.curiosity.process_input(input_text)
                self.memory.process_experience(
                    content=input_text,
                    emotional_valence=emotion.valence
                )
        
        # Verifica apprendimento
        final_knowledge = self.curiosity.development_state['knowledge_level']
        self.assertGreater(final_knowledge, initial_knowledge)

if __name__ == '__main__':
    unittest.main()
