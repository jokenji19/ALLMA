import unittest
from datetime import datetime
import torch
import torch.nn as nn
import numpy as np
from performance_optimizer import AdvancedOptimizer, OptimizationMetrics

class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(10, 2)
        
    def forward(self, x):
        return self.linear(x)

class TestAdvancedOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = AdvancedOptimizer()
        self.model = SimpleModel()
        
    def test_initial_optimization(self):
        """Test dell'ottimizzazione iniziale"""
        metrics = OptimizationMetrics(
            accuracy=0.8,
            response_time=0.1,
            memory_efficiency=0.7,
            learning_rate=0.001,
            timestamp=datetime.now()
        )
        
        params = self.optimizer.optimize_performance(self.model, metrics)
        self.assertIsInstance(params, dict)
        self.assertIn('learning_rate', params)
        self.assertIn('batch_size', params)
        
    def test_trend_analysis(self):
        """Test dell'analisi dei trend"""
        # Simula un miglioramento dell'accuratezza
        for i in range(10):
            metrics = OptimizationMetrics(
                accuracy=0.8 + i * 0.02,
                response_time=0.1,
                memory_efficiency=0.7,
                learning_rate=0.001,
                timestamp=datetime.now()
            )
            self.optimizer.metrics_history.append(metrics)
            
        trend = self.optimizer._analyze_trend([m.accuracy for m in self.optimizer.metrics_history])
        self.assertGreater(trend, 0, "Il trend dovrebbe essere positivo")
        
    def test_parameter_optimization(self):
        """Test dell'ottimizzazione dei parametri"""
        # Simula un peggioramento significativo delle prestazioni
        initial_metrics = OptimizationMetrics(
            accuracy=0.8,
            response_time=0.1,
            memory_efficiency=0.7,
            learning_rate=0.001,
            timestamp=datetime.now()
        )
        self.optimizer.optimize_performance(self.model, initial_metrics)
        
        # Aggiungi una metrica con prestazioni peggiori
        worse_metrics = OptimizationMetrics(
            accuracy=0.6,  # Calo significativo dell'accuratezza
            response_time=0.2,
            memory_efficiency=0.5,
            learning_rate=0.001,
            timestamp=datetime.now()
        )
        params = self.optimizer.optimize_performance(self.model, worse_metrics)
        
        # Verifica che i parametri siano stati adattati
        self.assertLess(params['learning_rate'], 0.001, 
                       "Il learning rate dovrebbe diminuire con prestazioni in peggioramento")
        
    def test_optimization_stats(self):
        """Test delle statistiche di ottimizzazione"""
        # Aggiungi alcune metriche
        for i in range(5):
            metrics = OptimizationMetrics(
                accuracy=0.8,
                response_time=0.1,
                memory_efficiency=0.7,
                learning_rate=0.001,
                timestamp=datetime.now()
            )
            self.optimizer.metrics_history.append(metrics)
            
        stats = self.optimizer.get_optimization_stats()
        self.assertIn('avg_accuracy', stats)
        self.assertIn('avg_response_time', stats)
        self.assertIn('avg_memory_efficiency', stats)
        
    def test_learning_rate_bounds(self):
        """Test dei limiti del learning rate"""
        # Test del limite inferiore
        metrics_low = OptimizationMetrics(
            accuracy=0.1,
            response_time=0.5,
            memory_efficiency=0.3,
            learning_rate=1e-6,
            timestamp=datetime.now()
        )
        params_low = self.optimizer.optimize_performance(self.model, metrics_low)
        self.assertGreaterEqual(params_low['learning_rate'], self.optimizer.min_learning_rate)
        
        # Test del limite superiore
        metrics_high = OptimizationMetrics(
            accuracy=0.99,
            response_time=0.01,
            memory_efficiency=0.99,
            learning_rate=1e-1,
            timestamp=datetime.now()
        )
        params_high = self.optimizer.optimize_performance(self.model, metrics_high)
        self.assertLessEqual(params_high['learning_rate'], self.optimizer.max_learning_rate)

if __name__ == '__main__':
    unittest.main()
