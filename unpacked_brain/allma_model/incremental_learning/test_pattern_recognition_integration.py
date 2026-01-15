"""
Test di integrazione del sistema di pattern recognition
"""

import unittest
import numpy as np
import time
from allma_model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem, Pattern
from allma_model.incremental_learning.pattern_validation import PatternValidator

class TestPatternRecognitionIntegration(unittest.TestCase):
    """Test di integrazione del sistema di pattern recognition"""
    
    def setUp(self):
        """Setup per i test"""
        self.system = PatternRecognitionSystem()
        
    def test_complete_pattern_lifecycle(self):
        """Test completo del ciclo di vita di un pattern"""
        # 1. Creazione e apprendimento iniziale
        features = [1.0, 0.0, 0.0]
        pattern = self.system.learn_pattern(features, "test_category")
        
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.category, "test_category")
        self.assertTrue(np.array_equal(pattern.features, np.array(features)))
        
        # Verifica la validazione iniziale
        self.assertTrue(len(pattern.validation_history) > 0)
        initial_validation = pattern.validation_history[-1]
        self.assertTrue(initial_validation.is_valid)
        
        # 2. Evoluzione del pattern
        # Crea più pattern simili per il clustering
        similar_patterns = [
            [0.95, 0.05, 0.0],
            [0.92, 0.08, 0.0],
            [0.88, 0.12, 0.0],
            [0.85, 0.15, 0.0]  # Aggiunto un altro pattern simile
        ]
        
        for feat in similar_patterns:
            self.system.learn_pattern(feat, "test_category")
            
        # Aggiungi un cluster diverso
        different_patterns = [
            [0.0, 1.0, 0.0],
            [0.05, 0.95, 0.0],
            [0.08, 0.92, 0.0]
        ]
        
        for feat in different_patterns:
            self.system.learn_pattern(feat, "test_category_2")
            
        evolved_features = [0.9, 0.1, 0.0]
        evolved_pattern = self.system.learn_pattern(evolved_features, "test_category")
        
        # Verifica che il pattern sia evoluto
        self.assertGreater(evolved_pattern.stability_score, 0.0)
        self.assertGreater(evolved_pattern.confidence, 0.0)
        
        # 3. Clustering e pattern correlati
        another_pattern = self.system.learn_pattern([0.8, 0.2, 0.0], "test_category")
        clusters = self.system.discover_pattern_clusters(
            min_samples=2,
            eps=0.3  # Aumentato il raggio di ricerca
        )
        
        self.assertGreater(len(clusters), 0)
        
        related = self.system.find_related_patterns(pattern.id)
        self.assertGreater(len(related), 0)
        
        # 4. Test di riconoscimento
        test_features = [0.95, 0.05, 0.0]
        recognition_results = self.system.recognize_pattern(test_features)
        
        self.assertTrue(len(recognition_results) > 0)
        best_match = recognition_results[0]
        self.assertGreater(best_match.similarity, 0.5)
        
        # 5. Test di ricerca per categoria
        category_patterns = self.system.find_patterns_by_category("test_category")
        self.assertGreater(len(category_patterns), 0)
        
        # 6. Test di stabilità nel tempo
        time.sleep(0.1)  # Simula il passaggio del tempo
        
        # Aggiorna più volte il pattern
        for _ in range(3):
            pattern = self.system.learn_pattern([0.85, 0.15, 0.0], "test_category")
            self.assertGreater(pattern.stability_score, 0.0)
            
        # Verifica la storia di validazione
        self.assertGreater(len(pattern.validation_history), 1)
        
        # 7. Test di qualità del pattern
        quality_scores = self.system.evaluate_pattern_quality(pattern.id)
        self.assertIsInstance(quality_scores, dict)
        self.assertTrue(any(score > 0.0 for score in quality_scores.values()),
                       f"Nessun punteggio positivo trovato in: {quality_scores}")
        
        # 8. Test di fusione dei pattern
        merged_pattern = self.system.merge_patterns([pattern.id, another_pattern.id])
        self.assertIsNotNone(merged_pattern)
        
        # Verifica che il pattern sia valido
        self.assertIsInstance(merged_pattern, Pattern)
        self.assertTrue(hasattr(merged_pattern, 'features'))
        self.assertTrue(hasattr(merged_pattern, 'category'))
        
    def test_pattern_evolution_under_stress(self):
        """Test del sistema sotto stress"""
        # 1. Creazione di molti pattern
        n_patterns = 50
        for i in range(n_patterns):
            features = [np.sin(i/10), np.cos(i/10), 0.0]
            self.system.learn_pattern(features, f"category_{i % 5}")
            
        # 2. Verifica delle prestazioni
        # Clustering
        start_time = time.time()
        clusters = self.system.discover_pattern_clusters()
        clustering_time = time.time() - start_time
        
        self.assertLess(clustering_time, 1.0)  # Non dovrebbe impiegare più di 1 secondo
        self.assertGreater(len(clusters), 0)
        
        # Riconoscimento
        start_time = time.time()
        test_features = [0.5, 0.5, 0.0]
        recognition_result = self.system.recognize_pattern(test_features)
        recognition_time = time.time() - start_time
        
        self.assertLess(recognition_time, 0.1)  # Non dovrebbe impiegare più di 0.1 secondi
        self.assertIsNotNone(recognition_result)
        
        # 3. Verifica della consistenza
        for category in range(5):
            patterns = self.system.find_patterns_by_category(f"category_{category}")
            self.assertEqual(len(patterns), n_patterns // 5)
            
        # 4. Test di robustezza
        # Aggiunta di rumore
        noisy_features = [0.5 + np.random.normal(0, 0.1) for _ in range(3)]
        noisy_pattern = self.system.learn_pattern(noisy_features, "noisy_category")
        
        # Il sistema dovrebbe gestire il rumore senza problemi
        self.assertIsNotNone(noisy_pattern)
        self.assertTrue(noisy_pattern.validation_history[-1].is_valid)
        
    def test_pattern_validation_integration(self):
        """Test dell'integrazione del sistema di validazione"""
        # 1. Pattern valido
        valid_pattern = self.system.learn_pattern([1.0, 0.0, 0.0], "test")
        self.assertTrue(valid_pattern.validation_history[-1].is_valid)
        
        # 2. Pattern con features non valide
        with self.assertRaises(ValueError):
            self.system.learn_pattern([], "test")  # Features vuote
            
        # 3. Pattern con bassa stabilità
        unstable_pattern = self.system.learn_pattern([0.5, 0.5, 0.0], "test")
        # Aggiorna con features molto diverse e frequentemente
        for _ in range(50):  # Aumentato ulteriormente il numero di aggiornamenti
            # Genera features completamente casuali
            features = np.random.random(3)
            # Normalizza le features per mantenere la somma = 1
            features = features / np.sum(features)
            # Aggiungi più rumore per rendere il pattern più instabile
            features += np.random.normal(0, 0.2, 3)  # Aumentato il rumore
            # Normalizza di nuovo
            features = np.clip(features, 0, 1)
            features = features / np.sum(features)
            
            unstable_pattern = self.system.learn_pattern(features.tolist(), "test")
            time.sleep(0.01)  # Piccola pausa per simulare il tempo reale
            
        self.assertLess(unstable_pattern.stability_score, 0.5)
        
        # 4. Pattern nel contesto
        # Crea un gruppo di pattern simili
        base_features = [1.0, 0.0, 0.0]
        for i in range(5):
            noise = np.random.normal(0, 0.01, 3)
            features = [base_features[j] + noise[j] for j in range(3)]
            pattern = self.system.learn_pattern(features, "context_test")
            self.assertTrue(pattern.validation_history[-1].is_valid)
            
        # Aggiungi un pattern molto diverso
        outlier_pattern = self.system.learn_pattern([0.0, 1.0, 0.0], "context_test")
        self.assertFalse(outlier_pattern.validation_history[-1].is_valid)
        
if __name__ == '__main__':
    unittest.main()
