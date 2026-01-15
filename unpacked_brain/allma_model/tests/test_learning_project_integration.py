"""Test di integrazione tra il sistema di apprendimento e il tracciamento dei progetti."""

import unittest
from datetime import datetime, timedelta
import json
import os
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.learning_system.incremental_learning import (
    IncrementalLearner,
    LearningUnit,
    FeedbackType,
    ConfidenceLevel
)
from allma_model.core.response_generator import ResponseGenerator
from allma_model.memory_system.knowledge_memory import KnowledgeMemory

class TestLearningProjectIntegration(unittest.TestCase):
    """Test di integrazione tra apprendimento e progetti."""
    
    def setUp(self):
        """Setup per i test."""
        self.test_dir = "Model/data/test"
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, "test_integration.db")
        self.test_user_id = "test_user"
        self.project_tracker = ProjectTracker(self.db_path)
        self.learner = IncrementalLearner()
        self.knowledge_memory = KnowledgeMemory(self.db_path)
        self.response_generator = ResponseGenerator(self.knowledge_memory)
        
    def tearDown(self):
        """Cleanup dopo i test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
            
    def test_project_based_learning(self):
        """Test dell'apprendimento basato sui progetti."""
        # 1. Crea un nuovo progetto
        project_name = "Machine Learning API"
        project_description = "Development of a REST API for ML models"
        project_id = self.project_tracker.create_project(
            self.test_user_id,
            project_name,
            project_description,
            {"domain": "machine_learning", "type": "api"}
        )
        
        # 2. Simula l'apprendimento durante lo sviluppo del progetto
        learning_stages = [
            {
                "topic": "api_design",
                "content": "Best practices for REST API design in ML context",
                "confidence": ConfidenceLevel.MEDIUM,
                "feedback": [(FeedbackType.POSITIVE, "Clear structure")]
            },
            {
                "topic": "model_deployment",
                "content": "Techniques for deploying ML models in production",
                "confidence": ConfidenceLevel.HIGH,
                "feedback": [(FeedbackType.POSITIVE, "Practical approach")]
            },
            {
                "topic": "performance_optimization",
                "content": "Methods to optimize API performance with ML models",
                "confidence": ConfidenceLevel.LOW,
                "feedback": [(FeedbackType.NEGATIVE, "Needs more detail")]
            }
        ]
        
        for stage in learning_stages:
            # Aggiungi unità di apprendimento
            unit = LearningUnit(
                topic=stage["topic"],
                content=stage["content"],
                source="project_work",
                confidence=stage["confidence"],
                timestamp=datetime.now()
            )
            self.learner.add_learning_unit(unit)
            
            # Integra feedback
            for feedback_type, feedback_content in stage["feedback"]:
                self.learner.integrate_feedback(
                    stage["topic"],
                    feedback_type,
                    feedback_content
                )
            
            # Memorizza la conoscenza
            self.knowledge_memory.store_knowledge(
                stage["content"],
                {
                    "project_id": project_id,
                    "topic": stage["topic"],
                    "confidence": stage["confidence"].value
                }
            )
            
            # Aggiorna il progetto
            self.project_tracker.update_project_status(
                project_id,
                f"Completed learning stage: {stage['topic']}",
                {"last_topic": stage["topic"]}
            )
            
        # 3. Verifica l'integrazione
        # Controlla lo stato del progetto
        project_summary = self.project_tracker.get_project_summary(project_id)
        self.assertEqual(project_summary["name"], project_name)
        self.assertEqual(
            project_summary["metadata"]["last_topic"],
            "performance_optimization"
        )
        
        # Verifica l'apprendimento
        for stage in learning_stages:
            state = self.learner.get_knowledge_state(stage["topic"])
            self.assertIsNotNone(state)
            
            # Calcola il livello di confidenza atteso dopo il feedback
            expected_confidence = stage["confidence"]
            for feedback_type, _ in stage["feedback"]:
                if feedback_type == FeedbackType.POSITIVE:
                    if expected_confidence.value < ConfidenceLevel.HIGH.value:
                        expected_confidence = ConfidenceLevel(expected_confidence.value + 1)
                else:
                    if expected_confidence.value > ConfidenceLevel.LOW.value:
                        expected_confidence = ConfidenceLevel(expected_confidence.value - 1)
            
            self.assertEqual(state.confidence, expected_confidence)
            
        # Verifica la conoscenza memorizzata
        results = self.knowledge_memory.get_knowledge_for_text("ML models")
        self.assertTrue(len(results) > 0)
        
    def test_adaptive_learning_in_project(self):
        """Test dell'apprendimento adattivo durante un progetto."""
        # 1. Crea un progetto con focus sull'apprendimento
        project_id = self.project_tracker.create_project(
            self.test_user_id,
            "Adaptive Learning System",
            "System that adapts to user learning patterns",
            {"focus": "adaptive_learning"}
        )
        
        # 2. Simula sessioni di apprendimento con adattamento
        learning_sessions = [
            {
                "initial_confidence": ConfidenceLevel.LOW,
                "content": "Basic concepts of adaptive learning",
                "feedback": FeedbackType.POSITIVE,
                "expected_confidence": ConfidenceLevel.MEDIUM
            },
            {
                "initial_confidence": ConfidenceLevel.MEDIUM,
                "content": "Advanced adaptation strategies",
                "feedback": FeedbackType.POSITIVE,
                "expected_confidence": ConfidenceLevel.HIGH
            }
        ]
        
        for i, session in enumerate(learning_sessions):
            # Crea unità di apprendimento
            unit = LearningUnit(
                topic=f"adaptive_learning_{i+1}",
                content=session["content"],
                source="project_session",
                confidence=session["initial_confidence"],
                timestamp=datetime.now()
            )
            self.learner.add_learning_unit(unit)
            
            # Simula feedback e adattamento
            self.learner.integrate_feedback(
                f"adaptive_learning_{i+1}",
                session["feedback"],
                "Session feedback"
            )
            
            # Verifica l'adattamento
            state = self.learner.get_knowledge_state(f"adaptive_learning_{i+1}")
            self.assertGreaterEqual(
                state.confidence.value,
                session["initial_confidence"].value
            )
            
            # Aggiorna il progetto
            self.project_tracker.update_project_status(
                project_id,
                f"Completed adaptive session {i+1}",
                {"session": i+1, "confidence": state.confidence.value}
            )
            
        # 3. Verifica finale
        project_summary = self.project_tracker.get_project_summary(project_id)
        self.assertEqual(project_summary["metadata"]["session"], 2)
        self.assertGreater(
            float(project_summary["metadata"]["confidence"]),
            ConfidenceLevel.LOW.value
        )
        
    def test_project_knowledge_transfer(self):
        """Test del trasferimento di conoscenza tra progetti."""
        # 1. Crea due progetti correlati
        project1_id = self.project_tracker.create_project(
            self.test_user_id,
            "ML Model Development",
            "Development of core ML models",
            {"domain": "machine_learning"}
        )
        
        project2_id = self.project_tracker.create_project(
            self.test_user_id,
            "ML Model API",
            "API for the ML models",
            {"domain": "machine_learning", "related_to": project1_id}
        )
        
        # 2. Simula l'acquisizione di conoscenza nel primo progetto
        model_knowledge = LearningUnit(
            topic="ml_models",
            content="Core concepts of ML model development",
            source="project_work",
            confidence=ConfidenceLevel.HIGH,
            timestamp=datetime.now()
        )
        self.learner.add_learning_unit(model_knowledge)
        
        # Memorizza la conoscenza con riferimento al progetto
        self.knowledge_memory.store_knowledge(
            model_knowledge.content,
            {
                "project_id": project1_id,
                "topic": "ml_models",
                "transferable": True
            }
        )
        
        # 3. Simula il trasferimento al secondo progetto
        # Cerca conoscenza rilevante dal primo progetto
        related_knowledge = self.knowledge_memory.get_knowledge_for_text("ML model")
        self.assertTrue(len(related_knowledge) > 0)
        
        # Applica la conoscenza al secondo progetto
        for knowledge in related_knowledge:
            self.knowledge_memory.store_knowledge(
                knowledge,
                {
                    "project_id": project2_id,
                    "topic": "ml_models",
                    "transferred_from": project1_id
                }
            )
            
        # 4. Verifica il trasferimento
        # Controlla che entrambi i progetti abbiano la conoscenza
        project1_knowledge = self.knowledge_memory.get_knowledge_for_text("ML model")
        project2_knowledge = self.knowledge_memory.get_knowledge_for_text("ML model")
        
        self.assertTrue(len(project1_knowledge) > 0)
        self.assertTrue(len(project2_knowledge) > 0)
        
        # Verifica che il secondo progetto abbia il riferimento al primo
        project2_summary = self.project_tracker.get_project_summary(project2_id)
        self.assertEqual(
            project2_summary["metadata"]["related_to"],
            project1_id
        )
