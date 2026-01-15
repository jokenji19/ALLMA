import unittest
from datetime import datetime, timedelta
from .metacognition_system import (
    MetaCognitionSystem, MetaCognitiveState, CognitiveStrategy,
    MetaCognitiveInsight, LearningProgress
)

class TestMetaCognitionSystem(unittest.TestCase):
    def setUp(self):
        self.meta = MetaCognitionSystem(max_insights=5)
        
    def test_monitor_cognitive_process(self):
        """Testa il monitoraggio dei processi cognitivi"""
        process_data = {
            "complexity": 0.8,
            "time_pressure": 0.3,
            "accuracy": 0.7,
            "consistency": 0.8,
            "completeness": 0.9,
            "speed": 0.6,
            "resource_usage": 0.4
        }
        
        insight = self.meta.monitor_cognitive_process(process_data)
        
        self.assertIsInstance(insight, MetaCognitiveInsight)
        self.assertEqual(insight.state, MetaCognitiveState.MONITORING)
        self.assertEqual(insight.strategy, CognitiveStrategy.DEEP_PROCESSING)
        self.assertTrue(0 <= insight.confidence <= 1)
        self.assertTrue(0 <= insight.effectiveness <= 1)
        
    def test_adapt_strategy(self):
        """Testa l'adattamento della strategia"""
        # Test con feedback positivo
        strategy = self.meta.adapt_strategy(0.9)
        self.assertIsInstance(strategy, CognitiveStrategy)
        self.assertEqual(self.meta.current_state, MetaCognitiveState.ADAPTING)
        
        # Verifica che l'efficacia sia stata aggiornata
        effectiveness = self.meta.strategy_effectiveness[strategy]
        self.assertGreater(effectiveness, 0.5)  # Il valore iniziale era 0.5
        
    def test_reflect_on_learning(self):
        """Testa la riflessione sull'apprendimento"""
        topic = "test_topic"
        time_spent = 1.5
        outcome = 0.8
        
        progress = self.meta.reflect_on_learning(topic, time_spent, outcome)
        
        self.assertIsInstance(progress, LearningProgress)
        self.assertEqual(progress.topic, topic)
        self.assertEqual(progress.time_spent, time_spent)
        self.assertEqual(progress.outcomes, [outcome])
        self.assertEqual(progress.understanding_level, outcome)
        self.assertEqual(self.meta.current_state, MetaCognitiveState.REFLECTING)
        
    def test_plan_learning_strategy(self):
        """Testa la pianificazione della strategia di apprendimento"""
        # Prima aggiungi alcuni dati di apprendimento
        topic = "test_topic"
        self.meta.reflect_on_learning(topic, 1.0, 0.7)
        
        plan = self.meta.plan_learning_strategy(topic)
        
        self.assertIsInstance(plan, dict)
        self.assertEqual(plan["topic"], topic)
        self.assertTrue(0 <= plan["understanding_gap"] <= 1)
        self.assertTrue(plan["time_efficiency"] >= 0)
        self.assertIsInstance(plan["recommended_strategies"], list)
        self.assertTrue(len(plan["recommended_strategies"]) > 0)
        self.assertEqual(self.meta.current_state, MetaCognitiveState.PLANNING)
        
    def test_get_insights(self):
        """Testa il recupero degli insight"""
        # Aggiungi alcuni insight
        process_data = {
            "complexity": 0.8,
            "accuracy": 0.7,
            "consistency": 0.8,
            "completeness": 0.9,
            "speed": 0.6,
            "resource_usage": 0.4
        }
        
        for _ in range(3):
            self.meta.monitor_cognitive_process(process_data)
            
        insights = self.meta.get_insights(n=2)
        
        self.assertIsInstance(insights, list)
        self.assertEqual(len(insights), 2)
        self.assertIsInstance(insights[0], MetaCognitiveInsight)
        
    def test_strategy_selection(self):
        """Testa la selezione della strategia"""
        # Test per DEEP_PROCESSING
        process_data = {"complexity": 0.8, "time_pressure": 0.3}
        strategy = self.meta._select_best_strategy(process_data)
        self.assertEqual(strategy, CognitiveStrategy.DEEP_PROCESSING)
        
        # Test per SURFACE_PROCESSING
        process_data = {"complexity": 0.5, "time_pressure": 0.8}
        strategy = self.meta._select_best_strategy(process_data)
        self.assertEqual(strategy, CognitiveStrategy.SURFACE_PROCESSING)
        
        # Test per ACTIVE_RECALL
        process_data = {"complexity": 0.5, "time_pressure": 0.5}
        strategy = self.meta._select_best_strategy(process_data)
        self.assertEqual(strategy, CognitiveStrategy.ACTIVE_RECALL)
        
    def test_confidence_evaluation(self):
        """Testa la valutazione della confidenza"""
        process_data = {
            "accuracy": 0.8,
            "consistency": 0.7,
            "completeness": 0.9
        }
        
        confidence = self.meta._evaluate_confidence(process_data)
        self.assertEqual(confidence, 0.8)  # (0.8 + 0.7 + 0.9) / 3
        
    def test_effectiveness_evaluation(self):
        """Testa la valutazione dell'efficacia"""
        process_data = {
            "accuracy": 1.0,
            "speed": 1.0,
            "resource_usage": 0.0
        }
        
        effectiveness = self.meta._evaluate_effectiveness(process_data)
        self.assertEqual(effectiveness, 1.0)  # Massima efficacia
        
    def test_learning_progress_accumulation(self):
        """Testa l'accumulazione del progresso di apprendimento"""
        topic = "test_topic"
        
        # Aggiungi multipli risultati di apprendimento
        self.meta.reflect_on_learning(topic, 1.0, 0.6)
        self.meta.reflect_on_learning(topic, 1.0, 0.8)
        
        progress = self.meta.learning_progress[topic]
        self.assertEqual(progress.time_spent, 2.0)
        self.assertEqual(progress.understanding_level, 0.7)  # Media di 0.6 e 0.8
        
if __name__ == '__main__':
    unittest.main()
