"""Test dell'orchestratore di apprendimento"""

import unittest
from datetime import datetime
import tempfile
import os
import json
from learning_orchestrator import LearningOrchestrator, LearningEvent

class TestLearningOrchestrator(unittest.TestCase):
    """Test suite per l'orchestratore"""
    
    def setUp(self):
        """Setup per i test"""
        self.orchestrator = LearningOrchestrator(
            emotional_social_weight=0.4,
            meta_learning_weight=0.3,
            pattern_weight=0.3
        )
        
    def test_initial_state(self):
        """Verifica lo stato iniziale"""
        self.assertEqual(self.orchestrator.weights["emotional_social"], 0.4)
        self.assertEqual(self.orchestrator.weights["meta_learning"], 0.3)
        self.assertEqual(self.orchestrator.weights["pattern"], 0.3)
        self.assertEqual(len(self.orchestrator.learning_history), 0)
        
    def test_process_learning_event(self):
        """Verifica il processamento di un evento"""
        content = "test content"
        context = {
            "valence": 0.7,
            "arousal": 0.3,
            "dominance": 0.6,
            "formal": 1.0,
            "cooperative": 1.0
        }
        
        result = self.orchestrator.process_learning_event(
            content=content,
            context=context,
            agent_id="test_agent"
        )
        
        # Verifica il risultato
        self.assertIn("success_level", result)
        self.assertIn("patterns", result)
        self.assertIn("strategy", result)
        self.assertIn("emotional_state", result)
        self.assertIn("behavior", result)
        
        # Verifica che l'evento sia stato memorizzato
        self.assertEqual(len(self.orchestrator.learning_history), 1)
        
    def test_provide_feedback(self):
        """Verifica la gestione del feedback"""
        # Crea un evento
        self.orchestrator.process_learning_event(
            content="test content",
            context={
                "valence": 0.7,
                "arousal": 0.3,
                "dominance": 0.6
            }
        )
        
        # Fornisci feedback
        feedback = {
            "emotional_social": {
                "emotional": {
                    "valence": 0.8,
                    "arousal": 0.4,
                    "dominance": 0.7,
                    "effectiveness": 0.9
                },
                "social": {
                    "relationship": 0.8,
                    "trust": 0.9,
                    "effectiveness": 0.8
                }
            },
            "meta_learning": {
                "effectiveness": 0.85
            },
            "pattern": {
                "accuracy": 0.9,
                "relevance": 0.8
            }
        }
        
        self.orchestrator.provide_feedback(0, feedback)
        
        # Verifica che il feedback sia stato memorizzato
        event = self.orchestrator.learning_history[0]
        self.assertEqual(event.feedback, feedback)
        
    def test_analyze_learning_trends(self):
        """Verifica l'analisi dei trend"""
        # Crea una serie di eventi
        contexts = [
            {"valence": 0.6 + i * 0.05, "arousal": 0.4, "dominance": 0.5}
            for i in range(5)
        ]
        
        for context in contexts:
            self.orchestrator.process_learning_event(
                content="test content",
                context=context
            )
            
        trends = self.orchestrator.analyze_learning_trends()
        
        # Verifica i risultati
        self.assertIn("average_success", trends)
        self.assertIn("trend", trends)
        self.assertIn("patterns", trends)
        self.assertIn("strategies", trends)
        
    def test_state_persistence(self):
        """Verifica il salvataggio e caricamento dello stato"""
        # Crea alcuni eventi
        self.orchestrator.process_learning_event(
            content="test content 1",
            context={"valence": 0.7}
        )
        self.orchestrator.process_learning_event(
            content="test content 2",
            context={"valence": 0.8}
        )
        
        # Salva lo stato
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.orchestrator.save_state(tmp.name)
            
            # Crea un nuovo orchestratore e carica lo stato
            new_orchestrator = LearningOrchestrator()
            new_orchestrator.load_state(tmp.name)
            
            # Verifica che lo stato sia stato caricato correttamente
            self.assertEqual(
                len(new_orchestrator.learning_history),
                len(self.orchestrator.learning_history)
            )
            self.assertEqual(
                new_orchestrator.weights,
                self.orchestrator.weights
            )
            
        # Pulisci
        os.unlink(tmp.name)
        
    def test_success_calculation(self):
        """Verifica il calcolo del successo"""
        patterns = ["pattern1", "pattern2"]
        meta_strategy = "test_strategy"
        emotional_state = type('obj', (object,), {
            'valence': 0.7,
            'arousal': 0.3,
            'dominance': 0.6
        })
        
        success = self.orchestrator._calculate_success(
            patterns=patterns,
            meta_strategy=meta_strategy,
            emotional_state=emotional_state,
            meta_success=0.8
        )
        
        # Verifica che il successo sia nel range corretto
        self.assertTrue(0 <= success <= 1)
        
if __name__ == '__main__':
    unittest.main()
