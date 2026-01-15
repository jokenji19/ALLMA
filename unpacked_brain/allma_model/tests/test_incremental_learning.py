"""Test per il sistema di apprendimento incrementale."""

import unittest
from datetime import datetime
from allma_model.learning_system.incremental_learning import (
    IncrementalLearner,
    LearningUnit,
    FeedbackType,
    ConfidenceLevel,
    KnowledgeState
)

class TestIncrementalLearning(unittest.TestCase):
    """Test per IncrementalLearner."""
    
    def setUp(self):
        """Setup per i test."""
        self.learner = IncrementalLearner()
        self.test_user = "test_user_123"
        
    def test_knowledge_acquisition(self):
        """Test dell'acquisizione di conoscenza."""
        # Crea unità di apprendimento
        unit = LearningUnit(
            topic="python exceptions",
            content="Le eccezioni in Python sono gestite con try/except",
            source="user_interaction",
            confidence=ConfidenceLevel.MEDIUM,
            timestamp=datetime.now()
        )
        
        # Aggiungi l'unità
        success = self.learner.add_learning_unit(unit)
        self.assertTrue(success)
        
        # Verifica che sia stata memorizzata
        state = self.learner.get_knowledge_state("python exceptions")
        self.assertIsNotNone(state)
        self.assertEqual(state.confidence, ConfidenceLevel.MEDIUM)
        
    def test_feedback_integration(self):
        """Test dell'integrazione del feedback."""
        # Crea unità iniziale
        unit = LearningUnit(
            topic="python decorators",
            content="I decoratori sono funzioni che modificano altre funzioni",
            source="documentation",
            confidence=ConfidenceLevel.LOW,
            timestamp=datetime.now()
        )
        self.learner.add_learning_unit(unit)
        
        # Aggiungi feedback positivo
        feedback = [
            (FeedbackType.POSITIVE, "Spiegazione chiara"),
            (FeedbackType.POSITIVE, "Molto utile"),
            (FeedbackType.NEGATIVE, "Mancano esempi")
        ]
        
        for type_, content in feedback:
            self.learner.integrate_feedback(
                "python decorators",
                type_,
                content
            )
            
        # Verifica l'impatto del feedback
        state = self.learner.get_knowledge_state("python decorators")
        self.assertGreater(state.confidence.value, ConfidenceLevel.LOW.value)
        self.assertIn("esempi", state.improvement_areas)
        
    def test_knowledge_refinement(self):
        """Test del raffinamento della conoscenza."""
        # Aggiungi conoscenza iniziale
        initial_unit = LearningUnit(
            topic="python generators",
            content="I generators sono funzioni che usano yield",
            source="user_interaction",
            confidence=ConfidenceLevel.LOW,
            timestamp=datetime.now()
        )
        self.learner.add_learning_unit(initial_unit)
        
        # Aggiungi conoscenza raffinata
        refined_unit = LearningUnit(
            topic="python generators",
            content="I generators sono iteratori che generano valori al volo",
            source="expert_review",
            confidence=ConfidenceLevel.HIGH,
            timestamp=datetime.now()
        )
        self.learner.add_learning_unit(refined_unit)
        
        # Verifica il raffinamento
        state = self.learner.get_knowledge_state("python generators")
        self.assertEqual(state.confidence, ConfidenceLevel.HIGH)
        self.assertIn("iteratori", state.content.lower())
        
    def test_knowledge_retrieval(self):
        """Test del recupero della conoscenza."""
        # Aggiungi diverse unità
        topics = ["python lists", "python tuples", "python sets"]
        for topic in topics:
            unit = LearningUnit(
                topic=topic,
                content=f"Informazioni su {topic}",
                source="documentation",
                confidence=ConfidenceLevel.MEDIUM,
                timestamp=datetime.now()
            )
            self.learner.add_learning_unit(unit)
            
        # Cerca conoscenza correlata
        results = self.learner.find_related_knowledge("python collections")
        self.assertGreater(len(results), 0)
        self.assertTrue(any("lists" in r.topic for r in results))
        
    def test_edge_cases(self):
        """Test dei casi limite."""
        # Test con topic vuoto
        unit = LearningUnit(
            topic="",
            content="Contenuto test",
            source="test",
            confidence=ConfidenceLevel.LOW,
            timestamp=datetime.now()
        )
        success = self.learner.add_learning_unit(unit)
        self.assertFalse(success)
        
        # Test con contenuto vuoto
        unit = LearningUnit(
            topic="test topic",
            content="",
            source="test",
            confidence=ConfidenceLevel.LOW,
            timestamp=datetime.now()
        )
        success = self.learner.add_learning_unit(unit)
        self.assertFalse(success)
        
        # Test recupero topic inesistente
        state = self.learner.get_knowledge_state("nonexistent")
        self.assertIsNone(state)
        
if __name__ == '__main__':
    unittest.main()
