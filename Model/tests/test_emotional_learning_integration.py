"""Test di integrazione tra il sistema emotivo e il sistema di apprendimento."""

import unittest
from datetime import datetime
import json
import os
from Model.emotional_system.emotional_core import EmotionalCore
from Model.learning_system.incremental_learning import (
    IncrementalLearner,
    LearningUnit,
    FeedbackType,
    ConfidenceLevel
)
from Model.personality_system.personality import Personality
from Model.memory_system.knowledge_memory import KnowledgeMemory

class TestEmotionalLearningIntegration(unittest.TestCase):
    """Test dell'integrazione tra emozioni e apprendimento."""
    
    def setUp(self):
        """Setup per i test."""
        self.test_dir = "Model/data/test"
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, "test_emotional_learning.db")
        self.emotional_core = EmotionalCore()
        self.learner = IncrementalLearner()
        self.personality = Personality()
        self.knowledge_memory = KnowledgeMemory(self.db_path)
        
    def tearDown(self):
        """Cleanup dopo i test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
            
    def test_emotional_impact_on_learning(self):
        """Test dell'impatto delle emozioni sull'apprendimento."""
        # 1. Simula diverse situazioni emotive durante l'apprendimento
        scenarios = [
            {
                "emotion": "excited",
                "message": "I can't wait to learn more about AI!",
                "topic": "ai_fundamentals",
                "content": "Basic concepts of artificial intelligence",
                "expected_confidence": ConfidenceLevel.HIGH
            },
            {
                "emotion": "frustrated",
                "message": "This neural network concept is confusing",
                "topic": "neural_networks",
                "content": "Neural network architecture and training",
                "expected_confidence": ConfidenceLevel.LOW
            },
            {
                "emotion": "satisfied",
                "message": "The reinforcement learning examples really helped",
                "topic": "reinforcement_learning",
                "content": "Principles of reinforcement learning",
                "expected_confidence": ConfidenceLevel.MEDIUM
            }
        ]
        
        for scenario in scenarios:
            # Rileva l'emozione
            detected_emotion = self.emotional_core.detect_emotion(
                scenario["message"]
            )
            
            # Adatta la personalità all'emozione
            self.personality.adapt_to_emotion(self.emotional_core)
            
            # Crea unità di apprendimento con influenza emotiva
            unit = LearningUnit(
                topic=scenario["topic"],
                content=scenario["content"],
                source="emotional_learning",
                confidence=scenario["expected_confidence"],
                timestamp=datetime.now()
            )
            
            # Aggiungi metadati emotivi
            unit.metadata = {
                "emotion": detected_emotion,
                "emotional_intensity": self.emotional_core.get_intensity()
            }
            
            # Memorizza l'unità
            self.learner.add_learning_unit(unit)
            
            # Verifica l'impatto dell'emozione
            state = self.learner.get_knowledge_state(scenario["topic"])
            self.assertEqual(state.confidence, scenario["expected_confidence"])
            self.assertIn("emotion", state.metadata)
            
    def test_emotional_feedback_processing(self):
        """Test dell'elaborazione del feedback emotivo."""
        # 1. Crea un'unità di apprendimento iniziale
        topic = "machine_learning"
        unit = LearningUnit(
            topic=topic,
            content="Introduction to machine learning concepts",
            source="course",
            confidence=ConfidenceLevel.MEDIUM,
            timestamp=datetime.now()
        )
        self.learner.add_learning_unit(unit)
        
        # 2. Simula feedback emotivi
        feedback_scenarios = [
            {
                "message": "This explanation really helped me understand!",
                "expected_emotion": "happy",
                "feedback_type": FeedbackType.POSITIVE
            },
            {
                "message": "I'm still confused about some parts...",
                "expected_emotion": "confused",
                "feedback_type": FeedbackType.NEGATIVE
            },
            {
                "message": "Now I get it, thanks to the examples!",
                "expected_emotion": "satisfied",
                "feedback_type": FeedbackType.POSITIVE
            }
        ]
        
        for scenario in feedback_scenarios:
            # Rileva l'emozione dal feedback
            emotion = self.emotional_core.detect_emotion(
                scenario["message"]
            )
            
            # Verifica l'emozione rilevata
            self.assertIsNotNone(emotion)
            
            # Integra il feedback con contesto emotivo
            self.learner.integrate_feedback(
                topic,
                scenario["feedback_type"],
                scenario["message"],
                metadata={"emotion": emotion}
            )
            
            # Aggiorna la conoscenza con il contesto emotivo
            self.knowledge_memory.store_knowledge(
                scenario["message"],
                {
                    "topic": topic,
                    "emotion": emotion.to_dict(),
                    "feedback_type": scenario["feedback_type"].value
                }
            )
        
        # 3. Verifica l'impatto complessivo
        final_state = self.learner.get_knowledge_state(topic)
        self.assertIsNotNone(final_state)
        
        # Controlla che ci siano più feedback positivi che negativi
        positive_count = sum(1 for s in feedback_scenarios 
                           if s["feedback_type"] == FeedbackType.POSITIVE)
        negative_count = sum(1 for s in feedback_scenarios 
                           if s["feedback_type"] == FeedbackType.NEGATIVE)
        self.assertGreater(positive_count, negative_count)
        
    def test_emotional_learning_adaptation(self):
        """Test dell'adattamento dell'apprendimento basato sulle emozioni."""
        # 1. Inizializza lo stato emotivo
        initial_message = "Let's start learning about data science!"
        initial_emotion = self.emotional_core.detect_emotion(initial_message)
        self.personality.adapt_to_emotion(self.emotional_core)
        
        # 2. Simula una sessione di apprendimento con adattamento emotivo
        learning_sequence = [
            {
                "message": "The statistics part is quite challenging...",
                "content": "Advanced statistical concepts",
                "expected_adaptation": "simplified"
            },
            {
                "message": "These visualizations make it much clearer!",
                "content": "Data visualization techniques",
                "expected_adaptation": "expanded"
            },
            {
                "message": "I'm really getting the hang of this!",
                "content": "Practical applications",
                "expected_adaptation": "advanced"
            }
        ]
        
        for i, step in enumerate(learning_sequence):
            # Aggiorna lo stato emotivo
            emotion = self.emotional_core.detect_emotion(step["message"])
            self.personality.adapt_to_emotion(self.emotional_core)
            
            # Crea unità di apprendimento adattata
            unit = LearningUnit(
                topic=f"data_science_{i+1}",
                content=step["content"],
                source="adaptive_session",
                confidence=ConfidenceLevel.MEDIUM,
                timestamp=datetime.now(),
                metadata={"adaptation": step["expected_adaptation"]}
            )
            
            # Adatta il contenuto in base all'emozione
            if emotion in ["frustrated", "confused"]:
                unit.content = f"Simplified: {unit.content}"
            elif emotion in ["happy", "satisfied"]:
                unit.content = f"Advanced: {unit.content}"
            
            # Memorizza l'unità
            self.learner.add_learning_unit(unit)
            
            # Verifica l'adattamento
            state = self.learner.get_knowledge_state(f"data_science_{i+1}")
            self.assertIn("adaptation", state.metadata)
            self.assertEqual(
                state.metadata["adaptation"],
                step["expected_adaptation"]
            )
            
        # 3. Verifica la progressione
        all_states = [
            self.learner.get_knowledge_state(f"data_science_{i+1}")
            for i in range(len(learning_sequence))
        ]
        
        # Controlla che ci sia una progressione nell'adattamento
        adaptations = [state.metadata["adaptation"] for state in all_states]
        self.assertEqual(adaptations[0], "simplified")
        self.assertEqual(adaptations[-1], "advanced")
