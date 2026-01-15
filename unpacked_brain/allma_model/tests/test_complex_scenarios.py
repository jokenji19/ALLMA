"""Test di scenari complessi che coinvolgono più componenti di ALLMA."""

import unittest
from datetime import datetime, timedelta
import json
from allma_model.core.allma_core import ALLMACore
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.emotional_system.emotional_core import EmotionalCore
from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.memory_system.knowledge_memory import KnowledgeMemory
from allma_model.core.response_generator import ResponseGenerator
from allma_model.learning_system.incremental_learning import IncrementalLearner
from allma_model.core.personality import Personality
from allma_model.response_system.contextual_response import ResponseContext, TechnicalLevel
from allma_model.core.learning_preferences import LearningPreference, LearningStyle

class TestComplexScenarios(unittest.TestCase):
    """Test di scenari complessi che coinvolgono più componenti."""
    
    def setUp(self):
        """Setup per i test."""
        self.db_path = "Model/data/test.db"
        self.knowledge_memory = KnowledgeMemory(self.db_path)
        self.response_generator = ResponseGenerator(self.knowledge_memory)
        self.allma = ALLMACore(
            knowledge_memory=self.knowledge_memory,
            response_generator=self.response_generator,
            db_path=self.db_path
        )
        self.test_user_id = "test_user"
        self.current_time = datetime.now()
        self.default_preferences = LearningPreference(
            primary_style=LearningStyle.BALANCED,
            technical_level=3,
            confidence=0.7,
            metadata={
                "detail_level": 0.7,
                "examples_vs_theory": 0.6
            }
        )
        
    def test_long_term_project_evolution(self):
        """
        Test di un progetto a lungo termine che evolve nel tempo.
        Questo test simula un progetto che dura settimane, con:
        - Multiple interazioni
        - Cambiamenti emotivi
        - Apprendimento incrementale
        - Adattamento della personalità
        """
        # 1. Crea un nuovo progetto
        project_name = f"Complex AI System {datetime.now().strftime('%Y%m%d%H%M%S')}"
        project_description = "A complex AI system development project"
        project_id = self.allma.project_tracker.create_project(
            user_id=self.test_user_id,
            name=project_name,
            description=project_description
        )
        
        # Simula una serie di interazioni su più "giorni"
        interactions = [
            {
                "day": 1,
                "message": "I want to start working on the AI system architecture",
                "emotion": "excited",
                "expected_topics": ["architecture", "planning"]
            },
            {
                "day": 3,
                "message": "We're having issues with the data pipeline",
                "emotion": "frustrated",
                "expected_topics": ["data", "pipeline", "issues"]
            },
            {
                "day": 7,
                "message": "The initial tests are showing promising results",
                "emotion": "happy",
                "expected_topics": ["testing", "results"]
            }
        ]
        
        for interaction in interactions:
            # Simula il passaggio del tempo
            current_time = self.current_time + timedelta(days=interaction["day"])
            
            # Rileva l'emozione
            emotional_state = self.allma.emotional_core.detect_emotion(
                interaction["message"],
                context={"user_id": self.test_user_id}
            )
            self.assertIsNotNone(emotional_state)
            
            # Memorizza l'interazione
            conversation_id = self.allma.conversational_memory.store_conversation(
                user_id=self.test_user_id,
                content=interaction["message"],
                metadata={
                    "project_id": project_id,
                    "timestamp": current_time.isoformat(),
                    "emotion": emotional_state
                }
            )
            
            # Crea il contesto della risposta
            response_context = ResponseContext(
                user_id=self.test_user_id,
                current_topic=interaction["expected_topics"][0],
                technical_level=TechnicalLevel.INTERMEDIATE,
                conversation_history=[interaction["message"]],
                user_preferences=self.default_preferences
            )
            
            # Genera una risposta
            response = self.allma.response_generator.generate_response(
                query=interaction["message"],
                context=response_context
            )
            self.assertIsNotNone(response)
            
            # Memorizza la risposta
            self.allma.conversational_memory.store_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response,
                metadata={
                    "project_id": project_id,
                    "timestamp": current_time.isoformat()
                }
            )
            
            # Applica l'apprendimento
            self.allma.incremental_learner.learn_from_interaction(
                interaction={
                    "input": interaction["message"],
                    "response": response,
                    "feedback": "positive"
                },
                user_id=self.test_user_id
            )
        
        # Verifica lo stato finale del progetto
        project_summary = self.allma.project_tracker.get_project_summary(project_id)
        self.assertEqual(project_summary["name"], project_name)
        self.assertEqual(project_summary["description"], project_description)
        self.assertEqual(project_summary["user_id"], self.test_user_id)
        self.assertEqual(project_summary["status"], "active")
        
    def test_emotional_learning_adaptation(self):
        """
        Test dell'adattamento del sistema alle emozioni dell'utente.
        Verifica come il sistema apprende e si adatta in base alle
        emozioni mostrate durante le interazioni.
        """
        # Sequenza di messaggi emotivi
        emotional_sequence = [
            ("I'm really excited about this project!", "joy"),
            ("This is so frustrating...", "anger"),
            ("I'm worried we won't meet the deadline", "fear"),
            ("We did it! The system is working!", "joy")
        ]
        
        emotional_states = []
        for message, expected_emotion in emotional_sequence:
            # Rileva l'emozione
            emotional_state = self.allma.emotional_core.detect_emotion(
                message,
                context={"user_id": self.test_user_id}
            )
            emotional_states.append(emotional_state)
            
            # Crea il contesto della risposta
            response_context = ResponseContext(
                user_id=self.test_user_id,
                current_topic="project_status",
                technical_level=TechnicalLevel.INTERMEDIATE,
                conversation_history=[message],
                user_preferences=self.default_preferences
            )
            
            # Genera e adatta la risposta in base all'emozione
            response = self.allma.response_generator.generate_response(
                query=message,
                context=response_context
            )
            
            # Aggiorna la personalità con l'emozione rilevata
            if isinstance(emotional_state, str):
                emotions = {emotional_state: 1.0}
            else:
                emotions = {
                    emotional_state.primary_emotion: emotional_state.confidence,
                    **emotional_state.secondary_emotions
                }
            self.allma.personality.update_personality(message, emotions)
            
            # Memorizza la conversazione
            self.allma.conversational_memory.store_conversation(
                user_id=self.test_user_id,
                content=message,
                metadata={"emotions": emotions}
            )
            
        # Verifica che il sistema abbia rilevato correttamente le emozioni
        self.assertEqual(len(emotional_states), len(emotional_sequence))
        
        # Verifica che il sistema si sia adattato alle emozioni
        final_style = self.allma.personality.get_interaction_style()
        self.assertIsNotNone(final_style)
        
    def test_knowledge_integration(self):
        """
        Test dell'integrazione della conoscenza attraverso multiple fonti.
        Verifica come il sistema integra conoscenza da:
        - Conversazioni passate
        - Feedback dell'utente
        - Documenti di progetto
        """
        # Simula l'acquisizione di conoscenza da diverse fonti
        knowledge_sources = [
            {
                "type": "conversation",
                "content": "The system should use TensorFlow for deep learning",
                "metadata": {"topic": "technology_stack"}
            },
            {
                "type": "document",
                "content": "Project requirements include real-time processing",
                "metadata": {"topic": "requirements"}
            },
            {
                "type": "feedback",
                "content": "The response time needs to be under 100ms",
                "metadata": {"topic": "performance"}
            }
        ]
        
        for source in knowledge_sources:
            # Memorizza la conoscenza nel KnowledgeMemory
            self.knowledge_memory.store_knowledge(
                content=source["content"],
                metadata=source["metadata"]
            )
            
            # Memorizza la conoscenza nel ConversationalMemory
            conversation_id = self.allma.conversational_memory.store_conversation(
                user_id=self.test_user_id,
                content=source["content"],
                metadata=source["metadata"]
            )
            
            # Apprende dalla fonte
            self.allma.incremental_learner.learn_from_interaction(
                interaction={
                    "input": source["content"],
                    "response": "Acknowledged",
                    "feedback": "positive"
                },
                user_id=self.test_user_id
            )
            
        # Verifica l'integrazione della conoscenza
        test_query = "What are the key technical requirements?"
        response_context = ResponseContext(
            user_id=self.test_user_id,
            current_topic="technical_requirements",
            technical_level=TechnicalLevel.INTERMEDIATE,
            conversation_history=[s["content"] for s in knowledge_sources],
            user_preferences=self.default_preferences
        )
        
        response = self.allma.response_generator.generate_response(
            query=test_query,
            context=response_context
        )
        
        self.assertIsNotNone(response)
        self.assertIn("TensorFlow", response)

if __name__ == '__main__':
    unittest.main()
